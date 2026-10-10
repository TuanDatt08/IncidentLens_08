"""Streaming rules and bounded sparse discovery, with explicit unexamined coverage."""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from statistics import median

from backend.services.log_normalization import NormalizedTelemetry
from backend.services.synchronization import TimeAlignment, finite
from backend.services.telemetry import TelemetryError


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
    version: str = "rules-2-log-flags"

    def __post_init__(self):
        if not self.recording_id.strip() or not finite(self.duration_s) or self.duration_s <= 0:
            raise ValueError("recording_id and finite positive duration required")
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
    if usable:
        previous_mode = None
        previous_values = {}
        active_thresholds = set()
        histories = {key: deque(maxlen=config.baseline_rows) for key in config.anomaly_signals}
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
                if brake >= config.brake_threshold and "default_brake" not in active_thresholds:
                    propose(at_s, "HARD_BRAKING", {"time_s": at_s, "signal": config.brake_column, "value": brake, "threshold": config.brake_threshold, "reason": "HARD_BRAKING"})
                if brake >= config.brake_threshold:
                    active_thresholds.add("default_brake")
                else:
                    active_thresholds.discard("default_brake")
            for signal in config.signal_thresholds.keys() | config.delta_thresholds.keys() | histories.keys():
                if signal not in row:
                    continue
                try:
                    value = float(row[signal])
                except (ValueError, TypeError) as exc:
                    raise TelemetryError("configured signal must be numeric") from exc
                if not math.isfinite(value):
                    raise TelemetryError("configured signal must be finite")
                threshold = config.signal_thresholds.get(signal)
                if threshold is not None:
                    if abs(value) >= threshold and signal not in active_thresholds:
                        propose(at_s, "SIGNAL_THRESHOLD", {"time_s": at_s, "signal": signal, "value": value, "threshold": threshold, "reason": "SIGNAL_THRESHOLD"})
                    if abs(value) >= threshold:
                        active_thresholds.add(signal)
                    else:
                        active_thresholds.discard(signal)
                delta = config.delta_thresholds.get(signal)
                if delta is not None and signal in previous_values and abs(value - previous_values[signal]) >= delta:
                    propose(at_s, "SIGNAL_DELTA", {"time_s": at_s, "signal": signal, "value": value, "previous_value": previous_values[signal], "threshold": delta, "reason": "SIGNAL_DELTA"})
                previous_values[signal] = value
                if signal in histories:
                    history = histories[signal]
                    if len(history) == config.baseline_rows and signal not in config.signal_thresholds:
                        baseline = median(history)
                        mad = median(abs(item - baseline) for item in history)
                        limit = max(config.anomaly_mad_multiplier * 1.4826 * mad, 1e-6)
                        active_key = "anomaly:" + signal
                        abnormal = abs(value - baseline) > limit
                        if abnormal and active_key not in active_thresholds:
                            propose(at_s, "SIGNAL_ANOMALY", {"time_s": at_s, "signal": signal, "value": value, "baseline": baseline, "deviation": value - baseline, "threshold": limit, "reason": "SIGNAL_ANOMALY"})
                        if abnormal:
                            active_thresholds.add(active_key)
                        else:
                            active_thresholds.discard(active_key)
                    history.append(value)
            mode = row.get(config.mode_column)
            if previous_mode is not None and mode != previous_mode and mode in config.manual_modes:
                propose(at_s, "DISENGAGEMENT", {"time_s": at_s, "signal": config.mode_column, "value": mode, "previous_value": previous_mode, "reason": "DISENGAGEMENT"})
            previous_mode = mode
        unknowns.append("Rules cover available configured signals only; unlogged visual events remain unknown.")
        unknowns.append(f"Rolling anomaly rules require {config.baseline_rows} prior rows; startup spikes and threshold calibration remain uncertain.")
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
    return CandidateSet(tuple(candidates), scan_times, Coverage(rows, sampled, unscanned), tuple(unknowns), config_hash)
