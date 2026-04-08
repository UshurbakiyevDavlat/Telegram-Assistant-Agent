"""
Claude service — wraps the Anthropic SDK.

Manages per-user conversation history in memory (dict).
History is a list of {"role": "user"|"assistant", "content": str} dicts
following the Anthropic Messages API format.

Thread-safety: asyncio is single-threaded, so the plain dict is safe here.
"""
import logging
from collections import defaultdict

import anthropic

from config import ClaudeConfig

logger = logging.getLogger(__name__)

# Type alias for a single message
Message = dict[str, str]


class ClaudeService:
    """
    Stateful Claude client with per-user message history.

    Usage:
        service = ClaudeService(config)
        reply = await service.chat(user_id=123, user_text="Hello!")
        service.clear_history(user_id=123)
    """

    def __init__(self, config: ClaudeConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(
            api_key=config.api_key.get_secret_value()
        )
        # user_id → list of messages
        self._history: dict[int, list[Message]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        user_id: int,
        user_text: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Send a message and return Claude's reply as a string.
        Appends both the user message and the assistant reply to history.

        Args:
            user_id: Unique key for history (user_id for personal, chat_id for groups).
            user_text: The user's message text.
            system_prompt: Override the default system prompt (e.g. for family mode).
        """
        self._append(user_id, role="user", content=user_text)

        messages = self._history[user_id]

        try:
            response = await self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system_prompt or self._config.system_prompt,
                messages=messages,  # type: ignore[arg-type]
            )
            reply_text: str = response.content[0].text  # type: ignore[union-attr]
        except anthropic.APIError as exc:
            logger.error("Anthropic API error for user %s: %s", user_id, exc)
            # Remove the user message we just appended so history stays clean
            self._history[user_id].pop()
            raise

        self._append(user_id, role="assistant", content=reply_text)
        self._trim_history(user_id)

        return reply_text

    def clear_history(self, user_id: int) -> None:
        """Delete all conversation history for a user."""
        self._history.pop(user_id, None)
        logger.info("History cleared for user %s", user_id)

    def history_length(self, user_id: int) -> int:
        """Return the number of messages in history for a user."""
        return len(self._history.get(user_id, []))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _append(self, user_id: int, role: str, content: str) -> None:
        self._history[user_id].append({"role": role, "content": content})

    def _trim_history(self, user_id: int) -> None:
        """
        Keep at most `history_limit` messages.
        We remove from the front in pairs to preserve role alternation.
        """
        limit = self._config.history_limit
        history = self._history[user_id]
        if len(history) > limit:
            # Drop oldest messages until within limit
            excess = len(history) - limit
            # Drop in pairs to keep user/assistant alternation intact
            if excess % 2 != 0:
                excess += 1
            self._history[user_id] = history[excess:]
