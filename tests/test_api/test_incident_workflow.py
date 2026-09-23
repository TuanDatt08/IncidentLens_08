from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.workflow import JobStatus
from src.schemas.incident import Evidence
from src.services.errors import IncidentIngestionError
from src.services.incident_ingestion import IncidentIngestionService
from src.services.logs import LogService
from src.services.package_repository import IncidentPackageRepository
from src.services.storage import LocalStorage
from src.services.video import VideoProbeResult


class FakeVideoService:
    def validate_upload(self, filename: str | None, content_type: str | None) -> None:
        if not filename or not filename.lower().endswith(".mp4") or content_type != "video/mp4":
            raise IncidentIngestionError("unsupported_format", "Unsupported video format.", field="video")

    def probe(self, video_path: Path) -> VideoProbeResult:
        assert video_path.exists()
        return VideoProbeResult(duration=20.0, fps=30.0, width=1280, height=720)


@pytest.fixture
def workflow_ingestion_service(tmp_path: Path) -> IncidentIngestionService:
    storage_root = tmp_path / "incidents"
    return IncidentIngestionService(
        storage=LocalStorage(storage_root),
        repository=IncidentPackageRepository(storage_root),
        video_service=FakeVideoService(),
        log_service=LogService(),
        max_video_size_bytes=1024 * 1024,
        max_log_size_bytes=1024 * 1024,
    )


def video_file() -> tuple[str, bytes, str]:
    return ("incident.mp4", b"video-bytes", "video/mp4")


async def upload(client, monkeypatch, service, log: bytes | None = None) -> str:
    monkeypatch.setattr("src.api.incidents.get_ingestion_service", lambda: service)
    files = {"video": video_file()}
    if log is not None:
        files["log"] = ("telemetry.csv", log, "text/csv")
    response = await client.post("/api/v1/incidents/upload", files=files)
    assert response.status_code == 201
    return response.json()["incident_id"]


@pytest.mark.asyncio
async def test_upload_dats_csv_prefers_incident_relative_time(client, monkeypatch, workflow_ingestion_service):
    csv = (
        "wall_clock_ts,sec_from_incident,sim_time_s,speed_kmh,throttle,steer,brake,"
        "loc_x,loc_y,loc_z,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,compass_deg,"
        "gnss_lat,gnss_lon,collision_intensity,collision_with\n"
        "2026-01-01T00:00:00Z,0,100,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,none\n"
        "2026-01-01T00:00:01Z,1,101,11,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,none\n"
    )
    incident_id = await upload(client, monkeypatch, workflow_ingestion_service, csv)
    package = workflow_ingestion_service.repository.get(incident_id)
    assert package is not None
    assert package.log_metadata == {
        "row_count": 2,
        "timestamp_column": "sec_from_incident",
        "timestamp_unit": "seconds",
        "time_reference": "incident_relative",
    }
    assert package.sync_offset is None


@pytest.mark.asyncio
async def test_incident_list_detail_and_analyze_return_polling_contract(
    client, monkeypatch, workflow_ingestion_service
):
    incident_id = await upload(client, monkeypatch, workflow_ingestion_service)

    listed = await client.get("/api/v1/incidents")
    assert listed.status_code == 200
    assert any(item["id"] == incident_id for item in listed.json())

    analyze = await client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert analyze.status_code == 202
    assert analyze.json()["status"] == "queued"
    job_id = analyze.json()["job_id"]

    queued = await client.get(f"/api/v1/jobs/{job_id}")
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert queued.json()["pass"] is None
    assert set(queued.json()["progress"]) == {"done", "total"}

    workflow = __import__("src.api.incidents", fromlist=["get_workflow_repository"])
    repository = workflow.get_workflow_repository()
    job = repository.get_job(job_id)
    assert job is not None
    job.status = JobStatus.RUNNING
    repository.save_job(job)
    running = await client.get(f"/api/v1/jobs/{job_id}")
    assert running.json()["status"] == "running"

    job.status = JobStatus.SUCCEEDED
    job.progress_done = 1
    job.progress_total = 1
    repository.save_job(job)
    succeeded = await client.get(f"/api/v1/jobs/{job_id}")
    assert succeeded.json()["status"] == "succeeded"


@pytest.mark.asyncio
async def test_invalid_review_transition_is_rejected(client, monkeypatch, workflow_ingestion_service):
    incident_id = await upload(client, monkeypatch, workflow_ingestion_service)
    approved = await client.post(f"/api/v1/incidents/{incident_id}/report/approve")
    assert approved.status_code == 409

    submitted = await client.post(f"/api/v1/incidents/{incident_id}/report/submit")
    assert submitted.status_code == 200
    approved = await client.post(f"/api/v1/incidents/{incident_id}/report/approve")
    assert approved.status_code == 200
    rejected = await client.post(
        f"/api/v1/incidents/{incident_id}/report/reject", json={"reason": "too late"}
    )
    assert rejected.status_code == 409

    audit = await client.get(f"/api/v1/incidents/{incident_id}/audit")
    assert audit.status_code == 200
    assert any(event["action"] == "report_approved" for event in audit.json())


def test_evidence_contract_accepts_normalized_shape_and_rejects_invalid_values():
    evidence = Evidence(
        evidence_id="EV-1",
        kind="frame",
        uri="evidence/EV-1.jpg",
        sha256="a" * 64,
        time_range_s=(0, 1.5),
        tier="core",
        bytes=None,
        media_type="image/jpeg",
    )
    assert evidence.time_range_s == (0, 1.5)

    with pytest.raises(ValidationError):
        Evidence(
            evidence_id="EV-2",
            kind="frame",
            uri="/absolute/path.jpg",
            sha256="A" * 64,
            time_range_s=(2, 1),
            tier=None,
            bytes=None,
            media_type=None,
        )


def test_evidence_boundary_maps_legacy_names():
    evidence = Evidence(
        evidence_id="EV-legacy",
        source_type="VIDEO",
        clip_path="evidence/clip.mp4",
        timestamp_start=0,
        timestamp_end=2,
        sha256="b" * 64,
    )
    assert evidence.kind == "video"
    assert evidence.uri == "evidence/clip.mp4"
    assert evidence.time_range_s == (0, 2)
