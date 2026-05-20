import logging

from core.llm.pool import llm_pool
from core.llm.prompts import HELITH_PERSONALITY
from domains.osu.client import osu_api_client
from domains.osu.ml_model import (
    calculate_improvement_indicator,
    predict_days_to_rank,
)
from domains.osu.models import OsuSnapshot
from domains.osu.repository import osu_repo

logger = logging.getLogger("helith.osu.service")


class OsuService:
    """Servicio central de coordinación para la predicción de rangos de osu!."""

    async def process_slash_predict(
        self, username: str, target_rank: int, server_id: str, user_id: str
    ) -> str:
        """Procesa la predicción estructural desde un Slash Command.

        1. Consulta los datos actuales e históricos de la API de osu!.
        2. Registra el snapshot de progreso en la BD.
        3. Calcula el Improvement Indicator y corre la regresión log-lineal.
        4. Genera respuesta final con la personalidad de Helith.
        """
        logger.info(
            f"Procesando predicción de osu! para: '{username}' al rank '{target_rank}'"
        )

        if target_rank <= 0:
            target_rank = 5000

        # 1. Consultar datos en la API de osu! (o mock)
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

        # 2. Calcular el Improvement Indicator (ii)
        ii = calculate_improvement_indicator(pp, play_time)

        # 3. Registrar snapshot de progreso diario en la base de datos
        snapshot = OsuSnapshot(
            osu_id=osu_id,
            username=actual_username,
            global_rank=current_rank,
            pp=pp,
            play_time=play_time,
            improvement_indicator=ii,
        )
        osu_repo.save_snapshot(snapshot)

        # 4. Generar la serie temporal para la regresión
        if not rank_history or len(rank_history) < 2:
            history_series = [(0, current_rank), (1, current_rank)]
        else:
            history_series = [(i, rank) for i, rank in enumerate(rank_history)]

        # 5. Entrenar y predecir
        prediction = predict_days_to_rank(history_series, target_rank, ii)

        # 6. Redactar respuesta final con el pool de LLMs manteniendo la identidad
        response = await self._generate_conversational_response(
            actual_username=actual_username,
            current_rank=current_rank,
            pp=pp,
            target_rank=target_rank,
            ii=ii,
            model_message=prediction["message"],
            user_id=user_id,
            server_id=server_id,
        )

        return response

    async def _generate_conversational_response(
        self,
        actual_username: str,
        current_rank: int,
        pp: float,
        target_rank: int,
        ii: float,
        model_message: str,
        user_id: str,
        server_id: str,
    ) -> str:
        """Pide al LLM que redacte la predicción matemática con la personalidad
        exacta de Helith.
        """
        prompt = (
            "Presenta los resultados del análisis predictivo de rango de osu! "
            "de forma seria, directa y analítica.\n"
            f"Jugador: {actual_username}\n"
            f"Rango actual: #{current_rank:,} (PP: {pp:.2f})\n"
            f"Rango Objetivo: #{target_rank:,}\n"
            f"Índice de Mejora (ii): {ii:.2f}\n"
            f"Resultado matemático del modelo: {model_message}\n\n"
            "Instrucciones de redacción:\n"
            "- Habla en primera persona, manteniendo la identidad de Helith "
            "(reservada, sobria, sin rodeos).\n"
            "- Enfatiza el análisis lógico e interpreta los números.\n"
            "- Mantén la respuesta concisa (máximo 3-4 líneas).\n"
            "- Evita saludos informales, emojis infantiles o formalidades de "
            "servicio de atención al cliente."
        )

        try:
            return await llm_pool.generate_response(
                prompt=prompt,
                system_prompt=HELITH_PERSONALITY,
                server_id=server_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Error al generar respuesta conversacional con el LLM: {e}")
            # Retorno de fallback directo si el LLM colapsa
            return (
                f"Análisis de {actual_username}: Rango actual #{current_rank:,} "
                f"({pp:.2f} PP). Rango objetivo #{target_rank:,}. {model_message}"
            )


osu_service = OsuService()
