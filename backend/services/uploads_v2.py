"""Filesystem development upload prototype; no production object store selected."""

from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import update

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.contracts_v2 import UploadRequestV2
from backend.models.tables_v2 import RecordingV2, UploadV2
from backend.services.evidence_extraction import file_hash
from backend.services.identity import Principal, authorize
from backend.services.video import VideoService


def local_storage_guard():
    if get_settings().app_env == "production":
        raise ApiError("STORAGE_NOT_CONFIGURED", "Reviewed production storage adapter required.", 503)


def upload_directory(upload_id: str) -> Path:
    if not re.fullmatch(r"UPL-[a-f0-9]{32}", upload_id):
        raise ApiError("NOT_FOUND", "Upload not found.", 404)
    root = Path(get_settings().incident_storage_dir).resolve()
    directory = (root / "uploads-v2" / upload_id).resolve()
    if root not in directory.parents:
        raise ApiError("INVALID_STORAGE", "Upload storage invalid.", 503)
    return directory


def load_upload(session, upload_id: str, actor: Principal) -> UploadV2:
    local_storage_guard()
    upload = session.get(UploadV2, upload_id)
    if upload is None:
        raise ApiError("NOT_FOUND", "Upload not found.", 404)
    authorize(actor, upload.recording_id, "Engineer")
    if upload.owner != actor.subject:
        raise ApiError("PERMISSION_DENIED", "Upload belongs to another actor.", 403)
    expires = upload.expires_at.replace(tzinfo=UTC) if upload.expires_at.tzinfo is None else upload.expires_at
    if upload.status != "COMPLETED" and expires <= datetime.now(UTC):
        raise ApiError("UPLOAD_EXPIRED", "Upload session expired.", 409)
    return upload


def upload_envelope(upload: UploadV2) -> dict:
    return {"upload_id": upload.upload_id, "recording_id": upload.recording_id, "expires_at": upload.expires_at.isoformat(), "part_size": upload.part_size, "part_count": math.ceil(upload.byte_count / upload.part_size), "parts": [{"number": int(number), **part} for number, part in sorted(upload.parts.items(), key=lambda item: int(item[0]))], "status": upload.status}


def init_upload(request: UploadRequestV2, actor: Principal) -> dict:
    local_storage_guard()
    authorize(actor, request.recording_id, "Engineer")
    if request.bytes > get_settings().max_video_size_mb * 1024 * 1024:
        raise ApiError("UPLOAD_TOO_LARGE", "Video exceeds configured upload limit.", 413)
    if Path(request.filename).name != request.filename or not request.filename.lower().endswith(".mp4"):
        raise ApiError("INVALID_FILENAME", "MP4 filename must be a basename.", 422)
    if len(request.recording_id) > 64:
        raise ApiError("INVALID_RECORDING", "Recording ID too long.", 422)
    with session_scope() as session:
        if session.get(RecordingV2, request.recording_id) is not None:
            raise ApiError("RECORDING_EXISTS", "Recording already exists.", 409)
        upload = UploadV2(upload_id="UPL-" + uuid4().hex, recording_id=request.recording_id, owner=actor.subject, byte_count=request.bytes, sha256=request.sha256, part_size=request.part_size, parts={}, version=1, status="UPLOADING", expires_at=datetime.now(UTC) + timedelta(hours=24))
        session.add(upload)
        session.flush()
        return upload_envelope(upload)


def resume_upload(upload_id: str, actor: Principal) -> dict:
    with session_scope() as session:
        upload = load_upload(session, upload_id, actor)
        directory = upload_directory(upload_id)
        for number, part in upload.parts.items():
            path = directory / f"part-{int(number)}"
            if not path.is_file() or path.stat().st_size != part["bytes"] or file_hash(path) != part["sha256"]:
                raise ApiError("PART_CORRUPT", "Stored upload part failed checksum verification.", 422)
        return upload_envelope(upload)


async def write_part(upload_id: str, number: int, digest: str, chunks: AsyncIterator[bytes], actor: Principal) -> dict:
    with session_scope() as session:
        upload = load_upload(session, upload_id, actor)
        count = math.ceil(upload.byte_count / upload.part_size)
        if upload.status != "UPLOADING" or not 1 <= number <= count or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ApiError("INVALID_PART", "Upload part number/hash/state invalid.", 422)
        expected_size = min(upload.part_size, upload.byte_count - (number - 1) * upload.part_size)
        directory = upload_directory(upload_id)
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / ("temp-" + uuid4().hex)
        actual = hashlib.sha256()
        received = 0
        try:
            with temporary.open("xb") as stream:
                async for chunk in chunks:
                    received += len(chunk)
                    if received > expected_size:
                        raise ApiError("PART_TOO_LARGE", "Upload part exceeds expected bytes.", 413)
                    actual.update(chunk)
                    stream.write(chunk)
            if received != expected_size or actual.hexdigest() != digest:
                raise ApiError("PART_CORRUPT", "Upload part size/checksum mismatch.", 422)
            part = {"bytes": received, "sha256": digest}
            existing = upload.parts.get(str(number))
            if existing is not None:
                if existing != part or not (directory / f"part-{number}").is_file() or file_hash(directory / f"part-{number}") != digest:
                    raise ApiError("PART_CONFLICT", "Upload part already exists with different bytes.", 409)
                return {"number": number, **part}
            parts = {**upload.parts, str(number): part}
            changed = session.execute(update(UploadV2).where(UploadV2.upload_id == upload_id, UploadV2.version == upload.version, UploadV2.status == "UPLOADING").values(parts=parts, version=upload.version + 1))
            if changed.rowcount != 1:
                raise ApiError("UPLOAD_CONFLICT", "Upload changed concurrently; resume and retry.", 409)
            os.replace(temporary, directory / f"part-{number}")
            return {"number": number, **part}
        finally:
            temporary.unlink(missing_ok=True)


def complete_upload(upload_id: str, actor: Principal) -> dict:
    with session_scope() as session:
        upload = load_upload(session, upload_id, actor)
        result = {"recording_id": upload.recording_id, "status": "READY", "sha256": upload.sha256}
        if upload.status == "COMPLETED":
            return result
        count = math.ceil(upload.byte_count / upload.part_size)
        if set(upload.parts) != {str(i) for i in range(1, count + 1)}:
            raise ApiError("UPLOAD_INCOMPLETE", "All verified parts are required.", 409)
        directory = upload_directory(upload_id)
        temporary = directory / ("complete-" + uuid4().hex + ".mp4")
        try:
            with temporary.open("xb") as target:
                for number in range(1, count + 1):
                    source = directory / f"part-{number}"
                    part = upload.parts[str(number)]
                    if not source.is_file() or source.stat().st_size != part["bytes"] or file_hash(source) != part["sha256"]:
                        raise ApiError("PART_CORRUPT", "Stored part failed checksum verification.", 422)
                    with source.open("rb") as stream:
                        shutil.copyfileobj(stream, target, length=1024 * 1024)
            if temporary.stat().st_size != upload.byte_count or file_hash(temporary) != upload.sha256:
                raise ApiError("UPLOAD_CORRUPT", "Complete upload checksum mismatch.", 422)
            with temporary.open("rb") as stream:
                signature = stream.read(12)
            if signature[4:8] != b"ftyp":
                raise ApiError("INVALID_MEDIA", "Upload is not an MP4 container.", 422)
            settings = get_settings()
            metadata = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin).probe(temporary).as_dict()
            changed = session.execute(update(UploadV2).where(UploadV2.upload_id == upload_id, UploadV2.version == upload.version, UploadV2.status == "UPLOADING").values(status="COMPLETED", version=upload.version + 1))
            if changed.rowcount != 1 or session.get(RecordingV2, upload.recording_id) is not None:
                raise ApiError("UPLOAD_CONFLICT", "Upload/recording changed concurrently.", 409)
            path = directory / "source.mp4"
            os.replace(temporary, path)
            root = Path(settings.incident_storage_dir).resolve()
            session.add(RecordingV2(recording_id=upload.recording_id, duration_s=metadata["duration"], video_uri=path.relative_to(root).as_posix(), metadata_json=metadata))
            return result
        finally:
            temporary.unlink(missing_ok=True)
