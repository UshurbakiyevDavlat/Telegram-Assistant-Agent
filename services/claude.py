"""
Claude service — Anthropic SDK with agentic tool_use loop.

Two modes:
  - Personal chat: full agentic loop with tools (KB, Notion, Web Search, Memory)
  - Family chat: simple chat without tools

Manages per-user conversation history in memory.
Supports per-user model override via /model command.
"""
import logging
from collections import defaultdict

import anthropic

from config import ClaudeConfig
from tools import execute_tool, get_tool_definitions

logger = logging.getLogger(__name__)

# Type alias
Message = dict


class ClaudeService:
    """
    Stateful Claude client with per-user history and optional tool_use loop.

    Usage:
        service = ClaudeService(config)

        # Personal chat (with tools)
        reply = await service.chat(user_id=123, user_text="What did we decide about MPS?")

        # Family chat (no tools)
        reply = await service.chat_simple(chat_id=-456, user_text="...", system_prompt="...")

        # Switch model
        service.set_model(user_id=123, model="claude-sonnet-4-5-20241022")
    """

    def __init__(self, config: ClaudeConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(
            api_key=config.api_key.get_secret_value()
        )
        # user_id → list of messages (Anthropic format)
        self._history: dict[int, list[Message]] = defaultdict(list)
        # user_id → model override (None = use default)
        self._model_overrides: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def get_model(self, user_id: int, mode: str = "personal") -> str:
        """Get the active model for a user. Falls back to mode default."""
        override = self._model_overrides.get(user_id)
        if override:
            return override
        if mode == "family":
            return self._config.family_model
        return self._config.personal_model

    def set_model(self, user_id: int, model: str) -> None:
        """Set a model override for a specific user/chat."""
        self._model_overrides[user_id] = model
        logger.info("Model override for %s: %s", user_id, model)

    def clear_model_override(self, user_id: int) -> None:
        """Remove model override, reverting to default."""
        self._model_overrides.pop(user_id, None)

    # ------------------------------------------------------------------
    # Personal chat — agentic loop with tools
    # ------------------------------------------------------------------

    async def chat(self, user_id: int, content: list | str) -> str:
        """
        Personal chat with agentic tool_use loop.

        Args:
            user_id: Telegram user ID (history key).
            content: User message — either a string or a list of content blocks
                     (for multimodal messages with images).

        Returns:
            Final text response from Claude after all tool calls resolve.
        """
        # Normalize content to Anthropic format
        if isinstance(content, str):
            user_content = content
        else:
            user_content = content  # list of blocks (text + image)

        self._append(user_id, role="user", content=user_content)

        model = self.get_model(user_id, mode="personal")
        tools = get_tool_definitions()
        max_turns = self._config.max_tool_turns

        for turn in range(max_turns):
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=self._config.max_tokens,
                    system=self._config.system_prompt,
                    tools=tools,  # type: ignore[arg-type]
                    messages=self._history[user_id],  # type: ignore[arg-type]
                )
            except anthropic.APIError as exc:
                logger.error("Claude API error (turn %d) for %s: %s", turn, user_id, exc)
                # Remove the user message we appended so history stays clean
                if turn == 0:
                    self._history[user_id].pop()
                raise

            # Append assistant response to history
            self._append(user_id, role="assistant", content=response.content)

            if response.stop_reason == "end_turn":
                # Normal completion — extract text
                reply = self._extract_text(response.content)
                self._trim_history(user_id)
                return reply

            if response.stop_reason == "tool_use":
                # Execute all tool calls and add results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info("Tool call: %s(%s)", block.name, block.input)
                        result = await execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                # Add tool results as a user message (Anthropic API format)
                self._append(user_id, role="user", content=tool_results)
                # Continue the loop — Claude will process tool results

            elif response.stop_reason == "max_tokens":
                # Hit token limit mid-response — return what we have
                reply = self._extract_text(response.content)
                self._trim_history(user_id)
                return reply + "\n\n⚠️ _Ответ обрезан из-за лимита токенов._"

        # Max turns reached
        reply = self._extract_text(
            self._history[user_id][-1].get("content", [])
            if self._history[user_id]
            else []
        )
        self._trim_history(user_id)
        return reply or "⚠️ Превышен лимит итераций инструментов."

    # ------------------------------------------------------------------
    # Family chat — simple, no tools
    # ------------------------------------------------------------------

    async def chat_simple(
        self,
        chat_id: int,
        user_text: str,
        system_prompt: str,
    ) -> str:
        """
        Simple chat without tools (for family group mode).
        Uses chat_id as history key.
        """
        self._append(chat_id, role="user", content=user_text)

        model = self.get_model(chat_id, mode="family")

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=self._config.max_tokens,
                system=system_prompt,
                messages=self._history[chat_id],  # type: ignore[arg-type]
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error for chat %s: %s", chat_id, exc)
            self._history[chat_id].pop()
            raise

        reply = self._extract_text(response.content)
        self._append(chat_id, role="assistant", content=reply)
        self._trim_history(chat_id)
        return reply

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self, user_id: int) -> None:
        """Delete all conversation history for a user/chat."""
        self._history.pop(user_id, None)
        logger.info("History cleared for %s", user_id)

    def history_length(self, user_id: int) -> int:
        """Return the number of messages in history."""
        return len(self._history.get(user_id, []))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _append(self, user_id: int, role: str, content) -> None:
        self._history[user_id].append({"role": role, "content": content})

    def _trim_history(self, user_id: int) -> None:
        """Keep at most `history_limit` messages, dropping from the front in pairs."""
        limit = self._config.history_limit
        history = self._history[user_id]
        if len(history) > limit:
            excess = len(history) - limit
            if excess % 2 != 0:
                excess += 1
            self._history[user_id] = history[excess:]

    @staticmethod
    def _extract_text(content) -> str:
        """Extract text from response content (list of blocks or raw)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if hasattr(block, "text"):
                    texts.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block["text"])
            return "\n".join(texts)
        return str(content)
