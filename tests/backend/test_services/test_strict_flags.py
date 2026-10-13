from backend.services.log_normalization import normalize_log
from backend.services.synchronization import align
from backend.services.trigger_detection import TriggerConfig, find_log_triggers


def test_strict_flags_ignore_ordinary_braking_and_keep_severe_deceleration(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,brake,acceleration\n0,0,0\n1,1,-19.5\n3,0,0\n5,0.9,-27\n6,0,0\n')
    log = normalize_log(path)
    result = find_log_triggers(log, config=TriggerConfig(min_priority=4, deceleration=22), alignment=align({'duration': 7.0}, log, []), video_metadata={'duration': 7.0, 'fps': 24})
    assert len(result['triggers']) == 1
    assert result['triggers'][0]['video_peak_s'] == 5.0
    assert result['triggers'][0]['reasons'] == ['DECELERATION']


def test_collision_sensor_still_triggers_under_strict_filter(tmp_path):
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,collision_intensity\n0,0\n1,1\n')
    log = normalize_log(path)
    result = find_log_triggers(log, config=TriggerConfig(min_priority=4, deceleration=22))
    assert result['triggers'][0]['reasons'] == ['COLLISION_SENSOR']


def test_flag_only_never_extracts_or_calls_model_without_flags(tmp_path, monkeypatch):
    from backend.config import Settings
    from backend.services.qwen_processing import process_local_incident
    from backend.services.video import VideoService

    (tmp_path / 'video.mp4').write_bytes(b'placeholder')
    (tmp_path / 'log.csv').write_text('t_video_s,brake,acceleration\n0,0,0\n1,1,-19\n')
    def forbidden(*args, **kwargs):
        raise AssertionError('No flags must mean no frame extraction or inference')
    monkeypatch.setattr(VideoService, 'extract_frame', forbidden)
    monkeypatch.setattr(VideoService, 'extract_clip', forbidden)
    class Provider:
        analyze = forbidden
    result = process_local_incident({'incident_id': 'INC-test', 'video_uri': 'video.mp4', 'telemetry_uri': 'log.csv', 'video_metadata': {'duration': 2.0, 'fps': 24}}, storage_root=tmp_path, provider=Provider(), settings=Settings(_env_file=None, qwen_flag_only=True, qwen_trigger_min_priority=4, qwen_trigger_deceleration=22))
    assert result.analysis.model_metadata['detection_state'] == 'NOT_ANALYZED_NO_FLAGS'
