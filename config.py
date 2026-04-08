"""
Application configuration via Pydantic Settings v2.
All values are loaded from environment variables or .env file.
"""
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
    model: str = "claude-opus-4-6"
    max_tokens: int = 2048
    # How many past messages to keep per user (user + assistant pairs)
    history_limit: int = 20
    system_prompt: str = (
        "Ты — личный AI-ассистент. Отвечай кратко и по делу. "
        "Если нужно — используй Markdown (жирный, курсив, код). "
        "Язык ответа подстраивай под язык пользователя."
    )
    family_system_prompt: str = (
        "Ты — дружелюбный семейный помощник в групповом чате. "
        "Отвечай просто и понятно, без технических деталей. "
        "Помогай с бытовыми вопросами, рецептами, переводами, советами. "
        "Сообщения приходят в формате [Имя]: текст — обращайся к человеку по имени. "
        "Язык ответа подстраивай под язык сообщения."
    )


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram: TelegramConfig = TelegramConfig()
    claude: ClaudeConfig = ClaudeConfig()
    debug: bool = False
