"""
Configuration settings for the FastAPI server
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # App configuration
    app_name: str = "UK Postcodes API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server configuration
    host: str = "0.0.0.0"  # nosec B104 - required for Docker container networking
    port: int = 8000
    reload: bool = False

    # CORS configuration
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database configuration (passed to library)
    database_path: Optional[str] = None
    auto_download: bool = True

    # API configuration
    max_bulk_requests: int = 100
    max_text_length: int = 10000
    max_search_results: int = 100
    max_area_results: int = 10000

    # Rate limiting (if implemented)
    rate_limit_requests_per_minute: int = 100

    model_config = {"env_prefix": "UK_POSTCODES_", "env_file": ".env"}


# Global settings instance
settings = Settings()
