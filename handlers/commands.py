"""
Bot commands: /start, /help, /clear, /model.

These handlers work in both private and group chats.
"""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery

from services import ClaudeService

logger = logging.getLogger(__name__)

commands_router = Router(name="commands")

# Available models for the /model command
AVAILABLE_MODELS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20241022",
    "haiku": "claude-haiku-4-5-20251001",
}


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------

@commands_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {user_name}!\n\n"
        "Я твой личный AI-ассистент на базе Claude.\n\n"
        "Просто напиши мне что-нибудь — отвечу сразу.\n\n"
        "<b>Команды:</b>\n"
        "/help — что умею\n"
        "/clear — очистить историю диалога\n"
        "/model — выбрать модель Claude",
        parse_mode="HTML",
    )


# ------------------------------------------------------------------
# /help
# ------------------------------------------------------------------

@commands_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Telegram Agent — справка</b>\n\n"
        "<b>Как пользоваться:</b>\n"
        "Просто пиши сообщение — я отвечу с учётом контекста.\n"
        "Можешь отправить фото — распознаю и отвечу.\n\n"
        "<b>Команды:</b>\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/clear — сбросить историю\n"
        "/model — выбрать модель (opus/sonnet/haiku)\n\n"
        "<b>Инструменты (личный чат):</b>\n"
        "• KB — поиск по базе знаний (проекты, решения)\n"
        "• Notion — поиск страниц, создание задач\n"
        "• Web Search — поиск в интернете\n"
        "• Memory — долгосрочная память (запоминаю факты)\n"
        "• Vision — анализ фотографий\n\n"
        "<b>В групповом чате:</b>\n"
        "Упомяни @бот или ответь реплаем на моё сообщение.",
        parse_mode="HTML",
    )


# ------------------------------------------------------------------
# /clear
# ------------------------------------------------------------------

@commands_router.message(Command("clear"))
async def cmd_clear(message: Message, claude_service: ClaudeService) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        return

    claude_service.clear_history(user_id)
    await message.answer("История диалога очищена. Начинаем с чистого листа!")


# ------------------------------------------------------------------
# /model — show current model + switch keyboard
# ------------------------------------------------------------------

@commands_router.message(Command("model"))
async def cmd_model(message: Message, claude_service: ClaudeService) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        return

    current = claude_service.get_model(user_id)
    # Find short name for current model
    current_short = next(
        (k for k, v in AVAILABLE_MODELS.items() if v == current),
        current,
    )

    builder = InlineKeyboardBuilder()
    for short_name, model_id in AVAILABLE_MODELS.items():
        marker = " ✓" if model_id == current else ""
        builder.button(
            text=f"{short_name.capitalize()}{marker}",
            callback_data=f"model:{short_name}",
        )
    builder.adjust(3)

    await message.answer(
        f"Текущая модель: <b>{current_short}</b>\n"
        f"<code>{current}</code>\n\n"
        "Выбери модель:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


# ------------------------------------------------------------------
# Callback: model selection
# ------------------------------------------------------------------

@commands_router.callback_query(lambda c: c.data and c.data.startswith("model:"))
async def callback_model_select(
    callback: CallbackQuery,
    claude_service: ClaudeService,
) -> None:
    user_id = callback.from_user.id
    short_name = callback.data.split(":")[1]  # type: ignore[union-attr]

    model_id = AVAILABLE_MODELS.get(short_name)
    if not model_id:
        await callback.answer("Неизвестная модель", show_alert=True)
        return

    claude_service.set_model(user_id, model_id)
    await callback.answer(f"Модель переключена на {short_name.capitalize()}")

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"Модель: <b>{short_name.capitalize()}</b>\n"
        f"<code>{model_id}</code>",
        parse_mode="HTML",
    )
