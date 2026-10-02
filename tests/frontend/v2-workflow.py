"""Real API + production Next.js browser smoke with synthetic, private temp fixtures.

Install Playwright separately as a development test tool; Chromium/Chrome needed.
Run from the repository root: python tests/frontend/v2-workflow.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TEMP_PLAYWRIGHT = Path(tempfile.gettempdir()) / "p076-playwright"
if TEMP_PLAYWRIGHT.exists():
    sys.path.insert(0, str(TEMP_PLAYWRIGHT))

import httpx  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402


def identity(key: str, subject: str, roles: list[str]) -> str:
    claims = {"sub": subject, "roles": roles, "recordings": ["rec-e2e", "rec-upload"], "exp": int(time.time()) + 1800, "iss": "local-v2", "aud": "incidentlens-v2"}
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return body + "." + hmac.new(key.encode(), body.encode(), hashlib.sha256).hexdigest()


def available(port: int) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


def wait_url(url: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("test server exited before readiness; inspect temporary server log")
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise RuntimeError("test server readiness timed out")


def main():
    available(8000)
    available(3016)
    directory = Path(tempfile.mkdtemp(prefix="p076-v2-e2e-"))
    storage = directory / "storage"
    storage.mkdir()
    key = secrets.token_urlsafe(48)
    environment = {**os.environ, "DATABASE_URL": f"sqlite:///{(directory / 'api.db').as_posix()}", "INCIDENT_STORAGE_DIR": str(storage), "APP_ENV": "test", "V2_IDENTITY_SECRET": key, "CORS_ORIGINS": "http://localhost:3016", "NEXT_TELEMETRY_DISABLED": "1"}
    os.environ.update({name: environment[name] for name in ("DATABASE_URL", "INCIDENT_STORAGE_DIR", "APP_ENV", "V2_IDENTITY_SECRET", "CORS_ORIGINS")})
    from alembic import command
    from alembic.config import Config

    from backend.config import get_settings
    from backend.db import get_session_factory, session_scope
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.models.tables_v2 import JobV2, RecordingV2
    from backend.services.evidence_extraction import EvidenceAsset, file_hash
    from backend.services.evidence_validation import EvidenceRegistry
    from backend.services.reports_v2 import create_report
    from backend.services.video import VideoService

    get_settings.cache_clear()
    get_session_factory.cache_clear()
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    source = storage / "synthetic.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=blue:s=160x120:r=10:d=4", "-c:v", "libx264", str(source)], check=True, capture_output=True, timeout=30)
    service = VideoService()
    frame = service.extract_frame(source, 2.5, storage / "masked-fixture.jpg")
    clip = service.extract_clip(source, 1, 3, storage / "masked-fixture.mp4")
    assets = (EvidenceAsset("EVD-frame", "rec-e2e", "cnd-e2e", frame, file_hash(frame), 2.5, 2.5, "VIDEO", "image/jpeg", 0, "MASKED", "PASSED"), EvidenceAsset("EVD-clip", "rec-e2e", "cnd-e2e", clip, file_hash(clip), 1.0, 3.0, "VIDEO", "video/mp4", None, "MASKED", "PASSED"))
    with session_scope() as session:
        session.add(RecordingV2(recording_id="rec-e2e", duration_s=4.0, video_uri="synthetic.mp4", metadata_json=service.probe(source).as_dict()))
    payload = {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.5, "end_s": 3.0}, "summary": "Synthetic browser fixture", "timeline": [{"time_s": 2.5, "observation": "Synthetic slowing", "evidence_ids": ["EVD-frame"], "source": "VIDEO", "certainty": "OBSERVED"}], "factors": [{"category": "VEHICLE_OR_SYSTEM", "label": "Internal cause", "claim_status": "UNKNOWN", "evidence_ids": []}], "unknowns": ["Synthetic case; no controller log."], "review_status": "DRAFT"}
    report = create_report(AIIncidentAnalysisV2.model_validate(payload), EvidenceRegistry("rec-e2e", "cnd-e2e", assets), duration_s=4.0, provenance={"provider": "synthetic-browser-fixture"})
    log = (directory / "servers.log").open("w", encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=flags)
    frontend = subprocess.Popen(["cmd.exe", "/c", "npm", "--prefix", "frontend", "run", "start", "--", "-p", "3016"], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=flags)
    try:
        wait_url("http://127.0.0.1:8000/health", backend)
        wait_url("http://localhost:3016/recordings", frontend)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.add_cookies([{"name": "incidentlens_v2_identity", "value": identity(key, "engineer", ["Engineer"]), "domain": "localhost", "path": "/", "httpOnly": True, "sameSite": "Lax"}])
            page = context.new_page()
            page.goto("http://localhost:3016/recordings")
            expect(page.get_by_role("link", name="rec-e2e", exact=True)).to_be_visible()
            page.get_by_label("Recording ID", exact=True).fill("rec-upload")
            page.get_by_label("MP4 video").set_input_files(source)
            page.get_by_label("Video SHA-256 checksum").fill(file_hash(source))
            page.get_by_role("button", name="Upload or resume").click()
            expect(page.get_by_role("link", name="rec-upload", exact=True)).to_be_visible(timeout=15000)
            page.get_by_role("link", name="rec-upload", exact=True).click()
            page.get_by_role("button", name="Analyze recording").click()
            expect(page.get_by_role("heading", name="Analysis: queued")).to_be_visible()
            page.reload()
            expect(page.get_by_role("heading", name="Analysis: queued")).to_be_visible()
            with session_scope() as session:
                from sqlalchemy import func, select
                assert session.scalar(select(func.count()).select_from(JobV2).where(JobV2.recording_id == "rec-upload")) == 1
            page.get_by_role("button", name="Cancel analysis").click()
            expect(page.get_by_role("heading", name="Analysis: cancelled")).to_be_visible()
            page.goto("http://localhost:3016/reports/" + report["report_id"])
            expect(page.get_by_role("textbox", name="Summary", exact=True)).to_have_value("Synthetic browser fixture")
            page.get_by_role("textbox", name="Observation 1", exact=True).fill("Edited typed observation")
            page.get_by_role("button", name="Save changes").click()
            expect(page.get_by_text("DRAFT · Version 2 · HARD_BRAKING", exact=True)).to_be_visible()
            page.get_by_role("button", name="2.50 video seconds", exact=True).click()
            page.wait_for_function("Math.abs(document.querySelector('video').currentTime - 1.5) < 0.1")
            page.get_by_role("button", name="Submit for review", exact=True).click()
            expect(page.get_by_role("dialog", name="Confirm submit")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).to_have_count(0)
            expect(page.get_by_role("button", name="Submit for review", exact=True)).to_be_focused()
            page.get_by_role("button", name="Submit for review", exact=True).click()
            page.get_by_role("button", name="Confirm submit", exact=True).click()
            expect(page.get_by_text("IN_REVIEW · Version 3 · HARD_BRAKING", exact=True)).to_be_visible()
            context.add_cookies([{"name": "incidentlens_v2_identity", "value": identity(key, "reviewer", ["Reviewer"]), "domain": "localhost", "path": "/", "httpOnly": True, "sameSite": "Lax"}])
            page.reload()
            page.get_by_role("button", name="Approve report", exact=True).click()
            page.get_by_role("button", name="Confirm approve", exact=True).click()
            expect(page.get_by_text("APPROVED · Version 4 · HARD_BRAKING", exact=True)).to_be_visible()
            expect(page.get_by_role("textbox", name="Summary", exact=True)).to_be_disabled()
            expect(page.get_by_role("heading", name="Audit history", exact=True)).to_be_visible()
            page.screenshot(path=str(directory / "desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(directory / "mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            context.clear_cookies()
            page.reload()
            expect(page.get_by_role("alert").first).to_contain_text("session")
            browser.close()
        print("PASS: real API upload, job recovery/cancel, typed edit, seek, dialog Escape/focus, two-actor approval, audit, desktop/mobile, 401")
        print("Synthetic fixtures and screenshots: " + str(directory))
    finally:
        backend.terminate()
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(frontend.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            frontend.terminate()
        backend.wait(timeout=15)
        log.close()


if __name__ == "__main__":
    main()
