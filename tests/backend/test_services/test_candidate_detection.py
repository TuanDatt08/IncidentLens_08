import importlib

import pytest

from backend.services.log_normalization import LogNormalizationConfig, normalize_log
from backend.services.synchronization import TimeAnchor, align


def test_multiple_events_merge_clamp_and_overflow(tmp_path):
    module = importlib.import_module("backend.services.candidate_detection")
    path = tmp_path / "log.csv"
    path.write_text("clock,brake,mode\n0,0,AUTO\n1,0.9,AUTO\n2,0.9,MANUAL\n50,0,AUTO\n51,0.9,AUTO\n")
    log = normalize_log(path, config=LogNormalizationConfig(timestamp_column="clock", time_reference="recording_relative"))
    alignment = align({"duration": 60.0}, log, [TimeAnchor(0, 0, "fixture"), TimeAnchor(59, 59, "fixture")])
    config = module.DetectionConfig(recording_id="rec-1", duration_s=60.0, pre_s=3.0, post_s=5.0, max_candidates=1)
    result = module.detect_candidates(log, alignment, config)
    assert len(result.candidates) == 2
    first, second = result.candidates
    assert first.start_s == 0
    assert first.end_s == 7
    assert {"HARD_BRAKING", "DISENGAGEMENT"} <= set(first.reasons)
    assert second.analysis_state == "UNANALYZED"
    assert result == module.detect_candidates(log, alignment, config)
    assert result.coverage.log_rows == 5


def test_five_hour_no_log_scan_covers_every_segment_without_claiming_absence():
    module = importlib.import_module("backend.services.candidate_detection")
    result = module.detect_candidates(None, None, module.DetectionConfig(recording_id="long", duration_s=18000.0), scan=lambda time_s: False)
    assert len(result.scan_times_s) > 5
    assert result.scan_times_s[0] == 0
    assert result.scan_times_s[-1] > 17900
    assert result.coverage.sampled_frames == len(result.scan_times_s)
    assert result.coverage.unscanned_ranges == ()
    assert result.unknowns
    assert not result.candidates


def test_sparse_scan_budget_records_unscanned_ranges():
    module = importlib.import_module("backend.services.candidate_detection")
    result = module.detect_candidates(None, None, module.DetectionConfig(recording_id="long", duration_s=18000.0, max_scan_frames=2), scan=lambda time_s: False)
    assert len(result.scan_times_s) == 2
    assert result.coverage.unscanned_ranges


def test_unknown_alignment_falls_back_to_scan(tmp_path):
    module = importlib.import_module("backend.services.candidate_detection")
    path = tmp_path / "log.csv"
    path.write_text("sec_from_incident,brake\n0,1\n1,1\n")
    log = normalize_log(path)
    alignment = align({"duration": 60.0}, log, [])
    result = module.detect_candidates(log, alignment, module.DetectionConfig(recording_id="rec", duration_s=60.0))
    assert result.scan_times_s
    assert not result.candidates


def test_scan_proposals_are_not_recorded_as_completed_without_scanner():
    module = importlib.import_module("backend.services.candidate_detection")
    config = module.DetectionConfig(recording_id="rec", duration_s=60.0)
    planned = module.detect_candidates(None, None, config)
    assert planned.coverage.sampled_frames == 0
    assert planned.coverage.unscanned_ranges == ((0.0, 60.0),)
    detected = module.detect_candidates(None, None, config, scan=lambda time_s: time_s == 0)
    assert len(detected.candidates) == 1
    assert detected.candidates[0].reasons == ("VISUAL_CANDIDATE",)


def test_configured_spike_flags_keep_values_and_original_times(tmp_path):
    from backend.services.candidate_detection import DetectionConfig, detect_candidates
    path = tmp_path / "spikes.csv"
    path.write_text("clock,jerk\n0,0\n9,0.1\n10,8\n10.5,9\n11,0\n30,0\n")
    log = normalize_log(path, config=LogNormalizationConfig(timestamp_column="clock", time_reference="recording_relative"))
    mapping = align({"duration": 40.0}, log, [TimeAnchor(0, 0, "fixture"), TimeAnchor(30, 30, "fixture")])
    result = detect_candidates(log, mapping, DetectionConfig("rec", 40.0, signal_thresholds={"jerk": 5.0}))
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert (candidate.start_s, candidate.critical_s, candidate.end_s) == (5.0, 10.5, 13.5)
    assert [(f['time_s'],f['value']) for f in candidate.flags] == [(10.,8.),(10.5,9.)]


def test_stable_signals_and_unverified_alignment_do_not_create_flags(tmp_path):
    from backend.services.candidate_detection import DetectionConfig, detect_candidates
    path = tmp_path / "stable.csv"
    path.write_text("clock,jerk\n0,1\n1,1\n2,1\n")
    log = normalize_log(path, config=LogNormalizationConfig(timestamp_column="clock", time_reference="recording_relative"))
    mapping = align({"duration": 20.0}, log, [TimeAnchor(0, 0, "fixture"), TimeAnchor(2, 2, "fixture")])
    config = DetectionConfig("rec", 20.0, signal_thresholds={"jerk": 5.0})
    assert not detect_candidates(log, mapping, config).candidates
    assert not detect_candidates(log, align({"duration": 20.0}, log, []), config).candidates


def test_delta_flags_and_invalid_signal_fail_explicitly(tmp_path):
    from backend.services.candidate_detection import DetectionConfig, detect_candidates
    path = tmp_path / "delta.csv"
    path.write_text("clock,speed\n0,10\n10,20\n20,nan\n")
    log = normalize_log(path, config=LogNormalizationConfig(timestamp_column="clock", time_reference="recording_relative"))
    mapping = align({"duration": 40.0}, log, [TimeAnchor(0, 0, "fixture"), TimeAnchor(30, 30, "fixture")])
    with pytest.raises(ValueError, match="finite"):
        detect_candidates(log, mapping, DetectionConfig("rec", 40.0, delta_thresholds={"speed": 5.0}))


def test_rolling_anomaly_without_hand_picked_signal_threshold(tmp_path):
    from backend.services.candidate_detection import DetectionConfig, detect_candidates
    path = tmp_path / "rolling.csv"
    path.write_text("clock,acceleration\n" + "".join(f"{i},0\n" for i in range(35)) + "35,20\n36,0\n")
    log = normalize_log(path, config=LogNormalizationConfig(timestamp_column="clock", time_reference="recording_relative"))
    mapping = align({"duration": 50.0}, log, [TimeAnchor(0, 0, "fixture"), TimeAnchor(36, 36, "fixture")])
    candidates = detect_candidates(log, mapping, DetectionConfig("rec", 50.0)).candidates
    assert len(candidates) == 1 and candidates[0].critical_s == 35.0
    assert candidates[0].flags[0]["reason"] == "EWMA_ANOMALY"
    assert candidates[0].flags[0]["signal"] == "acceleration"


@pytest.mark.parametrize("field,value", [("duration_s", float("nan")), ("pre_s", -1), ("max_candidates", 0), ("scan_interval_s", 0)])
def test_invalid_budget_and_time_rejected(field, value):
    module = importlib.import_module("backend.services.candidate_detection")
    config = {"recording_id": "rec", "duration_s": 60.0, field: value}
    with pytest.raises(ValueError):
        module.DetectionConfig(**config)
