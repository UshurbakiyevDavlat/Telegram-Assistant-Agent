"""
Entry point for the Telegram Agent bot.

Wires together:
  - AppConfig (pydantic-settings)
  - ClaudeService (Anthropic SDK + agentic tool_use loop)
  - Tool system (KB, Notion, Web Search, Memory)
  - AuthMiddleware (user_id whitelist)
  - Root router (commands + group + personal)
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
from tools import init_tools, close_tools

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
    All wiring in one place — factory pattern.
    Services are injected into Dispatcher's workflow_data so they
    become available as handler arguments automatically.
    """
    claude_service = ClaudeService(config.claude)

    dp = Dispatcher(
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

    # Initialize tool system (KB, Notion, Web Search, Memory)
    await init_tools(config)

    bot = Bot(
        token=config.telegram.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher(config)

    logger.info("Starting Telegram Agent")
    logger.info("Personal model: %s", config.claude.personal_model)
    logger.info("Family model: %s", config.claude.family_model)
    logger.info("Allowed user IDs: %s", config.telegram.allowed_ids or "NONE")
    logger.info("KB endpoint: %s", config.kb.url)

    # Drop pending updates accumulated while the bot was offline
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await close_tools()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
