from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from backend.services.errors import IncidentIngestionError


@dataclass(frozen=True)
class VideoProbeResult:
    duration: float
    fps: float
    width: int
    height: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "duration": self.duration,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
        }


class VideoService:
    """ffprobe adapter for upload metadata validation."""

    def __init__(self, ffprobe_bin: str = "ffprobe", ffmpeg_bin: str | None = None, *, max_output_bytes: int | None = None, output_guard: Callable[[], int] | None = None, frame_max_width: int | None = None) -> None:
        self.ffprobe_bin = ffprobe_bin
        # Retained for constructor compatibility with the later processing
        # workflow. Upload ingestion intentionally does not invoke FFmpeg.
        self.ffmpeg_bin = ffmpeg_bin
        if max_output_bytes is not None and (isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes <= 0):
            raise ValueError("output budget must be positive integer bytes")
        self.max_output_bytes = max_output_bytes
        self.output_guard = output_guard
        self.frame_max_width = frame_max_width

    def prepare_output(self) -> None:
        if self.output_guard is not None:
            self.max_output_bytes = self.output_guard()
            if self.max_output_bytes <= 0:
                raise ValueError("output budget exhausted")

    def write_json(self, destination: Path, payload: Any) -> None:
        self.prepare_output()
        data = json.dumps(payload, default=str, sort_keys=True, indent=2).encode("utf-8")
        if self.max_output_bytes is not None and len(data) >= self.max_output_bytes:
            raise ValueError("metadata output budget exhausted")
        destination.write_bytes(data)

    def validate_upload(self, filename: str | None, content_type: str | None) -> None:
        suffix = Path(filename or "").suffix.lower()
        if suffix != ".mp4":
            raise IncidentIngestionError(
                "unsupported_format",
                "Unsupported video format. Please upload an MP4 video.",
                field="video",
            )

        accepted_content_types = {None, "", "application/octet-stream", "video/mp4"}
        if content_type not in accepted_content_types:
            raise IncidentIngestionError(
                "unsupported_format",
                "Unsupported video content type. Please upload an MP4 video.",
                field="video",
            )

    def probe(self, video_path: Path) -> VideoProbeResult:
        command = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except OSError as exc:
            raise IncidentIngestionError(
                "video_tool_unavailable",
                "ffprobe is not installed or is not available on PATH.",
                status_code=500,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise IncidentIngestionError(
                "video_invalid",
                "Video metadata inspection timed out. The video may be corrupt.",
            ) from exc

        if completed.returncode != 0:
            message = self._stderr_message(completed.stderr)
            raise IncidentIngestionError(
                "video_invalid",
                f"The uploaded video is invalid or corrupt{f': {message}' if message else '.'}",
                field="video",
            )

        try:
            payload = json.loads(completed.stdout)
            stream = payload["streams"][0]
            duration = float(payload.get("format", {}).get("duration", 0))
            fps = self._parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
            width = int(stream["width"])
            height = int(stream["height"])
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IncidentIngestionError(
                "video_invalid",
                "Video metadata could not be read. The video may be corrupt.",
                field="video",
            ) from exc

        if duration <= 0 or fps <= 0 or width <= 0 or height <= 0:
            raise IncidentIngestionError(
                "video_invalid",
                "The uploaded video has incomplete or invalid metadata.",
                field="video",
            )
        return VideoProbeResult(duration=duration, fps=fps, width=width, height=height)

    def extract_frame(self, video_path: Path, at_s: float, destination: Path) -> Path:
        self.prepare_output()
        destination.parent.mkdir(parents=True, exist_ok=True)
        scale = ["-vf", f"scale='min({self.frame_max_width},iw)':-2"] if self.frame_max_width else []
        self._run_ffmpeg([
            "-y", "-ss", f"{at_s:.6f}", "-i", str(video_path),
            "-frames:v", "1", *scale, str(destination),
        ])
        return destination

    def extract_clip(self, video_path: Path, start_s: float, end_s: float, destination: Path) -> Path:
        self.prepare_output()
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run_ffmpeg([
            "-y", "-ss", f"{start_s:.6f}", "-i", str(video_path),
            "-t", f"{end_s - start_s:.6f}", "-c:v", "libx264", "-an", str(destination),
        ])
        return destination

    def _run_ffmpeg(self, args: list[str]) -> None:
        self.prepare_output()
        if self.max_output_bytes is not None:
            args = [*args[:-1], "-fs", str(self.max_output_bytes), args[-1]]
        try:
            completed = subprocess.run([self.ffmpeg_bin or "ffmpeg", *args], capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IncidentIngestionError("video_tool_unavailable", "FFmpeg is unavailable or timed out.", status_code=500) from exc
        if completed.returncode != 0:
            raise IncidentIngestionError("video_invalid", "FFmpeg could not extract the requested media.")
        if self.max_output_bytes is not None and Path(args[-1]).stat().st_size >= self.max_output_bytes:
            Path(args[-1]).unlink(missing_ok=True)
            raise ValueError("FFmpeg output budget exhausted; truncated evidence cannot be used")

    @staticmethod
    def _parse_fps(value: Any) -> float:
        if not value:
            return 0.0
        try:
            return float(Fraction(str(value)))
        except (ValueError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _stderr_message(stderr: str) -> str:
        return " ".join(stderr.strip().split())[:300]
