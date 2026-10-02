"""Transactional snapshots and shared evidence validation for V2 review."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.models.contracts_v2 import ReportEditV2, ReportEnvelopeV2, TransitionV2
from backend.models.tables_v2 import CandidateV2, RecordingV2, ReportV2, SnapshotV2
from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.evidence_validation import EvidenceRegistry, validate_analysis
from backend.services.identity import Principal, authorize


def envelope(report: ReportV2) -> dict:
    return ReportEnvelopeV2(recording_id=report.recording_id, candidate_id=report.candidate_id, report_id=report.report_id, version=report.version, analysis=report.analysis, provenance=report.provenance, submitted_by=report.submitted_by).model_dump(mode="json")


def registry_for(report: ReportV2) -> EvidenceRegistry:
    assets = tuple(EvidenceAsset(**{**asset, "path": Path(asset["path"])}) for asset in report.evidence_registry)
    return EvidenceRegistry(report.recording_id, report.candidate_id, assets)


def create_report(analysis: AIIncidentAnalysisV2, registry: EvidenceRegistry, *, duration_s: float, provenance: dict, session=None) -> dict:
    draft = AIIncidentAnalysisV2.model_validate(analysis.model_dump(), context={"video_duration_s": duration_s})
    validated = validate_analysis(draft, registry, duration_s)
    if validated.window is None:
        raise ValueError("candidate report requires a detected incident window")
    serialized_assets = [{**asdict(asset), "path": str(asset.path)} for asset in registry.assets]
    with nullcontext(session) if session is not None else session_scope() as session:
        recording = session.get(RecordingV2, registry.recording_id)
        if recording is None:
            recording = RecordingV2(recording_id=registry.recording_id, duration_s=duration_s, metadata_json={})
            session.add(recording)
            session.flush()
        elif recording.duration_s != duration_s:
            raise ValueError("duration cannot change for a stored recording")
        existing = session.scalar(select(ReportV2).where(ReportV2.candidate_id == registry.candidate_id))
        if existing is not None:
            if existing.recording_id != registry.recording_id:
                raise ValueError("candidate scope conflict")
            return envelope(existing)
        candidate = session.get(CandidateV2, registry.candidate_id)
        if candidate is None:
            session.add(CandidateV2(candidate_id=registry.candidate_id, recording_id=registry.recording_id, window=validated.window.model_dump(), reasons=[validated.event_type], analysis_state="ANALYZED"))
            session.flush()
        elif candidate.recording_id != registry.recording_id:
            raise ValueError("candidate scope conflict")
        report = ReportV2(report_id="RPT-" + uuid4().hex, candidate_id=registry.candidate_id, recording_id=registry.recording_id, version=1, analysis=validated.model_dump(mode="json"), provenance=provenance, evidence_registry=serialized_assets)
        session.add(report)
        session.flush()
        content = envelope(report)
        session.add(SnapshotV2(report_id=report.report_id, version=1, content=content, actor="system", action="GENERATED"))
        return content


def load_report(session, report_id: str, principal: Principal) -> ReportV2:
    report = session.get(ReportV2, report_id)
    if report is None:
        raise ApiError("NOT_FOUND", "Report not found.", 404)
    authorize(principal, report.recording_id)
    return report


def get_report(report_id: str, principal: Principal) -> dict:
    with session_scope() as session:
        return envelope(load_report(session, report_id, principal))


def mutate_report(report_id: str, principal: Principal, request: ReportEditV2 | TransitionV2, *, action: str) -> dict:
    try:
        with session_scope() as session:
            report = load_report(session, report_id, principal)
            role = "Reviewer" if action in {"approve", "reject"} else "Engineer"
            authorize(principal, report.recording_id, role)
            if report.version != request.expected_version:
                raise ApiError("STALE_VERSION", "Report version is stale.", 409, {"current_version": report.version})
            content = dict(report.analysis)
            state = content["review_status"]
            transitions = {"submit": ("DRAFT", "IN_REVIEW"), "approve": ("IN_REVIEW", "APPROVED"), "reject": ("IN_REVIEW", "REJECTED"), "reopen": ("REJECTED", "DRAFT")}
            submitted_by = report.submitted_by
            reason = None
            if action == "edit":
                if state != "DRAFT":
                    raise ApiError("INVALID_REPORT_STATE", "Only DRAFT can be edited.", 409)
                changes = request.model_dump(exclude_unset=True, exclude={"expected_version"})
                if not changes or any(value is None for value in changes.values()):
                    raise ApiError("INVALID_REPORT", "Edit must contain non-null fields.", 422)
                content.update(changes)
            else:
                expected, target = transitions[action]
                if state != expected:
                    raise ApiError("INVALID_REPORT_STATE", "Report state does not allow this action.", 409)
                if action in {"approve", "reject"} and principal.subject == submitted_by:
                    raise ApiError("SELF_REVIEW_DENIED", "Reviewer must differ from submitting Engineer.", 403)
                if action == "reject":
                    reason = request.reason
                    if reason is None:
                        raise ApiError("REASON_REQUIRED", "Rejection requires a reason.", 422)
                if action == "submit":
                    submitted_by = principal.subject
                elif action == "reopen":
                    submitted_by = None
                content["review_status"] = target
            recording = session.get(RecordingV2, report.recording_id)
            try:
                validated = validate_analysis(content, registry_for(report), recording.duration_s)
            except (ValueError, OSError) as exc:
                raise ApiError("INVALID_EVIDENCE", "Report schema or evidence is invalid.", 422) from exc
            next_version = report.version + 1
            changed = session.execute(update(ReportV2).where(ReportV2.report_id == report_id, ReportV2.version == request.expected_version).values(analysis=validated.model_dump(mode="json"), version=next_version, submitted_by=submitted_by))
            if changed.rowcount != 1:
                raise ApiError("STALE_VERSION", "Report changed concurrently.", 409)
            session.refresh(report)
            result = envelope(report)
            session.add(SnapshotV2(report_id=report_id, version=next_version, content=result, actor=principal.subject, action=action.upper(), reason=reason))
            return result
    except IntegrityError as exc:
        raise ApiError("STALE_VERSION", "Report changed concurrently.", 409) from exc


def report_history(report_id: str, principal: Principal, *, audit: bool = False) -> dict:
    with session_scope() as session:
        load_report(session, report_id, principal)
        snapshots = session.scalars(select(SnapshotV2).where(SnapshotV2.report_id == report_id).order_by(SnapshotV2.version)).all()
        items = [{"version": row.version, "actor": row.actor, "action": row.action, "reason": row.reason, "created_at": row.created_at.isoformat()} if audit else row.content for row in snapshots]
        return {"items": items, "next_cursor": None}


def list_candidates(recording_id: str, principal: Principal, *, cursor: str | None = None, limit: int = 50) -> dict:
    authorize(principal, recording_id)
    with session_scope() as session:
        if session.get(RecordingV2, recording_id) is None:
            raise ApiError("NOT_FOUND", "Recording not found.", 404)
        query = select(CandidateV2).where(CandidateV2.recording_id == recording_id)
        if cursor:
            query = query.where(CandidateV2.candidate_id > cursor)
        rows = session.scalars(query.order_by(CandidateV2.candidate_id).limit(limit + 1)).all()
        reports = dict(session.execute(select(ReportV2.candidate_id, ReportV2.report_id).where(ReportV2.recording_id == recording_id)).all())
        items = [{"candidate_id": row.candidate_id, "recording_id": row.recording_id, "window": row.window, "reasons": row.reasons, "analysis_state": row.analysis_state, "report_id": reports.get(row.candidate_id)} for row in rows[:limit]]
        return {"items": items, "next_cursor": rows[limit - 1].candidate_id if len(rows) > limit else None}


def list_evidence(report_id: str, principal: Principal) -> dict:
    with session_scope() as session:
        report = load_report(session, report_id, principal)
        items = []
        for asset in registry_for(report).assets:
            approved = (asset.privacy_state, asset.privacy_validation) == ("MASKED", "PASSED")
            items.append({"evidence_id": asset.evidence_id, "source": asset.source, "start_s": asset.time_start_s, "end_s": asset.time_end_s, "media_type": asset.media_type, "privacy_state": asset.privacy_state, "privacy_validation": asset.privacy_validation, "media_url": f"/recordings/{report.recording_id}/evidence/{asset.evidence_id}/media" if approved else None})
        return {"items": items, "next_cursor": None}


def media_asset(recording_id: str, evidence_id: str, principal: Principal) -> tuple[Path, str]:
    authorize(principal, recording_id)
    with session_scope() as session:
        reports = session.scalars(select(ReportV2).where(ReportV2.recording_id == recording_id)).all()
        for report in reports:
            for asset in registry_for(report).assets:
                if asset.evidence_id != evidence_id:
                    continue
                if (asset.privacy_state, asset.privacy_validation) != ("MASKED", "PASSED"):
                    raise ApiError("PRIVACY_BLOCKED", "Evidence has not passed privacy validation.", 403)
                root = Path(get_settings().incident_storage_dir).resolve()
                path = asset.path.resolve()
                if root not in path.parents or not path.is_file() or file_hash(path) != asset.sha256:
                    raise ApiError("MEDIA_UNAVAILABLE", "Evidence media unavailable.", 404)
                return path, asset.media_type
        raise ApiError("NOT_FOUND", "Evidence not found.", 404)
