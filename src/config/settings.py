"""
Configuration settings
"""
import os
from typing import Optional

class Settings:
    """Application settings"""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    
    # AWS Configuration
    aws_region: str = "us-east-1"
    s3_document_bucket: str = "document-processing-uploads"
    
    # PostgreSQL Database Configuration
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "document_processing"
    db_user: str = "postgres"
    db_password: str = "postgres"
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    
    def __init__(self):
        # Load from environment variables if available
        self.api_host = os.getenv("API_HOST", self.api_host)
        self.api_port = int(os.getenv("API_PORT", self.api_port))
        self.environment = os.getenv("ENVIRONMENT", self.environment)
        self.aws_region = os.getenv("AWS_REGION", self.aws_region)
        
        # Database configuration from environment
        self.db_host = os.getenv("DB_HOST", self.db_host)
        self.db_port = int(os.getenv("DB_PORT", self.db_port))
        self.db_name = os.getenv("DB_NAME", self.db_name)
        self.db_user = os.getenv("DB_USER", self.db_user)
        self.db_password = os.getenv("DB_PASSWORD", self.db_password)
    
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def async_database_url(self) -> str:
        """Async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

# Global settings instance
settings = Settings()
