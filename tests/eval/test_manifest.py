import importlib
import json
from pathlib import Path

import pytest


def test_checked_in_manifest_reports_zero_real_cases_and_blocks_benchmark():
    module = importlib.import_module("eval.manifest")
    manifest = module.load_manifest(Path("eval/datasets/manifest.json"))
    assert len(manifest.cases) == 0
    assert not manifest.release_ready
    assert "expert_cases" in manifest.blockers()


def test_split_leakage_is_rejected(tmp_path):
    module = importlib.import_module("eval.manifest")
    case = {"case_id": "one", "recording_id": "rec", "scenario_group": "scenario", "split": "calibration", "video_ref": "restricted/fixture.mp4", "video_sha256": "0" * 64, "licence_ref": "licence-fixture", "consent_ref": "consent-fixture", "annotator_ids": ["expert-a", "expert-b"], "resolution_ref": "signed-resolution", "ground_truth": []}
    payload = json.loads(Path("eval/datasets/manifest.json").read_text())
    payload["cases"] = [case, {**case, "case_id": "two", "split": "test"}]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="split"):
        module.load_manifest(path)
