"""Incident ingestion and factual metadata backed by the incidents table."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.contracts import IncidentRecordV1
from backend.models.tables import AuditEvent, Incident
from backend.services.errors import IncidentIngestionError
from backend.services.storage import LocalStorage
from backend.services.telemetry import TelemetryError, parse_telemetry
from backend.services.video import VideoService


def _ingestion_error(exc: IncidentIngestionError) -> ApiError:
    if exc.code == "file_too_large":
        return ApiError("VIDEO_TOO_LARGE" if exc.field == "video" else "INVALID_LOG", exc.message, 413)
    if exc.code.startswith("log_"):
        return ApiError("INVALID_LOG", exc.message, 422)
    if exc.code in {"unsupported_format", "video_invalid"}:
        return ApiError("INVALID_VIDEO", exc.message, 422)
    return ApiError("INTERNAL_ERROR", "Incident ingestion failed.", 500)


def create_incident(video: UploadFile, log: UploadFile | None = None) -> dict:
    settings = get_settings()
    storage = LocalStorage(settings.incident_storage_dir)
    video_service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin)
    incident_id = f"INC-{uuid4().hex[:12].upper()}"
    try:
        video_service.validate_upload(video.filename, video.content_type)
        if log is not None and Path(log.filename or "").suffix.lower() != ".csv":
            raise ApiError("INVALID_LOG", "Telemetry must be a CSV file.", 422)
        video_file = storage.save_stream(
            video.file,
            package_id=incident_id,
            relative_name="source/video.mp4",
            max_bytes=settings.max_video_size_mb * 1024 * 1024,
        )
        video_metadata = video_service.probe(video_file.path).as_dict()
        telemetry_file = None
        telemetry_metadata = None
        if log is not None:
            telemetry_file = storage.save_stream(
                log.file,
                package_id=incident_id,
                relative_name="source/telemetry.csv",
                max_bytes=settings.max_log_size_mb * 1024 * 1024,
            )
            telemetry_metadata = parse_telemetry(telemetry_file.path).model_dump()
        with session_scope() as session:
            incident = Incident(
                incident_id=incident_id,
                processing_status="READY",
                video_uri=video_file.relative_path.replace("\\", "/"),
                telemetry_uri=telemetry_file.relative_path.replace("\\", "/") if telemetry_file else None,
                video_metadata=video_metadata,
                telemetry_metadata=telemetry_metadata,
            )
            session.add(incident)
            session.flush()
            session.add(AuditEvent(incident_id=incident.id, action="INCIDENT_CREATED", actor="system", event_metadata={}))
        return {
            "incident_id": incident_id,
            "processing_status": "READY",
            "sync_offset": None,
            "frame_count": 0,
            "video_metadata": video_metadata,
        }
    except IncidentIngestionError as exc:
        storage.remove_package(incident_id)
        raise _ingestion_error(exc) from exc
    except TelemetryError as exc:
        storage.remove_package(incident_id)
        raise ApiError("INVALID_LOG", str(exc), 422) from exc
    except Exception:
        storage.remove_package(incident_id)
        raise


def get_incident(incident_id: str) -> dict:
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        return _incident_dict(incident)


def list_incidents(limit: int = 20, offset: int = 0) -> dict:
    with session_scope() as session:
        total = session.scalar(select(func.count()).select_from(Incident))
        incidents = session.scalars(select(Incident).order_by(Incident.created_at.desc(), Incident.incident_id.desc()).limit(limit).offset(offset)).all()
        return {"items": [_incident_dict(item) for item in incidents], "total": total, "limit": limit, "offset": offset}


def import_incident_record(incident_id: str, record: IncidentRecordV1) -> None:
    """Importer boundary; generator transport remains a NEED_CONFIRMATION."""
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        incident.raw_incident_data = record.model_dump(mode="json", exclude_none=True)
        incident.recorded_at = datetime.fromisoformat(record.recorded_at.replace("Z", "+00:00")) if record.recorded_at else None
        incident.scenario = record.scenario
        incident.template = record.template
        incident.source = record.source
        incident.collision = record.collision
        incident.ego = record.ego
        incident.quality = record.quality


def _incident_dict(incident: Incident) -> dict:
    return {
        "incident_id": incident.incident_id,
        "processing_status": incident.processing_status,
        "video_uri": incident.video_uri,
        "telemetry_uri": incident.telemetry_uri,
        "video_metadata": incident.video_metadata,
        "telemetry_metadata": incident.telemetry_metadata,
        "incident_record": incident.raw_incident_data,
        "created_at": incident.created_at.isoformat(),
        "updated_at": incident.updated_at.isoformat(),
    }
