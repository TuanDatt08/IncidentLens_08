from pathlib import Path

import pytest

from src.models.incident import IncidentPackage
from src.services.errors import IncidentIngestionError
from src.services.incident_ingestion import IncidentIngestionService
from src.services.logs import LogService
from src.services.package_repository import IncidentPackageRepository
from src.services.storage import LocalStorage
from src.services.video import VideoProbeResult


class FakeVideoService:
    def validate_upload(self, filename: str | None, content_type: str | None) -> None:
        if not filename or not filename.lower().endswith(".mp4") or content_type != "video/mp4":
            raise IncidentIngestionError(
                "unsupported_format",
                "Unsupported video format.",
                field="video",
            )

    def probe(self, video_path: Path) -> VideoProbeResult:
        assert video_path.exists()
        return VideoProbeResult(duration=20.0, fps=30.0, width=1280, height=720)


@pytest.fixture
def ingestion_service(tmp_path: Path) -> IncidentIngestionService:
    storage_root = tmp_path / "incidents"
    return IncidentIngestionService(
        storage=LocalStorage(storage_root),
        repository=IncidentPackageRepository(storage_root),
        video_service=FakeVideoService(),
        log_service=LogService(),
        max_video_size_bytes=1024 * 1024,
        max_log_size_bytes=1024 * 1024,
    )


def video_file(content: bytes = b"video-bytes") -> tuple[str, bytes, str]:
    return ("incident.mp4", content, "video/mp4")


@pytest.mark.asyncio
async def test_upload_mp4_success_with_optional_csv(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={
            "video": video_file(),
            "log": ("telemetry.csv", b"timestamp_ms,speed\n1000,12\n2000,13\n", "text/csv"),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["package_id"].startswith("PKG-")
    assert payload["status"] == "READY"
    assert payload["sync_offset"] is None
    assert payload["frame_count"] == 0
    assert payload["video_metadata"] == {
        "duration": 20.0,
        "fps": 30.0,
        "width": 1280,
        "height": 720,
    }
    assert payload["warnings"] == []

    package = ingestion_service.repository.get(payload["package_id"])
    assert isinstance(package, IncidentPackage)
    assert package.status.value == "READY"
    assert package.sync_offset is None
    assert package.frame_count == 0
    assert package.normalized_log_path is not None
    assert package.log_metadata == {
        "row_count": 2,
        "timestamp_column": "timestamp_ms",
        "timestamp_unit": "milliseconds",
    }


@pytest.mark.asyncio
async def test_upload_mp4_success_without_log(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={"video": video_file()},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "READY"
    assert payload["sync_offset"] is None
    assert payload["frame_count"] == 0
    package = ingestion_service.repository.get(payload["package_id"])
    assert package is not None
    assert package.log_path is None
    assert package.normalized_log_path is None


@pytest.mark.asyncio
async def test_missing_video_uses_fastapi_validation(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post("/api/v1/incidents/upload", files={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "video"]


@pytest.mark.asyncio
async def test_upload_invalid_video_type_returns_structured_422(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={"video": ("incident.mov", b"video-bytes", "video/quicktime")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "unsupported_format"
    assert detail["field"] == "video"
    assert detail["package_id"].startswith("PKG-")


@pytest.mark.asyncio
async def test_upload_corrupt_video_returns_structured_422(client, monkeypatch, ingestion_service):
    def reject_video(video_path: Path) -> VideoProbeResult:
        raise IncidentIngestionError(
            "video_invalid",
            "The uploaded video is invalid or corrupt.",
            field="video",
        )

    ingestion_service.video_service.probe = reject_video
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={"video": video_file(b"not-a-real-video")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "video_invalid"
    assert detail["field"] == "video"
    assert detail["package_id"].startswith("PKG-")
    package = ingestion_service.repository.get(detail["package_id"])
    assert package is not None
    assert package.status.value == "FAILED"


@pytest.mark.asyncio
async def test_upload_invalid_log_returns_structured_422(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={
            "video": video_file(),
            "log": ("telemetry.csv", b"speed\n12\n13\n", "text/csv"),
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "log_missing_timestamp"
    assert detail["field"] == "log"
    package = ingestion_service.repository.get(detail["package_id"])
    assert package is not None
    assert package.status.value == "FAILED"


@pytest.mark.asyncio
async def test_upload_video_too_large_returns_structured_422(client, monkeypatch, ingestion_service):
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: ingestion_service)

    response = await client.post(
        "/api/v1/incidents/upload",
        files={"video": video_file(b"x" * (1024 * 1024 + 1))},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "file_too_large"
    assert detail["field"] == "video"
    assert detail["package_id"].startswith("PKG-")
