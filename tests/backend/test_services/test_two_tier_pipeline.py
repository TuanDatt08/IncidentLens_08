import shutil
import subprocess

import pytest

from backend.config import Settings
from backend.services import two_tier_pipeline as tt


def w(start, choice, strict=None):
    return {'start_s': start, 'end_s': start + 1.8, 'choice': choice, **({'strict': strict} if strict else {})}


def test_rules_need_a_second_check():
    assert [len(r) for r in tt.runs([w(0, 'A'), w(1.2, 'B'), w(2.4, 'C'), w(3.6, 'A'), w(4.8, 'B')])] == [2, 1]
    assert tt.classify([w(0, 'C')], 'C') == {'kind': 'FALL_OR_COLLISION', 'confidence': 'high'}
    assert tt.classify([w(0, 'C')], 'A') is None                       # tier 2 rejects a lone C
    assert tt.classify([w(0, 'B')], 'B') is None                       # a lone B is never an event
    assert tt.classify([w(0, 'B', 'B'), w(1.2, 'B', 'B')], 'B') == {'kind': 'NEAR_MISS', 'confidence': 'high'}
    assert tt.classify([w(0, 'B', 'A'), w(1.2, 'B', 'B')], 'B') == {'kind': 'NEAR_MISS', 'confidence': 'review'}
    assert tt.classify([w(0, 'B', 'B'), w(1.2, 'B', 'B')], 'A') is None  # tier 2 sees normal traffic


def test_tier2_targets_the_road_user_doing_the_dangerous_thing():
    # Real tier-1 text from CARLA v18 and the motorcycle clip.
    v18 = ('A motorcycle on the right side of the road disappears from view. A red car remains stationary on the right curb. '
           'A pedestrian appears on the sidewalk and runs towards the street, crossing in front of a black vehicle ahead.')
    fall = 'A person on a red motorcycle is riding alongside the camera car, then falls off their bike onto the roadside vegetation. A white SUV drives ahead in the same lane.'
    assert tt.named_actors(v18)[0] == 'pedestrian'
    assert tt.named_actors(fall)[0] == 'motorcycle'


def test_dashboard_speed_drops_find_hard_braking_only():
    mph = lambda xs: [None if x is None else x * 0.44704 for x in xs]
    # On-screen MPH every 0.5 s, read by eye from the web clips.
    near_miss = mph([26, 26, 26, 26, 25, 24, 23, 22, 21, 18, 13, 7, 2, 1, 0, 0, 1])          # 4B7BE, car cuts across
    stop_sign = mph([20, 19, 17, 16, 14, 13, 11, 9, 8, 6, 4, 2, 1, 0, 0, 0])                  # B39C6, calm stop
    cut_across = mph([0, 0, 2, 5, 8, 11, 13, 10, 4, 1, 0, 0])                                  # B39C6 16.5 s+, SUV crosses
    [brake] = tt.speed_drops(near_miss)
    assert brake['start_s'] == 4.0 and brake['peak_s'] == 5.0 and brake['min_acceleration'] < -4.5
    assert tt.speed_drops(stop_sign) == []
    assert [t['peak_s'] for t in tt.speed_drops(cut_across)] == [3.5]
    assert tt.speed_drops(mph([26, 26, 26, 2, 26, 26, 26])) == []                             # one misread digit
    assert tt.speed_drops(mph([26, None, 10])) == []                                       # gap: unverifiable drop


def test_grounding_coordinates_per_model():
    assert tt.to_pixels('qwen3.5:9b', [500, 0, 1000, 500], 720, 440) == [360, 0, 720, 220]
    assert tt.to_pixels('qwen2.5vl:7b', [0, 0, 1148, 728], 720, 440) == [0, 0, 720, 440]
    assert tt.incident_type('FALL_OR_COLLISION', 'motorcycle') == 'LOSS_OF_CONTROL'
    assert tt.incident_type('NEAR_MISS', 'pedestrian') == 'PEDESTRIAN_CONFLICT'


def synthetic_incident(tmp_path):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        pytest.skip('ffmpeg not installed')
    video = tmp_path / 'INC-T' / 'source' / 'video.mp4'
    video.parent.mkdir(parents=True)
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=10', '-t', '6', '-pix_fmt', 'yuv420p', str(video)], check=True)
    incident = {'incident_id': 'INC-T', 'video_uri': 'INC-T/source/video.mp4', 'video_metadata': {'duration': 6.0, 'fps': 10, 'width': 320, 'height': 180}}
    settings = Settings(_env_file=None, qwen_runtime='ollama', qwen_ollama_model='qwen3.5:9b', qwen_video_pipeline='two_tier',
                        qwen_endpoint='http://127.0.0.1:11434/v1/chat/completions', ffmpeg_bin=ffmpeg, ffprobe_bin=shutil.which('ffprobe') or 'ffprobe')
    return incident, settings


def test_hard_braking_in_the_csv_triggers_and_confirms_a_tier2_near_miss(tmp_path, monkeypatch):
    incident, settings = synthetic_incident(tmp_path)
    rows = ['t_video_s,speed_kmh,brake,accel_x']
    for i in range(int(6 * 24)):
        t = i / 24
        braking = 4.4 <= t <= 4.8                                  # hard brake peaking around 4.5 s video
        glitch = i == 1                                             # CARLA spawn glitch: absurd deceleration, no brake
        rows.append(f'{t:.3f},{30 - (t - 4.4) * 40 if braking else 30:.2f},{0.9 if braking else 0},{-9.0 if braking else -40000 if glitch else 0.02}')
    (tmp_path / 'INC-T' / 'source' / 'telemetry.csv').write_text('\n'.join(rows))
    incident['telemetry_uri'] = 'INC-T/source/telemetry.csv'

    def fake_ask(self, text, images, schema, max_tokens=200):
        props = schema['properties']
        if 'b_boxes' in props:
            return {'a_found': 'nothing attached', 'b_boxes': []}
        if 'b_bbox' in props:
            return {'a_actor': 'pedestrian', 'b_bbox': [300, 200, 700, 900]}
        if 'crops around' in text:                                # only the telemetry-forced tier 2 sees the hazard
            return {'a_description': 'a pedestrian runs into the lane ahead', 'b_choice': 'B'}
        return {'a_description': 'normal', 'b_choice': 'A'}       # tier 1 misses it

    monkeypatch.setattr(tt.TwoTier, 'ask', fake_ask)
    monkeypatch.setattr(tt, 'ensure_ollama_runtime', lambda s: None)
    result = tt.process_two_tier_incident(incident, storage_root=tmp_path, settings=settings, job_id='JOB-B')

    analysis = result.analysis
    assert analysis.incident_detected and analysis.incident_type == 'PEDESTRIAN_CONFLICT'
    assert analysis.model_metadata['telemetry_alignment'] == 'VERIFIED'
    assert [round(t['peak_s']) for t in analysis.model_metadata['braking_triggers']] == [4]          # spawn glitch ignored
    assert 4.3 <= result.collision_offset_in_video_s <= 4.9                          # critical moment = braking peak
    assert 'telemetry phanh gấp' in analysis.summary and any(t['phase'] == 'REACTION' for t in analysis.timeline)


def test_review_only_near_miss_keeps_the_report_empty(tmp_path, monkeypatch):
    incident, settings = synthetic_incident(tmp_path)

    def fake_ask(self, text, images, schema, max_tokens=200):
        props = schema['properties']
        if 'b_boxes' in props:
            return {'a_found': 'nothing attached', 'b_boxes': []}
        if 'b_bbox' in props:
            return {'a_actor': 'pedestrian', 'b_bbox': [300, 200, 700, 900]}
        if 'how close it gets' in text:                  # strict re-check: never within two car lengths
            return {'a_description': 'stays far ahead', 'b_choice': 'A'}
        if 'crops around' in text:
            return {'a_description': 'pedestrian crosses ahead', 'b_choice': 'B'}
        return {'a_description': 'pedestrian crosses', 'b_choice': 'B'} if ('t = 2.70s' in text or 't = 3.90s' in text) else {'a_description': 'normal', 'b_choice': 'A'}

    monkeypatch.setattr(tt.TwoTier, 'ask', fake_ask)
    monkeypatch.setattr(tt, 'ensure_ollama_runtime', lambda s: None)
    result = tt.process_two_tier_incident(incident, storage_root=tmp_path, settings=settings, job_id='JOB-R')

    analysis = result.analysis
    assert not analysis.incident_detected and result.evidence == [] and result.collision_offset_in_video_s is None
    assert analysis.incident_type is None and analysis.summary is None and analysis.unknowns == [] and analysis.timeline == []
    assert analysis.model_metadata['detection_state'] == 'REVIEW_REQUIRED_TWO_TIER_CANDIDATE'
    assert analysis.model_metadata['draft_v3']['summary'].startswith('1 sự kiện cần kỹ sư xem lại')
    assert [e['confidence'] for e in analysis.model_metadata['events']] == ['review']
    assert [v['analysis_status'] for v in analysis.model_metadata['structured_analyses']] == ['INCONCLUSIVE']


def test_pipeline_reports_a_fall_confirmed_by_both_tiers(tmp_path, monkeypatch):
    incident, settings = synthetic_incident(tmp_path)
    asked = []

    def fake_ask(self, text, images, schema, max_tokens=200):
        asked.append(text)
        props = schema['properties']
        if 'b_boxes' in props:
            return {'a_found': 'nothing attached', 'b_boxes': []}
        if 'b_bbox' in props:
            return {'a_actor': 'motorcycle', 'b_bbox': [300, 200, 700, 900]}
        if 'a_summary' in props:
            return {'a_summary': 'Xe máy ngã bên lề đường.'}
        if 'crops around' in text:
            return {'a_description': 'the motorcycle tips over', 'b_choice': 'C'}
        return {'a_description': 'rider falls', 'b_choice': 'C'} if 't = 2.70s' in text else {'a_description': 'normal', 'b_choice': 'A'}

    monkeypatch.setattr(tt.TwoTier, 'ask', fake_ask)
    monkeypatch.setattr(tt, 'ensure_ollama_runtime', lambda s: None)
    result = tt.process_two_tier_incident(incident, storage_root=tmp_path, settings=settings, job_id='JOB-T')

    analysis = result.analysis
    assert analysis.incident_detected and analysis.incident_type == 'LOSS_OF_CONTROL'
    assert result.collision_offset_in_video_s == pytest.approx(3.3)                 # C window 2.7 s + one 0.6 s step
    assert (analysis.incident_window.start, analysis.incident_window.end) == pytest.approx((-0.6, 1.2))
    assert analysis.model_metadata['detection_state'] == 'CONFIRMED'
    view = analysis.model_metadata['structured_analyses'][0]
    assert view['analysis_status'] == 'CONFIRMED' and view['event_details']['participants'] == ['motorcycle']
    assert view['outcome']['near_miss_occurred'] is False and view['timeline'][0]['time_s'] == 2.7   # video seconds, not rebased
    assert result.evidence and all((tmp_path / e.uri).is_file() for e in result.evidence)
    assert sum('t = ' in q and 'crops' not in q and 'Vietnamese' not in q for q in asked) == 4   # 10 frames -> 4 windows, no strict re-check for C
    assert analysis.summary.endswith('Toàn clip (Qwen): Xe máy ngã bên lề đường.')
