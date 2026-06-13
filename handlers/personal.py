"""
Personal chat handler — responds to text and photo messages with Claude.

Applies to private chats only (family group handled in group.py).
Text messages go through the agentic tool_use loop.
Photos are sent as base64 images via Claude Vision.
"""
import base64
import io
import logging
import re
from pathlib import Path

import anthropic
from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from services import ClaudeService

logger = logging.getLogger(__name__)

# Where downloaded documents are stored so the KB MCP (same VPS) can index them.
UPLOADS_DIR = Path("/opt/telegram-agent/data/uploads")
# File extensions the KB indexer (kb_add_file) understands.
KB_INDEXABLE_EXT = {".md", ".txt", ".pdf"}

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
    file_name = doc.file_name or "file"  # type: ignore[union-attr]
    ext = Path(file_name).suffix.lower()

    await _send_typing(message)

    # Download the file to local disk so the KB MCP (same VPS) can index it
    # by absolute path. We always download; for KB-indexable types we hand the
    # path to Claude so it can call kb_add_file on request.
    saved_path: str | None = None
    if ext in KB_INDEXABLE_EXT:
        try:
            saved_path = await _download_document(message, doc, file_name)
        except Exception as exc:
            logger.error("Failed to download document from user %s: %s", user_id, exc)

    if saved_path:
        text = (
            f"[Пользователь отправил файл: {file_name} "
            f"({doc.mime_type}, {doc.file_size} байт). "  # type: ignore[union-attr]
            f"Файл сохранён на сервере по пути: {saved_path}]\n"
            f"Если пользователь просит запомнить/сохранить/проанализировать файл — "
            f"вызови kb_add_file с этим путём (path={saved_path})."
        )
    else:
        # Non-indexable type (or download failed): fall back to metadata only.
        text = (
            f"[Пользователь отправил файл: {file_name}, "
            f"размер: {doc.file_size} байт, "  # type: ignore[union-attr]
            f"тип: {doc.mime_type}. "  # type: ignore[union-attr]
            f"Содержимое недоступно для индексации (поддерживаются .md, .txt, .pdf).]"
        )
    if caption:
        text += f"\n{caption}"
    elif not saved_path:
        text += "\nЧто ты можешь сказать об этом файле?"

    try:
        reply = await claude_service.chat(user_id=user_id, content=text)
    except anthropic.APIError as exc:
        await _handle_api_error(message, user_id, exc)
        return

    await _send_reply(message, reply)


async def _download_document(message: Message, doc, file_name: str) -> str:
    """Download a Telegram document to UPLOADS_DIR, return its absolute path."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    # Sanitize the filename and prefix with the unique file_id to avoid clashes.
    safe_name = re.sub(r"[^\w.\-]", "_", file_name)
    dest = UPLOADS_DIR / f"{doc.file_id}_{safe_name}"
    file = await message.bot.get_file(doc.file_id)  # type: ignore[union-attr]
    await message.bot.download_file(file.file_path, str(dest))  # type: ignore[union-attr]
    return str(dest)


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
    """Send reply, splitting if it exceeds Telegram's 4096 char limit.

    Telegram's legacy Markdown parser is fragile: an unbalanced *, _ or `
    in the model output makes the whole send fail with TelegramBadRequest.
    On any parse error we retry the same chunk as plain text so the user
    always gets the content (just without formatting) instead of silence.
    """
    if not reply:
        reply = "(пустой ответ)"

    chunks = [reply] if len(reply) <= 4096 else _split_message(reply)
    for chunk in chunks:
        await _send_chunk(message, chunk)


async def _send_chunk(message: Message, chunk: str) -> None:
    """Send one chunk, falling back to plain text if Markdown is invalid."""
    try:
        await message.answer(chunk, parse_mode="Markdown")
    except TelegramBadRequest as exc:
        if "can't parse entities" in str(exc).lower() or "parse" in str(exc).lower():
            logger.warning("Markdown parse failed, retrying as plain text: %s", exc)
            await message.answer(chunk)  # no parse_mode → plain text
        else:
            raise


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
