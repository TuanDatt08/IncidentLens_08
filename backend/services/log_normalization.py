"""Streaming, explicit-clock CSV normalization without changing API v1 parsing."""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from backend.services.telemetry import TelemetryError, TelemetryMetadata

_SECONDS_PER_UNIT = {"s": Decimal(1), "ms": Decimal("0.001"), "us": Decimal("0.000001"), "ns": Decimal("0.000000001")}
_TIME_REFERENCES = {"incident_relative", "recording_relative", "unix_epoch"}


@dataclass(frozen=True)
class LogNormalizationConfig:
    timestamp_column: str = "sec_from_incident"
    timestamp_unit: str = "s"
    time_reference: str = "incident_relative"

    def __post_init__(self):
        if not self.timestamp_column.strip() or self.timestamp_column == "time_s":
            raise TelemetryError("timestamp_column must name a source column; time_s is reserved for normalized output")
        if self.timestamp_unit not in _SECONDS_PER_UNIT:
            raise TelemetryError("timestamp_unit must be s, ms, us or ns")
        if self.time_reference not in _TIME_REFERENCES:
            raise TelemetryError("time_reference must explicitly identify incident_relative, recording_relative or unix_epoch")


class NormalizedTelemetryMetadata(TelemetryMetadata):
    time_column: str = "time_s"
    output_unit: str = "s"
    source_time_reference: str
    timestamp_column: str
    timestamp_unit: str
    source_timestamp_origin: str | None
    signal_columns: list[str]


@dataclass(frozen=True)
class NormalizedTelemetry:
    source_path: Path
    config: LogNormalizationConfig
    metadata: NormalizedTelemetryMetadata

    def iter_rows(self) -> Iterator[dict]:
        """Re-read a stored source sequentially; never load the whole log into RAM."""
        for row, _origin in _normalized_rows(self.source_path, self.config):
            yield row


def _normalized_rows(path: Path, config: LogNormalizationConfig) -> Iterator[tuple[dict, str | None]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            names = reader.fieldnames
            if (
                not names
                or len(set(names)) != len(names)
                or config.timestamp_column not in names
                or "time_s" in names
            ):
                raise TelemetryError("CSV requires unique source columns and the configured clock; time_s is reserved")
            previous = previous_normalized = origin = None
            seen = False
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise TelemetryError("CSV row must have exactly the declared columns")
                try:
                    clock = Decimal(row[config.timestamp_column])
                except (InvalidOperation, ValueError) as exc:
                    raise TelemetryError("timestamp must be numeric") from exc
                if not clock.is_finite():
                    raise TelemetryError("timestamp must be finite")
                if previous is not None and clock <= previous:
                    raise TelemetryError("timestamp must increase strictly; rows are not sorted or dropped automatically")
                previous = clock
                if origin is None and config.time_reference == "unix_epoch":
                    origin = clock
                seconds = float((clock - (origin if origin is not None else Decimal(0))) * _SECONDS_PER_UNIT[config.timestamp_unit])
                if not math.isfinite(seconds) or (previous_normalized is not None and seconds <= previous_normalized):
                    raise TelemetryError("normalized timestamp must be finite and preserve strict order")
                previous_normalized = seconds
                seen = True
                normalized = {"time_s": seconds, **{key: value for key, value in row.items() if key != config.timestamp_column}}
                # Explicit CARLA field units; retain source columns for audit.
                for canonical, source, scale in (("speed", "speed_kmh", 1 / 3.6), ("acceleration", "accel_x", 1.0)):
                    if canonical not in normalized and source in normalized:
                        try:
                            value = float(normalized[source]) * scale
                        except (ValueError, TypeError) as exc:
                            raise TelemetryError(f"{source} must be numeric") from exc
                        if not math.isfinite(value):
                            raise TelemetryError(f"{source} must be finite")
                        normalized[canonical] = value
                yield normalized, str(origin) if origin is not None else None
            if not seen:
                raise TelemetryError("CSV has no telemetry rows")
    except (OSError, UnicodeError, csv.Error) as exc:
        raise TelemetryError("CSV could not be read") from exc


def normalize_log(
    path: str | Path,
    format: str = "csv",  # noqa: A002 - signature follows the task's public contract
    config: LogNormalizationConfig | None = None,
    *, guard: Callable[[], None] | None = None,
) -> NormalizedTelemetry:
    if format.lower() in {"ros2", "ros2_bag", "bag", "db3", "mcap"}:
        raise TelemetryError("ROS2 bag is not supported by this CSV adapter; export approved topics to CSV with explicit clock metadata")
    if format.lower() != "csv":
        raise TelemetryError("unsupported telemetry format; supported format: csv")
    if config is None:
        try:
            with Path(path).open('r', encoding='utf-8-sig', newline='') as stream:
                columns = next(csv.reader(stream), [])
        except (OSError, UnicodeError, csv.Error) as exc:
            raise TelemetryError('CSV could not be read') from exc
        config = (LogNormalizationConfig(timestamp_column='t_video_s', time_reference='recording_relative')
                  if 't_video_s' in columns else LogNormalizationConfig())
    source = Path(path)
    count = 0
    first = last = origin = None
    columns = []
    for row, origin in _normalized_rows(source, config):
        if guard is not None and count % 1000 == 0:
            guard()
        if first is None:
            first = row["time_s"]
            columns = [key for key in row if key != "time_s"]
        last = row["time_s"]
        count += 1
    metadata = NormalizedTelemetryMetadata(
        row_count=count, start_s=first, end_s=last,
        time_reference="recording_relative" if config.time_reference == "unix_epoch" else config.time_reference,
        source_time_reference=config.time_reference,
        timestamp_column=config.timestamp_column, timestamp_unit=config.timestamp_unit,
        source_timestamp_origin=origin, signal_columns=columns,
    )
    return NormalizedTelemetry(source, config, metadata)
