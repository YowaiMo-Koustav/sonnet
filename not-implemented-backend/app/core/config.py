from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import logging
import sys


def setup_logging(debug: bool = False):
    """
    Configure application logging.
    
    Sets up structured logging with appropriate levels and formats.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",  # Look for .env in current directory
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'  # Ignore unknown fields from .env
    )
    
    # Application
    app_name: str = "Sonnet"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database
    database_url: Optional[str] = None
    
    # File Storage
    pdf_storage_path: str = "./storage/pdfs"
    
    # Redis Cache
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_ttl_schemes: int = 3600  # 1 hour for popular schemes
    cache_ttl_locations: int = 86400  # 24 hours for location hierarchies
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # AI Services
    gemini_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    # Setup logging when settings are loaded
    setup_logging(debug=settings.debug)
    return settings
