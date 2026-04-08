"""
Entry point for the Telegram Agent bot.

Wires together:
  - AppConfig (pydantic-settings)
  - ClaudeService (Anthropic SDK + history)
  - AuthMiddleware (user_id whitelist)
  - Root router (commands + personal chat)
  - Dispatcher + Bot (aiogram 3)

Run:
    python bot.py
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import AppConfig
from handlers import root_router
from middleware import AuthMiddleware
from services import ClaudeService

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Dispatcher factory
# ------------------------------------------------------------------

def create_dispatcher(config: AppConfig) -> Dispatcher:
    """
    All wiring in one place, following the factory pattern.
    Services are injected into Dispatcher's workflow_data so they
    become available as handler arguments automatically.
    """
    claude_service = ClaudeService(config.claude)

    dp = Dispatcher(
        # MemoryStorage is fine for Phase 1 (no FSM states yet)
        storage=MemoryStorage(),
        # Injected into every handler via dependency injection
        config=config,
        claude_service=claude_service,
    )

    # Auth middleware — runs before all handlers
    dp.update.outer_middleware(AuthMiddleware())

    # Register all routers
    dp.include_router(root_router)

    return dp


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

async def main() -> None:
    config = AppConfig()

    bot = Bot(
        token=config.telegram.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher(config)

    logger.info("Starting Telegram Agent (model: %s)", config.claude.model)
    logger.info("Allowed user IDs: %s", config.telegram.allowed_ids or "NONE — bot is closed")

    # Drop pending updates accumulated while the bot was offline
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
