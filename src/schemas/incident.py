import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.incident import IngestionStatus, ProcessingStatus, ReviewStatus


class VideoMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration: float = Field(..., ge=0)
    fps: float = Field(..., gt=0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class IncidentUploadResponse(BaseModel):
    """Response contract consumed by the IncidentLens frontend."""

    package_id: str
    incident_id: str
    status: IngestionStatus
    processing_status: ProcessingStatus
    review_status: ReviewStatus
    sync_offset: float | None
    frame_count: int = Field(..., ge=0)
    video_metadata: VideoMetadata | None = None
    warnings: list[str] = Field(default_factory=list)


class IncidentRecordResponse(BaseModel):
    """Incident metadata; report content is intentionally a separate resource."""

    id: str
    package_id: str
    file_name: str
    created_at: str
    processing_status: ProcessingStatus
    review_status: ReviewStatus
    video_url: str | None = None
    frame_count: int = Field(default=0, ge=0)
    sync_offset: float | None = None
    video_metadata: VideoMetadata | None = None
    log_metadata: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class ReportPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_type: str | None = None
    summary_text: str | None = None
    unknowns: list[str] | None = None
    observations: list[str] | None = None
    key_factors: list[str] | None = None
    start_sec: float | None = Field(default=None, ge=0)
    critical_sec: float | None = Field(default=None, ge=0)
    end_sec: float | None = Field(default=None, ge=0)
    timeline: list[dict[str, Any]] | None = None
    evidence_ids: list[str] | None = None


class AnalysisReport(BaseModel):
    """Structured report output, separate from factual incident metadata.

    The worker/VLM is not part of this MVP slice. Missing generated values are
    represented explicitly in the skeleton rather than inferred in the API.
    """

    report_id: str
    incident_id: str
    incident_type: str
    confidence: float = Field(ge=0, le=1)
    start_sec: float = Field(ge=0)
    critical_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    summary_text: str
    unknowns: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    key_factors: list[str] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    review_status: ReviewStatus
    rejection_reason: str | None = None
    created_at: str
    updated_at: str


class RejectReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


class EvidenceKind(StrEnum):
    VIDEO = "video"
    TELEMETRY = "telemetry"
    FRAME = "frame"
    ANNOTATION = "annotation"


class EvidenceTier(StrEnum):
    CORE = "core"
    BULKY = "bulky"


class Evidence(BaseModel):
    """The single Evidence contract used by API and frontend."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    evidence_id: str
    kind: EvidenceKind
    uri: str
    sha256: str
    time_range_s: tuple[float, float]
    tier: EvidenceTier | None = None
    bytes: int | None = Field(default=None, ge=0)
    media_type: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_legacy_fields(cls, value: Any) -> Any:
        """Accept persisted pre-contract records only at the boundary."""
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "time_range_s" not in data and {
            "timestamp_start",
            "timestamp_end",
        }.issubset(data):
            data["time_range_s"] = [data.pop("timestamp_start"), data.pop("timestamp_end")]
        if "uri" not in data and "clip_path" in data:
            data["uri"] = data.pop("clip_path")
        if "kind" not in data and "source_type" in data:
            data["kind"] = data.pop("source_type")
        if isinstance(data.get("kind"), str):
            data["kind"] = data["kind"].lower()
        return data

    @model_validator(mode="after")
    def validate_contract(self) -> "Evidence":
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("sha256 must be lowercase 64-character hexadecimal")
        if self.uri.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", self.uri):
            raise ValueError("uri must be a relative path")
        if self.time_range_s[0] < 0 or self.time_range_s[1] < self.time_range_s[0]:
            raise ValueError("time_range_s must be an ordered incident-relative range")
        return self


class JobProgress(BaseModel):
    done: int = Field(ge=0)
    total: int = Field(ge=0)


class AnalyzeResponse(BaseModel):
    job_id: str
    status: Literal["queued"]


class JobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    pass_number: Literal[1, 2] | None = Field(default=None, alias="pass")
    progress: JobProgress
    updated_at: str
    result_uri: str | None = None
    error: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AuditEventResponse(BaseModel):
    event_id: str
    incident_id: str
    action: str
    actor: str
    role: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IncidentErrorCode(StrEnum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_TOO_LARGE = "file_too_large"
    VIDEO_INVALID = "video_invalid"
    VIDEO_TOOL_UNAVAILABLE = "video_tool_unavailable"
    LOG_INVALID = "log_invalid"
    LOG_MISSING_TIMESTAMP = "log_missing_timestamp"
    STORAGE_ERROR = "storage_error"
    INGESTION_FAILED = "ingestion_failed"
