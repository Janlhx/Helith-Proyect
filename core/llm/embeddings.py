import logging

import google.generativeai as genai

from core.config import settings

logger = logging.getLogger("helith.llm.embeddings")


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector (768 dimensions) for the text using Gemini.

    If the API key is not configured or the request fails, returns a dummy vector
    of 768 dimensions to ensure Helith's technical resilience.
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_key":
        logger.warning(
            "Gemini API key not configured or is the default. "
            "Returning dummy vector of 768 dimensions."
        )
        return [0.0] * 768

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Using the modern recommended 768-dimension model
        result = await genai.embed_content_async(
            model="models/gemini-embedding-2",
            content=text,
            task_type="retrieval_query",
            output_dimensionality=768,
        )
        # Result typically returns a floating point list
        return result["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding with Gemini: {e}")
        return [0.0] * 768
