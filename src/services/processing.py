"""Pass 1 → media/telemetry preparation → Pass 2, without DB writes."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4

from src.config import get_settings
from src.models.contracts import AnalysisResult, EvidenceV1, LocalizationResult
from src.services.storage import LocalStorage
from src.services.telemetry import select_window
from src.services.video import VideoService


class InsufficientEvidence(ValueError):
    pass


@dataclass(frozen=True)
class PreparedPass2:
    incident_id: str
    clip_path: Path
    frame_paths: list[Path]
    telemetry_rows: list[dict]
    candidate_start: float
    critical_time: float
    candidate_end: float


@dataclass(frozen=True)
class ProcessedResult:
    analysis: AnalysisResult
    evidence: list[EvidenceV1]
    collision_offset_in_video_s: float | None


class VLMAdapter(Protocol):
    def pass1(self, video_path: Path, sampled_frames: list[Path], metadata: dict) -> LocalizationResult: ...

    def pass2(self, prepared: PreparedPass2) -> AnalysisResult: ...


def _evidence(root: Path, path: Path, kind: str, start_s: float, end_s: float, media_type: str) -> EvidenceV1:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return EvidenceV1(
        evidence_id=f"EVD-{uuid4().hex[:12].upper()}",
        kind=kind,
        uri=path.relative_to(root).as_posix(),
        sha256=digest,
        time_range_s=(start_s, end_s),
        tier="bulky" if kind == "video" else "core",
        bytes=path.stat().st_size,
        media_type=media_type,
    )


def process_incident(
    incident: dict,
    *,
    storage_root: str | Path,
    vlm: VLMAdapter,
    on_progress: Callable[[int, int, int | None], None] | None = None,
) -> ProcessedResult:
    storage = LocalStorage(storage_root)
    root = storage.root
    incident_id = incident["incident_id"]
    video_path = (root / incident["video_uri"]).resolve()
    if root not in video_path.parents or not video_path.is_file():
        raise InsufficientEvidence("Source video is unavailable.")
    metadata = incident["video_metadata"]
    duration = float(metadata["duration"])
    video_service = VideoService(get_settings().ffprobe_bin, get_settings().ffmpeg_bin)
    sample_times = [duration * i / 4 for i in range(4)] + [max(0.0, duration - 0.01)]
    if on_progress:
        on_progress(1, 0, 2)
    sampled_frames = [
        video_service.extract_frame(video_path, at_s, root / incident_id / "frames" / f"pass1_{index}.jpg")
        for index, at_s in enumerate(sample_times)
    ]
    localization = LocalizationResult.model_validate(vlm.pass1(video_path, sampled_frames, metadata))
    if on_progress:
        on_progress(1, 1, 2)
    if not localization.incident_detected:
        return ProcessedResult(AnalysisResult(incident_detected=False), [], localization.collision_offset_in_video_s)
    offset = localization.collision_offset_in_video_s
    if offset is None:
        raise InsufficientEvidence("Collision position in the MP4 is unknown.")
    video_start = offset + localization.candidate_start
    video_end = offset + localization.candidate_end
    if video_start < 0 or video_end > duration or video_start >= video_end:
        raise InsufficientEvidence("Candidate window is outside the source video.")
    clip_path = video_service.extract_clip(video_path, video_start, video_end, root / incident_id / "clips" / "candidate.mp4")
    frame_times = localization.evidence_timestamps or [localization.critical_time]
    frame_paths = [
        video_service.extract_frame(video_path, offset + relative_s, root / incident_id / "frames" / f"evidence_{index}.jpg")
        for index, relative_s in enumerate(frame_times)
    ]
    telemetry_rows: list[dict] = []
    telemetry_uri = incident.get("telemetry_uri")
    if telemetry_uri:
        telemetry_path = (root / telemetry_uri).resolve()
        if root not in telemetry_path.parents:
            raise InsufficientEvidence("Telemetry path is invalid.")
        telemetry_rows = select_window(telemetry_path, localization.candidate_start, localization.candidate_end)
    prepared = PreparedPass2(
        incident_id=incident_id,
        clip_path=clip_path,
        frame_paths=frame_paths,
        telemetry_rows=telemetry_rows,
        candidate_start=localization.candidate_start,
        critical_time=localization.critical_time,
        candidate_end=localization.candidate_end,
    )
    if on_progress:
        on_progress(2, 1, 2)
    analysis = AnalysisResult.model_validate(vlm.pass2(prepared))
    if on_progress:
        on_progress(2, 2, 2)
    if not analysis.incident_detected or analysis.incident_window is None:
        raise InsufficientEvidence("Pass 2 did not confirm a valid incident window.")
    window = analysis.incident_window
    if window.start < localization.candidate_start or window.end > localization.candidate_end:
        raise InsufficientEvidence("Pass 2 window is outside Pass 1 candidate.")
    evidence = [_evidence(root, clip_path, "video", localization.candidate_start, localization.candidate_end, "video/mp4")]
    evidence.extend(
        _evidence(root, frame_path, "frame", relative_s, relative_s, "image/jpeg")
        for frame_path, relative_s in zip(frame_paths, frame_times)
    )
    if telemetry_rows:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=telemetry_rows[0].keys())
        writer.writeheader()
        writer.writerows(telemetry_rows)
        telemetry_file = storage.write_bytes(incident_id, "clips/telemetry_window.csv", output.getvalue().encode("utf-8"))
        evidence.append(_evidence(root, telemetry_file.path, "telemetry", telemetry_rows[0]["sec_from_incident"], telemetry_rows[-1]["sec_from_incident"], "text/csv"))
    return ProcessedResult(analysis, evidence, offset)
