import pytest

from tests.api.test_auth import login, seed_user

ROUTES = [
    ("GET", "/incidents"), ("GET", "/incidents/INC-X"),
    ("POST", "/incidents/upload"), ("POST", "/incidents/INC-X/analyze"),
    ("GET", "/jobs/JOB-X"), ("GET", "/incidents/INC-X/report"),
    ("PATCH", "/incidents/INC-X/report"), ("POST", "/incidents/INC-X/report/submit"),
    ("POST", "/incidents/INC-X/report/approve"), ("POST", "/incidents/INC-X/report/reject"),
    ("GET", "/incidents/INC-X/evidence"), ("GET", "/incidents/INC-X/audit"),
    ("GET", "/incidents/INC-X/video"), ("GET", "/incidents/INC-X/telemetry"),
    ("GET", "/incidents/INC-X/evidence/E-X/media"), ("GET", "/admin/users"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ROUTES)
async def test_all_business_routes_reject_anonymous(auth_client, method, path):
    auth_client.cookies.clear()
    response = await auth_client.request(method, "/api/v1" + path, headers={"X-User-ID": "spoofed", "X-Role": "admin"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role,path", [
    ("reviewer", "/incidents/upload"), ("reviewer", "/incidents/X/analyze"),
    ("reviewer", "/incidents/X/report/submit"), ("admin", "/incidents/upload"),
    ("admin", "/incidents/X/report/approve"), ("engineer", "/incidents/X/report/approve"),
    ("engineer", "/incidents/X/report/reject"), ("engineer", "/admin/users"),
])
async def test_permissions_checked_before_mutations(auth_client, role, path):
    seed_user(roles=[role])
    await login(auth_client)
    response = await auth_client.post("/api/v1" + path, json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["approve", "reject"])
async def test_multi_role_user_cannot_review_own_edits_or_submission(auth_client, action):
    from backend.db import session_scope
    from backend.models.tables import AnalysisReport, Incident, ReportVersion
    user_id = seed_user(roles=["engineer", "reviewer"])
    seed_user("reviewer@example.com", ["reviewer"])
    with session_scope() as session:
        incident = Incident(incident_id="INC-SELF", processing_status="COMPLETED", video_uri="unused")
        session.add(incident)
        session.flush()
        report = AnalysisReport(incident_id=incident.id, incident_detected=False, review_status="DRAFT")
        session.add(report)
        session.flush()
        session.add(ReportVersion(report_id=report.id, version=1, content={}))
    await login(auth_client)
    url = "/api/v1/incidents/INC-SELF/report"
    edited = await auth_client.patch(url, json={"version": 1, "summary": "edited"}, headers={"X-User-ID": "another-user", "X-Role": "admin"})
    assert edited.status_code == 200
    assert (await auth_client.post(url + "/submit")).status_code == 200
    response = await auth_client.post(url + "/" + action, json={"reason": "needs review"})
    assert response.status_code == 403 and response.json()["error"]["code"] == "SELF_REVIEW_FORBIDDEN"
    audit = (await auth_client.get("/api/v1/incidents/INC-SELF/audit")).json()["items"]
    assert all(item["actor"] == str(user_id) for item in audit)
    await login(auth_client, "reviewer@example.com")
    assert (await auth_client.post(url + "/" + action, json={"reason": "needs review"})).status_code == 200


@pytest.mark.asyncio
async def test_upload_respects_lowered_size_limit_and_records_no_incident(auth_client, monkeypatch):
    from backend.config import get_settings
    from backend.services.video import VideoProbeResult, VideoService
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "1")
    get_settings.cache_clear()
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(1, 30, 320, 240))
    seed_user()
    await login(auth_client)
    response = await auth_client.post("/api/v1/incidents/upload", files={"video": ("clip.mp4", b"v" * (1024 * 1024 + 1), "video/mp4")})
    assert response.status_code == 413
    assert (await auth_client.get("/api/v1/incidents")).json()["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["engineer", "reviewer", "admin"])
@pytest.mark.parametrize("method,path,allowed", [
    ("GET", "/incidents", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/report", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/evidence", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/audit", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/video", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/telemetry", ["engineer", "reviewer", "admin"]),
    ("GET", "/incidents/MISSING/evidence/MISSING/media", ["engineer", "reviewer", "admin"]),
    ("GET", "/jobs/MISSING", ["engineer", "reviewer", "admin"]),
    ("POST", "/incidents/upload", ["engineer"]),
    ("POST", "/incidents/MISSING/analyze", ["engineer"]),
    ("PATCH", "/incidents/MISSING/report", ["engineer"]),
    ("POST", "/incidents/MISSING/report/submit", ["engineer"]),
    ("POST", "/incidents/MISSING/report/approve", ["reviewer"]),
    ("POST", "/incidents/MISSING/report/reject", ["reviewer"]),
    ("GET", "/admin/users", ["admin"]),
    ("POST", "/admin/users", ["admin"]),
])
async def test_direct_api_role_matrix(auth_client, method, path, allowed, role):
    seed_user(roles=[role])
    await login(auth_client)
    response = await auth_client.request(method, "/api/v1" + path, json={} if method != "GET" else None)
    if role in allowed:
        assert response.status_code in {200, 404, 422}
    else:
        assert response.status_code == 403 and response.json()["error"]["code"] == "PERMISSION_DENIED"
