import logging

import httpx

from core.config import settings

logger = logging.getLogger("helith.tools.search")


class TavilySearchClient:
    """Client for web searches using the Tavily API."""

    @property
    def api_key(self) -> str:
        return getattr(settings, "TAVILY_API_KEY", "")

    @property
    def enabled(self) -> bool:
        key = self.api_key
        return bool(key) and key != "your_tavily_key"

    async def search(self, query: str, max_results: int = 3) -> str:
        """Search Tavily and return a concise summary of 2-3 key points.

        Optimizes token consumption and aligns with Helith's personality.
        """
        if not self.enabled:
            logger.warning(
                "Tavily API key not configured or empty. Skipping search."
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
                        return "No relevant results found."

                    # Summarize to 2-3 key points
                    summary_points = []
                    for res in results[:max_results]:
                        title = res.get("title", "No title")
                        snippet = res.get("content", "").strip()
                        # Limit snippet to 150 characters
                        if len(snippet) > 150:
                            snippet = snippet[:147] + "..."
                        summary_points.append(f"- {title}: {snippet}")

                    return "\n".join(summary_points)
                else:
                    logger.error(
                        f"Tavily error: {response.status_code} - {response.text}"
                    )
                    return ""
        except Exception as e:
            logger.error(f"Exception in Tavily search: {e}")
            return ""


tavily_search = TavilySearchClient()
