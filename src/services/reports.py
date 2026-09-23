"""Atomic persistence and read models for analysis reports and evidence."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path

from sqlalchemy import func, select

from src.api.errors import ApiError
from src.db import session_scope
from src.config import get_settings
from src.models.contracts import AnalysisReportV1, EvidenceV1
from src.models.tables import AnalysisReport as ReportRow
from src.models.tables import AuditEvent, Evidence, Incident, Job, ReportVersion
from src.services.processing import InsufficientEvidence, ProcessedResult


def _report_contract(incident_id: str, report: ReportRow, version: int) -> AnalysisReportV1:
    window = None
    if report.start_s is not None and report.critical_s is not None and report.end_s is not None:
        window = {"start": report.start_s, "critical": report.critical_s, "end": report.end_s}
    return AnalysisReportV1(
        incident_id=incident_id,
        incident_detected=report.incident_detected,
        incident_type=report.incident_type,
        incident_window=window,
        summary=report.summary,
        timeline=report.timeline,
        key_factors=report.key_factors,
        observations=report.observations,
        unknowns=report.unknowns,
        evidence_ids=report.evidence_ids,
        review_status=report.review_status,
        version=version,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )


def complete_analysis(job_id: str, result: ProcessedResult, *, expected_attempt: int | None = None) -> dict:
    if not result.analysis.incident_detected:
        raise InsufficientEvidence("No-incident success semantics await contract confirmation.")
    # Validate everything before the first database write.
    evidence = [EvidenceV1.model_validate(item) for item in result.evidence]
    if not evidence:
        raise InsufficientEvidence("Analysis produced no evidence.")
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id).with_for_update())
        if job is None:
            raise ApiError("JOB_NOT_FOUND", "Job was not found.", 404)
        if job.status != "running":
            raise ApiError("INVALID_REPORT_STATE", "Job is not running.", 409)
        if expected_attempt is not None and job.attempt != expected_attempt:
            raise ApiError("JOB_LEASE_LOST", "Job lease belongs to another worker.", 409)
        incident = session.get(Incident, job.incident_id)
        root = Path(get_settings().incident_storage_dir).expanduser().resolve()
        for item in evidence:
            asset = (root / item.uri).resolve()
            if root not in asset.parents or item.uri.split("/")[0] != incident.incident_id or not asset.is_file():
                raise InsufficientEvidence("Evidence asset is unavailable.")
            try:
                with asset.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError as exc:
                raise InsufficientEvidence("Evidence asset could not be read.") from exc
            if digest != item.sha256 or (item.bytes is not None and asset.stat().st_size != item.bytes):
                raise InsufficientEvidence("Evidence asset digest or size does not match.")
        existing = session.scalar(select(ReportRow).where(ReportRow.incident_id == incident.id))
        if existing is not None:
            raise ApiError("INVALID_REPORT_STATE", "Analysis report already exists.", 409)
        current = datetime.now(UTC)
        for item in evidence:
            session.add(Evidence(
                evidence_id=item.evidence_id,
                incident_id=incident.id,
                kind=item.kind,
                uri=item.uri,
                sha256=item.sha256,
                time_start_s=item.time_range_s[0],
                time_end_s=item.time_range_s[1],
                tier=item.tier,
                bytes=item.bytes,
                media_type=item.media_type,
            ))
        analysis = result.analysis
        window = analysis.incident_window
        report = ReportRow(
            incident_id=incident.id,
            incident_detected=analysis.incident_detected,
            incident_type=analysis.incident_type,
            start_s=window.start if window else None,
            critical_s=window.critical if window else None,
            end_s=window.end if window else None,
            summary=analysis.summary,
            timeline=analysis.timeline,
            key_factors=analysis.key_factors,
            observations=analysis.observations,
            unknowns=analysis.unknowns,
            evidence_ids=[item.evidence_id for item in evidence],
            model_metadata=analysis.model_metadata,
            review_status="DRAFT",
            created_at=current,
            updated_at=current,
        )
        session.add(report)
        session.flush()
        content = _report_contract(incident.incident_id, report, 1).model_dump(mode="json")
        session.add(ReportVersion(report_id=report.id, version=1, content=content, edited_by=None))
        incident.processing_status = "COMPLETED"
        if result.collision_offset_in_video_s is not None:
            incident.video_metadata = {**(incident.video_metadata or {}), "collision_offset_in_video_s": result.collision_offset_in_video_s}
        job.status = "succeeded"
        job.pass_number = 2
        job.progress_done = 2
        job.progress_total = 2
        job.result_uri = f"/api/v1/incidents/{incident.incident_id}/report"
        job.error = None
        job.lease_until = None
        job.updated_at = current
        job.completed_at = current
        session.add(AuditEvent(incident_id=incident.id, action="ANALYSIS_COMPLETED", actor="system", event_metadata={"job_id": job_id}))
        return content


def get_report(incident_id: str) -> dict:
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        report = session.scalar(select(ReportRow).where(ReportRow.incident_id == incident.id))
        if report is None:
            raise ApiError("REPORT_NOT_FOUND", "Analysis report is not available.", 404)
        version = session.scalar(select(func.max(ReportVersion.version)).where(ReportVersion.report_id == report.id)) or 1
        return _report_contract(incident_id, report, version).model_dump(mode="json")


def get_evidence(incident_id: str) -> dict:
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        rows = session.scalars(select(Evidence).where(Evidence.incident_id == incident.id).order_by(Evidence.created_at, Evidence.evidence_id)).all()
        items = [EvidenceV1(
            evidence_id=item.evidence_id,
            kind=item.kind,
            uri=item.uri,
            sha256=item.sha256,
            time_range_s=(item.time_start_s, item.time_end_s),
            tier=item.tier,
            bytes=item.bytes,
            media_type=item.media_type,
        ).model_dump(mode="json") for item in rows]
        return {"incident_id": incident_id, "items": items}
