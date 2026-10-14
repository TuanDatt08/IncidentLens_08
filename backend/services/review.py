"""Versioned engineer edits and human review on the existing report row."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from backend.db import session_scope
from backend.errors import ApiError
from backend.models.contracts import RejectRequest, ReportPatch
from backend.models.tables import AnalysisReport, AuditEvent, Incident, ReportVersion
from backend.services.access import Principal, require_permission
from backend.services.reports import _report_contract

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


def edit_report(incident_id: str, patch: ReportPatch, *, principal: Principal) -> dict:
    require_permission(principal, "report:edit")
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
        session.add(ReportVersion(report_id=report.id, version=next_version, content=content, edited_by=str(principal.user_id)))
        session.add(AuditEvent(incident_id=incident.id, action="REPORT_EDITED", actor=str(principal.user_id), event_metadata={"version": next_version, "fields": fields}))
        return content


def _transition(incident_id: str, *, principal: Principal, expected: str, target: str, action: str, reason: str | None = None) -> dict:
    require_permission(principal, {"IN_REVIEW": "report:submit", "APPROVED": "report:approve", "REJECTED": "report:reject"}[target])
    with session_scope() as session:
        incident, report, version = _load_report(session, incident_id)
        if report.review_status != expected:
            raise ApiError("INVALID_REPORT_STATE", f"Report must be {expected} for this action.", 409)
        if target in {"APPROVED", "REJECTED"}:
            edited = session.scalar(select(ReportVersion.id).where(ReportVersion.report_id == report.id, ReportVersion.edited_by == str(principal.user_id)).limit(1))
            submitted = session.scalar(select(AuditEvent.id).where(AuditEvent.incident_id == incident.id, AuditEvent.action == "REPORT_SUBMITTED", AuditEvent.actor == str(principal.user_id)).limit(1))
            if edited or submitted:
                raise ApiError("SELF_REVIEW_FORBIDDEN", "You cannot review a report you edited or submitted.", 403)
        report.review_status = target
        report.updated_at = datetime.now(UTC)
        actor = str(principal.user_id)
        metadata = {"version": version}
        if reason is not None:
            metadata["reason"] = reason
        session.add(AuditEvent(incident_id=incident.id, action=action, actor=actor, event_metadata=metadata))
        return {"incident_id": incident_id, "status": target, "version": version, "rejection_reason": reason}


def submit_report(incident_id: str, *, principal: Principal) -> dict:
    return _transition(incident_id, principal=principal, expected="DRAFT", target="IN_REVIEW", action="REPORT_SUBMITTED")


def approve_report(incident_id: str, *, principal: Principal) -> dict:
    return _transition(incident_id, principal=principal, expected="IN_REVIEW", target="APPROVED", action="REPORT_APPROVED")


def reject_report(incident_id: str, request: RejectRequest, *, principal: Principal) -> dict:
    return _transition(incident_id, principal=principal, expected="IN_REVIEW", target="REJECTED", action="REPORT_REJECTED", reason=request.reason)
