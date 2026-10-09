from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic.fields import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        populate_by_name=True,
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite:///./opspilot_telemetry.db",
        validation_alias="DATABASE_URL",
    )
    env: str = Field(default="development", validation_alias="ENV")
    allowed_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="ALLOWED_ORIGINS",
    )
    llm_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        validation_alias="LLM_PROVIDER",
    )
    llm_model: str = Field(default="", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=15, validation_alias="LLM_TIMEOUT_SECONDS")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    chaos_enabled: bool = Field(default=False, validation_alias="CHAOS_ENABLED")
    zero_touch_default: bool = Field(default=False, validation_alias="ZERO_TOUCH_DEFAULT")
    auth_enabled: bool = Field(default=False, validation_alias="AUTH_ENABLED")
    api_key: SecretStr | None = Field(default=None, validation_alias="API_KEY")
    monitor_enabled: bool = Field(default=True, validation_alias="MONITOR_ENABLED")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
