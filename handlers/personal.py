"""
Personal chat handler — responds to text and photo messages with Claude.

Applies to private chats only (family group handled in group.py).
Text messages go through the agentic tool_use loop.
Photos are sent as base64 images via Claude Vision.
"""
import base64
import io
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


# ------------------------------------------------------------------
# Text messages — agentic loop with tools
# ------------------------------------------------------------------

@personal_router.message(F.text)
async def personal_text_handler(
    message: Message,
    claude_service: ClaudeService,
) -> None:
    """Handle text messages in personal chat — full agentic Claude."""
    user_id = message.from_user.id if message.from_user else None
    if not user_id or not message.text:
        return

    await _send_typing(message)

    try:
        reply = await claude_service.chat(user_id=user_id, content=message.text)
    except anthropic.APIError as exc:
        await _handle_api_error(message, user_id, exc)
        return

    await _send_reply(message, reply)


# ------------------------------------------------------------------
# Photo messages — Claude Vision
# ------------------------------------------------------------------

@personal_router.message(F.photo)
async def personal_photo_handler(
    message: Message,
    claude_service: ClaudeService,
) -> None:
    """
    Handle photo messages — download, encode to base64, send to Claude Vision.
    If the photo has a caption, use it as the user's question about the image.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    await _send_typing(message)

    # Get the largest available photo size
    photo = message.photo[-1]
    try:
        file = await message.bot.get_file(photo.file_id)  # type: ignore[union-attr]
        bio = io.BytesIO()
        await message.bot.download_file(file.file_path, bio)  # type: ignore[union-attr]
        image_data = base64.standard_b64encode(bio.getvalue()).decode("utf-8")
    except Exception as exc:
        logger.error("Failed to download photo from user %s: %s", user_id, exc)
        await message.answer("Не удалось загрузить фото. Попробуй ещё раз.")
        return

    # Build multimodal content blocks
    caption = message.caption or "Что на этом изображении?"
    content_blocks = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_data,
            },
        },
        {
            "type": "text",
            "text": caption,
        },
    ]

    try:
        reply = await claude_service.chat(user_id=user_id, content=content_blocks)
    except anthropic.APIError as exc:
        await _handle_api_error(message, user_id, exc)
        return

    await _send_reply(message, reply)


# ------------------------------------------------------------------
# Document/file messages — forward as text description
# ------------------------------------------------------------------

@personal_router.message(F.document)
async def personal_document_handler(
    message: Message,
    claude_service: ClaudeService,
) -> None:
    """Handle document uploads — describe the document and ask Claude."""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    doc = message.document
    caption = message.caption or ""
    text = (
        f"[Пользователь отправил файл: {doc.file_name}, "  # type: ignore[union-attr]
        f"размер: {doc.file_size} байт, "  # type: ignore[union-attr]
        f"тип: {doc.mime_type}]"  # type: ignore[union-attr]
    )
    if caption:
        text += f"\n{caption}"
    else:
        text += "\nЧто ты можешь сказать об этом файле?"

    await _send_typing(message)

    try:
        reply = await claude_service.chat(user_id=user_id, content=text)
    except anthropic.APIError as exc:
        await _handle_api_error(message, user_id, exc)
        return

    await _send_reply(message, reply)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _send_typing(message: Message) -> None:
    """Send typing indicator."""
    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )


async def _handle_api_error(message: Message, user_id: int, exc: anthropic.APIError) -> None:
    """Handle Claude API errors gracefully."""
    if isinstance(exc, anthropic.APIStatusError):
        logger.error("Claude API status error for user %s: %s", user_id, exc)
        await message.answer(
            f"API Claude error: <code>{exc.status_code}</code>\nПопробуй ещё раз через минуту.",
            parse_mode="HTML",
        )
    elif isinstance(exc, anthropic.APIConnectionError):
        logger.error("Claude connection error for user %s: %s", user_id, exc)
        await message.answer("Не могу подключиться к Claude. Попробуй позже.")
    else:
        logger.error("Claude API error for user %s: %s", user_id, exc)
        await message.answer("Произошла ошибка. Попробуй ещё раз.")


async def _send_reply(message: Message, reply: str) -> None:
    """Send reply, splitting if it exceeds Telegram's 4096 char limit."""
    if not reply:
        reply = "_(пустой ответ)_"

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
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
