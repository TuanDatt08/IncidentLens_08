import importlib

import pytest
from test_authorization import signed_identity

from backend.models.analysis_v2 import AIIncidentAnalysisV2


@pytest.mark.asyncio
async def test_v2_authentication_does_not_trust_role_header(db_client):
    response = await db_client.get("/api/v2/recordings/rec/candidates", headers={"X-Role": "Reviewer"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_v2_review_snapshots_versions_rbac_and_immutable_approval(db_client, monkeypatch, tmp_path):
    import secrets

    from backend.config import get_settings

    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("V2_IDENTITY_SECRET", key)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    module = importlib.import_module("backend.services.reports_v2")
    from backend.services.evidence_extraction import EvidenceAsset, file_hash
    from backend.services.evidence_validation import EvidenceRegistry

    asset_path = tmp_path / "frame.jpg"
    asset_path.write_bytes(b"fixture")
    asset = EvidenceAsset("EVD-fixture", "rec", "cnd", asset_path, file_hash(asset_path), 2.0, 2.0, "VIDEO", "image/jpeg", 0)
    payload = {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.0, "end_s": 3.0}, "summary": "Braking", "timeline": [{"time_s": 2.0, "observation": "Slowing", "evidence_ids": ["EVD-fixture"], "source": "VIDEO", "certainty": "OBSERVED"}], "factors": [], "unknowns": [], "review_status": "DRAFT"}
    report = module.create_report(AIIncidentAnalysisV2.model_validate(payload), EvidenceRegistry("rec", "cnd", (asset,)), duration_s=10.0, provenance={"provider": "fixture"})
    report_id = report["report_id"]
    engineer = {"Authorization": "Bearer " + signed_identity(key)}
    reviewer = {"Authorization": "Bearer " + signed_identity(key, subject="reviewer", roles=["Reviewer"])}
    dual = {"Authorization": "Bearer " + signed_identity(key, roles=["Engineer", "Reviewer"])}
    base = "/api/v2/reports/" + report_id
    response = await db_client.get("/api/v2/recordings/rec/candidates", headers=engineer)
    assert response.status_code == 200
    assert response.json()["items"][0]["candidate_id"] == "cnd"
    patch = await db_client.patch(base, json={"expected_version": 1, "summary": "Reviewed braking"}, headers=engineer)
    assert patch.status_code == 200
    assert patch.json()["version"] == 2
    stale = await db_client.patch(base, json={"expected_version": 1, "summary": "Stale"}, headers=engineer)
    assert stale.status_code == 409
    submitted = await db_client.post(base + "/submit", json={"expected_version": 2}, headers=engineer)
    assert submitted.json()["version"] == 3
    self_approve = await db_client.post(base + "/approve", json={"expected_version": 3}, headers=dual)
    assert self_approve.status_code == 403
    no_reason = await db_client.post(base + "/reject", json={"expected_version": 3}, headers=reviewer)
    assert no_reason.status_code == 422
    rejected = await db_client.post(base + "/reject", json={"expected_version": 3, "reason": "Need review"}, headers=reviewer)
    assert rejected.json()["version"] == 4
    reopened = await db_client.post(base + "/reopen", json={"expected_version": 4}, headers=engineer)
    assert reopened.json()["version"] == 5
    await db_client.post(base + "/submit", json={"expected_version": 5}, headers=engineer)
    asset_path.unlink()
    assert (await db_client.post(base + "/approve", json={"expected_version": 6}, headers=reviewer)).status_code == 422
    asset_path.write_bytes(b"fixture")
    approved = await db_client.post(base + "/approve", json={"expected_version": 6}, headers=reviewer)
    assert approved.status_code == 200
    assert approved.json()["version"] == 7
    assert approved.json()["analysis"]["review_status"] == "APPROVED"
    assert (await db_client.patch(base, json={"expected_version": 7, "summary": "Overwrite"}, headers=engineer)).status_code == 409
    assert (await db_client.get(base, headers={"Authorization": "Bearer " + signed_identity(key, scopes=["other"])})).status_code == 404
    history = await db_client.get(base + "/versions", headers=engineer)
    assert [item["version"] for item in history.json()["items"]] == list(range(1, 8))
    audit = await db_client.get(base + "/audit", headers=engineer)
    assert len(audit.json()["items"]) == 7
    assert audit.json()["items"][-1]["actor"] == "reviewer"
    evidence = await db_client.get(base + "/evidence", headers=engineer)
    assert evidence.status_code == 200
    assert "path" not in evidence.text
    media = await db_client.get("/api/v2/recordings/rec/evidence/EVD-fixture/media", headers=engineer)
    assert media.status_code == 403
    asset_path.write_bytes(b"changed")
    assert (await db_client.get(base, headers=engineer)).json() == approved.json()


@pytest.mark.asyncio
async def test_concurrent_edits_have_one_winner(db_client, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from backend.errors import ApiError
    from backend.models.contracts_v2 import ReportEditV2
    from backend.services.evidence_validation import EvidenceRegistry
    from backend.services.identity import Principal
    from backend.services.reports_v2 import create_report, mutate_report, report_history
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"rec"}))
    payload = {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.0, "end_s": 3.0}, "summary": "Fixture", "timeline": [], "factors": [], "unknowns": ["Unverified visual fixture"], "review_status": "DRAFT"}
    report = create_report(AIIncidentAnalysisV2.model_validate(payload), EvidenceRegistry("rec", "concurrent", ()), duration_s=10.0, provenance={"provider": "fixture"})
    barrier = Barrier(2)
    def edit(summary):
        barrier.wait(timeout=10)
        try:
            return mutate_report(report["report_id"], actor, ReportEditV2(expected_version=1, summary=summary), action="edit")["version"]
        except ApiError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(edit, ["First edit", "Second edit"]))
    assert sorted(outcomes) == [2, 409]
    assert len(report_history(report["report_id"], actor)["items"]) == 2
