import json
from pathlib import Path

import pytest

from eval.metrics import COST_COMPONENTS
from eval.run_benchmark import compare


def fixture(tmp_path):
    manifest = json.loads(Path("eval/datasets/manifest.json").read_text())
    manifest.update(test_locked_at="2026-10-03T00:00:00Z", threshold_signoff={"owner": "synthetic-owner", "reviewer": "synthetic-reviewer", "signed_at": "fixture", "thresholds_ref": "fixture-only"}, hardware_profile="synthetic", api_policy_ref="synthetic")
    manifest["cases"] = [{"case_id": f"case-{index}", "recording_id": f"rec-{index}", "scenario_group": f"scenario-{index}", "split": "calibration" if index == 0 else "test", "video_ref": "synthetic", "video_sha256": f"{index:064x}", "licence_ref": "synthetic", "consent_ref": "synthetic", "annotator_ids": ["fixture-a", "fixture-b"], "resolution_ref": "synthetic", "ground_truth": []} for index in range(50)]
    rows = [{"provider": provider, "case_id": case["case_id"], "input_sha256": case["video_sha256"], "expert_review_ref": "synthetic", "pricing_source": "synthetic", "provenance": {"model": "fixture"}, "accepted": False, "latency_s": index + 1, "budget_hash": "synthetic-budget", "cost_usd": dict.fromkeys(COST_COMPONENTS, 0.0), "evidence_correctness": {"numerator": 0, "denominator": 0}} for provider in ("fixture-external", "fixture-selfhost") for index, case in enumerate(manifest["cases"][1:])]
    path, measurements = tmp_path / "manifest.json", tmp_path / "measurements.json"
    path.write_text(json.dumps(manifest))
    measurements.write_text(json.dumps(rows))
    return path, measurements, rows


def test_comparison_aggregates_same_cases_with_zero_acceptance(tmp_path):
    manifest, measurements, _ = fixture(tmp_path)
    result = compare(manifest, measurements)
    for profile in result["providers"].values():
        assert profile["case_count"] == 49
        assert profile["latency_p50_s"] == 25.0
        assert profile["cost_per_accepted_usd"] is None
    # All test evidence is synthetic; no checked-in expert result is generated.


@pytest.mark.parametrize("field,value", [("input_sha256", "invalid"), ("budget_hash", "different"), ("expert_review_ref", "")])
def test_comparison_rejects_unmatched_or_unsigned_measurements(tmp_path, field, value):
    manifest, measurements, rows = fixture(tmp_path)
    rows[0][field] = value
    measurements.write_text(json.dumps(rows))
    with pytest.raises(ValueError):
        compare(manifest, measurements)
