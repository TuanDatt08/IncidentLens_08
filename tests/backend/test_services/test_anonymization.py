import importlib
import subprocess

import pytest

from backend.services.evidence_extraction import EvidenceAsset, file_hash


def frame(tmp_path):
    path = tmp_path / "face-plate-fixture.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=white:s=64x64", "-frames:v", "1", str(path)], check=True, capture_output=True, timeout=30)
    return EvidenceAsset("EVD-1", "rec", "cnd", path, file_hash(path), 2.0, 2.0, "VIDEO", "image/jpeg", 0)


def test_real_mask_covers_fixture_regions_and_requires_review(tmp_path):
    module = importlib.import_module("backend.services.anonymization")
    source = frame(tmp_path)
    policy = module.PrivacyPolicy("fixture-detector-1", "reviewer-fixture")
    regions = [module.MaskRegion(8, 8, 16, 16, "FACE"), module.MaskRegion(32, 32, 16, 16, "PLATE")]
    result = module.mask_and_validate(source, policy, detector=lambda path: regions, review=lambda path, found: found == regions, output_root=tmp_path / "masked")
    assert (result.asset.privacy_state, result.asset.privacy_validation) == ("MASKED", "PASSED")
    assert result.asset.evidence_id == source.evidence_id
    pixels = subprocess.run(["ffmpeg", "-v", "error", "-i", str(result.asset.path), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], check=True, capture_output=True, timeout=30).stdout
    for x, y in [(16, 16), (40, 40)]:
        assert max(pixels[(y * 64 + x) * 3:(y * 64 + x) * 3 + 3]) < 20
    assert source.privacy_state == "RAW"
    assert result.detector_version == "fixture-detector-1"


def test_detector_failure_or_review_failure_never_marks_passed(tmp_path):
    module = importlib.import_module("backend.services.anonymization")
    source = frame(tmp_path)
    def broken(path):
        raise RuntimeError("detector offline")
    policy = module.PrivacyPolicy("fixture", "reviewer")
    with pytest.raises(ValueError, match="privacy"):
        module.mask_and_validate(source, policy, detector=broken, review=lambda path, found: True, output_root=tmp_path)
    with pytest.raises(ValueError, match="privacy"):
        module.mask_and_validate(source, policy, detector=lambda path: [], review=lambda path, found: False, output_root=tmp_path)


def test_video_requires_full_motion_privacy_adapter(tmp_path):
    module = importlib.import_module("backend.services.anonymization")
    from dataclasses import replace
    source = replace(frame(tmp_path), media_type="video/mp4")
    with pytest.raises(ValueError, match="video"):
        module.mask_and_validate(source, module.PrivacyPolicy("fixture", "reviewer"), detector=lambda path: [], review=lambda path, found: True, output_root=tmp_path)
