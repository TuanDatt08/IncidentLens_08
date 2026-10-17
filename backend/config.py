from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def cloud_database_url(value: str) -> str:
    """Normalize PostgreSQL cloud URLs without changing encoded credentials."""
    parts = urlsplit(value)
    if parts.scheme not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError("Cloud database requires PostgreSQL")
    if not parts.hostname or not parts.username or not parts.path.strip("/"):
        raise ValueError("Cloud PostgreSQL requires host, user and database")
    query = parse_qsl(parts.query, keep_blank_values=True)
    modes = [item for key, item in query if key == "sslmode"]
    if any(mode not in {"require", "verify-ca", "verify-full"} for mode in modes):
        raise ValueError("Cloud PostgreSQL requires SSL")
    if not modes:
        query.append(("sslmode", "require"))
    if not any(key == "connect_timeout" for key, _ in query):
        query.append(("connect_timeout", "10"))
    return urlunsplit(("postgresql+psycopg2", parts.netloc, parts.path, urlencode(query), ""))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # App
    app_name: str = "RAV18 IncidentLens API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    runtime_log_dir: str = "./logs/runtime"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    auth_cookie_secure: bool = False
    auth_absolute_timeout_seconds: int = Field(default=28800, ge=60)
    auth_idle_timeout_seconds: int = Field(default=1800, ge=60)
    auth_email_failure_limit: int = Field(default=5, ge=1)
    auth_ip_failure_limit: int = Field(default=30, ge=1)

    @property
    def auth_cookie_name(self) -> str:
        return "__Host-incidentlens_session" if self.auth_cookie_secure else "incidentlens_session"

    @model_validator(mode="after")
    def validate_production_auth(self):
        from urllib.parse import urlsplit
        origins = [value.strip() for value in self.cors_origins.split(",") if value.strip()]
        for origin in origins:
            parsed = urlsplit(origin)
            if "*" in origin or parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins")
        if self.app_env == "production" and (not self.auth_cookie_secure or not origins or any(not value.startswith("https://") for value in origins)):
            raise ValueError("Production auth requires Secure cookies and explicit HTTPS origins")
        return self

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_cloud: bool = False
    database_url: str = "postgresql+psycopg2://rav18:rav18@localhost:5432/rav18"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value, info):
        return cloud_database_url(value) if info.data.get("database_cloud") else value

    # Incident ingestion
    incident_storage_dir: str = "./backend/data/incidents"
    gpu_media_base_url: str = ""

    @field_validator('gpu_media_base_url')
    @classmethod
    def validate_gpu_media_base_url(cls, value):
        if value:
            from urllib.parse import urlsplit
            parsed = urlsplit(value)
            if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
                raise ValueError('GPU media service must use the private loopback SSH tunnel')
        return value

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
    qwen_remote_ollama: bool = False
    worker_poll_s: float = Field(default=2, ge=1, le=300)
    qwen_ollama_model: Literal["qwen2.5vl:7b", "qwen3.5:9b"] = "qwen2.5vl:7b"
    # Ollama /v1 thinks by default for qwen3.5; "none" turns reasoning off. Unset = field not sent.
    qwen_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    # MP4-only analysis: "stages" = Stage A/B prompt pipeline, "two_tier" = window scan + actor-crop check.
    qwen_video_pipeline: Literal["stages", "two_tier"] = "stages"
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
    qwen_summary_prompt_path: str = "./backend/prompts/video_summary.txt"
    qwen_video_summary: bool = False
    qwen_outputs_path: str = "./logs/qwen/outputs.txt"
    qwen_timeout_s: float = Field(default=600, gt=0, le=3600)
    qwen_startup_timeout_s: float = Field(default=120, gt=0, le=600)
    qwen_context_size: int = Field(default=32768, ge=4096, le=131072)
    qwen_batch_frames: int = Field(default=1, ge=1, le=32)
    qwen_temporal_context: bool = False
    qwen_sampling_fps: float = Field(default=4, gt=0, le=30)
    qwen_trigger_min_priority: int = Field(default=1, ge=1, le=5)
    qwen_trigger_deceleration: float = Field(default=6, gt=0)
    qwen_braking_confirmation_s: float = Field(default=0, ge=0, le=10)
    qwen_flag_only: bool = False
    qwen_two_stage: bool = False
    qwen_signal_thresholds: dict[str, float] = Field(default_factory=dict)
    qwen_delta_thresholds: dict[str, float] = Field(default_factory=dict)
    # V1 collision-relative CSV cannot imply where collision lies in the MP4.
    qwen_v1_log_offset_s: float | None = None

    @model_validator(mode='after')
    def validate_temporal_budget(self):
        if self.qwen_temporal_context and self.qwen_batch_frames != 6:
            raise ValueError('Temporal trigger context requires a six-frame batch budget')
        if self.qwen_temporal_context and (self.qwen_batch_frames < 4 or (self.qwen_inference_frame_limit is not None and self.qwen_inference_frame_limit < 4)):
            raise ValueError('Temporal context requires at least four frames per batch and inference budget')
        if self.qwen_temporal_context and self.qwen_two_stage:
            raise ValueError('Select one candidate aggregation strategy: temporal context or frame-then-decision')
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
