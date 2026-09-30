from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.services.errors import IncidentIngestionError


@dataclass(frozen=True)
class NormalizedLog:
    content: bytes
    row_count: int
    timestamp_column: str
    timestamp_unit: str
    time_reference: str

    def metadata(self) -> dict[str, str | int]:
        metadata: dict[str, str | int] = {
            "row_count": self.row_count,
            "timestamp_column": self.timestamp_column,
            "timestamp_unit": self.timestamp_unit,
        }
        if self.timestamp_column.strip().lower() in {
            "sec_from_incident",
            "sim_time_s",
            "wall_clock_ts",
        }:
            metadata["time_reference"] = self.time_reference
        return metadata


class LogService:
    """Pandas adapter for upload-time telemetry validation/normalization.

    Timestamp alignment with the video belongs to the later processing flow.
    This service only verifies and normalizes the optional CSV before the
    package is marked ready; it does not calculate a video-log offset.
    """

    timestamp_candidates = (
        "sec_from_incident",
        "sim_time_s",
        "wall_clock_ts",
        "timestamp_sec",
        "timestamp_ms",
        "timestamp",
        "time_sec",
        "time_ms",
        "time",
        "ts",
    )

    def validate_upload(self, filename: str | None, content_type: str | None) -> None:
        if Path(filename or "").suffix.lower() != ".csv":
            raise IncidentIngestionError(
                "log_invalid",
                "The telemetry log must be a CSV file.",
                field="log",
            )

    def normalize(self, csv_path: Path) -> NormalizedLog:
        try:
            dataframe = pd.read_csv(csv_path)
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise IncidentIngestionError(
                "log_invalid",
                "The telemetry log could not be parsed as CSV.",
                field="log",
            ) from exc

        if dataframe.empty:
            raise IncidentIngestionError(
                "log_invalid",
                "The telemetry log is empty.",
                field="log",
            )

        timestamp_column = self._find_timestamp_column(dataframe.columns)
        if timestamp_column is None:
            raise IncidentIngestionError(
                "log_missing_timestamp",
                "The telemetry log must contain a timestamp column.",
                field="log",
            )

        normalized, unit, time_reference = self._normalize_timestamp(
            dataframe[timestamp_column], timestamp_column
        )
        if normalized.isna().any():
            raise IncidentIngestionError(
                "log_invalid",
                f"The log timestamp column '{timestamp_column}' contains invalid values.",
                field="log",
            )

        dataframe["timestamp_sec"] = normalized.round(6)
        return NormalizedLog(
            content=dataframe.to_csv(index=False).encode("utf-8"),
            row_count=len(dataframe.index),
            timestamp_column=timestamp_column,
            timestamp_unit=unit,
            time_reference=time_reference,
        )

    def validate(self, csv_path: Path) -> NormalizedLog:
        """Backward-compatible alias for callers that only need validation."""
        return self.normalize(csv_path)

    @classmethod
    def _find_timestamp_column(cls, columns: pd.Index) -> str | None:
        by_lowercase = {str(column).strip().lower(): str(column) for column in columns}
        for candidate in cls.timestamp_candidates:
            if candidate in by_lowercase:
                return by_lowercase[candidate]
        return None

    @staticmethod
    def _normalize_timestamp(
        series: pd.Series, column_name: str
    ) -> tuple[pd.Series, str, str]:
        canonical_name = column_name.strip().lower()
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().all():
            unit = "milliseconds" if "ms" in column_name.lower() else "seconds"
            divisor = 1000.0 if unit == "milliseconds" else 1.0
            values = numeric / divisor
            if canonical_name == "sec_from_incident":
                return values, "seconds", "incident_relative"
            reference = "simulation" if canonical_name == "sim_time_s" else "wall_clock"
            return values - values.iloc[0], unit, reference

        parsed = pd.to_datetime(series, errors="coerce", utc=True)
        if parsed.notna().all():
            values = (parsed - parsed.iloc[0]).dt.total_seconds()
            reference = "wall_clock" if canonical_name == "wall_clock_ts" else "datetime"
            return values, "datetime", reference
        return (
            pd.Series([float("nan")] * len(series), index=series.index),
            "unknown",
            "unknown",
        )
