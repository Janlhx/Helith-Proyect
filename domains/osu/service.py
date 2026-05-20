import logging
import json
import re
from typing import Dict, Any, List, Tuple
from core.llm.pool import llm_pool
from core.llm.prompts import HELITH_PERSONALITY
from domains.osu.client import osu_api_client
from domains.osu.models import OsuSnapshot
from domains.osu.repository import osu_repo
from domains.osu.ml_model import (
    calculate_improvement_indicator,
    predict_days_to_rank
)

logger = logging.getLogger("helith.osu.service")

class OsuService:
    """Servicio central de coordinación para la predicción de rangos de osu!."""

    async def process_query(self, channel_id: str, user_id: str, query: str) -> str:
        """Procesa una consulta conversacional sobre el rango de osu!.
        
        1. Extrae las entidades (nombre de usuario, rango objetivo) usando el LLM.
        2. Consulta los datos actuales e históricos de la API de osu!.
        3. Registra el snapshot de progreso en la base de datos (con fallback).
        4. Calcula el Improvement Indicator y ejecuta la predicción log-lineal.
        5. Genera una respuesta analítica final con la personalidad de Helith.
        """
        logger.info(f"Procesando consulta de osu!: '{query}'")
        
        # 1. Extraer entidades usando el LLM de forma rápida y estructurada
        username, target_rank = await self._extract_entities(query, user_id, channel_id)
        
        if not username:
            return (
                "Para hacer la predicción, necesito que me indiques un nombre de usuario de osu! "
                "y, opcionalmente, un rango objetivo (por ejemplo: 'Helith, ¿cuánto tardará Litxe en llegar al rank 5000?')."
            )

        # 2. Consultar datos en la API de osu! (o mock)
        user_data = await osu_api_client.get_user_data(username)
        if not user_data:
            return (
                f"No he podido encontrar al usuario '{username}' en osu!. "
                "Por favor, verifica que el nombre de usuario sea válido."
            )
            
        osu_id = user_data["osu_id"]
        actual_username = user_data["username"]
        current_rank = user_data["global_rank"]
        pp = user_data["pp"]
        play_time = user_data["play_time"]
        rank_history = user_data["rank_history"]

        # 3. Calcular el Improvement Indicator (ii)
        ii = calculate_improvement_indicator(pp, play_time)

        # 4. Registrar snapshot de progreso diario en la base de datos
        snapshot = OsuSnapshot(
            osu_id=osu_id,
            username=actual_username,
            global_rank=current_rank,
            pp=pp,
            play_time=play_time,
            improvement_indicator=ii
        )
        osu_repo.save_snapshot(snapshot)

        # 5. Generar la serie temporal para la regresión
        # osu! nos da los últimos 90 días en orden cronológico en rank_history
        if not rank_history or len(rank_history) < 2:
            # Si no hay historial suficiente (por ejemplo, cuenta inactiva o recién activada en API),
            # creamos una mini-serie plana basada en el rango actual para evitar fallos matemáticos.
            history_series = [(0, current_rank), (1, current_rank)]
        else:
            history_series = [(i, rank) for i, rank in enumerate(rank_history)]

        # 6. Entrenar y predecir
        prediction = predict_days_to_rank(history_series, target_rank, ii)

        # 7. Redactar respuesta final con el pool de LLMs manteniendo la identidad
        response = await self._generate_conversational_response(
            actual_username=actual_username,
            current_rank=current_rank,
            pp=pp,
            target_rank=target_rank,
            ii=ii,
            model_message=prediction["message"],
            user_id=user_id,
            server_id=channel_id
        )
        
        return response

    async def _extract_entities(
        self, query: str, user_id: str, server_id: str
    ) -> Tuple[Optional[str], int]:
        """Usa el LLM para parsear la consulta de forma rápida y obtener el usuario y rango objetivo."""
        prompt = (
            "Dada la consulta de un usuario sobre su rango en osu!, extrae el nombre de usuario de osu! "
            "y el rango global objetivo que desea alcanzar. "
            "Devuelve ÚNICAMENTE un objeto JSON en español con este formato exacto:\n"
            '{"username": "nombre_de_usuario_o_null", "target_rank": entero_o_5000}\n'
            "Si no se indica un rango objetivo, pon 5000 por defecto.\n\n"
            f"Consulta: '{query}'"
        )
        
        try:
            raw_response = await llm_pool.generate_response(
                prompt=prompt,
                system_prompt="Eres un parser de texto que solo responde en JSON estructurado y limpio.",
                server_id=server_id,
                user_id=user_id
            )
            
            # Limpiar posibles bloques de código markdown que meta el modelo
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            username = data.get("username")
            target_rank = int(data.get("target_rank", 5000))
            
            # Asegurar que el target_rank sea un entero positivo razonable
            if target_rank <= 0:
                target_rank = 5000
                
            return username, target_rank
            
        except Exception as e:
            logger.error(f"Error al extraer entidades con LLM: {e}. Usando regex fallback.")
            return self._extract_entities_regex_fallback(query)

    def _extract_entities_regex_fallback(self, query: str) -> Tuple[Optional[str], int]:
        """Método de respaldo con Expresiones Regulares si falla la llamada al LLM."""
        # Buscar números de rango objetivo (ej: 5000, 10k, 5k)
        target_rank = 5000
        numbers = re.findall(r'\b\d+k?\b', query.lower())
        for num in numbers:
            if 'k' in num:
                val = int(num.replace('k', '')) * 1000
            else:
                val = int(num)
            # Descartar números muy pequeños que no representen rangos válidos de consulta
            if val > 1:
                target_rank = val
                break
                
        # Intentar extraer palabras que no sean comandos ni preposiciones
        words = re.findall(r'\b[a-zA-Z0-9_\-\[\]]+\b', query)
        stopwords = {
            "osu", "predict", "rank", "tiempo", "llegar", "helith", "bot", "el", "la", "en", "para", 
            "de", "mi", "usuario", "es", "como", "cuanto", "tardare", "tardara", "llegar", "a", "al"
        }
        
        username = None
        for word in words:
            if word.lower() not in stopwords and not word.isdigit():
                username = word
                break
                
        return username, target_rank

    async def _generate_conversational_response(
        self,
        actual_username: str,
        current_rank: int,
        pp: float,
        target_rank: int,
        ii: float,
        model_message: str,
        user_id: str,
        server_id: str
    ) -> str:
        """Pide al LLM que redacte la predicción matemática con la personalidad exacta de Helith."""
        prompt = (
            "Presenta los resultados del análisis predictivo de rango de osu! de forma seria, directa y analítica.\n"
            f"Jugador: {actual_username}\n"
            f"Rango actual: #{current_rank:,} (PP: {pp:.2f})\n"
            f"Rango Objetivo: #{target_rank:,}\n"
            f"Índice de Mejora (ii): {ii:.2f}\n"
            f"Resultado matemático del modelo: {model_message}\n\n"
            "Instrucciones de redacción:\n"
            "- Habla en primera persona, manteniendo la identidad de Helith (reservada, sobria, sin rodeos).\n"
            "- Enfatiza el análisis lógico e interpreta los números.\n"
            "- Mantén la respuesta concisa (máximo 3-4 líneas).\n"
            "- Evita saludos informales, emojis infantiles o formalidades de servicio de atención al cliente."
        )
        
        try:
            return await llm_pool.generate_response(
                prompt=prompt,
                system_prompt=HELITH_PERSONALITY,
                server_id=server_id,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Error al generar respuesta conversacional con el LLM: {e}")
            # Retorno de fallback directo si el LLM colapsa
            return (
                f"Análisis de {actual_username}: Rango actual #{current_rank:,} ({pp:.2f} PP). "
                f"Rango objetivo #{target_rank:,}. {model_message}"
            )

osu_service = OsuService()
