import pytest

from backend.services.log_normalization import normalize_log
from backend.services.synchronization import align


def test_explicit_video_clock_takes_priority_and_has_identity_mapping(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,sec_from_incident,speed_kmh\n0,-58,30\n1,-57,29\n', encoding='utf-8')
    log = normalize_log(path)
    assert log.config.timestamp_column == 't_video_s'
    mapping = align({'duration': 2.0}, log, [])
    assert mapping.quality == 'VERIFIED'
    assert mapping.to_video_seconds(1.0) == 1.0
    assert mapping.anchors[0].source == 'explicit_t_video_s'


def test_incident_relative_clock_still_requires_anchors(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('sec_from_incident,speed_kmh\n0,30\n1,29\n', encoding='utf-8')
    assert align({'duration': 2.0}, normalize_log(path), []).quality == 'UNKNOWN'


def test_video_clock_outside_duration_is_rejected(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,speed_kmh\n10,30\n11,29\n', encoding='utf-8')
    with pytest.raises(ValueError, match='video duration'):
        align({'duration': 2.0}, normalize_log(path), [])


def test_video_clock_can_include_trailing_telemetry(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,speed_kmh\n0,30\n2.2,29\n', encoding='utf-8')
    assert align({'duration': 2.0}, normalize_log(path), []).to_video_seconds(1.0) == 1.0
