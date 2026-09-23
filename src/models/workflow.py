from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisJob:
    job_id: str
    incident_id: str
    status: JobStatus = JobStatus.QUEUED
    pass_number: int | None = None
    progress_done: int = 0
    progress_total: int = 0
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    result_uri: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class AuditEvent:
    event_id: str
    incident_id: str
    action: str
    actor: str = "system"
    role: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
