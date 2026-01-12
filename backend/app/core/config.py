from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "Orbit Backend"
    environment: str = Field("development", env="ENVIRONMENT")
    database_url: str = Field(..., env="DATABASE_URL")
    access_token_expires_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRES_MINUTES")
    refresh_token_expires_minutes: int = Field(60 * 24 * 7, env="REFRESH_TOKEN_EXPIRES_MINUTES")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    cors_origins: Union[List[AnyHttpUrl], List[str]] = Field(default_factory=list, env="CORS_ORIGINS")
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    google_allowed_redirects: List[str] = Field(default_factory=list, env="GOOGLE_ALLOWED_REDIRECTS")
    google_authorize_url: AnyHttpUrl = Field(
        "https://accounts.google.com/o/oauth2/v2/auth", env="GOOGLE_OAUTH_AUTHORIZE_URL"
    )
    google_token_url: AnyHttpUrl = Field(
        "https://oauth2.googleapis.com/token", env="GOOGLE_OAUTH_TOKEN_URL"
    )
    google_userinfo_url: AnyHttpUrl = Field(
        "https://openidconnect.googleapis.com/v1/userinfo", env="GOOGLE_OAUTH_USERINFO_URL"
    )
    google_state_ttl_seconds: int = Field(600, env="GOOGLE_STATE_TTL_SECONDS")
    smtp_host: Optional[str] = Field(None, env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(None, env="SMTP_FROM")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    password_reset_emails_per_hour: int = Field(5, env="PASSWORD_RESET_EMAILS_PER_HOUR")
    invite_emails_per_hour: int = Field(20, env="INVITE_EMAILS_PER_HOUR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()


