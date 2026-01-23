"""Configuration module for environment variables."""

import os
from typing import Optional


class Config:
    """Application configuration from environment variables."""

    # AI Configuration
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o")
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "300"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))

    # Metadata API Configuration
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    OMDB_API_KEY: str = os.getenv("OMDB_API_KEY", "")
    METADATA_API_TIMEOUT: int = int(os.getenv("METADATA_API_TIMEOUT", "30"))

    # Network Configuration
    HTTP_PROXY: Optional[str] = os.getenv("HTTP_PROXY", None)
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "3000"))
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Authentication
    AUTH_USERNAME: str = os.getenv("AUTH_USERNAME", "admin")
    AUTH_PASSWORD: str = os.getenv("AUTH_PASSWORD", "admin")
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "change-me-in-production")
    SESSION_EXPIRY: int = int(os.getenv("SESSION_EXPIRY", "86400"))  # 24 hours in seconds

    # Scheduling Configuration
    SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL", "3600"))  # 1 hour in seconds
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hour
    WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "30"))  # 30 seconds
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "7200"))  # 2 hours in seconds

    # Processing Configuration
    MAX_FAILURE_COUNT: int = int(os.getenv("MAX_FAILURE_COUNT", "3"))
    MAX_CONCURRENT_WORKERS: int = int(os.getenv("MAX_CONCURRENT_WORKERS", "2"))
    AUDIO_SEGMENT_DURATION: int = int(os.getenv("AUDIO_SEGMENT_DURATION", "300"))  # 5 minutes in seconds
    AUDIO_OVERLAP_DURATION: int = int(os.getenv("AUDIO_OVERLAP_DURATION", "10"))  # 10 seconds
    SCREENSHOTS_PER_SEGMENT: int = int(os.getenv("SCREENSHOTS_PER_SEGMENT", "10"))
    TARGET_SUBTITLE_LANGUAGE: str = os.getenv("TARGET_SUBTITLE_LANGUAGE", "en")
    TEMP_CLEANUP_ENABLED: bool = os.getenv("TEMP_CLEANUP_ENABLED", "true").lower() == "true"
    TEMP_RETENTION_HOURS: int = int(os.getenv("TEMP_RETENTION_HOURS", "24"))

    # Directory paths
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "/media")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp")
    CONFIG_DIR: str = os.getenv("CONFIG_DIR", "/config")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "/config/media_library.db")

    # Worker identification
    WORKER_ID: str = os.getenv("WORKER_ID", "worker-1")


# Global config instance
config = Config()
