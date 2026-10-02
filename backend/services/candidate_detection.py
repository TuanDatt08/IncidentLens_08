"""Streaming rules and bounded sparse discovery, with explicit unexamined coverage."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass

from backend.services.log_normalization import NormalizedTelemetry
from backend.services.synchronization import TimeAlignment, finite
from backend.services.telemetry import TelemetryError


@dataclass(frozen=True)
class DetectionConfig:
    recording_id: str
    duration_s: float
    pre_s: float = 5.0
    post_s: float = 5.0
    merge_gap_s: float = 1.0
    brake_threshold: float = 0.8
    max_candidates: int = 100
    scan_interval_s: float = 60.0
    max_scan_frames: int = 1000
    brake_column: str = "brake"
    mode_column: str = "mode"
    manual_modes: tuple[str, ...] = ("MANUAL",)
    version: str = "rules-1"

    def __post_init__(self):
        if not self.recording_id.strip() or not finite(self.duration_s) or self.duration_s <= 0:
            raise ValueError("recording_id and finite positive duration required")
        if any(not finite(value) or value < 0 for value in (self.pre_s, self.post_s, self.merge_gap_s, self.brake_threshold)):
            raise ValueError("rule thresholds/windows must be finite and nonnegative")
        if self.pre_s + self.post_s <= 0 or not finite(self.scan_interval_s) or self.scan_interval_s <= 0:
            raise ValueError("window length and scan interval must be positive")
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (self.max_candidates, self.max_scan_frames)):
            raise ValueError("budgets must be positive integers")


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    start_s: float
    critical_s: float
    end_s: float
    reasons: tuple[str, ...]
    analysis_state: str


@dataclass(frozen=True)
class Coverage:
    log_rows: int
    sampled_frames: int
    unscanned_ranges: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class CandidateSet:
    candidates: tuple[Candidate, ...]
    scan_times_s: tuple[float, ...]
    coverage: Coverage
    unknowns: tuple[str, ...]
    config_hash: str


def detect_candidates(telemetry: NormalizedTelemetry | None, alignment: TimeAlignment | None, config: DetectionConfig, *, scan: Callable[[float], bool] | None = None, guard: Callable[[], None] | None = None) -> CandidateSet:
    config_hash = hashlib.sha256(json.dumps(asdict(config), sort_keys=True).encode()).hexdigest()
    windows: list[list] = []

    def propose(at_s: float, reason: str):
        if not 0 <= at_s < config.duration_s:
            return
        start, end = max(0.0, at_s - config.pre_s), min(config.duration_s, at_s + config.post_s)
        if end <= start:
            return
        if windows and start <= windows[-1][2] + config.merge_gap_s:
            windows[-1][2] = max(windows[-1][2], end)
            windows[-1][3].add(reason)
        else:
            windows.append([start, at_s, end, {reason}])

    rows = sampled = 0
    scan_times: tuple[float, ...] = ()
    unscanned: tuple[tuple[float, float], ...] = ()
    unknowns: list[str] = []
    usable = telemetry is not None and alignment is not None and alignment.quality == "VERIFIED"
    if usable and not {config.brake_column, config.mode_column}.intersection(telemetry.metadata.signal_columns):
        usable = False
        unknowns.append("No configured event signals in telemetry.")
    if usable:
        previous_mode = None
        for row in telemetry.iter_rows():
            if guard is not None and rows % 1000 == 0:
                guard()
            rows += 1
            at_s = alignment.to_video_seconds(row["time_s"])
            brake = row.get(config.brake_column)
            if brake is not None:
                try:
                    brake = float(brake)
                except (ValueError, TypeError) as exc:
                    raise TelemetryError("configured brake signal must be numeric") from exc
                if not math.isfinite(brake):
                    raise TelemetryError("configured brake signal must be finite")
                if brake >= config.brake_threshold:
                    propose(at_s, "HARD_BRAKING")
            mode = row.get(config.mode_column)
            if previous_mode is not None and mode != previous_mode and mode in config.manual_modes:
                propose(at_s, "DISENGAGEMENT")
            previous_mode = mode
        unknowns.append("Rules cover available configured signals only; unlogged visual events remain unknown.")
    else:
        count = min(config.max_scan_frames, math.ceil(config.duration_s / config.scan_interval_s))
        scan_times = tuple(i * config.scan_interval_s for i in range(count))
        if scan is not None:
            for at_s in scan_times:
                detected = scan(at_s)
                if not isinstance(detected, bool):
                    raise ValueError("sparse scanner must return a boolean")
                sampled += 1
                if detected:
                    propose(at_s, "VISUAL_CANDIDATE")
        covered_end = min(config.duration_s, sampled * config.scan_interval_s)
        if covered_end < config.duration_s:
            unscanned = ((covered_end, config.duration_s),)
        unknowns.append("Sparse samples cannot establish absence of incidents between frames; log alignment/signals unavailable.")
    candidates = []
    for index, (start, critical, end, reasons) in enumerate(windows):
        stable_key = json.dumps([config.recording_id, config_hash, start, critical, end, sorted(reasons)])
        candidate_id = "CND-" + hashlib.sha256(stable_key.encode()).hexdigest()[:24]
        candidates.append(Candidate(candidate_id, start, critical, end, tuple(sorted(reasons)), "PENDING" if index < config.max_candidates else "UNANALYZED"))
    if len(candidates) > config.max_candidates:
        unknowns.append("Candidate budget exhausted; overflow windows retained as UNANALYZED.")
    return CandidateSet(tuple(candidates), scan_times, Coverage(rows, sampled, unscanned), tuple(unknowns), config_hash)
