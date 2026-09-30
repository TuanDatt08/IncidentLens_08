from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.contracts import AnalysisResult, LocalizationResult
from src.services.jobs import claim_job, create_job, get_job
from src.services.processing import ProcessedResult
from src.services.processing import InsufficientEvidence
from src.services.reports import complete_analysis
from src.services.video import VideoProbeResult, VideoService
from src.worker import run_once


class FakeVLM:
    def pass1(self, video_path, sampled_frames, metadata):
        return LocalizationResult(
            incident_detected=True,
            candidate_start=-1.0,
            critical_time=0,
            candidate_end=1.0,
            evidence_timestamps=[0],
            collision_offset_in_video_s=5.0,
        )

    def pass2(self, prepared):
        assert prepared.candidate_start == -1.0
        return AnalysisResult(
            incident_detected=True,
            incident_type="pedestrian_collision",
            incident_window={"start": -1.0, "critical": 0, "end": 1.0},
            summary="Pedestrian entered roadway.",
            observations=["Contact visible"],
        )


@pytest.fixture(autouse=True)
def fake_media_tools(monkeypatch):
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


@pytest.mark.asyncio
async def test_worker_persists_report_evidence_and_terminal_job(db_client):
    upload = await db_client.post(
        "/api/v1/incidents/upload",
        files={
            "video": ("clip.mp4", b"video", "video/mp4"),
            "log": ("telemetry.csv", b"sec_from_incident,sim_time_s\n-1,9\n0,10\n1,11\n", "text/csv"),
        },
    )
    incident_id = upload.json()["incident_id"]
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}/report")).status_code == 404
    job_id = (await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")).json()["job_id"]
    assert run_once(vlm=FakeVLM()) is True
    job = (await db_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "succeeded"
    assert job["result_uri"] == f"/api/v1/incidents/{incident_id}/report"
    assert job["error"] is None
    report = (await db_client.get(job["result_uri"])).json()
    evidence = (await db_client.get(f"/api/v1/incidents/{incident_id}/evidence")).json()["items"]
    assert report["review_status"] == "DRAFT"
    assert report["incident_id"] == incident_id
    assert report["incident_window"]["start"] == -1.0
    assert set(report["evidence_ids"]) == {item["evidence_id"] for item in evidence}
    assert any(item["time_range_s"] == [-1.0, 1.0] for item in evidence)
    assert any(item["kind"] == "telemetry" and item["time_range_s"] == [-1.0, 1.0] for item in evidence)
    assert all(not Path(item["uri"]).is_absolute() for item in evidence)
    detail = (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()
    assert detail["processing_status"] == "COMPLETED"
    assert detail["video_metadata"]["collision_offset_in_video_s"] == 5.0
    assert detail["incident_record"] is None
    audit = (await db_client.get(f"/api/v1/incidents/{incident_id}/audit")).json()["items"]
    assert [event["action"] for event in audit] == ["INCIDENT_CREATED", "ANALYSIS_STARTED", "ANALYSIS_COMPLETED"]
    assert run_once(vlm=FakeVLM()) is False


@pytest.mark.asyncio
async def test_invalid_evidence_rolls_back_report_and_job_success(db_client):
    upload = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": ("clip.mp4", b"video", "video/mp4")},
    )
    incident_id = upload.json()["incident_id"]
    job_id = create_job(incident_id)["job_id"]
    assert claim_job().job_id == job_id
    result = ProcessedResult(
        analysis=AnalysisResult(incident_detected=True, incident_window={"start": -1, "critical": 0, "end": 1}),
        evidence=[{"evidence_id": "EVD-BAD", "kind": "video", "uri": "../bad", "sha256": "bad", "time_range_s": [-1, 1]}],
        collision_offset_in_video_s=5.0,
    )
    with pytest.raises(ValidationError):
        complete_analysis(job_id, result)
    assert get_job(job_id)["status"] == "running"
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}/report")).status_code == 404


@pytest.mark.asyncio
async def test_evidence_hash_must_match_stored_file(db_client):
    from src.config import get_settings

    upload = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": ("clip.mp4", b"video", "video/mp4")},
    )
    incident_id = upload.json()["incident_id"]
    job_id = create_job(incident_id)["job_id"]
    claim_job()
    clip = Path(get_settings().incident_storage_dir) / incident_id / "clips" / "candidate.mp4"
    clip.parent.mkdir(parents=True, exist_ok=True)
    clip.write_bytes(b"clip")
    result = ProcessedResult(
        analysis=AnalysisResult(incident_detected=True, incident_window={"start": -1, "critical": 0, "end": 1}),
        evidence=[{"evidence_id": "EVD-BAD-HASH", "kind": "video", "uri": f"{incident_id}/clips/candidate.mp4", "sha256": "a" * 64, "time_range_s": [-1, 1]}],
        collision_offset_in_video_s=5,
    )
    with pytest.raises(InsufficientEvidence):
        complete_analysis(job_id, result)
    assert get_job(job_id)["status"] == "running"
