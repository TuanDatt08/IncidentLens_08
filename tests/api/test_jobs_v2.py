import importlib
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from test_authorization import signed_identity

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.tables_v2 import RecordingV2
from backend.services.identity import Principal


@pytest.mark.asyncio
async def test_v2_job_idempotency_resume_stale_fencing_and_budget(db_client, monkeypatch):
    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("V2_IDENTITY_SECRET", key)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    with session_scope() as session:
        session.add(RecordingV2(recording_id="rec", duration_s=18000.0, video_uri="video.mp4", metadata_json={}))
    headers = {"Authorization": "Bearer " + signed_identity(key), "Idempotency-Key": "fixture-run"}
    response = await db_client.post("/api/v2/recordings/rec/analyze", json={"provider_profile": "self_hosted"}, headers=headers)
    assert response.status_code == 202
    assert (await db_client.post("/api/v2/recordings/rec/analyze", json={"provider_profile": "self_hosted"}, headers=headers)).json() == response.json()
    job_id = response.json()["job_id"]
    module = importlib.import_module("backend.services.jobs_v2")
    claim = module.claim_job(job_id)
    assert claim.attempt == 1
    module.checkpoint(job_id, claim.attempt, "segment-1", stage="DETECTION", coverage={"sampled_frames": 10}, result={"candidate_ids": ["cnd-1"]})
    module.reserve_call(job_id, claim.attempt)
    with session_scope() as session:
        job = session.get(module.JobV2, job_id)
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    resumed = module.claim_job(job_id)
    assert resumed.attempt == 2
    assert "segment-1" in resumed.checkpoints
    with pytest.raises(ApiError) as exc:
        module.checkpoint(job_id, 1, "stale", stage="ANALYSIS", coverage={}, result={})
    assert exc.value.code == "JOB_LEASE_LOST"
    module.checkpoint(job_id, 2, "segment-1", stage="DETECTION", coverage={"sampled_frames": 10}, result={"candidate_ids": ["cnd-1"]})
    status = await db_client.get("/api/v2/jobs/" + job_id, headers=headers)
    assert status.json()["progress"]["done"] == 1
    assert status.json()["budget"]["calls_used"] == 1
    assert status.json()["coverage"]["sampled_frames"] == 10
    module.checkpoint(job_id, 2, "discovery", stage="DETECTION", coverage={"sampled_frames": 0}, result={"scan_pending": True})
    module.checkpoint(job_id, 2, "discovery", stage="DETECTION", coverage={"sampled_frames": 3}, result={"scan_pending": False})
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"rec"}))
    assert module.get_job(job_id, actor)["coverage"]["sampled_frames"] == 3
    cancelled = await db_client.post("/api/v2/jobs/" + job_id + "/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    with pytest.raises(ApiError):
        module.reserve_call(job_id, 2)
