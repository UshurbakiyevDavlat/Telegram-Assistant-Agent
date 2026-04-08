"""
Web Search tool — DuckDuckGo via the duckduckgo_search library.

Free, no API key needed. Rate-limited by DDG, but fine for personal use.
"""
import json
import logging

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class WebSearchTool:
    """DuckDuckGo web search."""

    async def search(self, query: str, max_results: int = 5) -> str:
        """
        Search the web and return results as JSON.
        Returns title, URL, and snippet for each result.
        """
        max_results = min(max(max_results, 1), 10)

        try:
            ddgs = DDGS()
            results = ddgs.text(
                keywords=query,
                max_results=max_results,
            )

            if not results:
                return f"No web results found for '{query}'."

            formatted = []
            for r in results:
                formatted.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )

            return json.dumps(formatted, ensure_ascii=False, indent=2)

        except Exception as exc:
            logger.error("Web search error: %s", exc)
            return json.dumps({"error": f"Web search failed: {type(exc).__name__}: {exc}"})
