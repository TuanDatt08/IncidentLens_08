"""Durable V2 leases/checkpoints with reservation before expensive calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError

from backend.db import session_scope
from backend.errors import ApiError
from backend.models.tables_v2 import JobV2, RecordingV2
from backend.services.identity import Principal, authorize

LEASE_SECONDS = 120
STAGES = {"QUEUED", "VALIDATION", "SYNCHRONIZATION", "DETECTION", "EXTRACTION", "PRIVACY", "ANALYSIS", "EVIDENCE_VALIDATION", "COMPLETED", "FAILED", "CANCELLED"}
DEFAULT_BUDGET = {"max_attempts": 3, "max_calls": 200, "calls_used": 0, "max_disk_bytes": 2 * 1024**3, "max_wall_s": 36000, "max_scan_frames": 1000}


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    recording_id: str
    provider_profile: str
    attempt: int
    checkpoints: dict
    budget: dict


def job_envelope(job: JobV2) -> dict:
    return {"job_id": job.job_id, "recording_id": job.recording_id, "status": job.status, "stage": job.stage, "attempt": job.attempt, "progress": {"done": len(job.checkpoints), "total": None}, "coverage": job.coverage, "budget": job.budget, "partial_results": list(job.checkpoints.values()), "error": {"code": job.error_code, "message": "Processing could not be completed."} if job.error_code else None}


def create_job(recording_id: str, profile: str, key: str, actor: Principal) -> dict:
    authorize(actor, recording_id, "Engineer")
    if not key.strip() or len(key) > 128:
        raise ApiError("INVALID_IDEMPOTENCY_KEY", "Idempotency-Key required (1–128 characters).", 422)
    try:
        with session_scope() as session:
            existing = session.scalar(select(JobV2).where(JobV2.recording_id == recording_id, JobV2.idempotency_key == key))
            if existing is not None:
                if existing.provider_profile != profile:
                    raise ApiError("IDEMPOTENCY_CONFLICT", "Key belongs to a different provider profile.", 409)
                return {"job_id": existing.job_id, "recording_id": recording_id}
            if session.get(RecordingV2, recording_id) is None:
                raise ApiError("NOT_FOUND", "Recording not found.", 404)
            active = session.scalar(select(JobV2).where(JobV2.recording_id == recording_id, JobV2.status.in_(["queued", "running"])))
            if active is not None:
                raise ApiError("ANALYSIS_ALREADY_RUNNING", "Analysis already running.", 409, {"job_id": active.job_id})
            job = JobV2(job_id="JOB-" + uuid4().hex, recording_id=recording_id, idempotency_key=key, provider_profile=profile, status="queued", stage="QUEUED", attempt=0, checkpoints={}, coverage={}, budget=dict(DEFAULT_BUDGET))
            session.add(job)
            session.flush()
            return {"job_id": job.job_id, "recording_id": recording_id}
    except IntegrityError as exc:
        raise ApiError("ANALYSIS_ALREADY_RUNNING", "Concurrent analysis exists; recover active job.", 409) from exc


def claim_job(job_id: str | None = None) -> JobClaim | None:
    with session_scope() as session:
        current = datetime.now(UTC)
        query = select(JobV2).where(or_(JobV2.status == "queued", and_(JobV2.status == "running", JobV2.lease_until < current)))
        if job_id:
            query = query.where(JobV2.job_id == job_id)
        job = session.scalar(query.order_by(JobV2.created_at).with_for_update(skip_locked=True).limit(1))
        if job is None:
            return None
        if job.attempt >= job.budget["max_attempts"]:
            job.status, job.stage, job.error_code = "failed", "FAILED", "ATTEMPT_BUDGET_EXHAUSTED"
            return None
        attempt = job.attempt
        changed = session.execute(update(JobV2).where(JobV2.job_id == job.job_id, JobV2.attempt == attempt, or_(JobV2.status == "queued", and_(JobV2.status == "running", JobV2.lease_until < current))).values(status="running", attempt=attempt + 1, lease_until=current + timedelta(seconds=LEASE_SECONDS), started_at=job.started_at or current).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            return None
        session.refresh(job)
        return JobClaim(job.job_id, job.recording_id, job.provider_profile, job.attempt, job.checkpoints, job.budget)


def owned_job(session, job_id: str, attempt: int, *, enforce_wall: bool = True) -> JobV2:
    current = datetime.now(UTC)
    job = session.scalar(select(JobV2).where(JobV2.job_id == job_id, JobV2.status == "running", JobV2.attempt == attempt, JobV2.lease_until >= current).with_for_update())
    if job is None:
        raise ApiError("JOB_LEASE_LOST", "Job lease is expired, cancelled or owned by another attempt.", 409)
    started = job.started_at.replace(tzinfo=UTC) if job.started_at.tzinfo is None else job.started_at
    if enforce_wall and (current - started).total_seconds() >= job.budget["max_wall_s"]:
        raise ApiError("WALL_BUDGET_EXHAUSTED", "Wall-time budget exhausted.", 429)
    return job


def heartbeat(job_id: str, attempt: int) -> None:
    with session_scope() as session:
        job = owned_job(session, job_id, attempt)
        job.lease_until = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)


def set_stage(job_id: str, attempt: int, stage: str) -> None:
    if stage not in STAGES:
        raise ValueError("invalid job stage")
    with session_scope() as session:
        owned_job(session, job_id, attempt).stage = stage


def reserve_call(job_id: str, attempt: int) -> None:
    with session_scope() as session:
        job = owned_job(session, job_id, attempt)
        if job.budget["calls_used"] >= job.budget["max_calls"]:
            raise ApiError("CALL_BUDGET_EXHAUSTED", "Provider call budget exhausted.", 429)
        job.budget = {**job.budget, "calls_used": job.budget["calls_used"] + 1}


def checkpoint(job_id: str, attempt: int, segment: str, *, stage: str, coverage: dict, result: dict, session=None) -> None:
    from contextlib import nullcontext
    if stage not in STAGES or not segment.strip():
        raise ValueError("stage and segment invalid")
    with nullcontext(session) if session is not None else session_scope() as transaction:
        job = owned_job(transaction, job_id, attempt)
        previous = job.checkpoints.get(segment)
        if previous is None or (segment == "discovery" and previous.get("scan_pending") is True and result.get("scan_pending") is False):
            job.checkpoints = {**job.checkpoints, segment: result}
            job.coverage = coverage
        job.stage = stage


def finish(job_id: str, attempt: int, *, error_code: str | None = None) -> None:
    with session_scope() as session:
        job = owned_job(session, job_id, attempt, enforce_wall=False)
        job.status, job.stage = ("failed", "FAILED") if error_code else ("succeeded", "COMPLETED")
        job.error_code = error_code
        job.lease_until = None


def get_job(job_id: str, actor: Principal, *, cancel: bool = False) -> dict:
    with session_scope() as session:
        job = session.scalar(select(JobV2).where(JobV2.job_id == job_id).with_for_update())
        if job is None:
            raise ApiError("NOT_FOUND", "Job not found.", 404)
        authorize(actor, job.recording_id, "Engineer" if cancel else None)
        if cancel and job.status in {"queued", "running"}:
            job.status, job.stage, job.lease_until = "cancelled", "CANCELLED", None
        return job_envelope(job)


def active_job(recording_id: str, actor: Principal) -> dict:
    authorize(actor, recording_id)
    with session_scope() as session:
        job = session.scalar(select(JobV2).where(JobV2.recording_id == recording_id).order_by(JobV2.created_at.desc()).limit(1))
        return {"items": [job_envelope(job)] if job else [], "next_cursor": None}
