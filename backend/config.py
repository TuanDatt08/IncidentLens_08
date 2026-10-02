from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "RAV18 IncidentLens API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_url: str = "postgresql+psycopg2://rav18:rav18@localhost:5432/rav18"

    # Incident ingestion
    incident_storage_dir: str = "./backend/data/incidents"
    max_video_size_mb: int = Field(default=2048, ge=1)
    max_log_size_mb: int = Field(default=100, ge=1)
    ffprobe_bin: str = "ffprobe"
    ffmpeg_bin: str = "ffmpeg"

@lru_cache
def get_settings() -> Settings:
    return Settings()
