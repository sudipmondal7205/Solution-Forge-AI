"""
Configuration management.

Reads environment variables from .env (and from the system environment)
and exposes them as a typed Settings object.

Why: We keep all configuration (MongoDB URI, JWT secret, LLM keys) in one
place instead of scattering strings across the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "solutionforge"

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 720

    SERPER_API_KEY: str
    COHERE_API_KEY: str
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()