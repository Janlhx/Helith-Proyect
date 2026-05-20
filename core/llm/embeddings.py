import logging

import google.generativeai as genai

from core.config import settings

logger = logging.getLogger("helith.llm.embeddings")


async def generate_embedding(text: str) -> list[float]:
    """Genera un vector de embedding (768 dimensiones) para el texto usando Gemini.

    Si no se encuentra configurada la llave o la petición falla, se retorna un
    vector dummy de 768 dimensiones para garantizar la resiliencia técnica de Helith.
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_key":
        logger.warning(
            "API key de Gemini no configurada o es la por defecto. "
            "Retornando vector dummy de 768 dimensiones."
        )
        return [0.0] * 768

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Usamos el modelo moderno recomendado de 768 dimensiones
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query",
        )
        # El resultado suele retornar una lista flotante
        return result["embedding"]
    except Exception as e:
        logger.error(f"Error al generar embedding con Gemini: {e}")
        return [0.0] * 768
