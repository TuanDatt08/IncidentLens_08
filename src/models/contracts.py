"""Public RAV18 v1.1 shapes and validated VLM boundary values."""

from __future__ import annotations

import math
import re
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProcessingState = Literal["UPLOADED", "READY", "PROCESSING", "COMPLETED", "FAILED"]
JobState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
ReviewState = Literal["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"]


class IncidentRecordV1(BaseModel):
    """Factual generator data; new generator fields remain readable."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    recorded_at: str | None = None
    scenario: str | None = None
    template: Literal["rear_end", "pedestrian"] | None = None
    source: dict[str, Any] | None = None
    collision: dict[str, Any] | None = None
    ego: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None


class IncidentWindow(BaseModel):
    start: float
    critical: float
    end: float

    @model_validator(mode="after")
    def ordered(self) -> IncidentWindow:
        if not all(math.isfinite(x) for x in (self.start, self.critical, self.end)):
            raise ValueError("incident window must be finite")
        if not self.start <= self.critical <= self.end:
            raise ValueError("incident window must contain critical time")
        return self


class AnalysisReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    incident_detected: bool
    incident_type: str | None = None
    incident_window: IncidentWindow | None = None
    summary: str | None = None
    timeline: list[Any] = Field(default_factory=list)
    key_factors: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    unknowns: list[Any] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    review_status: ReviewState = "DRAFT"
    version: int = Field(default=1, ge=1)
    created_at: str | None = None
    updated_at: str | None = None


class EvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    kind: Literal["video", "telemetry", "frame", "annotation"]
    uri: str
    sha256: str
    time_range_s: tuple[float, float]
    tier: Literal["core", "bulky"] | None = None
    bytes: int | None = Field(default=None, ge=0)
    media_type: str | None = None

    @model_validator(mode="after")
    def valid_asset(self) -> EvidenceV1:
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("sha256 must be 64 lowercase hex digits")
        normalized = self.uri.replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or ":" in normalized
            or any(part in (".", "..") for part in normalized.split("/"))
        ):
            raise ValueError("uri must be a safe relative path")
        start, end = self.time_range_s
        if not (math.isfinite(start) and math.isfinite(end) and start <= end):
            raise ValueError("time_range_s must be finite and ordered")
        return self


class JobProgress(BaseModel):
    done: int = Field(ge=0)
    total: int | None = Field(default=None, ge=0)


class JobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str
    status: JobState
    pass_number: Literal[1, 2] | None = Field(default=None, alias="pass")
    progress: JobProgress
    updated_at: str
    result_uri: str | None = None
    error: dict[str, Any] | None = None

    @model_validator(mode="after")
    def valid_state(self) -> JobResponse:
        if self.status == "queued" and self.pass_number is not None:
            raise ValueError("queued job cannot have a pass")
        if self.result_uri is not None and self.status != "succeeded":
            raise ValueError("result_uri is only available after success")
        if self.error is not None and self.status != "failed":
            raise ValueError("error is only available after failure")
        return self


class LocalizationResult(BaseModel):
    incident_detected: bool
    candidate_start: float | None = None
    critical_time: float | None = None
    candidate_end: float | None = None
    incident_type: str | None = None
    evidence_timestamps: list[float] = Field(default_factory=list)
    # Internal mapping from collision-relative seconds to MP4 seconds.
    collision_offset_in_video_s: float | None = None

    @model_validator(mode="after")
    def valid_window(self) -> LocalizationResult:
        if self.collision_offset_in_video_s is not None and (
            not math.isfinite(self.collision_offset_in_video_s) or self.collision_offset_in_video_s < 0
        ):
            raise ValueError("collision_offset_in_video_s must be finite and nonnegative")
        if self.incident_detected:
            if None in (self.candidate_start, self.critical_time, self.candidate_end):
                raise ValueError("detected incident requires candidate window")
            IncidentWindow(start=self.candidate_start, critical=self.critical_time, end=self.candidate_end)
            if any(not math.isfinite(t) or not self.candidate_start <= t <= self.candidate_end for t in self.evidence_timestamps):
                raise ValueError("evidence timestamp outside candidate window")
        return self


class AnalysisResult(BaseModel):
    incident_detected: bool
    incident_type: str | None = None
    incident_window: IncidentWindow | None = None
    summary: str | None = None
    timeline: list[Any] = Field(default_factory=list)
    key_factors: list[Any] = Field(default_factory=list)
    observations: list[Any] = Field(default_factory=list)
    unknowns: list[Any] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
