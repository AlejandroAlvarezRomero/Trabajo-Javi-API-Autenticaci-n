"""Configuración global de la aplicación (lee variables de .env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    PROJECT_NAME: str = "Board Game Tracker API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # --- Base de datos ---
    DATABASE_URL: str = "sqlite:///./boardgames.db"

    # --- Seguridad / JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15          # Access Token: corta duración
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14            # Refresh Token: larga duración

    # --- Cookie HttpOnly del Refresh Token ---
    COOKIE_SECURE: bool = False                    # true en producción con HTTPS
    COOKIE_SAMESITE: str = "lax"

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # --- BoardGameGeek ---
    BGG_API_BASE: str = "https://boardgamegeek.com/xmlapi2"


settings = Settings()
