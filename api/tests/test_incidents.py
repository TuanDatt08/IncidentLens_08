import pytest

from backend.models.contracts import IncidentRecordV1
from backend.services.incidents import import_incident_record
from backend.services.video import VideoProbeResult, VideoService


@pytest.fixture(autouse=True)
def fake_ffprobe(monkeypatch):
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10.0, 30.0, 1920, 1080))


@pytest.mark.asyncio
async def test_upload_and_list_use_public_incident_id_and_database(db_client):
    response = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": ("clip.mp4", b"fake-video", "video/mp4")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["incident_id"].startswith("INC-")
    assert data["processing_status"] == "READY"
    assert data["sync_offset"] is None
    assert data["frame_count"] == 0
    assert "package_id" not in data
    incident_id = data["incident_id"]

    detail = (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()
    assert detail["incident_id"] == incident_id
    assert detail["incident_record"] is None
    assert detail["telemetry_metadata"] is None
    assert detail["video_uri"].endswith(f"{incident_id}/source/video.mp4")
    assert not detail["video_uri"].startswith("C:")
    listing = (await db_client.get("/api/v1/incidents?limit=10&offset=0")).json()
    assert listing["total"] == 1
    assert listing["items"][0]["incident_id"] == incident_id


@pytest.mark.asyncio
async def test_upload_canonical_csv_and_factual_record_stay_separate(db_client):
    csv = b"sec_from_incident,sim_time_s,wall_clock_ts\n-1,9,2026-09-23T00:00:00Z\n0,10,2026-09-23T00:00:01Z\n"
    response = await db_client.post(
        "/api/v1/incidents/upload",
        files={
            "video": ("clip.mp4", b"fake-video", "video/mp4"),
            "log": ("telemetry.csv", csv, "text/csv"),
        },
    )
    assert response.status_code == 201
    incident_id = response.json()["incident_id"]
    record = IncidentRecordV1(scenario="jaywalk_occluded", template="pedestrian", collision={"hit_category": "walker"})
    import_incident_record(incident_id, record)
    detail = (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()
    assert detail["telemetry_metadata"]["time_column"] == "sec_from_incident"
    assert detail["telemetry_metadata"]["start_s"] == -1
    assert detail["incident_record"]["scenario"] == "jaywalk_occluded"
    assert "summary" not in detail["incident_record"]


@pytest.mark.asyncio
async def test_upload_rejects_invalid_video_and_log_without_incident(db_client):
    bad_video = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": ("clip.txt", b"bad", "text/plain")},
    )
    assert bad_video.status_code == 422
    assert bad_video.json()["error"]["code"] == "INVALID_VIDEO"

    bad_log = await db_client.post(
        "/api/v1/incidents/upload",
        files={
            "video": ("clip.mp4", b"fake-video", "video/mp4"),
            "log": ("telemetry.csv", b"sim_time_s\n1\n", "text/csv"),
        },
    )
    assert bad_log.status_code == 422
    assert bad_log.json()["error"]["code"] == "INVALID_LOG"
    assert (await db_client.get("/api/v1/incidents")).json()["total"] == 0
