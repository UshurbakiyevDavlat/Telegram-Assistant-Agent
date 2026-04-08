"""
Family group chat handler — Claude without personal tools.

Responds only when:
  - The bot is mentioned via @username
  - The user replies to the bot's message

Uses chat_simple() — no tools, separate family system prompt.
History is shared per group (keyed by chat_id).
"""
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.types import Message

from config import AppConfig
from services import ClaudeService

logger = logging.getLogger(__name__)

group_router = Router(name="group")

# Only handle group/supergroup chats
group_router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


def _is_bot_mentioned(message: Message, bot_username: str) -> bool:
    """Check if the bot is mentioned via @username in the message text."""
    if not message.entities or not message.text or not bot_username:
        return False
    for entity in message.entities:
        if entity.type == "mention":
            mention = message.text[entity.offset : entity.offset + entity.length]
            if mention.lower() == f"@{bot_username.lower()}":
                return True
    return False


def _is_reply_to_bot(message: Message, bot_id: int) -> bool:
    """Check if the message is a reply to the bot's own message."""
    if not message.reply_to_message:
        return False
    reply_from = message.reply_to_message.from_user
    if not reply_from:
        return False
    return reply_from.id == bot_id


def _strip_bot_mention(text: str, bot_username: str) -> str:
    """Remove @bot_username from the message text."""
    return text.replace(f"@{bot_username}", "").strip()


@group_router.message(F.text)
async def group_message_handler(
    message: Message,
    bot: Bot,
    claude_service: ClaudeService,
    config: AppConfig,
) -> None:
    """
    Handle messages in the family group chat.
    Only responds if the bot is mentioned or the message is a reply to the bot.
    """
    if not message.text:
        return

    bot_user = await bot.get_me()
    mentioned = _is_bot_mentioned(message, bot_user.username or "")
    replied = _is_reply_to_bot(message, bot_user.id)

    if not mentioned and not replied:
        return

    # Build user text — strip @mention, prefix with sender name
    user_text = message.text
    if mentioned:
        user_text = _strip_bot_mention(user_text, bot_user.username or "")

    if not user_text.strip():
        return

    sender_name = message.from_user.first_name if message.from_user else "Кто-то"
    prefixed_text = f"[{sender_name}]: {user_text}"

    # Shared history per group — keyed by chat_id
    history_key = message.chat.id

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        reply = await claude_service.chat_simple(
            chat_id=history_key,
            user_text=prefixed_text,
            system_prompt=config.claude.family_system_prompt,
        )
    except Exception:
        logger.exception("Claude error in group chat %s", message.chat.id)
        await message.reply("Не смог обработать запрос. Попробуйте ещё раз.")
        return

    if len(reply) <= 4096:
        await message.reply(reply, parse_mode="Markdown")
    else:
        for i, chunk in enumerate(_split_message(reply)):
            if i == 0:
                await message.reply(chunk, parse_mode="Markdown")
            else:
                await message.answer(chunk, parse_mode="Markdown")


def _split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into chunks."""
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
