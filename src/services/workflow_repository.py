from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.models.incident import IncidentPackage, ProcessingStatus, ReviewStatus
from src.models.workflow import AnalysisJob, AuditEvent, JobStatus


class WorkflowRepository:
    """Small JSON-backed MVP store for jobs, reports, evidence and audit.

    The current repository has no SQLAlchemy/Alembic/Postgres implementation;
    keeping this store beside the existing package manifest makes the new API
    runnable without introducing an unrelated persistence migration.
    """

    def __init__(self, storage_root: str | Path) -> None:
        self.root = Path(storage_root).expanduser().resolve()
        self.path = self.root / "workflow.json"

    def create_job(self, incident_id: str) -> AnalysisJob:
        data = self._read()
        for raw in data["jobs"].values():
            if raw["incident_id"] == incident_id and raw["status"] in {
                JobStatus.QUEUED.value,
                JobStatus.RUNNING.value,
            }:
                return self._job_from_record(raw)
        job = AnalysisJob(job_id=f"JOB-{uuid.uuid4().hex[:12].upper()}", incident_id=incident_id)
        data["jobs"][job.job_id] = job.to_dict()
        self._write(data)
        return job

    def get_job(self, job_id: str) -> AnalysisJob | None:
        raw = self._read()["jobs"].get(job_id)
        return self._job_from_record(raw) if raw else None

    def save_job(self, job: AnalysisJob) -> AnalysisJob:
        job.updated_at = datetime.now(UTC).isoformat()
        data = self._read()
        data["jobs"][job.job_id] = job.to_dict()
        self._write(data)
        return job

    def get_report(self, incident_id: str) -> dict[str, Any]:
        data = self._read()
        report = data["reports"].get(incident_id)
        if report is None:
            now = datetime.now(UTC).isoformat()
            report = {
                "report_id": f"RPT-{uuid.uuid4().hex[:12].upper()}",
                "incident_id": incident_id,
                "incident_type": "UNAVAILABLE",
                "confidence": 0.0,
                "start_sec": 0.0,
                "critical_sec": 0.0,
                "end_sec": 0.0,
                "summary_text": "Analysis report is not available until a worker completes the job.",
                "unknowns": ["VLM/worker processing is not enabled in this MVP runtime."],
                "observations": [],
                "key_factors": [],
                "timeline": [],
                "evidence_ids": [],
                "review_status": ReviewStatus.DRAFT.value,
                "rejection_reason": None,
                "created_at": now,
                "updated_at": now,
            }
            data["reports"][incident_id] = report
            self._write(data)
        return dict(report)

    def save_report(self, incident_id: str, report: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data["reports"][incident_id] = dict(report)
        self._write(data)
        return dict(report)

    def get_evidence(self, incident_id: str) -> list[dict[str, Any]]:
        return list(self._read()["evidence"].get(incident_id, []))

    def add_audit(self, incident_id: str, action: str, *, metadata: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:12].upper()}",
            incident_id=incident_id,
            action=action,
            metadata=metadata or {},
        )
        data = self._read()
        data["audit"].setdefault(incident_id, []).append(event.to_dict())
        self._write(data)
        return event

    def get_audit(self, incident_id: str) -> list[dict[str, Any]]:
        return list(self._read()["audit"].get(incident_id, []))

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"jobs": {}, "reports": {}, "evidence": {}, "audit": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            value = {}
        return {
            "jobs": value.get("jobs", {}),
            "reports": value.get("reports", {}),
            "evidence": value.get("evidence", {}),
            "audit": value.get("audit", {}),
        }

    def _write(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _job_from_record(raw: dict[str, Any]) -> AnalysisJob:
        value = dict(raw)
        value["status"] = JobStatus(value["status"])
        # JSON uses the response spelling ``pass`` only at the API boundary.
        value["pass_number"] = value.pop("pass", value.get("pass_number"))
        return AnalysisJob(**value)


def incident_to_record(package: IncidentPackage) -> dict[str, Any]:
    return {
        "id": package.package_id,
        "package_id": package.package_id,
        "file_name": package.video_filename or Path(package.video_path).name or "incident.mp4",
        "created_at": package.created_at,
        "processing_status": package.processing_status.value,
        "review_status": package.review_status.value,
        "video_url": None,
        "frame_count": package.frame_count,
        "sync_offset": package.sync_offset,
        "video_metadata": package.video_metadata,
        "log_metadata": package.log_metadata,
        "error_code": package.error_code,
        "error_message": package.error_message,
    }


def processing_status_for_upload(package: IncidentPackage) -> ProcessingStatus:
    return package.processing_status
