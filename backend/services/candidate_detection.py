"""Streaming rules and bounded sparse discovery, with explicit unexamined coverage."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from backend.services.log_normalization import NormalizedTelemetry
from backend.services.synchronization import TimeAlignment, finite


@dataclass(frozen=True)
class DetectionConfig:
    recording_id: str
    duration_s: float
    pre_s: float = 5.0
    post_s: float = 3.0
    merge_gap_s: float = 1.0
    brake_threshold: float = 0.8
    max_candidates: int = 100
    scan_interval_s: float = 60.0
    max_scan_frames: int = 1000
    brake_column: str = "brake"
    mode_column: str = "mode"
    manual_modes: tuple[str, ...] = ("MANUAL",)
    signal_thresholds: dict[str, float] = field(default_factory=dict)
    delta_thresholds: dict[str, float] = field(default_factory=dict)
    anomaly_signals: tuple[str, ...] = ("speed", "brake", "acceleration", "jerk", "collision_intensity")
    baseline_rows: int = 30
    anomaly_mad_multiplier: float = 6.0
    fps: float = 24.0
    version: str = "rules-3-streaming-triggers"

    def __post_init__(self):
        if not self.recording_id.strip() or not finite(self.duration_s) or self.duration_s <= 0:
            raise ValueError("recording_id and finite positive duration required")
        if not finite(self.fps) or self.fps <= 0:
            raise ValueError('positive video FPS required')
        if any(not finite(value) or value < 0 for value in (self.pre_s, self.post_s, self.merge_gap_s, self.brake_threshold)):
            raise ValueError("rule thresholds/windows must be finite and nonnegative")
        if self.pre_s + self.post_s <= 0 or not finite(self.scan_interval_s) or self.scan_interval_s <= 0:
            raise ValueError("window length and scan interval must be positive")
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (self.max_candidates, self.max_scan_frames)):
            raise ValueError("budgets must be positive integers")
        for thresholds in (self.signal_thresholds, self.delta_thresholds):
            if any(key not in {"speed", "brake", "acceleration", "jerk", "collision_intensity"} or not finite(value) or value <= 0 for key, value in thresholds.items()):
                raise ValueError("signal thresholds require approved signal names and finite positive values in source units")
        if isinstance(self.baseline_rows, bool) or not isinstance(self.baseline_rows, int) or not 3 <= self.baseline_rows <= 1000 or not finite(self.anomaly_mad_multiplier) or self.anomaly_mad_multiplier <= 0:
            raise ValueError("rolling baseline requires bounded rows and positive MAD multiplier")
        if any(key not in {"speed", "brake", "acceleration", "jerk", "collision_intensity"} for key in self.anomaly_signals):
            raise ValueError("anomaly signals must be approved numeric signals")


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    start_s: float
    critical_s: float
    end_s: float
    reasons: tuple[str, ...]
    analysis_state: str
    flags: tuple[dict, ...] = ()


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
    log_trigger_data: dict | None = None


def detect_candidates(telemetry: NormalizedTelemetry | None, alignment: TimeAlignment | None, config: DetectionConfig, *, scan: Callable[[float], bool] | None = None, guard: Callable[[], None] | None = None) -> CandidateSet:
    config_hash = hashlib.sha256(json.dumps(asdict(config), sort_keys=True).encode()).hexdigest()
    windows: list[list] = []

    def propose(at_s: float, reason: str, flag: dict | None = None):
        if not 0 <= at_s < config.duration_s:
            return
        start, end = max(0.0, at_s - config.pre_s), min(config.duration_s, at_s + config.post_s)
        if end <= start:
            return
        if windows and start <= windows[-1][2] + config.merge_gap_s:
            windows[-1][2] = max(windows[-1][2], end)
            windows[-1][3].add(reason)
            if flag is not None:
                windows[-1][4].append(flag)
        else:
            windows.append([start, at_s, end, {reason}, [flag] if flag is not None else []])

    rows = sampled = 0
    scan_times: tuple[float, ...] = ()
    unscanned: tuple[tuple[float, float], ...] = ()
    unknowns: list[str] = []
    usable = telemetry is not None and alignment is not None and alignment.quality == "VERIFIED"
    signal_names = {config.brake_column, config.mode_column, *config.signal_thresholds, *config.delta_thresholds, *config.anomaly_signals}
    if usable and not signal_names.intersection(telemetry.metadata.signal_columns):
        usable = False
        unknowns.append("No configured event signals in telemetry.")
    raw = None
    if telemetry is not None:
        from backend.services.trigger_detection import TriggerConfig, find_log_triggers
        raw = find_log_triggers(telemetry, config=TriggerConfig(pre_s=config.pre_s,post_s=config.post_s,merge_gap_s=config.merge_gap_s,brake_threshold=config.brake_threshold,max_triggers=max(1000,config.max_candidates)), alignment=alignment, video_metadata={'duration':config.duration_s,'fps':config.fps}, signal_thresholds=config.signal_thresholds, delta_thresholds=config.delta_thresholds, guard=guard)
        rows = raw['rows']
        unknowns.extend(raw['unknowns'])
    if usable:
        for event in raw['triggers']:
            peak = event['video_peak_s']
            start, end = event['clip_start_s'], event['clip_end_s']
            if peak is None or not 0 <= peak < config.duration_s or end <= start:
                continue
            flags = tuple({**item,'time_s':alignment.to_video_seconds(item['log_time_s'])} for item in event['flags'])
            windows.append([start,peak,end,set(event['reasons']),list(flags)])
        unknowns.append('Telemetry triggers are candidate suspicion; event boundaries and causes require video evidence and engineer review.')
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
    for index, (start, critical, end, reasons, flags) in enumerate(windows):
        stable_key = json.dumps([config.recording_id, config_hash, start, critical, end, sorted(reasons), flags], sort_keys=True)
        candidate_id = "CND-" + hashlib.sha256(stable_key.encode()).hexdigest()[:24]
        candidates.append(Candidate(candidate_id, start, critical, end, tuple(sorted(reasons)), "PENDING" if index < config.max_candidates else "UNANALYZED", tuple(flags)))
    if len(candidates) > config.max_candidates:
        unknowns.append("Candidate budget exhausted; overflow windows retained as UNANALYZED.")
    return CandidateSet(tuple(candidates), scan_times, Coverage(rows, sampled, unscanned), tuple(unknowns), config_hash, raw)
