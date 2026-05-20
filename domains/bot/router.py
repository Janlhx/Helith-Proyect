import logging

import discord

logger = logging.getLogger("helith.router")


class IntentRouter:
    """Clasifica los mensajes entrantes para decidir qué dominio debe manejarlos."""

    def classify_intent(self, message: discord.Message) -> str:
        """Clasifica el contenido del mensaje en una intención."""
        # En la Fase 6, los dominios osu y monitoreo se movieron a Slash Commands.
        # Solo sobrevive la conversación natural.
        return "conversation"

    def needs_web_search(self, content: str) -> bool:
        """Determina de forma heurística si una consulta requiere búsqueda web."""
        text = content.lower().strip()

        # Prefijos de búsqueda explícitos para forzar trigger
        explicit_triggers = ["busca ", "buscar ", "search ", "google "]
        if any(text.startswith(trigger) for trigger in explicit_triggers):
            return True

        # Palabras clave heurísticas en español e inglés
        keywords = [
            # Noticias y actualidad
            "noticias",
            "news",
            "actualidad",
            "actual",
            "reciente",
            "recientes",
            "recientemente",
            "último",
            "ultimo",
            "últimos",
            "ultimos",
            "hoy",
            "today",
            "suceso",
            "sucesos",
            "pasando",
            "pasó",
            "paso",
            "sucedió",
            "sucedio",
            "ocurrió",
            "ocurrio",
            "este año",
            "this year",
            "este mes",
            "esta semana",
            # Decesos
            "murió",
            "murio",
            "falleció",
            "fallecio",
            "muerte",
            "muerto",
            # Movilizaciones y eventos sociales
            "paro",
            "huelga",
            "protesta",
            "protestas",
            "marcha",
            "marchas",
            "manifestación",
            "manifestacion",
            # Deportes y competiciones
            "partido",
            "partidos",
            "fútbol",
            "futbol",
            "soccer",
            "juego",
            "juegos",
            "resultado",
            "resultados",
            "ganador",
            "ganadores",
            "campeón",
            "campeon",
            "campeonato",
            "copa",
            "mundial",
            # Entretenimiento y cultura
            "canción",
            "cancion",
            "álbum",
            "album",
            "música",
            "musica",
            "estreno",
            "lanzamiento",
            "lanzó",
            "lanzo",
            "estrenó",
            "estrenó",
            "shakira",
            "oscar",
            "oscars",
            "grammy",
            "grammys",
            "película",
            "pelicula",
            "serie",
            "series",
            # Finanzas
            "precio",
            "precios",
            "valor",
            "dólar",
            "dolar",
            "euro",
            "peso",
            "pesos",
            "trm",
            "tasa",
            "cambio",
            "cotización",
            "cotizacion",
            "bitcoin",
            "crypto",
            "cripto",
            "acciones",
            "bolsa",
            # Clima
            "clima",
            "weather",
            "tiempo",
            "pronóstico",
            "pronostico",
            "temperatura",
            "lluvia",
            "lluvias",
            "sol",
            "ideam",
            "alerta",
            "alertas",
            # Preguntas de identidad/rol actual
            "quien gano",
            "quién ganó",
            "quien es el actual",
            "quién es el actual",
            "qué pasó con",
            "que paso con",
            "quien es hoy",
            "quién es hoy",
            "quien es el presidente",
            "quién es el presidente",
            "quien es el alcalde",
            "quién es el alcalde",
        ]

        import re

        for keyword in keywords:
            # Búsqueda por palabra completa para evitar falsos positivos
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text):
                return True

        return False


intent_router = IntentRouter()
