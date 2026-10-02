"""Persistent analysis jobs and PostgreSQL worker leasing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from backend.db import session_scope
from backend.errors import ApiError
from backend.models.contracts import JobResponse
from backend.models.tables import AuditEvent, Incident, Job

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    incident_id: str
    attempt: int


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat().replace("+00:00", "Z")


def _job_dict(job: Job) -> dict:
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        **{"pass": job.pass_number},
        progress={"done": job.progress_done, "total": job.progress_total},
        updated_at=_iso(job.updated_at),
        result_uri=job.result_uri,
        error=job.error,
    ).model_dump(by_alias=True)


def create_job(incident_id: str) -> dict:
    try:
        with session_scope() as session:
            incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id).with_for_update())
            if incident is None:
                raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
            active = session.scalar(select(Job).where(Job.incident_id == incident.id, Job.status.in_(["queued", "running"])))
            if active is not None:
                raise ApiError("ANALYSIS_ALREADY_RUNNING", "Analysis is already running.", 409)
            if incident.processing_status not in {"READY", "FAILED"}:
                raise ApiError("INCIDENT_NOT_READY", "Incident is not ready for analysis.", 409)
            job_id = f"JOB-{uuid4().hex[:12].upper()}"
            job = Job(job_id=job_id, incident_id=incident.id, status="queued", progress_done=0, progress_total=None, attempt=0)
            session.add(job)
            incident.processing_status = "PROCESSING"
            session.add(AuditEvent(incident_id=incident.id, action="ANALYSIS_STARTED", actor="system", event_metadata={"job_id": job_id}))
            session.flush()
            return {"job_id": job_id, "incident_id": incident_id, "status": "queued"}
    except IntegrityError as exc:
        raise ApiError("ANALYSIS_ALREADY_RUNNING", "Analysis is already running.", 409) from exc


def get_job(job_id: str) -> dict:
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id))
        if job is None:
            raise ApiError("JOB_NOT_FOUND", "Job was not found.", 404)
        return _job_dict(job)


def claim_job(job_id: str | None = None) -> ClaimedJob | None:
    """Claim one queued or expired job; SKIP LOCKED prevents duplicate PG workers."""
    with session_scope() as session:
        current = datetime.now(UTC)
        query = select(Job).where(or_(Job.status == "queued", and_(Job.status == "running", Job.lease_until < current)))
        if job_id is not None:
            query = query.where(Job.job_id == job_id)
        job = session.scalar(query.order_by(Job.created_at, Job.id).with_for_update(skip_locked=True).limit(1))
        if job is None:
            return None
        incident = session.get(Incident, job.incident_id)
        if job.attempt >= MAX_ATTEMPTS:
            job.status = "failed"
            job.error = {"code": "VLM_FAILED", "message": "Worker retry limit reached.", "details": None}
            job.completed_at = current
            job.updated_at = current
            incident.processing_status = "FAILED"
            session.add(AuditEvent(incident_id=incident.id, action="ANALYSIS_FAILED", actor="system", event_metadata={"job_id": job.job_id, "code": "VLM_FAILED"}))
            return None
        job.status = "running"
        job.attempt += 1
        job.started_at = job.started_at or current
        job.lease_until = current + timedelta(seconds=LEASE_SECONDS)
        job.updated_at = current
        return ClaimedJob(job.job_id, incident.incident_id, job.attempt)


def heartbeat(job_id: str, *, pass_number: int, done: int, total: int | None, expected_attempt: int | None = None) -> None:
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id).with_for_update())
        if job is None:
            raise ApiError("JOB_NOT_FOUND", "Job was not found.", 404)
        if job.status != "running":
            raise ApiError("INVALID_REPORT_STATE", "Job is not running.", 409)
        if expected_attempt is not None and job.attempt != expected_attempt:
            raise ApiError("JOB_LEASE_LOST", "Job lease belongs to another worker.", 409)
        current = datetime.now(UTC)
        job.pass_number = pass_number
        job.progress_done = done
        job.progress_total = total
        job.lease_until = current + timedelta(seconds=LEASE_SECONDS)
        job.updated_at = current


def fail_job(job_id: str, code: str, message: str, *, expected_attempt: int | None = None) -> None:
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id).with_for_update())
        if job is None:
            raise ApiError("JOB_NOT_FOUND", "Job was not found.", 404)
        if job.status in {"failed", "succeeded", "cancelled"}:
            return
        if expected_attempt is not None and job.attempt != expected_attempt:
            raise ApiError("JOB_LEASE_LOST", "Job lease belongs to another worker.", 409)
        current = datetime.now(UTC)
        job.status = "failed"
        job.error = {"code": code, "message": message, "details": None}
        job.lease_until = None
        job.completed_at = current
        job.updated_at = current
        incident = session.get(Incident, job.incident_id)
        incident.processing_status = "FAILED"
        session.add(AuditEvent(incident_id=incident.id, action="ANALYSIS_FAILED", actor="system", event_metadata={"job_id": job_id, "code": code}))
