import pytest

from src.models.contracts import AnalysisResult, LocalizationResult
from src.services.video import VideoProbeResult, VideoService
from src.worker import run_once


class FakeVLM:
    def pass1(self, video_path, sampled_frames, metadata):
        return LocalizationResult(
            incident_detected=True,
            candidate_start=-1,
            critical_time=0,
            candidate_end=1,
            collision_offset_in_video_s=5,
        )

    def pass2(self, prepared):
        return AnalysisResult(
            incident_detected=True,
            incident_window={"start": -1, "critical": 0, "end": 1},
            summary="Observed collision",
        )


@pytest.mark.asyncio
async def test_audit_shows_upload_analyze_and_completion_in_order(db_client, monkeypatch):
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))

    def write_asset(self, video_path, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"asset")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", write_asset)

    def write_clip(self, video_path, start_s, end_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"clip")
        return destination

    monkeypatch.setattr(VideoService, "extract_clip", write_clip)
    upload = await db_client.post("/api/v1/incidents/upload", files={"video": ("clip.mp4", b"video", "video/mp4")})
    incident_id = upload.json()["incident_id"]
    await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    run_once(vlm=FakeVLM())
    response = await db_client.get(f"/api/v1/incidents/{incident_id}/audit")
    assert response.status_code == 200
    assert [item["action"] for item in response.json()["items"]] == [
        "INCIDENT_CREATED",
        "ANALYSIS_STARTED",
        "ANALYSIS_COMPLETED",
    ]
