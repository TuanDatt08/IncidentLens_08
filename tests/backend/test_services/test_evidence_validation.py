import importlib
from dataclasses import replace

import pytest

from backend.services.evidence_extraction import EvidenceAsset, file_hash


def analysis():
    return {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.0, "end_s": 3.0}, "summary": "Braking observed", "timeline": [{"time_s": 2.0, "observation": "Vehicle slows", "evidence_ids": ["EVD-1"], "source": "VIDEO", "certainty": "OBSERVED"}], "factors": [{"category": "VEHICLE_OR_SYSTEM", "label": "Internal cause", "claim_status": "UNKNOWN", "evidence_ids": []}], "unknowns": ["No controller log"], "review_status": "DRAFT"}


def registry(tmp_path):
    path = tmp_path / "frame.jpg"
    path.write_bytes(b"fixture")
    module = importlib.import_module("backend.services.evidence_validation")
    asset = EvidenceAsset("EVD-1", "rec", "cnd", path, file_hash(path), 2.0, 2.0, "VIDEO", "image/jpeg", 0)
    return module, module.EvidenceRegistry("rec", "cnd", (asset,))


def test_unknown_preserved_and_valid_claim_resolves(tmp_path):
    module, refs = registry(tmp_path)
    result = module.validate_analysis(analysis(), refs, 10.0)
    assert result.factors[0].claim_status == "UNKNOWN"
    assert result.timeline[0].evidence_ids == ["EVD-1"]


@pytest.mark.parametrize("mutation", ["id", "recording", "candidate", "time", "source", "hash", "internal_cause"])
def test_invalid_scope_time_source_hash_and_internal_cause_blocked(tmp_path, mutation):
    module, refs = registry(tmp_path)
    payload = analysis()
    asset = refs.assets[0]
    if mutation == "id":
        payload["timeline"][0]["evidence_ids"] = ["missing"]
    elif mutation in {"recording", "candidate"}:
        refs = replace(refs, assets=(replace(asset, **{mutation + "_id": "other"}),))
    elif mutation == "time":
        refs = replace(refs, assets=(replace(asset, time_start_s=4.0, time_end_s=4.0),))
    elif mutation == "source":
        payload["timeline"][0]["source"] = "TELEMETRY"
    elif mutation == "hash":
        asset.path.write_bytes(b"modified")
    else:
        payload["factors"][0].update(claim_status="SUPPORTED_INFERENCE", evidence_ids=["EVD-1"])
    with pytest.raises(ValueError):
        module.validate_analysis(payload, refs, 10.0)


def test_fused_claim_requires_both_sources(tmp_path):
    module, refs = registry(tmp_path)
    payload = analysis()
    payload["timeline"][0]["source"] = "FUSED"
    with pytest.raises(ValueError, match="source"):
        module.validate_analysis(payload, refs, 10.0)
