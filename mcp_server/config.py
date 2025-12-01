"""
Configuration management for MCP Server
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """MCP Server configuration loaded from environment variables"""

    # Server Configuration
    MCP_PORT: int = 8001
    LOG_LEVEL: str = "DEBUG"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./mcp.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    EVENT_RETENTION_DAYS: int = 90

    # Auth Service Integration
    AUTH_SERVICE_URL: str = "http://auth-service:8000"

    # Fraud Detection Configuration
    FRAUD_THRESHOLD: float = 0.7
    RULE_BASED_FALLBACK: bool = True
    BAML_ENABLED: bool = False
    BAML_TIMEOUT_MS: int = 5000

    # Alert Configuration
    ALERT_CONSOLIDATION_WINDOW_MINUTES: int = 5
    MAX_EVENTS_PER_ALERT: int = 10

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
