import logging

import httpx

from core.config import settings

logger = logging.getLogger("helith.tools.search")


class TavilySearchClient:
    """Cliente para realizar búsquedas en la web usando la API de Tavily."""

    @property
    def api_key(self) -> str:
        return getattr(settings, "TAVILY_API_KEY", "")

    @property
    def enabled(self) -> bool:
        key = self.api_key
        return bool(key) and key != "your_tavily_key"

    async def search(self, query: str, max_results: int = 3) -> str:
        """Busca en Tavily y retorna un resumen conciso de 2-3 puntos clave.

        Optimiza el consumo de tokens y se ajusta a la personalidad de Helith.
        """
        if not self.enabled:
            logger.warning(
                "API key de Tavily no configurada o vacía. Saltando búsqueda."
            )
            return ""

        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if not results:
                        return "No se encontraron resultados relevantes."

                    # Resumimos a 2-3 puntos clave
                    summary_points = []
                    for res in results[:max_results]:
                        title = res.get("title", "Sin título")
                        snippet = res.get("content", "").strip()
                        # Limitar snippet a 150 caracteres
                        if len(snippet) > 150:
                            snippet = snippet[:147] + "..."
                        summary_points.append(f"- {title}: {snippet}")

                    return "\n".join(summary_points)
                else:
                    logger.error(
                        f"Error de Tavily: {response.status_code} - {response.text}"
                    )
                    return ""
        except Exception as e:
            logger.error(f"Excepción en la búsqueda de Tavily: {e}")
            return ""


tavily_search = TavilySearchClient()
