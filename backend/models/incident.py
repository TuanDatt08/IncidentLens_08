from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class IngestionStatus(StrEnum):
    VALIDATING = "VALIDATING"
    EXTRACTING = "EXTRACTING"
    SYNCHRONIZING = "SYNCHRONIZING"
    READY = "READY"
    FAILED = "FAILED"


class ProcessingStatus(StrEnum):
    """Pipeline state exposed by the incident API."""

    UPLOADED = "UPLOADED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewStatus(StrEnum):
    """Human review state, intentionally separate from pipeline state."""

    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class IncidentPackage:
    """Persisted ingestion package metadata.

    This is intentionally limited to upload/ingestion data. IncidentDraft,
    Evidence, VLM metadata and analysis state belong to a later workflow.
    """

    package_id: str
    status: IngestionStatus
    video_path: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    # ``status`` is retained as an ingestion compatibility field for existing
    # clients/manifests. These fields are the new public workflow contract.
    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    review_status: ReviewStatus = ReviewStatus.DRAFT
    video_filename: str | None = None
    log_path: str | None = None
    normalized_log_path: str | None = None
    frames_path: str | None = None
    frame_count: int = 0
    sync_offset: float | None = None
    video_metadata: dict[str, Any] | None = None
    log_metadata: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["processing_status"] = self.processing_status.value
        data["review_status"] = self.review_status.value
        return data
