"""Opt-in real PostgreSQL + FFmpeg smoke test inside the backend image.

Run only with RAV18_PG_E2E=1 and DATABASE_URL ending in /rav18_e2e.
"""

import os
import subprocess
import sys
import json

import pytest
from fastapi.testclient import TestClient

from src.main import app
def test_postgres_ffmpeg_upload_to_review(tmp_path):
    if os.environ.get("RAV18_PG_E2E") != "1" or not os.environ.get("DATABASE_URL", "").endswith("/rav18_e2e"):
        pytest.skip("requires the isolated rav18_e2e PostgreSQL database")
    video = tmp_path / "synthetic.mp4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=10", "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(video)],
        check=True,
    )
    with TestClient(app) as client:
        upload = client.post(
            "/api/v1/incidents/upload",
            files={
                "video": (video.name, video.read_bytes(), "video/mp4"),
                "log": ("log.csv", b"sec_from_incident,sim_time_s\n-0.5,1.5\n0,2\n0.5,2.5\n", "text/csv"),
            },
        )
        assert upload.status_code == 201, upload.text
        incident_id = upload.json()["incident_id"]
        job_id = client.post(f"/api/v1/incidents/{incident_id}/analyze").json()["job_id"]
        demo = subprocess.run([sys.executable, "-m", "src.demo_fake_worker", job_id], capture_output=True, text=True)
        assert demo.returncode == 0, demo.stderr
        assert json.loads(demo.stdout)["status"] == "succeeded"
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "succeeded", job
        report_url = job["result_uri"]
        report = client.get(report_url).json()
        assert "DEMO" in report["summary"]
        assert report["incident_window"] == {"start": -0.5, "critical": 0.0, "end": 0.5}
        evidence = client.get(f"/api/v1/incidents/{incident_id}/evidence").json()["items"]
        assert any(item["kind"] == "video" and item["time_range_s"] == [-0.5, 0.5] for item in evidence)
        assert client.patch(report_url, json={"version": 1, "summary": "Engineer checked"}).json()["version"] == 2
        assert client.post(f"{report_url}/submit").json()["status"] == "IN_REVIEW"
        assert client.post(f"{report_url}/approve").json()["status"] == "APPROVED"
        assert client.get(f"/api/v1/incidents/{incident_id}/video", headers={"Range": "bytes=0-9"}).status_code == 206
