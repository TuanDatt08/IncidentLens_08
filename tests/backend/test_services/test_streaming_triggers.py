
import pytest

from backend.services.log_normalization import normalize_log


def test_confirmed_braking_filters_weak_spikes_but_preserves_collision(tmp_path):
    from backend.services.trigger_detection import TriggerConfig, find_log_triggers
    p = tmp_path/'braking.csv'
    p.write_text('t_video_s,brake,accel_x,collision_intensity\n'
                 '0,0,0,0\n1,.9,-19.5,0\n2,0,0,0\n'
                 '4,.9,-27,0\n4.042,0,0,0\n6,0,0,0\n'
                 '8,.902,-27,0\n8.042,.902,-26,0\n8.083,.902,-25,0\n9,0,0,0\n'
                 '12,0,0,1\n')
    result = find_log_triggers(normalize_log(p), config=TriggerConfig(deceleration=22, braking_confirmation_s=.08))
    selected = [t for t in result['triggers'] if t['selection']['selected']]
    assert len(selected) == 2
    assert selected[0]['log_peak_s'] == 8
    assert selected[1]['reasons'] == ['COLLISION_SENSOR']
    assert len(result['triggers']) == 4


def test_braking_confirmation_resets_after_timestamp_gap(tmp_path):
    from backend.services.trigger_detection import TriggerConfig, find_log_triggers
    p = tmp_path/'gap-braking.csv'
    p.write_text('t_video_s,brake,accel_x\n0,.9,-27\n.5,.9,-27\n')
    result = find_log_triggers(normalize_log(p), config=TriggerConfig(deceleration=22, braking_confirmation_s=.08))
    assert not any(t['selection']['selected'] for t in result['triggers'])


def test_high_deceleration_without_braking_is_not_confirmed(tmp_path):
    from backend.services.trigger_detection import TriggerConfig, find_log_triggers
    p = tmp_path/'no-brake.csv'
    p.write_text('t_video_s,brake,accel_x\n0,0,-27\n.042,0,-27\n.083,0,-27\n')
    result = find_log_triggers(normalize_log(p), config=TriggerConfig(deceleration=22, braking_confirmation_s=.08))
    assert not any(t['selection']['selected'] for t in result['triggers'])


def test_candidate_filter_does_not_submit_rejected_groups(tmp_path):
    from backend.services.candidate_detection import DetectionConfig, detect_candidates
    from backend.services.synchronization import align
    p = tmp_path/'selection.csv'
    p.write_text('t_video_s,brake,accel_x\n0,0,0\n1,.9,-19\n2,0,0\n'
                 '5,.9,-27\n5.042,.9,-26\n5.083,.9,-25\n6,0,0\n')
    log = normalize_log(p)
    result = detect_candidates(log, align({'duration':6},log,[]),
        DetectionConfig('INC-TEST',6,trigger_deceleration=22,braking_confirmation_s=.08))
    assert len(result.log_trigger_data['triggers']) == 2
    assert len(result.candidates) == 1
    assert result.candidates[0].critical_s == 5


def test_unsynced_log_still_finds_braking(tmp_path):
    from backend.services.trigger_detection import find_log_triggers
    p = tmp_path/'log.csv'
    p.write_text('sec_from_incident,speed_kmh,brake,accel_x\n-1,30,0,0\n-0.9,28,.9,-8\n-0.8,25,.9,-12\n0,0,0,0\n')
    result = find_log_triggers(normalize_log(p))
    assert result['rows'] == 4
    assert len(result['triggers']) == 1
    event = result['triggers'][0]
    assert event['log_start_s'] == -.9
    assert event['video_peak_s'] is None
    assert event['frame_peak'] is None
    assert 'HARD_BRAKING' in event['reasons']


def test_constant_position_velocity_and_compass_wrap_are_not_incidents(tmp_path):
    from backend.services.trigger_detection import find_log_triggers
    p = tmp_path/'steady.csv'
    p.write_text('sec_from_incident,speed_kmh,brake,loc_x,loc_y,loc_z,compass_deg\n0,36,0,0,0,0,359.9\n.1,36,0,1,0,0,0\n.2,36,0,2,0,0,.1\n')
    assert find_log_triggers(normalize_log(p))['triggers'] == []


@pytest.mark.parametrize('signal,values,reason', [('steer','0,0,0,0\n.1,30,1,3\n.2,30,1,3','SHARP_TURN'), ('loc_z','0,30,0,9.81\n.1,30,.1,9.81\n.2,30,.8,14','VERTICAL_SHOCK')])
def test_turn_and_vertical_independent_of_longitudinal_acceleration(tmp_path, signal, values, reason):
    from backend.services.trigger_detection import find_log_triggers
    p = tmp_path/'log.csv'
    fourth = 'accel_y' if signal == 'steer' else 'accel_z'
    p.write_text(f'sec_from_incident,speed_kmh,{signal},{fourth}\n{values}\n')
    assert any(reason in t['reasons'] for t in find_log_triggers(normalize_log(p))['triggers'])


def test_verified_mapping_uses_actual_fps_and_merges(tmp_path):
    from backend.services.synchronization import TimeAnchor, align
    from backend.services.trigger_detection import find_log_triggers
    p = tmp_path/'log.csv'
    p.write_text('sec_from_incident,brake\n-1,0\n-.5,.9\n0,0\n.5,.95\n1,0\n')
    log = normalize_log(p)
    mapping = align({'duration':2.},log,[TimeAnchor(-1,0,'test'),TimeAnchor(1,2,'test')])
    t = find_log_triggers(log,alignment=mapping,video_metadata={'duration':2.,'fps':30.})['triggers'][0]
    assert t['video_start_s'] == .5
    assert t['video_peak_s'] == 1.5
    assert t['frame_peak'] == 45
    assert t['clip_start_s'] == 0
    assert t['clip_end_s'] == 2


def test_clock_gap_does_not_produce_derivative_spike(tmp_path):
    from backend.services.trigger_detection import find_log_triggers
    p = tmp_path/'gap.csv'
    p.write_text('sec_from_incident,speed_kmh,steer,accel_y\n0,30,0,3\n10,30,1,3\n')
    assert find_log_triggers(normalize_log(p))['triggers'] == []
