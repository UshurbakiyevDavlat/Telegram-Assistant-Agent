"""
Notion tool — search pages and create tasks via the Notion API.

Uses httpx directly (lighter than the official notion-client SDK).
Requires NOTION_API_KEY (internal integration token).
"""
import json
import logging

import httpx

from config import NotionConfig

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"


class NotionTool:
    """Notion API client for search and task creation."""

    def __init__(self, config: NotionConfig) -> None:
        self._config = config
        api_key = config.api_key.get_secret_value()
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": config.api_version,
            "Content-Type": "application/json",
        }
        self._enabled = bool(api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def search(self, query: str) -> str:
        """Search Notion workspace for pages matching the query."""
        if not self._enabled:
            return json.dumps({"error": "Notion is not configured. Set NOTION_API_KEY."})

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{NOTION_API_BASE}/search",
                    headers=self._headers,
                    json={
                        "query": query,
                        "page_size": 5,
                        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for page in data.get("results", []):
                title = _extract_title(page)
                url = page.get("url", "")
                last_edited = page.get("last_edited_time", "")[:10]
                results.append({"title": title, "url": url, "last_edited": last_edited})

            if not results:
                return f"No Notion pages found for '{query}'."

            return json.dumps(results, ensure_ascii=False, indent=2)

        except httpx.HTTPStatusError as exc:
            logger.error("Notion search HTTP error: %s", exc)
            return json.dumps({"error": f"Notion API error: {exc.response.status_code}"})
        except Exception as exc:
            logger.error("Notion search error: %s", exc)
            return json.dumps({"error": f"Notion search failed: {exc}"})

    async def create_task(self, title: str, description: str = "") -> str:
        """Create a new page in the tasks database."""
        if not self._enabled:
            return json.dumps({"error": "Notion is not configured. Set NOTION_API_KEY."})

        db_id = self._config.tasks_database_id
        if not db_id:
            return json.dumps({"error": "NOTION_TASKS_DATABASE_ID is not configured."})

        try:
            body: dict = {
                "parent": {"database_id": db_id},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": title}}],
                    },
                },
            }

            # Add description as page content if provided
            if description:
                body["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": description}}],
                        },
                    },
                ]

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{NOTION_API_BASE}/pages",
                    headers=self._headers,
                    json=body,
                )
                resp.raise_for_status()
                page = resp.json()

            return json.dumps(
                {
                    "status": "created",
                    "title": title,
                    "url": page.get("url", ""),
                },
                ensure_ascii=False,
            )

        except httpx.HTTPStatusError as exc:
            logger.error("Notion create task HTTP error: %s", exc)
            return json.dumps({"error": f"Notion API error: {exc.response.status_code}"})
        except Exception as exc:
            logger.error("Notion create task error: %s", exc)
            return json.dumps({"error": f"Notion create failed: {exc}"})


def _extract_title(page: dict) -> str:
    """Extract plain-text title from a Notion page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return title_arr[0].get("plain_text", "Untitled")
    return "Untitled"
