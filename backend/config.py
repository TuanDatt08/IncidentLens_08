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

    # Local/test signed identities. Production requires a reviewed identity integration.
    v2_identity_secret: str = ""
    v2_provider_endpoint: str = ""
    v2_provider_model: str = ""
    v2_provider_revision: str = ""
    v2_external_egress_approved: bool = False
    v2_external_allowed_hosts: str = ""

    # Qwen local; paths are resolved by the backend, never supplied by HTTP users.
    qwen_runtime: Literal["llama_cpp", "ollama"] = "llama_cpp"
    qwen_ollama_model: str = "qwen2.5vl:7b"
    qwen_artifact_subdir: str = ""
    qwen_requests_dir: str | None = None
    qwen_inference_frame_limit: int | None = Field(default=None, ge=2, le=256)
    qwen_candidate_min_acceleration: float | None = Field(default=None, gt=0, le=50)
    qwen_endpoint: str = "http://127.0.0.1:8091/v1/chat/completions"
    qwen_model_dir: str = "./backend/data/model"
    qwen_model_file: str = "Qwen2.5-VL-7B-Instruct-Q8_0.gguf"
    qwen_projector_file: str = "mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf"
    qwen_server_bin: str = "llama-server"
    qwen_prompt_path: str = "./backend/data/promt.txt"
    qwen_log_prompt_path: str = "./backend/prompts/ollama_incident.txt"
    qwen_outputs_path: str = "./backend/data/outputs.txt"
    qwen_timeout_s: float = Field(default=600, gt=0, le=3600)
    qwen_startup_timeout_s: float = Field(default=120, gt=0, le=600)
    qwen_context_size: int = Field(default=32768, ge=4096, le=131072)
    qwen_batch_frames: int = Field(default=1, ge=1, le=32)
    qwen_sampling_fps: float = Field(default=4, gt=0, le=30)
    qwen_signal_thresholds: dict[str, float] = Field(default_factory=dict)
    qwen_delta_thresholds: dict[str, float] = Field(default_factory=dict)
    # V1 collision-relative CSV cannot imply where collision lies in the MP4.
    qwen_v1_log_offset_s: float | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()
