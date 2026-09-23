"""Public upload-to-review workflow with fake VLM and media extraction."""

import pytest
from sqlalchemy import select

from src.config import get_settings
from src.db import session_scope
from src.demo_fake_worker import DemoVLM
from src.models.contracts import AnalysisResult, LocalizationResult
from src.models.tables import AnalysisReport, Incident, ReportVersion
from src.services.video import VideoProbeResult, VideoService
from src.worker import run_once


class IncidentVLM:
    def pass1(self, video_path, sampled_frames, metadata):
        return LocalizationResult(
            incident_detected=True,
            candidate_start=-1,
            critical_time=0,
            candidate_end=1,
            evidence_timestamps=[0],
            collision_offset_in_video_s=5,
        )

    def pass2(self, prepared):
        assert [row["sec_from_incident"] for row in prepared.telemetry_rows] == [-1, 0, 1]
        return AnalysisResult(
            incident_detected=True,
            incident_window={"start": -1, "critical": 0, "end": 1},
            summary="Initial analysis",
        )


class NoIncidentVLM:
    def pass1(self, video_path, sampled_frames, metadata):
        return LocalizationResult(incident_detected=False)

    def pass2(self, prepared):
        raise AssertionError("Pass 2 must not run")


@pytest.fixture(autouse=True)
def media_tools(monkeypatch):
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
        "/api/v1/incidents/upload",
        files={
            "video": ("incident.mp4", b"source-video", "video/mp4"),
            "log": ("log.csv", b"sec_from_incident,sim_time_s\n-1,9\n0,10\n1,11\n", "text/csv"),
        },
    )
    assert response.status_code == 201
    return response.json()["incident_id"]


@pytest.mark.asyncio
async def test_upload_poll_edit_review_and_media(db_client):
    incident_id = await upload(db_client)
    started = await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert started.status_code == 202
    job_id = started.json()["job_id"]
    assert (await db_client.get(f"/api/v1/jobs/{job_id}")).json()["status"] == "queued"
    assert run_once(vlm=IncidentVLM())
    assert (await db_client.get(f"/api/v1/jobs/{job_id}")).json()["status"] == "succeeded"

    report_url = f"/api/v1/incidents/{incident_id}/report"
    report = (await db_client.get(report_url)).json()
    assert report["version"] == 1 and report["review_status"] == "DRAFT"
    evidence = (await db_client.get(f"/api/v1/incidents/{incident_id}/evidence")).json()["items"]
    assert any(item["kind"] == "video" and item["time_range_s"] == [-1.0, 1.0] for item in evidence)
    video = await db_client.get(f"/api/v1/incidents/{incident_id}/video")
    assert video.status_code == 200 and video.content == b"source-video"
    seek = await db_client.get(f"/api/v1/incidents/{incident_id}/video", headers={"Range": "bytes=0-5"})
    assert seek.status_code == 206 and seek.content == b"source"
    clip = next(item for item in evidence if item["kind"] == "video")
    asset = await db_client.get(f"/api/v1/incidents/{incident_id}/evidence/{clip['evidence_id']}/media")
    assert asset.status_code == 200 and asset.content == b"mp4"
    assert (await db_client.get(f"/api/v1/incidents/OTHER/evidence/{clip['evidence_id']}/media")).status_code == 404

    edited = await db_client.patch(report_url, json={"version": 1, "summary": "Verified against telemetry"})
    assert edited.status_code == 200
    assert edited.json()["version"] == 2
    assert edited.json()["summary"] == "Verified against telemetry"
    with session_scope() as session:
        incident_row = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        report_row = session.scalar(select(AnalysisReport).where(AnalysisReport.incident_id == incident_row.id))
        versions = session.scalars(select(ReportVersion).where(ReportVersion.report_id == report_row.id).order_by(ReportVersion.version)).all()
        assert [item.version for item in versions] == [1, 2]
        assert versions[0].content["summary"] == "Initial analysis"
        assert versions[1].content["summary"] == "Verified against telemetry"
    stale = await db_client.patch(report_url, json={"version": 1, "summary": "Stale"})
    assert stale.status_code == 409
    forbidden_field = await db_client.patch(report_url, json={"version": 2, "evidence_ids": []})
    assert forbidden_field.status_code == 422
    submitted = await db_client.post(f"{report_url}/submit")
    assert submitted.status_code == 200 and submitted.json()["status"] == "IN_REVIEW"
    approved = await db_client.post(f"{report_url}/approve")
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    assert (await db_client.post(f"{report_url}/reject", json={"reason": "late"})).status_code == 409
    assert (await db_client.get(report_url)).json()["review_status"] == "APPROVED"
    audit = (await db_client.get(f"/api/v1/incidents/{incident_id}/audit")).json()["items"]
    assert [item["action"] for item in audit][-3:] == ["REPORT_EDITED", "REPORT_SUBMITTED", "REPORT_APPROVED"]


@pytest.mark.asyncio
async def test_reject_requires_reason_and_keeps_rejected_state(db_client):
    incident_id = await upload(db_client)
    await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert run_once(vlm=IncidentVLM())
    report_url = f"/api/v1/incidents/{incident_id}/report"
    await db_client.post(f"{report_url}/submit")
    assert (await db_client.post(f"{report_url}/reject", json={"reason": "  "})).status_code == 422
    rejected = await db_client.post(f"{report_url}/reject", json={"reason": "Evidence needs review"})
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"
    assert (await db_client.patch(report_url, json={"version": 1, "summary": "late"})).status_code == 409
    audit = (await db_client.get(f"/api/v1/incidents/{incident_id}/audit")).json()["items"]
    assert audit[-1]["metadata"]["reason"] == "Evidence needs review"


@pytest.mark.asyncio
async def test_no_incident_is_success_with_empty_report(db_client):
    incident_id = await upload(db_client)
    job_id = (await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")).json()["job_id"]
    assert run_once(vlm=NoIncidentVLM())
    job = (await db_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "succeeded" and job["pass"] == 1
    report = (await db_client.get(job["result_uri"])).json()
    assert report["incident_detected"] is False
    assert report["review_status"] == "DRAFT" and report["version"] == 1
    assert report["incident_window"] is None and report["evidence_ids"] == []
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}/evidence")).json()["items"] == []
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()["processing_status"] == "COMPLETED"
    audit = (await db_client.get(f"/api/v1/incidents/{incident_id}/audit")).json()["items"]
    assert audit[-1]["action"] == "ANALYSIS_COMPLETED"


@pytest.mark.asyncio
async def test_review_and_media_are_closed_in_production_without_auth(db_client, monkeypatch):
    incident_id = await upload(db_client)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    report_url = f"/api/v1/incidents/{incident_id}/report"
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}/video")).status_code == 403
    assert (await db_client.patch(report_url, json={"version": 1, "summary": "x"})).status_code == 403
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_media_route_rejects_storage_path_escape(db_client):
    incident_id = await upload(db_client)
    with session_scope() as session:
        incident = session.scalar(select(Incident).where(Incident.incident_id == incident_id))
        incident.video_uri = "../outside.mp4"
    response = await db_client.get(f"/api/v1/incidents/{incident_id}/video")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEDIA_NOT_FOUND"


@pytest.mark.asyncio
async def test_demo_fake_worker_processes_only_selected_job(db_client):
    first_incident = await upload(db_client)
    second_incident = await upload(db_client)
    first_job = (await db_client.post(f"/api/v1/incidents/{first_incident}/analyze")).json()["job_id"]
    second_job = (await db_client.post(f"/api/v1/incidents/{second_incident}/analyze")).json()["job_id"]

    assert run_once(vlm=DemoVLM(), job_id=second_job)
    assert (await db_client.get(f"/api/v1/jobs/{first_job}")).json()["status"] == "queued"
    assert (await db_client.get(f"/api/v1/jobs/{second_job}")).json()["status"] == "succeeded"
    report = (await db_client.get(f"/api/v1/incidents/{second_incident}/report")).json()
    assert report["incident_detected"] is True
    assert report["incident_window"] == {"start": -0.5, "critical": 0.0, "end": 0.5}
    assert "DEMO" in report["summary"]
    assert report["review_status"] == "DRAFT"
