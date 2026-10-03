from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CuraMind API"
    app_env: str = "development"
    database_url: str = "sqlite:///./curamind.db"
    jwt_secret: str = "development-only-change-me-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    refresh_cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allow_public_registration: bool = True
    default_workspace_name: str = "CuraMind Workspace"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self):
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.jwt_secret == "development-only-change-me-before-deployment" or len(settings.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be a unique random secret of at least 32 characters in production")
        if not settings.refresh_cookie_secure:
            raise RuntimeError("REFRESH_COOKIE_SECURE must be true in production")
        if settings.allow_public_registration:
            raise RuntimeError("Disable public registration in production until an invite/approval flow is configured")
    return settings