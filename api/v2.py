"""Authenticated V2 adapters; V1 keeps its payload and time basis."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Query, Request

from backend.errors import ApiError
from backend.models.contracts_v2 import AnalyzeRequestV2, ReportEditV2, ReportEnvelopeV2, TransitionV2
from backend.services import jobs_v2
from backend.services.identity import Principal, authenticate
from backend.services.reports_v2 import get_report, list_candidates, mutate_report, report_history

router = APIRouter(prefix="/api/v2", tags=["V2"])


def principal(request: Request, authorization: Annotated[str | None, Header()] = None, incidentlens_v2_identity: Annotated[str | None, Cookie()] = None, x_requested_with: Annotated[str | None, Header()] = None) -> Principal:
    if authorization is None and incidentlens_v2_identity:
        if request.method not in {"GET", "HEAD", "OPTIONS"} and x_requested_with != "IncidentLens":
            raise ApiError("CSRF_BLOCKED", "Session mutation requires the application request header.", 403)
        authorization = "Bearer " + incidentlens_v2_identity
    return authenticate(authorization)


Identity = Annotated[Principal, Depends(principal)]


@router.get("/session")
def session_identity(actor: Identity):
    return {"subject": actor.subject, "roles": sorted(actor.roles)}


@router.get("/recordings")
def recordings(actor: Identity, cursor: str | None = None, limit: int = Query(50, ge=1, le=200)):
    from sqlalchemy import select

    from backend.db import session_scope
    from backend.models.tables_v2 import RecordingV2
    with session_scope() as session:
        query = select(RecordingV2).where(RecordingV2.recording_id.in_(actor.recordings))
        if cursor:
            query = query.where(RecordingV2.recording_id > cursor)
        rows = session.scalars(query.order_by(RecordingV2.recording_id).limit(limit + 1)).all()
        return {"items": [{"recording_id": row.recording_id, "duration_s": row.duration_s} for row in rows[:limit]], "next_cursor": rows[limit - 1].recording_id if len(rows) > limit else None}


@router.get("/recordings/{recording_id}/candidates")
def candidates(recording_id: str, actor: Identity, cursor: str | None = None, limit: int = Query(50, ge=1, le=200)):
    return list_candidates(recording_id, actor, cursor=cursor, limit=limit)


@router.get("/reports/{report_id}", response_model=ReportEnvelopeV2)
def report(report_id: str, actor: Identity):
    return get_report(report_id, actor)


@router.patch("/reports/{report_id}", response_model=ReportEnvelopeV2)
def edit(report_id: str, request: ReportEditV2, actor: Identity):
    return mutate_report(report_id, actor, request, action="edit")


@router.get("/reports/{report_id}/versions")
def versions(report_id: str, actor: Identity):
    return report_history(report_id, actor)


@router.get("/reports/{report_id}/audit")
def audit(report_id: str, actor: Identity):
    return report_history(report_id, actor, audit=True)


@router.post("/reports/{report_id}/submit", response_model=ReportEnvelopeV2)
def submit(report_id: str, request: TransitionV2, actor: Identity):
    return mutate_report(report_id, actor, request, action="submit")


@router.post("/reports/{report_id}/approve", response_model=ReportEnvelopeV2)
def approve(report_id: str, request: TransitionV2, actor: Identity):
    return mutate_report(report_id, actor, request, action="approve")


@router.post("/reports/{report_id}/reject", response_model=ReportEnvelopeV2)
def reject(report_id: str, request: TransitionV2, actor: Identity):
    return mutate_report(report_id, actor, request, action="reject")


@router.post("/reports/{report_id}/reopen", response_model=ReportEnvelopeV2)
def reopen(report_id: str, request: TransitionV2, actor: Identity):
    return mutate_report(report_id, actor, request, action="reopen")


@router.post("/recordings/{recording_id}/analyze", status_code=202)
def analyze(recording_id: str, request: AnalyzeRequestV2, actor: Identity, idempotency_key: Annotated[str, Header()]):
    return jobs_v2.create_job(recording_id, request.provider_profile, idempotency_key, actor)


@router.get("/recordings/{recording_id}/jobs")
def recording_jobs(recording_id: str, actor: Identity):
    return jobs_v2.active_job(recording_id, actor)


@router.get("/jobs/{job_id}")
def job_status(job_id: str, actor: Identity):
    return jobs_v2.get_job(job_id, actor)


@router.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: str, actor: Identity):
    return jobs_v2.get_job(job_id, actor, cancel=True)


@router.post("/jobs/{job_id}/resume")
def job_resume(job_id: str, actor: Identity):
    from backend.worker_v2 import resume_failed
    return resume_failed(job_id, actor)


@router.get("/reports/{report_id}/evidence")
def report_evidence(report_id: str, actor: Identity):
    from backend.services.reports_v2 import list_evidence
    return list_evidence(report_id, actor)


@router.get("/recordings/{recording_id}/evidence/{evidence_id}/media")
def evidence_media(recording_id: str, evidence_id: str, actor: Identity):
    from api.media import _response
    from backend.services.reports_v2 import media_asset
    return _response(media_asset(recording_id, evidence_id, actor))
