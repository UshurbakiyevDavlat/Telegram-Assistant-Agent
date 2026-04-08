"""
Tool executor — dispatches Claude tool_use calls to the right implementation.

Lifecycle:
    init_tools(config) → creates tool instances, initializes DBs
    get_tool_definitions() → returns Anthropic API tool schemas
    execute_tool(name, input) → runs the tool and returns string result
    close_tools() → cleanup (close DB connections)
"""
import logging

from config import AppConfig
from .definitions import TOOL_DEFINITIONS
from .kb import KBTool
from .memory import MemoryTool
from .notion_tool import NotionTool
from .web_search import WebSearchTool

logger = logging.getLogger(__name__)

# Tool instances — populated by init_tools()
_kb: KBTool | None = None
_notion: NotionTool | None = None
_web_search: WebSearchTool | None = None
_memory: MemoryTool | None = None


async def init_tools(config: AppConfig) -> None:
    """Initialize all tool instances. Call once at bot startup."""
    global _kb, _notion, _web_search, _memory

    _kb = KBTool(config.kb)
    _notion = NotionTool(config.notion)
    _web_search = WebSearchTool()
    _memory = MemoryTool(config.memory)
    await _memory.init()

    logger.info(
        "Tools initialized: KB=%s, Notion=%s, WebSearch=yes, Memory=%s",
        config.kb.url,
        "enabled" if _notion.enabled else "disabled (no API key)",
        config.memory.db_path,
    )


async def close_tools() -> None:
    """Cleanup — close connections. Call on bot shutdown."""
    if _memory:
        await _memory.close()
    logger.info("Tools closed.")


def get_tool_definitions() -> list[dict]:
    """Return tool definitions for the Anthropic API."""
    defs = list(TOOL_DEFINITIONS)

    # Filter out Notion tools if not configured
    if _notion and not _notion.enabled:
        defs = [t for t in defs if not t["name"].startswith("notion_")]

    return defs


async def execute_tool(name: str, tool_input: dict) -> str:
    """
    Execute a tool by name with the given input.

    Returns the result as a string. Errors are returned as data
    (not raised) so the model can decide how to handle them.
    """
    try:
        match name:
            # ── KB ────────────────────────────────────────────────────
            case "kb_search":
                return await _kb.search(  # type: ignore[union-attr]
                    query=tool_input["query"],
                    top_k=tool_input.get("top_k", 5),
                )
            case "kb_get_facts":
                return await _kb.get_facts()  # type: ignore[union-attr]

            # ── Notion ────────────────────────────────────────────────
            case "notion_search":
                return await _notion.search(  # type: ignore[union-attr]
                    query=tool_input["query"],
                )
            case "notion_create_task":
                return await _notion.create_task(  # type: ignore[union-attr]
                    title=tool_input["title"],
                    description=tool_input.get("description", ""),
                )

            # ── Web Search ────────────────────────────────────────────
            case "web_search":
                return await _web_search.search(  # type: ignore[union-attr]
                    query=tool_input["query"],
                    max_results=tool_input.get("max_results", 5),
                )

            # ── Memory ────────────────────────────────────────────────
            case "memory_store":
                return await _memory.store(  # type: ignore[union-attr]
                    key=tool_input["key"],
                    value=tool_input["value"],
                )
            case "memory_recall":
                return await _memory.recall(  # type: ignore[union-attr]
                    query=tool_input["query"],
                )

            case _:
                return f"Error: Unknown tool '{name}'"

    except Exception as exc:
        logger.error("Tool execution error (%s): %s", name, exc, exc_info=True)
        return f"Error executing {name}: {type(exc).__name__}: {exc}"
