"""Job polling and review transitions on the PostgreSQL-ready workflow."""

import pytest
from pydantic import ValidationError

from src.demo_fake_worker import DemoVLM
from src.models.contracts import EvidenceV1
from src.services.jobs import claim_job, fail_job, get_job, heartbeat
from src.services.video import VideoProbeResult, VideoService
from src.worker import run_once


@pytest.fixture(autouse=True)
def fake_media(monkeypatch):
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))

    def frame(self, video_path, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return destination

    def clip(self, video_path, start_s, end_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"mp4")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", frame)
    monkeypatch.setattr(VideoService, "extract_clip", clip)


async def upload(db_client):
    response = await db_client.post(
        "/api/v1/incidents/upload", files={"video": ("incident.mp4", b"video-bytes", "video/mp4")}
    )
    assert response.status_code == 201
    return response.json()["incident_id"]


@pytest.mark.asyncio
async def test_incident_analyze_job_polling_and_report_are_separate_states(db_client):
    incident_id = await upload(db_client)
    listing = (await db_client.get("/api/v1/incidents")).json()
    assert any(item["incident_id"] == incident_id for item in listing["items"])

    accepted = await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert accepted.status_code == 202
    job_id = accepted.json()["job_id"]
    assert (await db_client.get(f"/api/v1/jobs/{job_id}")).json()["status"] == "queued"
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()["processing_status"] == "PROCESSING"
    assert (await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")).status_code == 409

    assert run_once(vlm=DemoVLM(), job_id=job_id)
    job = (await db_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "succeeded" and job["pass"] == 2
    report = (await db_client.get(job["result_uri"])).json()
    assert report["review_status"] == "DRAFT"
    assert report["incident_id"] == incident_id
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()["processing_status"] == "COMPLETED"
    audit = (await db_client.get(f"/api/v1/incidents/{incident_id}/audit")).json()["items"]
    assert [item["action"] for item in audit] == ["INCIDENT_CREATED", "ANALYSIS_STARTED", "ANALYSIS_COMPLETED"]


@pytest.mark.asyncio
async def test_worker_can_claim_one_job_without_stealing_another(db_client):
    first = await upload(db_client)
    second = await upload(db_client)
    first_job = (await db_client.post(f"/api/v1/incidents/{first}/analyze")).json()["job_id"]
    second_job = (await db_client.post(f"/api/v1/incidents/{second}/analyze")).json()["job_id"]

    claim = claim_job(second_job)
    assert claim.job_id == second_job
    heartbeat(second_job, pass_number=1, done=0, total=2, expected_attempt=claim.attempt)
    assert get_job(first_job)["status"] == "queued"
    assert get_job(second_job)["status"] == "running"
    fail_job(second_job, "VLM_FAILED", "Demo failure", expected_attempt=claim.attempt)
    assert get_job(second_job)["status"] == "failed"
    assert (await db_client.get(f"/api/v1/incidents/{second}")).json()["processing_status"] == "FAILED"


@pytest.mark.asyncio
async def test_review_requires_report_and_valid_transition_order(db_client):
    incident_id = await upload(db_client)
    report_url = f"/api/v1/incidents/{incident_id}/report"
    missing = await db_client.post(f"{report_url}/submit")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "REPORT_NOT_FOUND"

    job_id = (await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")).json()["job_id"]
    assert run_once(vlm=DemoVLM(), job_id=job_id)
    assert (await db_client.post(f"{report_url}/approve")).status_code == 409
    assert (await db_client.post(f"{report_url}/submit")).json()["status"] == "IN_REVIEW"
    assert (await db_client.post(f"{report_url}/reject", json={"reason": "  "})).status_code == 422
    assert (await db_client.post(f"{report_url}/approve")).json()["status"] == "APPROVED"
    assert (await db_client.post(f"{report_url}/reject", json={"reason": "too late"})).status_code == 409


def test_evidence_contract_rejects_legacy_fields():
    payload = {
        "evidence_id": "EVD-001",
        "kind": "video",
        "uri": "INC-001/clips/clip.mp4",
        "sha256": "a" * 64,
        "time_range_s": (-0.5, 0.5),
    }
    assert EvidenceV1.model_validate(payload).time_range_s == (-0.5, 0.5)
    with pytest.raises(ValidationError):
        EvidenceV1.model_validate({**payload, "timestamp_start": 0, "clip_path": "old.mp4"})
