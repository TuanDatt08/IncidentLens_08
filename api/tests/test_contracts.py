import pytest
from pydantic import ValidationError

from backend.models.contracts import (
    AnalysisReportV1,
    EvidenceV1,
    IncidentRecordV1,
    JobResponse,
    LocalizationResult,
)


@pytest.mark.asyncio
async def test_v1_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_record_is_factual_and_tolerates_generator_fields():
    record = IncidentRecordV1.model_validate(
        {
            "schema_version": "1.0",
            "scenario": "jaywalk_occluded",
            "template": "pedestrian",
            "source": {"generator": "CARLA", "new_field": 1},
            "collision": {"hit_category": "walker"},
            "ego": {},
            "quality": {},
            "future_field": True,
        }
    )
    assert record.scenario == "jaywalk_occluded"
    assert record.model_dump()["future_field"] is True
    assert "summary" not in record.model_dump()


def test_report_and_job_have_separate_statuses():
    report = AnalysisReportV1.model_validate(
        {
            "incident_id": "INC-001",
            "incident_detected": True,
            "incident_type": "pedestrian_collision",
            "incident_window": {"start": -2.5, "critical": 0, "end": 1.5},
            "summary": "A pedestrian was hit.",
            "review_status": "DRAFT",
        }
    )
    assert report.review_status == "DRAFT"
    assert report.incident_window.start == -2.5
    assert "collision" not in report.model_dump()

    queued = JobResponse.model_validate(
        {
            "job_id": "JOB-001",
            "status": "queued",
            "pass": None,
            "progress": {"done": 0, "total": None},
            "updated_at": "2026-09-23T00:00:00Z",
        }
    )
    assert queued.progress.total is None
    assert queued.pass_number is None


def test_evidence_accepts_negative_relative_time_but_rejects_unsafe_uri():
    payload = {
        "evidence_id": "EVD-001",
        "kind": "video",
        "uri": "incidents/INC-001/clips/clip.mp4",
        "sha256": "a" * 64,
        "time_range_s": [-2.5, 1.5],
    }
    assert EvidenceV1.model_validate(payload).time_range_s[0] == -2.5
    for uri in ("/etc/passwd", "../secret", "C:/secret", "incidents/../secret"):
        with pytest.raises(ValidationError):
            EvidenceV1.model_validate({**payload, "uri": uri})
    with pytest.raises(ValidationError):
        EvidenceV1.model_validate({**payload, "sha256": "A" * 64})
    with pytest.raises(ValidationError):
        EvidenceV1.model_validate({**payload, "time_range_s": [2, -1]})


def test_localization_uses_incident_relative_order():
    result = LocalizationResult.model_validate(
        {
            "incident_detected": True,
            "candidate_start": -2.5,
            "critical_time": 0,
            "candidate_end": 1.5,
            "evidence_timestamps": [-1.2, 0, 0.8],
        }
    )
    assert result.candidate_start == -2.5
    with pytest.raises(ValidationError):
        LocalizationResult.model_validate(
            {"incident_detected": True, "candidate_start": 1, "critical_time": 0, "candidate_end": 2}
        )
