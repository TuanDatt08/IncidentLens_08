"""Canonical CARLA CSV handling using collision-relative seconds."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from pydantic import BaseModel


class TelemetryError(ValueError):
    pass


class TelemetryMetadata(BaseModel):
    row_count: int
    time_column: str = "sec_from_incident"
    time_reference: str = "incident_relative"
    start_s: float
    end_s: float


def _read_rows(csv_path: str | Path):
    try:
        with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "sec_from_incident" not in reader.fieldnames:
                raise TelemetryError("CSV requires sec_from_incident")
            previous = None
            count = 0
            for row in reader:
                try:
                    second = float(row["sec_from_incident"])
                except (TypeError, ValueError) as exc:
                    raise TelemetryError("sec_from_incident must be numeric") from exc
                if not math.isfinite(second):
                    raise TelemetryError("sec_from_incident must be finite")
                if previous is not None and second <= previous:
                    raise TelemetryError("sec_from_incident must increase strictly")
                previous = second
                count += 1
                row["sec_from_incident"] = second
                yield row
            if count == 0:
                raise TelemetryError("CSV has no telemetry rows")
    except (OSError, UnicodeError, csv.Error) as exc:
        raise TelemetryError("CSV could not be read") from exc


def parse_telemetry(csv_path: str | Path) -> TelemetryMetadata:
    count = 0
    start = end = None
    for row in _read_rows(csv_path):
        second = row["sec_from_incident"]
        if start is None:
            start = second
        end = second
        count += 1
    return TelemetryMetadata(row_count=count, start_s=start, end_s=end)


def select_window(csv_path: str | Path, start_s: float, end_s: float) -> list[dict]:
    if not (math.isfinite(start_s) and math.isfinite(end_s) and start_s <= end_s):
        raise TelemetryError("telemetry window must be finite and ordered")
    return [row for row in _read_rows(csv_path) if start_s <= row["sec_from_incident"] <= end_s]
