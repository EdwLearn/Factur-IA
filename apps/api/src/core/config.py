"""
Configuration management using Pydantic Settings.
Supports multiple environments and secret management.
"""

from pathlib import Path
from typing import Optional, Literal
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Busca el .env en la raíz del proyecto (2 niveles arriba de apps/api/src/core/)
_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    environment: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        description="Application environment"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8001, description="API port")
    api_url: str = Field(default="http://localhost:8001", description="API base URL")
    api_version: str = Field(default="1.0.0", description="API version")

    # Security
    secret_key: str = Field(
        ...,  # sin default — requerido obligatoriamente
        description="JWT secret key — must be set in .env"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8001"],
        description="Allowed CORS origins"
    )

    # Database - PostgreSQL
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="facturia_dev", description="Database name")
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(default="postgres", description="Database password")
    db_echo: bool = Field(default=False, description="Echo SQL queries")
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Database max overflow")

    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")
    aws_endpoint_url: Optional[str] = Field(default=None, description="AWS endpoint (for LocalStack)")

    # S3
    s3_document_bucket: str = Field(default="facturia-documents-dev", description="S3 bucket for documents")
    s3_max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size (10MB)")

    # Textract
    textract_region: str = Field(default="us-east-1", description="Textract region")
    textract_timeout: int = Field(default=300, description="Textract timeout in seconds")

    # ML Models
    ml_model_cache_dir: str = Field(default="/tmp/ml_models", description="ML model cache directory")
    enable_ml_cache: bool = Field(default=True, description="Enable ML model caching")
    ml_classification_threshold: float = Field(default=0.7, description="ML classification confidence threshold")

    # Processing
    duplicate_similarity_threshold: float = Field(default=0.90, description="Duplicate detection threshold")
    default_margin_percentage: float = Field(default=35.0, description="Default profit margin")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(default="json", description="Log format: json or text")

    # Alegra integration
    alegra_base_url: str = Field(
        default="https://sandbox.alegra.com/api/v1",
        description="Alegra API base URL (sandbox or production)"
    )
    alegra_encryption_key: str = Field(
        default="",
        description="Fernet key for encrypting Alegra API tokens at rest. Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

    # Wompi integration
    wompi_webhook_secret: str = Field(default="", description="Wompi webhook HMAC secret")

    # Feature Flags
    enable_ml_recommendations: bool = Field(default=True, description="Enable ML recommendations")
    enable_duplicate_detection: bool = Field(default=True, description="Enable duplicate detection")

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @property
    def database_url(self) -> str:
        """Synchronous database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        """Check if running tests."""
        return self.environment == "test"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance for backward compatibility
settings = get_settings()
