from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        populate_by_name=True,
        extra="ignore",
    )

    app_name: str = Field(
        default="Clarivo Ingestion Service",
        validation_alias=AliasChoices("APP_NAME", "app_name"),
    )
    environment: Literal["dev", "stage", "prod"] = Field(
        default="dev",
        validation_alias=AliasChoices("ENVIRONMENT", "environment"),
    )
    debug: bool = Field(default=True, validation_alias=AliasChoices("DEBUG", "debug"))
    clarification_min_length: int = Field(
        default=500,
        validation_alias=AliasChoices("CLARIFICATION_MIN_LENGTH", "clarification_min_length"),
    )
    clarification_timeout_hours: int = Field(
        default=24,
        validation_alias=AliasChoices("CLARIFICATION_TIMEOUT_HOURS", "clarification_timeout_hours"),
    )
    scope_generation_strategy: Literal["heuristic", "llm", "hybrid"] = Field(
        default="heuristic",
        validation_alias=AliasChoices("SCOPE_GENERATION_STRATEGY", "scope_generation_strategy"),
    )
    # Gemini API configuration (preferred)
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"),
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model"),
    )
    gemini_api_base: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias=AliasChoices("GEMINI_API_BASE", "gemini_api_base"),
    )
    
    # OpenAI API configuration
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
    )
    openai_api_url: AnyHttpUrl = Field(
        default="https://api.openai.com/v1/chat/completions",
        validation_alias=AliasChoices("OPENAI_API_URL", "openai_api_url"),
    )
    
    # Legacy Groq support (deprecated)
    groq_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"),
    )
    groq_model: str = Field(
        default="llama3-70b-8192",
        validation_alias=AliasChoices("GROQ_MODEL", "groq_model"),
    )
    groq_api_url: AnyHttpUrl = Field(
        default="https://api.groq.com/openai/v1/chat/completions",
        validation_alias=AliasChoices("GROQ_API_URL", "groq_api_url"),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

