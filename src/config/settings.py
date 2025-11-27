"""Configuration management for the chatbot application."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenRouterConfig(BaseSettings):
    """OpenRouter API configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = Field(default="mock_api_key_for_testing", alias="OPENROUTER_API_KEY")
    model: str = Field(default="openai/gpt-oss-20b", alias="OPENROUTER_MODEL")
    base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )


class ApplicationConfig(BaseSettings):
    """Core application configuration."""

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    max_conversation_turns: int = Field(default=20, alias="MAX_CONVERSATION_TURNS")
    response_timeout_seconds: int = Field(default=30, alias="RESPONSE_TIMEOUT_SECONDS")
    otlp_endpoint: str | None = Field(default=None, alias="OTLP_ENDPOINT")


class MemoryConfig(BaseSettings):
    """Memory and persistence configuration."""

    backend: str = Field(default="inmemory", alias="MEMORY_BACKEND")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    mongodb_url: str | None = Field(default=None, alias="MONGODB_URL")
    mongodb_database: str = Field(default="orchestration", alias="MONGODB_DATABASE")


class VectorDBConfig(BaseSettings):
    """Vector database configuration."""

    chromadb_path: str = Field(default="./data/chromadb", alias="CHROMADB_PATH")
    qdrant_url: str | None = Field(default=None, alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    pgvector_url: str | None = Field(default=None, alias="PGVECTOR_URL")


class MessageBrokerConfig(BaseSettings):
    """Message broker configuration."""

    rabbitmq_url: str | None = Field(default=None, alias="RABBITMQ_URL")
    max_connections: int = Field(default=10, alias="RABBITMQ_MAX_CONNECTIONS")
    max_channels: int = Field(default=100, alias="RABBITMQ_MAX_CHANNELS")


class TelemetryConfig(BaseSettings):
    """Observability and telemetry configuration."""

    enable_telemetry: bool = Field(default=True, alias="ENABLE_TELEMETRY")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")


class SecurityConfig(BaseSettings):
    """Security and authentication configuration."""

    secret_key: str = Field(default="your-secret-key-change-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    encryption_key: str | None = Field(default=None, alias="ENCRYPTION_KEY")
    
    # Rate limiting
    requests_per_minute: int = Field(default=60, alias="REQUESTS_PER_MINUTE")
    requests_per_hour: int = Field(default=1000, alias="REQUESTS_PER_HOUR")
    api_key_requests_per_minute: int = Field(default=100, alias="API_KEY_REQUESTS_PER_MINUTE")
    api_key_requests_per_hour: int = Field(default=5000, alias="API_KEY_REQUESTS_PER_HOUR")


class Settings(BaseSettings):
    """Root settings container."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    app: ApplicationConfig = Field(default_factory=ApplicationConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    message_broker: MessageBrokerConfig = Field(default_factory=MessageBrokerConfig)


# Global settings instance
_settings: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Get or initialize the global settings instance."""
    global _settings
    if _settings is None or reload:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing or reloading config)."""
    global _settings
    _settings = None
