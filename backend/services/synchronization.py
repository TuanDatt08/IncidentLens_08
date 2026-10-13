"""Explicit log-to-video affine mapping; missing anchors never imply zero offset."""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.services.log_normalization import NormalizedTelemetry


def finite(value: float) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


@dataclass(frozen=True)
class TimeAnchor:
    log_s: float
    video_s: float
    source: str


@dataclass(frozen=True)
class TimeAlignment:
    duration_s: float
    source_time_reference: str
    quality: str
    offset_s: float | None
    drift_ppm: float | None
    residual_s: float | None
    anchors: tuple[TimeAnchor, ...]
    unknowns: tuple[str, ...]

    def to_video_seconds(self, log_s: float) -> float:
        if self.quality != "VERIFIED":
            raise ValueError("time alignment must be verified before precise inference")
        if not finite(log_s):
            raise ValueError("log seconds must be finite")
        return self.offset_s + log_s * (1 + self.drift_ppm / 1_000_000)

    def to_log_seconds(self, video_s: float) -> float:
        if self.quality != "VERIFIED" or not finite(video_s):
            raise ValueError("finite time and verified alignment required")
        return (video_s - self.offset_s) / (1 + self.drift_ppm / 1_000_000)


def align(video_metadata: dict, telemetry: NormalizedTelemetry, anchors: list[TimeAnchor], *, tolerance_s: float = 0.1) -> TimeAlignment:
    duration = video_metadata.get("duration")
    if not finite(duration) or duration <= 0 or not finite(tolerance_s) or tolerance_s <= 0:
        raise ValueError("duration and tolerance must be finite positive seconds")
    if not anchors and telemetry.config.timestamp_column == 't_video_s' and telemetry.config.time_reference == 'recording_relative':
        if telemetry.metadata.start_s < 0 or telemetry.metadata.start_s >= duration:
            raise ValueError('t_video_s must start within the video duration')
        anchors = [TimeAnchor(0.0, 0.0, 'explicit_t_video_s'), TimeAnchor(duration, duration, 'explicit_t_video_s')]
    points = tuple(sorted(anchors, key=lambda anchor: anchor.log_s))
    for i, anchor in enumerate(points):
        if not finite(anchor.log_s) or not finite(anchor.video_s) or not 0 <= anchor.video_s <= duration or not anchor.source.strip():
            raise ValueError("anchors require finite times, video bounds and provenance")
        if i and (anchor.log_s <= points[i - 1].log_s or anchor.video_s <= points[i - 1].video_s):
            raise ValueError("anchors must increase strictly in both clocks")
    reference = telemetry.metadata.time_reference
    if not points:
        return TimeAlignment(duration, reference, "UNKNOWN", None, None, None, points, ("No verified log/video anchors.",))
    if len(points) == 1:
        return TimeAlignment(duration, reference, "ESTIMATED", points[0].video_s - points[0].log_s, None, None, points, ("Single anchor cannot verify drift.",))
    mean_x = sum(point.log_s for point in points) / len(points)
    mean_y = sum(point.video_s for point in points) / len(points)
    denominator = sum((point.log_s - mean_x) ** 2 for point in points)
    slope = sum((point.log_s - mean_x) * (point.video_s - mean_y) for point in points) / denominator
    offset = mean_y - slope * mean_x
    residual = max(abs(point.video_s - (offset + slope * point.log_s)) for point in points)
    if not all(finite(value) for value in (slope, offset, residual)) or slope <= 0:
        raise ValueError("anchors cannot form a finite increasing time mapping")
    verified = residual <= tolerance_s
    return TimeAlignment(duration, reference, "VERIFIED" if verified else "UNKNOWN", offset, (slope - 1) * 1_000_000, residual, points, () if verified else ("Anchor residual exceeds tolerance; precise inference disabled.",))
