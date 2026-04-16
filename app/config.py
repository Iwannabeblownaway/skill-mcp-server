"""
Application configuration module using Pydantic Settings.

Loads configuration from environment variables with sensible defaults.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields in .env
    )

    # Database Configuration
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=3306, description="Database port (MySQL)")
    DB_USER: str = Field(default="root", description="Database username")
    DB_PASSWORD: str = Field(default="", description="Database password")
    DB_NAME: str = Field(default="skill_mcp", description="Database name")

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: str = Field(default="", description="Redis password")

    # Security Configuration
    API_KEY_LENGTH: int = Field(default=32, description="Length of generated API keys")
    SECRET_KEY: str = Field(
        default="change-me-in-production", description="Secret key for signing"
    )

    # Application Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Application port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    @property
    def database_url(self) -> str:
        """Generate database URL from settings."""
        return (
            f"mysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def redis_url(self) -> str:
        """Generate Redis URL from settings."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Global settings instance
settings = Settings()
