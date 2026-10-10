"""Ordered, scoped evidence bundles for video-second candidates."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from backend.services.candidate_detection import Candidate
from backend.services.synchronization import finite
from backend.services.video import VideoService


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True)
class SamplingConfig:
    times_s: tuple[float, ...] = ()
    max_frames: int = 32


def window_sample_times(candidate: Candidate, metadata: dict, fps: float = 4.0) -> tuple[float, ...]:
    duration, source_fps = metadata.get("duration"), metadata.get("fps")
    if any(not finite(value) or value <= 0 for value in (duration, source_fps, fps)):
        raise ValueError("sampling requires finite positive duration and FPS")
    if not 0 <= candidate.start_s <= candidate.critical_s <= candidate.end_s <= duration or candidate.start_s >= candidate.end_s:
        raise ValueError("candidate must fit source video")
    count = math.ceil((candidate.end_s - candidate.start_s) * fps)
    if count > 256:
        raise ValueError("candidate exceeds total extraction budget of 256 frames")
    last = max(0.0, duration - 1 / source_fps)
    return tuple(at_s for index in range(count) if (at_s := candidate.start_s + index / fps) < candidate.end_s and at_s <= last)


@dataclass(frozen=True)
class EvidenceAsset:
    evidence_id: str
    recording_id: str
    candidate_id: str
    path: Path
    sha256: str
    time_start_s: float
    time_end_s: float
    source: str
    media_type: str
    frame_order: int | None = None
    privacy_state: str = "RAW"
    privacy_validation: str = "NOT_CHECKED"


@dataclass(frozen=True)
class EvidenceBundle:
    recording_id: str
    candidate_id: str
    clip: EvidenceAsset
    frames: tuple[EvidenceAsset, ...]
    manifest_path: Path
    source_sha256: str


def extract_candidate(video: str | Path, candidate: Candidate, sampling: SamplingConfig, *, recording_id: str, output_root: Path, metadata: dict | None = None, video_service: VideoService | None = None) -> EvidenceBundle:
    service = video_service or VideoService()
    times = tuple(sorted(sampling.times_s or (candidate.start_s, candidate.critical_s)))
    if not recording_id.strip() or any(not finite(value) for value in (candidate.start_s, candidate.critical_s, candidate.end_s, *times)):
        raise ValueError("scope and finite video-second times required")
    if not 0 <= candidate.start_s <= candidate.critical_s <= candidate.end_s or candidate.start_s >= candidate.end_s:
        raise ValueError("candidate window must be ordered and positive")
    if not isinstance(sampling.max_frames, int) or isinstance(sampling.max_frames, bool) or not 0 < len(times) <= sampling.max_frames <= 256 or len(set(times)) != len(times):
        raise ValueError("frame order must be unique and within finite frame budget")
    if any(not candidate.start_s <= at_s < candidate.end_s for at_s in times):
        raise ValueError("frame times must be inside candidate window")
    source = Path(video)
    metadata = metadata or service.probe(source).as_dict()
    duration, fps = metadata.get("duration"), metadata.get("fps")
    if not finite(duration) or not finite(fps) or duration <= 0 or fps <= 0 or candidate.end_s > duration:
        raise ValueError("candidate must fit valid source metadata")
    if any(at_s > max(0.0, duration - 1 / fps) for at_s in times):
        raise ValueError("frame seek extends beyond final decodable source frame")
    source_hash = file_hash(source)
    key = hashlib.sha256(json.dumps([recording_id, candidate.candidate_id, source_hash, candidate.start_s, candidate.end_s, times]).encode()).hexdigest()
    directory = Path(output_root) / key
    directory.mkdir(parents=True, exist_ok=True)

    def asset(path: Path, start: float, end: float, media_type: str, order: int | None = None) -> EvidenceAsset:
        digest = file_hash(path)
        identity = json.dumps([key, digest, start, end, order]).encode()
        return EvidenceAsset("EVD-" + hashlib.sha256(identity).hexdigest()[:24], recording_id, candidate.candidate_id, path, digest, start, end, "VIDEO", media_type, order)

    clip_path = service.extract_clip(source, candidate.start_s, candidate.end_s, directory / "clip.mp4")
    clip = asset(clip_path, candidate.start_s, candidate.end_s, "video/mp4")
    frames = tuple(asset(service.extract_frame(source, at_s, directory / f"frame-{order:04d}.jpg"), at_s, at_s, "image/jpeg", order) for order, at_s in enumerate(times))
    manifest = directory / "manifest.json"
    payload = {"recording_id": recording_id, "candidate_id": candidate.candidate_id, "source_sha256": source_hash, "time_basis": "video_seconds", "clip": asdict(clip), "frames": [asdict(frame) for frame in frames]}
    service.write_json(manifest, payload)
    return EvidenceBundle(recording_id, candidate.candidate_id, clip, frames, manifest, source_hash)
