"""Environment settings for Pio_lab."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings loaded from environment and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Pio_lab"
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pio_lab"
    postgres_user: str = "pio_lab"
    postgres_password: str = "changeme"

    obsidian_vault_path: str = "./vault"

    anthropic_api_key: str | None = Field(default=None)
    anthropic_api_key_2: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    openai_api_key_2: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    gemini_api_key_2: str | None = Field(default=None)
    deepseek_api_key: str | None = Field(default=None)
    deepseek_api_key_2: str | None = Field(default=None)
    ollama_host: str | None = Field(default=None)
    ollama_default_model: str = "gpt-oss-20b"

    telegram_bot_token: str | None = Field(default=None)
    telegram_allowed_users: str | None = Field(default=None)
    discord_bot_token: str | None = Field(default=None)
    discord_guild_id: str | None = Field(default=None)
    zalo_oa_id: str | None = Field(default=None)
    zalo_oa_secret: str | None = Field(default=None)
    zalo_access_token: str | None = Field(default=None)
    web_ui_secret: str = "changeme-jwt-secret"
    web_ui_admin_password: str = "changeme"

    @field_validator("postgres_port", "app_port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("port must be between 1 and 65535")
        return value

    @property
    def postgres_dsn(self) -> str:
        """Return the async SQLAlchemy Postgres URL."""
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        database = self.postgres_db
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()


__all__ = ["Settings", "get_settings"]
