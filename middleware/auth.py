"""
Auth middleware — blocks all updates from unauthorized chats.

Personal chat (private): only users whose ID is in TELEGRAM_ALLOWED_USER_IDS.
Group chat: only groups whose chat_id is in TELEGRAM_ALLOWED_GROUP_IDS.
  If TELEGRAM_ALLOWED_GROUP_IDS is empty, ALL groups are allowed (open mode).

If TELEGRAM_ALLOWED_USER_IDS is empty, ALL private users are blocked.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import TelegramObject, Update

from config import AppConfig

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Outer middleware — runs before any handler.
    Allows:
      - Group/supergroup chats in TELEGRAM_ALLOWED_GROUP_IDS (or all if empty)
      - Private chats only for whitelisted user IDs
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        config: AppConfig = data["config"]
        update: Update = data.get("event_update", event)  # type: ignore[assignment]

        # Extract chat type, chat_id, and user from the update
        chat_type: str | None = None
        chat_id: int | None = None
        user_id: int | None = None

        if hasattr(update, "message") and update.message:
            chat_type = update.message.chat.type
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id if update.message.from_user else None
        elif hasattr(update, "callback_query") and update.callback_query:
            if update.callback_query.message:
                chat_type = update.callback_query.message.chat.type
                chat_id = update.callback_query.message.chat.id
            user_id = update.callback_query.from_user.id

        # Group/supergroup chats — check whitelist (empty = allow all)
        if chat_type in (ChatType.GROUP, ChatType.SUPERGROUP):
            allowed_groups = config.telegram.allowed_groups
            if allowed_groups and chat_id not in allowed_groups:
                logger.warning("Blocked unauthorized group chat: %s", chat_id)
                return None
            return await handler(event, data)

        # Private chats — check whitelist
        if chat_type == ChatType.PRIVATE:
            allowed_ids = config.telegram.allowed_ids
            if user_id in allowed_ids:
                return await handler(event, data)
            else:
                logger.warning("Blocked unauthorized user: %s", user_id)
                # Silently drop — do not respond to unauthorized users
                return None

        # Unknown chat types — drop silently
        return None
