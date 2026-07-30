"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the meal planner service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    openai_api_key: SecretStr | None = None
    openai_model_name: str = "gpt-4o-mini"
    model_provider: Literal["openai", "anthropic"] = "openai"
    anthropic_api_key: SecretStr | None = None
    anthropic_model_name: str = "claude-3-5-sonnet-latest"

    default_servings: int = Field(default=2, ge=1, le=20)
    default_weekly_budget: float = Field(default=150.0, gt=0)
    default_currency: str = "USD"
    max_meals_per_day: int = Field(default=4, ge=1, le=8)
    enable_bulk_optimization: bool = True

    crew_verbose: bool = True
    crew_memory: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def llm_model(self) -> str:
        if self.model_provider == "anthropic":
            return self.anthropic_model_name
        return self.openai_model_name


@lru_cache
def get_settings() -> Settings:
    return Settings()
