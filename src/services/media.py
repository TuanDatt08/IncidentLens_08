"""Resolve incident-owned media without exposing storage paths."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from src.api.errors import ApiError
from src.config import get_settings
from src.db import session_scope
from src.models.tables import Evidence, Incident
from src.services.access import require_demo_access


def _resolve_asset(incident_id: str, uri: str) -> Path:
    root = Path(get_settings().incident_storage_dir).expanduser().resolve()
    path = (root / uri).resolve()
    if root not in path.parents or uri.replace("\\", "/").split("/")[0] != incident_id:
        raise ApiError("MEDIA_NOT_FOUND", "Media is not available.", 404)
    if not path.is_file():
        raise ApiError("MEDIA_NOT_FOUND", "Media is not available.", 404)
    return path


def source_video(incident_id: str) -> tuple[Path, str]:
    require_demo_access()
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        return _resolve_asset(incident_id, incident.video_uri), "video/mp4"


def evidence_asset(incident_id: str, evidence_id: str) -> tuple[Path, str]:
    require_demo_access()
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        if incident is None:
            raise ApiError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
        evidence = session.scalar(select(Evidence).where(Evidence.incident_id == incident.id, Evidence.evidence_id == evidence_id))
        if evidence is None:
            raise ApiError("MEDIA_NOT_FOUND", "Media is not available.", 404)
        media_types = {
            "video": "video/mp4",
            "frame": "image/jpeg",
            "telemetry": "text/csv",
            "annotation": "application/octet-stream",
        }
        return _resolve_asset(incident_id, evidence.uri), media_types.get(evidence.kind, "application/octet-stream")
