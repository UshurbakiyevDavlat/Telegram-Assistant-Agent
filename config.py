"""
Application configuration via Pydantic Settings v2.
All values are loaded from environment variables or .env file.
"""
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=".env", extra="ignore")

    bot_token: SecretStr
    # Comma-separated list of allowed Telegram user IDs (personal mode)
    allowed_user_ids: str = ""

    @property
    def allowed_ids(self) -> set[int]:
        """Parse TELEGRAM_ALLOWED_USER_IDS=123456,789012 into a set of ints."""
        if not self.allowed_user_ids:
            return set()
        return {int(uid.strip()) for uid in self.allowed_user_ids.split(",") if uid.strip()}


class ClaudeConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLAUDE_", env_file=".env", extra="ignore")

    api_key: SecretStr
    # Default models per mode — can be overridden at runtime via /model
    personal_model: str = "claude-opus-4-6"
    family_model: str = "claude-sonnet-4-5-20241022"
    max_tokens: int = 4096
    # How many past messages to keep per user (user + assistant pairs)
    history_limit: int = 30
    # Max tool_use loop iterations per request
    max_tool_turns: int = 10
    system_prompt: str = (
        "Ты — личный AI-ассистент Давлата. Отвечай кратко и по делу. "
        "Если нужно — используй Markdown (жирный, курсив, код). "
        "Язык ответа подстраивай под язык пользователя. "
        "Ты имеешь доступ к инструментам: база знаний (KB), Notion, веб-поиск, память. "
        "Используй их проактивно когда это поможет дать лучший ответ. "
        "Для вопросов о проектах, решениях, архитектуре — ВСЕГДА сначала ищи в KB."
    )
    family_system_prompt: str = (
        "Ты — дружелюбный семейный помощник в групповом чате. "
        "Отвечай просто и понятно, без технических деталей. "
        "Помогай с бытовыми вопросами, рецептами, переводами, советами. "
        "Сообщения приходят в формате [Имя]: текст — обращайся к человеку по имени. "
        "Язык ответа подстраивай под язык сообщения."
    )


class KBConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KB_", env_file=".env", extra="ignore")

    # MCP SSE endpoint — local on same VPS, no auth needed
    url: str = "http://127.0.0.1:8000/sse"
    # Token for external access (via nginx), leave empty for local
    token: str = ""
    # Timeout for KB calls (seconds)
    timeout: int = 30


class NotionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTION_", env_file=".env", extra="ignore")

    api_key: SecretStr = SecretStr("")
    # Default database ID for creating tasks
    tasks_database_id: str = ""
    # Notion API version
    api_version: str = "2022-06-28"


class MemoryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_", env_file=".env", extra="ignore")

    # SQLite database path for long-term memory
    db_path: str = "data/memory.db"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram: TelegramConfig = TelegramConfig()
    claude: ClaudeConfig = ClaudeConfig()
    kb: KBConfig = KBConfig()
    notion: NotionConfig = NotionConfig()
    memory: MemoryConfig = MemoryConfig()
    debug: bool = False
