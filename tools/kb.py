"""
Knowledge Base tool — connects to the Personal KB MCP server on VPS via SSE.

The KB server runs FastMCP with SSE transport at http://127.0.0.1:8000/sse.
Since the Telegram bot runs on the same VPS, no auth token is needed for local access.

Uses the official MCP Python SDK for clean SSE client communication.
"""
import json
import logging

from mcp import ClientSession
from mcp.client.sse import sse_client

from config import KBConfig

logger = logging.getLogger(__name__)


class KBTool:
    """
    Client for the Personal Knowledge Base MCP server.

    Connects via SSE per-call (simple, robust for low-traffic personal bot).
    """

    def __init__(self, config: KBConfig) -> None:
        self._config = config
        url = config.url
        if config.token:
            url = f"{url}?token={config.token}"
        self._url = url

    async def search(self, query: str, top_k: int = 5) -> str:
        """Search the knowledge base for relevant chunks."""
        try:
            async with sse_client(url=self._url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "kb_search",
                        arguments={"query": query, "top_k": top_k},
                    )
                    if result.content:
                        return result.content[0].text  # type: ignore[union-attr]
                    return "No results found in knowledge base."
        except Exception as exc:
            logger.error("KB search error: %s", exc)
            return json.dumps({"error": f"KB search failed: {type(exc).__name__}: {exc}"})

    async def get_facts(self) -> str:
        """Get stored personal facts from the knowledge base."""
        try:
            async with sse_client(url=self._url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    result = await session.call_tool("kb_get_facts", arguments={})
                    if result.content:
                        return result.content[0].text  # type: ignore[union-attr]
                    return "No facts stored in knowledge base."
        except Exception as exc:
            logger.error("KB get_facts error: %s", exc)
            return json.dumps({"error": f"KB get_facts failed: {type(exc).__name__}: {exc}"})
