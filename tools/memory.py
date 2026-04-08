"""
Memory tool — SQLite-backed long-term fact storage.

Stores key-value pairs that persist across bot restarts.
Used for personal preferences, facts about family members,
project context, and anything worth remembering long-term.

Schema:
    memories(key TEXT PRIMARY KEY, value TEXT, created_at, updated_at)
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from config import MemoryConfig

logger = logging.getLogger(__name__)


class MemoryTool:
    """SQLite-backed long-term memory for personal facts."""

    def __init__(self, config: MemoryConfig) -> None:
        self._db_path = config.db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Create DB directory and table if they don't exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await self._db.commit()
        logger.info("Memory DB initialized at %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def store(self, key: str, value: str) -> str:
        """
        Store or update a fact. Returns confirmation.
        Upserts — if key exists, updates the value.
        """
        if not self._db:
            return json.dumps({"error": "Memory DB not initialized"})

        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._db.execute(
                """
                INSERT INTO memories (key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
                """,
                (key, value, now, now, value, now),
            )
            await self._db.commit()
            return json.dumps(
                {"status": "stored", "key": key, "value": value},
                ensure_ascii=False,
            )
        except Exception as exc:
            logger.error("Memory store error: %s", exc)
            return json.dumps({"error": f"Memory store failed: {exc}"})

    async def recall(self, query: str) -> str:
        """
        Search memories by key or value containing the query.
        Returns matching facts as JSON.
        """
        if not self._db:
            return json.dumps({"error": "Memory DB not initialized"})

        try:
            cursor = await self._db.execute(
                """
                SELECT key, value, updated_at FROM memories
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY updated_at DESC
                LIMIT 10
                """,
                (f"%{query}%", f"%{query}%"),
            )
            rows = await cursor.fetchall()

            if not rows:
                return f"No memories found matching '{query}'."

            facts = [
                {"key": row[0], "value": row[1], "updated": row[2][:10]}
                for row in rows
            ]
            return json.dumps(facts, ensure_ascii=False, indent=2)

        except Exception as exc:
            logger.error("Memory recall error: %s", exc)
            return json.dumps({"error": f"Memory recall failed: {exc}"})
