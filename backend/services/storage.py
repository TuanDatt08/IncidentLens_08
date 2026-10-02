from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from backend.services.errors import IncidentIngestionError


@dataclass(frozen=True)
class StoredFile:
    path: Path
    relative_path: str
    size_bytes: int


class LocalStorage:
    """Small local-storage abstraction used by ingestion.

    The rest of the ingestion flow works with this interface rather than
    depending on a filesystem path layout, so an object store can replace it
    later without changing the API orchestration.
    """

    chunk_size = 1024 * 1024

    def __init__(self, root_dir: str | Path) -> None:
        self.root = Path(root_dir).expanduser().resolve()

    def package_dir(self, package_id: str) -> Path:
        package_dir = (self.root / package_id).resolve()
        if self.root not in package_dir.parents:
            raise IncidentIngestionError(
                "storage_error",
                "The package storage path is invalid.",
                status_code=500,
            )
        package_dir.mkdir(parents=True, exist_ok=True)
        return package_dir

    def save_stream(
        self,
        stream: BinaryIO,
        *,
        package_id: str,
        relative_name: str,
        max_bytes: int,
    ) -> StoredFile:
        package_dir = self.package_dir(package_id)
        destination = (package_dir / relative_name).resolve()
        if package_dir not in destination.parents:
            raise IncidentIngestionError(
                "storage_error",
                "The upload storage path is invalid.",
                status_code=500,
            )
        destination.parent.mkdir(parents=True, exist_ok=True)

        size = 0
        try:
            stream.seek(0)
            with destination.open("wb") as output:
                while chunk := stream.read(self.chunk_size):
                    size += len(chunk)
                    if size > max_bytes:
                        raise IncidentIngestionError(
                            "file_too_large",
                            f"The uploaded file exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                            field="video" if relative_name == "source/video.mp4" else "log",
                        )
                    output.write(chunk)
        except IncidentIngestionError:
            destination.unlink(missing_ok=True)
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise IncidentIngestionError(
                "storage_error",
                "The uploaded file could not be saved to local storage.",
                status_code=500,
            ) from exc

        return StoredFile(
            path=destination,
            relative_path=str(destination.relative_to(self.root)),
            size_bytes=size,
        )

    def write_bytes(self, package_id: str, relative_name: str, content: bytes) -> StoredFile:
        package_dir = self.package_dir(package_id)
        destination = (package_dir / relative_name).resolve()
        if package_dir not in destination.parents:
            raise IncidentIngestionError(
                "storage_error",
                "The storage path is invalid.",
                status_code=500,
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.write_bytes(content)
        except OSError as exc:
            raise IncidentIngestionError(
                "storage_error",
                "The normalized log could not be saved to local storage.",
                status_code=500,
            ) from exc
        return StoredFile(
            path=destination,
            relative_path=str(destination.relative_to(self.root)),
            size_bytes=len(content),
        )

    def remove_package(self, package_id: str) -> None:
        package_dir = (self.root / package_id).resolve()
        if self.root in package_dir.parents and package_dir.exists():
            shutil.rmtree(package_dir, ignore_errors=True)
