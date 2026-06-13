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

    async def _call(self, tool: str, arguments: dict, empty_msg: str) -> str:
        """Open an SSE session, call one KB tool, return its text result."""
        try:
            async with sse_client(url=self._url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments=arguments)
                    if result.content:
                        return result.content[0].text  # type: ignore[union-attr]
                    return empty_msg
        except Exception as exc:
            logger.error("KB %s error: %s", tool, exc)
            return json.dumps(
                {"error": f"KB {tool} failed: {type(exc).__name__}: {exc}"}
            )

    async def search(self, query: str, top_k: int = 5) -> str:
        """Search the knowledge base for relevant chunks."""
        return await self._call(
            "kb_search",
            {"query": query, "top_k": top_k},
            "No results found in knowledge base.",
        )

    async def get_facts(self) -> str:
        """Get stored personal facts from the knowledge base."""
        return await self._call(
            "kb_get_facts", {}, "No facts stored in knowledge base."
        )

    async def add_document(
        self,
        text: str,
        title: str,
        source_type: str = "manual",
        source_url: str | None = None,
        doc_date: str | None = None,
    ) -> str:
        """Index a piece of text (note, fact, conversation summary) into the KB."""
        args: dict = {"text": text, "title": title, "source_type": source_type}
        if source_url:
            args["source_url"] = source_url
        if doc_date:
            args["doc_date"] = doc_date
        return await self._call("kb_add_document", args, "Document added (no detail returned).")

    async def add_file(
        self,
        path: str,
        title: str | None = None,
        doc_date: str | None = None,
    ) -> str:
        """Index a local file (.md, .txt, .pdf) into the KB by absolute path."""
        args: dict = {"path": path}
        if title:
            args["title"] = title
        if doc_date:
            args["doc_date"] = doc_date
        return await self._call("kb_add_file", args, "File added (no detail returned).")
