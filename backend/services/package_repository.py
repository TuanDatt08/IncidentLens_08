from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from backend.models.incident import (
    IncidentPackage,
    IngestionStatus,
    ProcessingStatus,
    ReviewStatus,
)


class IncidentPackageRepository:
    """JSON-backed persistence for the MVP local ingestion package."""

    def __init__(self, storage_root: str | Path) -> None:
        self.root = Path(storage_root).expanduser().resolve()
        self.manifest_path = self.root / "packages.json"

    def new_package_id(self) -> str:
        return f"PKG-{uuid.uuid4().hex[:12].upper()}"

    def save(self, package: IncidentPackage) -> IncidentPackage:
        self.root.mkdir(parents=True, exist_ok=True)
        records = self._read_records()
        records[package.package_id] = package.to_dict()
        temporary_path = self.manifest_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        temporary_path.replace(self.manifest_path)
        return package

    def get(self, package_id: str) -> IncidentPackage | None:
        record = self._read_records().get(package_id)
        if record is None:
            return None
        return self._from_record(record)

    def list(self) -> list[IncidentPackage]:
        return [self._from_record(record) for record in self._read_records().values()]

    def _read_records(self) -> dict[str, dict[str, Any]]:
        if not self.manifest_path.exists():
            return {}
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _from_record(record: dict[str, Any]) -> IncidentPackage:
        data = dict(record)
        data["status"] = IngestionStatus(data["status"])
        # Old manifests predate the split pipeline/review contract.
        data["processing_status"] = ProcessingStatus(
            data.get("processing_status", "READY" if data["status"] == "READY" else "FAILED")
        )
        data["review_status"] = ReviewStatus(data.get("review_status", "DRAFT"))
        data.setdefault("video_filename", None)
        return IncidentPackage(**data)
