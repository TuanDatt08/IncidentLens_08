"""Versioned engineer edits and human review on the existing report row."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from src.api.errors import ApiError
from src.db import session_scope
from src.models.contracts import RejectRequest, ReportPatch
from src.models.tables import AnalysisReport, AuditEvent, Incident, ReportVersion
from src.services.access import require_demo_access
from src.services.reports import _report_contract


EDITABLE_FIELDS = {"summary", "timeline", "key_factors", "observations", "unknowns"}


def _load_report(session, incident_id: str) -> tuple[Incident, AnalysisReport, int]:
    incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
    if incident is None:
        raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
    report = session.scalar(select(AnalysisReport).where(AnalysisReport.incident_id == incident.id).with_for_update())
    if report is None:
        raise ApiError("REPORT_NOT_FOUND", "Analysis report is not available.", 404)
    version = session.scalar(select(func.max(ReportVersion.version)).where(ReportVersion.report_id == report.id)) or 1
    return incident, report, version


def edit_report(incident_id: str, patch: ReportPatch) -> dict:
    require_demo_access()
    with session_scope() as session:
        incident, report, version = _load_report(session, incident_id)
        if report.review_status != "DRAFT":
            raise ApiError("INVALID_REPORT_STATE", "Only draft reports can be edited.", 409)
        if patch.version != version:
            raise ApiError("INVALID_REPORT_STATE", "Report version is stale.", 409, {"current_version": version})
        fields = sorted(patch.model_fields_set & EDITABLE_FIELDS)
        for field in fields:
            setattr(report, field, getattr(patch, field))
        report.updated_at = datetime.now(UTC)
        next_version = version + 1
        content = _report_contract(incident_id, report, next_version).model_dump(mode="json")
        session.add(ReportVersion(report_id=report.id, version=next_version, content=content, edited_by="demo-engineer"))
        session.add(AuditEvent(incident_id=incident.id, action="REPORT_EDITED", actor="demo-engineer", event_metadata={"version": next_version, "fields": fields}))
        return content


def _transition(incident_id: str, *, expected: str, target: str, action: str, reason: str | None = None) -> dict:
    require_demo_access()
    with session_scope() as session:
        incident, report, version = _load_report(session, incident_id)
        if report.review_status != expected:
            raise ApiError("INVALID_REPORT_STATE", f"Report must be {expected} for this action.", 409)
        report.review_status = target
        report.updated_at = datetime.now(UTC)
        actor = "demo-engineer" if target == "IN_REVIEW" else "demo-reviewer"
        metadata = {"version": version}
        if reason is not None:
            metadata["reason"] = reason
        session.add(AuditEvent(incident_id=incident.id, action=action, actor=actor, event_metadata=metadata))
        return {"incident_id": incident_id, "status": target, "version": version, "rejection_reason": reason}


def submit_report(incident_id: str) -> dict:
    return _transition(incident_id, expected="DRAFT", target="IN_REVIEW", action="REPORT_SUBMITTED")


def approve_report(incident_id: str) -> dict:
    return _transition(incident_id, expected="IN_REVIEW", target="APPROVED", action="REPORT_APPROVED")


def reject_report(incident_id: str, request: RejectRequest) -> dict:
    return _transition(incident_id, expected="IN_REVIEW", target="REJECTED", action="REPORT_REJECTED", reason=request.reason)
