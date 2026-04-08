"""
Bot commands: /start, /help, /clear.

These handlers work in both private and group chats.
In group chats /clear only resets history for the specific user who called it.
"""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from services import ClaudeService

logger = logging.getLogger(__name__)

commands_router = Router(name="commands")


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------

@commands_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        "Я твой личный AI-ассистент на базе Claude.\n\n"
        "Просто напиши мне что-нибудь — отвечу сразу.\n\n"
        "Команды:\n"
        "/help — что умею\n"
        "/clear — очистить историю диалога"
    )


# ------------------------------------------------------------------
# /help
# ------------------------------------------------------------------

@commands_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🤖 <b>Telegram Agent — справка</b>\n\n"
        "<b>Как пользоваться:</b>\n"
        "Просто пиши сообщение — я отвечу с учётом контекста нашего диалога.\n\n"
        "<b>Команды:</b>\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/clear — сбросить историю разговора (начать заново)\n\n"
        "<b>Особенности:</b>\n"
        "• Помню контекст последних сообщений\n"
        "• Поддерживаю Markdown в ответах\n"
        "• Работаю на Claude claude-opus-4-6",
        parse_mode="HTML",
    )


# ------------------------------------------------------------------
# /clear
# ------------------------------------------------------------------

@commands_router.message(Command("clear"))
async def cmd_clear(message: Message, claude_service: ClaudeService) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await message.answer("Не удалось определить пользователя.")
        return

    claude_service.clear_history(user_id)
    await message.answer(
        "🗑 История диалога очищена.\n"
        "Начинаем разговор с чистого листа!"
    )
