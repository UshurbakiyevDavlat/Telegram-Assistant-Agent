"""
Personal chat handler — responds to any text message with Claude.

Applies to private chats only (family group chat will be added in Phase 2).
Shows a "typing..." action while Claude is thinking.
Handles API errors gracefully without crashing the bot.
"""
import logging

import anthropic
from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.types import Message

from services import ClaudeService

logger = logging.getLogger(__name__)

personal_router = Router(name="personal")

# Only handle private chats in this router
personal_router.message.filter(F.chat.type == ChatType.PRIVATE)


@personal_router.message(F.text)
async def personal_message_handler(
    message: Message,
    claude_service: ClaudeService,
) -> None:
    """
    Main message handler for private chats.
    Sends user text to Claude and replies with the result.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not message.text:
        return

    # Show typing indicator — non-blocking
    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    try:
        reply = await claude_service.chat(user_id=user_id, user_text=message.text)
    except anthropic.APIStatusError as exc:
        logger.error("Claude API status error for user %s: %s", user_id, exc)
        await message.answer(
            "⚠️ Ошибка API Claude. Попробуй ещё раз через минуту.\n"
            f"<code>{exc.status_code}: {exc.message}</code>",
            parse_mode="HTML",
        )
        return
    except anthropic.APIConnectionError as exc:
        logger.error("Claude connection error for user %s: %s", user_id, exc)
        await message.answer("⚠️ Не могу подключиться к Claude. Проверь интернет или попробуй позже.")
        return
    except anthropic.APIError as exc:
        logger.error("Unexpected Claude API error for user %s: %s", user_id, exc)
        await message.answer("⚠️ Произошла непредвиденная ошибка. Попробуй ещё раз.")
        return

    # Telegram has a 4096 char limit per message — split if needed
    if len(reply) <= 4096:
        await message.answer(reply, parse_mode="Markdown")
    else:
        for chunk in _split_message(reply):
            await message.answer(chunk, parse_mode="Markdown")


def _split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Try to split at a newline near the limit
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
