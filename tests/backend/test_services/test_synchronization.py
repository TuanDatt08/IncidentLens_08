import importlib

import pytest

from backend.services.log_normalization import normalize_log


def telemetry(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("sec_from_incident,speed\n-10,2\n0,1\n10,0\n")
    return normalize_log(path)


def test_offset_drift_residual_and_collision_clock(tmp_path):
    module = importlib.import_module("backend.services.synchronization")
    result = module.align({"duration": 100.0}, telemetry(tmp_path), [
        module.TimeAnchor(log_s=-10.0, video_s=19.99, source="fixture"),
        module.TimeAnchor(log_s=10.0, video_s=40.01, source="fixture"),
    ])
    assert result.quality == "VERIFIED"
    assert result.offset_s == pytest.approx(30)
    assert result.drift_ppm == pytest.approx(1000)
    assert result.residual_s < 0.1
    assert result.to_video_seconds(0) == pytest.approx(30)
    assert result.to_log_seconds(30) == pytest.approx(0)
    assert result.source_time_reference == "incident_relative"


def test_no_anchor_is_unknown_and_cannot_map(tmp_path):
    module = importlib.import_module("backend.services.synchronization")
    result = module.align({"duration": 100.0}, telemetry(tmp_path), [])
    assert result.quality == "UNKNOWN"
    assert result.unknowns
    with pytest.raises(ValueError, match="verified"):
        result.to_video_seconds(0)


def test_one_anchor_estimates_offset_but_does_not_verify_drift(tmp_path):
    module = importlib.import_module("backend.services.synchronization")
    result = module.align({"duration": 100.0}, telemetry(tmp_path), [module.TimeAnchor(0, 30, "fixture")])
    assert result.quality == "ESTIMATED"
    assert result.drift_ppm is None
    with pytest.raises(ValueError, match="verified"):
        result.to_video_seconds(0)


@pytest.mark.parametrize("anchors", [
    [(0, 2), (0, 3)], [(0, 5), (1, 4)], [(0, -1), (1, 4)],
    [(0, 2), (1, 101)], [(0, float("nan")), (1, 4)],
])
def test_invalid_anchors_are_rejected(tmp_path, anchors):
    module = importlib.import_module("backend.services.synchronization")
    with pytest.raises(ValueError):
        module.align({"duration": 100.0}, telemetry(tmp_path), [module.TimeAnchor(x, y, "fixture") for x, y in anchors])


def test_inconsistent_anchors_disable_precise_inference(tmp_path):
    module = importlib.import_module("backend.services.synchronization")
    result = module.align({"duration": 100.0}, telemetry(tmp_path), [
        module.TimeAnchor(0, 10, "fixture"), module.TimeAnchor(1, 12, "fixture"), module.TimeAnchor(2, 13, "fixture"),
    ])
    assert result.quality == "UNKNOWN"
    assert result.residual_s > 0.1
