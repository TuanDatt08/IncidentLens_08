"""Canonical V2 boundary regressions, independent of v1 or a live provider."""

import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError


@pytest.fixture
def draft():
    return {
        "schema_version": "2.0",
        "incident_detected": True,
        "event_type": "DISENGAGEMENT",
        "time_basis": "video_seconds",
        "window": {"start_s": 10.0, "critical_s": 12.0, "end_s": 15.0},
        "summary": "A vehicle ahead slowed before the mode change.",
        "timeline": [
            {
                "time_s": 11.0,
                "observation": "The vehicle ahead slowed.",
                "evidence_ids": ["EVD-001"],
                "source": "VIDEO",
                "certainty": "OBSERVED",
            },
        ],
        "factors": [
            {
                "category": "EXTERNAL_CONDITION",
                "label": "Vehicle ahead slowed.",
                "claim_status": "SUPPORTED_INFERENCE",
                "evidence_ids": ["EVD-001"],
            },
            {
                "category": "VEHICLE_OR_SYSTEM",
                "label": "Internal controller cause is not established.",
                "claim_status": "UNKNOWN",
                "evidence_ids": [],
            },
        ],
        "unknowns": ["No controller-state telemetry was provided."],
        "review_status": "DRAFT",
    }


def models():
    return importlib.import_module("backend.models.analysis_v2")


def test_valid_draft_round_trips_without_losing_claims(draft):
    result = models().AIIncidentAnalysisV2.model_validate(draft)
    assert result.model_dump(mode="json") == draft
    assert models().IncidentAnalysisV2.model_validate_json(result.model_dump_json()).model_dump(mode="json") == draft


@pytest.mark.parametrize("path,value", [
    (("event_type",), "disengagement"),
    (("schema_version",), "3.0"),
    (("time_basis",), "incident_relative"),
    (("incident_detected",), "true"),
    (("window", "critical_s"), "12"),
    (("window", "critical_s"), True),
    (("window", "critical_s"), float("nan")),
    (("timeline", 0, "time_s"), float("inf")),
    (("timeline", 0, "source"), "CAMERA"),
    (("timeline", 0, "certainty"), "supported"),
    (("factors", 0, "category"), "SOFTWARE_BUG"),
    (("factors", 0, "claim_status"), "supported_inference"),
    (("summary",), "   "),
    (("timeline", 0, "observation"), ""),
    (("factors", 0, "label"), ""),
    (("timeline", 0, "evidence_ids"), [""]),
])
def test_rejects_invalid_values_and_coercion(draft, path, value):
    target = draft
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


@pytest.mark.parametrize("path", [(), ("window",), ("timeline", 0), ("factors", 0)])
def test_rejects_unrecognized_fields_at_every_object_level(draft, path):
    target = draft
    for key in path:
        target = target[key]
    target["invented"] = "ignored fields would lose audit meaning"
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


@pytest.mark.parametrize("window", [
    {"start_s": -1.0, "critical_s": 12.0, "end_s": 15.0},
    {"start_s": 10.0, "critical_s": 9.0, "end_s": 15.0},
    {"start_s": 10.0, "critical_s": 16.0, "end_s": 15.0},
    {"start_s": 12.0, "critical_s": 12.0, "end_s": 12.0},
])
def test_rejects_invalid_window_order_or_video_time(draft, window):
    draft["window"] = window
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


def test_video_duration_and_timeline_bounds_are_checked(draft):
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft, context={"video_duration_s": 14.0})
    models().AIIncidentAnalysisV2.model_validate(draft, context={"video_duration_s": 15.0})
    draft["timeline"][0]["time_s"] = 16.0
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


@pytest.mark.parametrize("claim_status", ["OBSERVED", "SUPPORTED_INFERENCE"])
@pytest.mark.parametrize("collection,status_field", [("timeline", "certainty"), ("factors", "claim_status")])
def test_supported_claims_require_nonempty_evidence(draft, claim_status, collection, status_field):
    draft[collection][0][status_field] = claim_status
    draft[collection][0]["evidence_ids"] = []
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


def test_hypotheses_and_unknowns_do_not_require_invented_evidence(draft):
    draft["timeline"][0].update(certainty="HYPOTHESIS", evidence_ids=[])
    draft["factors"][0].update(claim_status="UNKNOWN", evidence_ids=[])
    assert models().AIIncidentAnalysisV2.model_validate(draft).factors[0].evidence_ids == []


def test_no_detection_requires_an_empty_analysis_and_null_window(draft):
    no_incident = deepcopy(draft)
    no_incident.update(
        incident_detected=False, event_type="UNKNOWN", window=None, timeline=[], factors=[],
        summary="No candidate was found in the sampled segments.",
        unknowns=["Sparse sampling does not establish full coverage."],
    )
    assert models().AIIncidentAnalysisV2.model_validate(no_incident).window is None
    for field in ("window", "timeline", "factors", "event_type"):
        invalid = {**no_incident, field: draft[field]}
        with pytest.raises(ValidationError):
            models().AIIncidentAnalysisV2.model_validate(invalid)
    draft["window"] = None
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


@pytest.mark.parametrize("status", ["IN_REVIEW", "APPROVED", "REJECTED"])
def test_ai_cannot_assign_human_review_states(draft, status):
    draft["review_status"] = status
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)
    assert models().IncidentAnalysisV2.model_validate(draft).review_status == status


def test_no_incident_report_cannot_be_approved_as_an_incident(draft):
    draft.update(incident_detected=False, event_type="UNKNOWN", window=None, timeline=[], factors=[], review_status="APPROVED")
    with pytest.raises(ValidationError):
        models().IncidentAnalysisV2.model_validate(draft)


def test_json_schema_is_closed_and_requires_all_business_fields(draft):
    schema = models().AIIncidentAnalysisV2.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(draft)
    assert schema["properties"]["review_status"]["const"] == "DRAFT"
    for definition in schema["$defs"].values():
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


@pytest.mark.parametrize("field", ["schema_version", "incident_detected", "event_type", "time_basis", "window", "summary", "timeline", "factors", "unknowns", "review_status"])
def test_rejects_missing_business_fields(draft, field):
    del draft[field]
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft)


@pytest.mark.parametrize("duration", [0, -1, True, "15", float("nan"), float("inf")])
def test_rejects_invalid_trusted_video_duration(draft, duration):
    with pytest.raises(ValidationError):
        models().AIIncidentAnalysisV2.model_validate(draft, context={"video_duration_s": duration})


@pytest.mark.parametrize("model_name,filename", [
    ("IncidentAnalysisV2", "incident-analysis-v2.json"),
    ("AIIncidentAnalysisV2", "ai-incident-analysis-v2.json"),
])
def test_published_json_schema_matches_runtime_validation(model_name, filename):
    path = Path(__file__).resolve().parents[3] / "backend" / "models" / "json_schema" / filename
    published = json.loads(path.read_text(encoding="utf-8"))
    assert published == getattr(models(), model_name).model_json_schema()
