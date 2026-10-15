from pathlib import Path

import pytest

from backend.services.prompt_pipeline import prompt_contracts, validate_stage


def test_requested_prompt_contracts_and_required_fields():
    contracts = prompt_contracts(Path('backend/data/promt.txt').read_text(encoding='utf-8'))
    assert contracts['A'][1].model_json_schema()['properties']['schema_version']['const'] == 'incident_detection_v3'
    assert 'causal_analysis' in contracts['B'][1].model_json_schema()['required']
    with pytest.raises(ValueError):
        validate_stage({'schema_version': '2.0'}, contracts['A'][1], {}, 10)


def test_invented_evidence_and_out_of_bounds_times_rejected():
    contracts = prompt_contracts(Path('backend/data/promt.txt').read_text(encoding='utf-8'))
    data = {'schema_version': 'incident_detection_v3', 'time_basis': 'video_seconds', 'review_status': 'DRAFT', 'video_duration_s': 10.0, 'analyzed_intervals': [{'start_s': 0.0, 'end_s': 10.0}], 'overall_status': 'INCONCLUSIVE', 'incidents': [{'incident_id': 'I1', 'status': 'INCONCLUSIVE', 'event_type': 'OTHER', 'onset_s': None, 'critical_s': None, 'end_s': None, 'clip_window': {'start_s': None, 'end_s': None}, 'confidence': 0.1, 'event_summary': 'Chưa đủ bằng chứng', 'evidence': [{'evidence_id': 'FAKE', 'time_s': 1.0, 'source': 'VIDEO_FRAME', 'observation': 'Xe'}], 'unknowns': ['Chưa đủ frame']}], 'coverage_limitations': ['Mẫu thưa']}
    with pytest.raises(ValueError, match='evidence'):
        validate_stage(data, contracts['A'][1], {}, 10)


def test_pipeline_keeps_prompt_raw_response_and_missing_sync(monkeypatch, tmp_path):
    import json

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline
    root = tmp_path / 'incidents'
    source = root / 'INC-TEST' / 'source'
    source.mkdir(parents=True)
    (source / 'video.mp4').write_bytes(b'video')
    (source / 'telemetry.csv').write_text('sec_from_incident,speed_kmh,brake,accel_x\n-1,20,0,0\n0,0,1,-10\n')
    prompt = tmp_path / 'promt.txt'
    prompt.write_text(Path('backend/data/promt.txt').read_text(encoding='utf-8'), encoding='utf-8')
    settings = Settings(qwen_runtime='ollama', qwen_prompt_path=str(prompt), qwen_outputs_path=str(tmp_path/'outputs.txt'))
    requests = []
    response = {'schema_version': 'incident_detection_v3', 'time_basis': 'video_seconds', 'review_status': 'DRAFT', 'video_duration_s': 2.0, 'analyzed_intervals': [{'start_s': 0., 'end_s': 2.}], 'overall_status': 'NO_INCIDENT', 'incidents': [], 'coverage_limitations': ['Mẫu thưa, chưa đủ quan sát toàn bộ.']}
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            import httpx
            requests.append(json)
            return httpx.Response(200, json={'choices': [{'message': {'content': __import__('json').dumps(response)}}], 'usage': {'total_tokens': 1}}, request=httpx.Request('POST', url))
    def extract(self, source, at, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'image')
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    result = pipeline.process_prompt_incident({'incident_id': 'INC-TEST', 'video_uri': 'INC-TEST/source/video.mp4', 'telemetry_uri': 'INC-TEST/source/telemetry.csv', 'video_metadata': {'duration': 2.0, 'fps': 30.}}, storage_root=root, settings=settings, job_id='JOB-TEST')
    assert not result.analysis.incident_detected
    assert result.analysis.model_metadata['draft_v3']['alignment']['quality'] == 'UNKNOWN'
    assert len(requests[0]['messages'][1]['content']) == 5
    context = json.loads(requests[0]['messages'][1]['content'][0]['text'])
    assert context['unsynchronized_log']['rows']
    assert requests[0]['messages'][0]['content'].startswith('## STAGE A')
    output = root/'INC-TEST'/'output'
    assert list((output/'requests').glob('*.response.json'))
    assert (output/'JOB-TEST.draft-v3.json').is_file()


def test_explicit_offset_supplies_synchronized_log(monkeypatch, tmp_path):
    # Clock correctness is checked independently of any model verdict.
    from backend.services.log_normalization import normalize_log
    from backend.services.synchronization import TimeAnchor, align
    path = tmp_path/'log.csv'
    path.write_text('sec_from_incident,speed_kmh\n-7.967,30\n1.5,0\n')
    mapping = align({'duration': 9.533333}, normalize_log(path), [TimeAnchor(-7.967, 0., 'explicit_upload_offset'), TimeAnchor(1.566333, 9.533333, 'explicit_upload_offset')])
    assert mapping.quality == 'VERIFIED'
    assert mapping.to_video_seconds(-7.967) == pytest.approx(0.)


def test_stage_b_full_fields_are_kept_for_inconclusive_candidate(monkeypatch, tmp_path):
    import json

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline

    root = tmp_path/'storage'
    source = root/'INC-T'/'source'
    source.mkdir(parents=True)
    (source/'video.mp4').write_bytes(b'video')
    prompt = Path('backend/data/promt.txt').read_text(encoding='utf-8')
    section_b = prompt.split('## STAGE B')[1]
    schema_b = json.JSONDecoder().raw_decode(section_b[section_b.index('{\n'):])[0]
    def enum_values(value):
        if isinstance(value, dict):
            return {k: enum_values(v) for k,v in value.items()}
        if isinstance(value, list):
            return []
        return value.split(' | ')[0] if isinstance(value, str) else value
    b = enum_values(schema_b)
    b.update(analysis_status='INCONCLUSIVE', summary='Chưa đủ bằng chứng để xác nhận sự cố.', confidence=0.1)
    b['timing'].update(clip_start_s=0., clip_end_s=2.)
    stages = []
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            import httpx
            stage = json['response_format']['json_schema']['name'][-1]
            stages.append(stage)
            if stage == 'B':
                result = b
            else:
                context = __import__('json').loads(json['messages'][1]['content'][0]['text'])
                event = {'incident_id':'I1','status':'INCONCLUSIVE','event_type':'OTHER','onset_s':None,'critical_s':None,'end_s':None,'clip_window':{'start_s':None,'end_s':None},'confidence':0.1,'event_summary':'Cần kiểm tra thêm frame.','evidence':[{'evidence_id':context['evidence'][0]['evidence_id'],'time_s':0.,'source':'VIDEO_FRAME','observation':'Xe đang di chuyển.'}],'unknowns':['Chưa đủ quan sát.']}
                result = {'schema_version':'incident_detection_v3','time_basis':'video_seconds','review_status':'DRAFT','video_duration_s':2.,'analyzed_intervals':[{'start_s':0.,'end_s':2.}],'overall_status':'INCONCLUSIVE','incidents':[event],'coverage_limitations':['Frame thưa.']}
            return httpx.Response(200, json={'choices':[{'message':{'content':__import__('json').dumps(result)}}]},request=httpx.Request('POST',url))
    def extract(self, source, at, *args):
        path = args[-1]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'evidence')
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    monkeypatch.setattr(pipeline.VideoService, 'extract_clip', extract)
    settings = Settings(qwen_runtime='ollama',qwen_outputs_path=str(tmp_path/'outputs.txt'))
    result = pipeline.process_prompt_incident({'incident_id':'INC-T','video_uri':'INC-T/source/video.mp4','video_metadata':{'duration':2.,'fps':30.}},storage_root=root,settings=settings,job_id='JOB-T')
    assert stages == ['A','B']
    stored = result.analysis.model_metadata['draft_v3']['stage_b'][0]
    assert stored['analysis_status'] == 'INCONCLUSIVE'
    assert set(stored['causal_analysis']) == {'supported_immediate_cause','root_cause','contributing_factors','hypotheses','causal_uncertainty'}
    assert not result.analysis.incident_detected


@pytest.mark.parametrize('invalid_sequence', [False, True])
def test_temporal_video_only_sends_all_frames_global_numbers_and_final_summary(monkeypatch, tmp_path, invalid_sequence):
    import json

    import httpx

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline

    source = tmp_path / 'INC-T/source'
    source.mkdir(parents=True)
    (source / 'video.mp4').write_bytes(b'video')
    requests = []
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            requests.append(json)
            context = __import__('json').loads(json['messages'][1]['content'][0]['text'])
            if json['response_format']['json_schema']['name'] == 'video_summary':
                result = {'overall_status': 'INCONCLUSIVE' if invalid_sequence else 'NO_INCIDENT_IN_OBSERVED_COVERAGE',
                          'summary': 'Không thấy sự cố trong các ảnh đã xem.', 'events': [],
                          'unknowns': [], 'review_status': 'DRAFT'}
                if invalid_sequence:
                    result['events'] = [{'candidate_ids': [r['candidate_id']], 'status': 'INCONCLUSIVE',
                                        'event_type': 'UNKNOWN', 'summary': 'Chuỗi chưa được kiểm tra.', 'evidence_ids': []}
                                       for r in context['records'] if r['status']=='INCONCLUSIVE']
            elif invalid_sequence and context.get('decision_scope')=='SUPPLIED_SEQUENCE':
                result = {'invalid': True}
            else:
                result = {'schema_version': 'incident_detection_v3', 'time_basis': 'frame_sequence',
                          'review_status': 'DRAFT', 'total_frames': context['total_frames'],
                          'analyzed_intervals': [{'start_frame_seq': context['clip_start_frame_seq'],
                                                  'end_frame_seq': context['clip_end_frame_seq']}],
                          'overall_status': 'NO_INCIDENT', 'incidents': [],
                          'coverage_limitations': ['Chỉ xem các ảnh được cung cấp.']}
            return httpx.Response(200, json={'choices': [{'message': {'content': __import__('json').dumps(result)}}]}, request=httpx.Request('POST', url))
    def extract(self, source, at, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at).encode())
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    settings = Settings(_env_file=None, qwen_runtime='ollama', qwen_video_summary=True,
                        qwen_batch_frames=6, qwen_outputs_path=str(tmp_path / 'output.txt'))
    result = pipeline.process_prompt_incident({'incident_id': 'INC-T', 'video_uri': 'INC-T/source/video.mp4',
             'video_metadata': {'duration': 2., 'fps': 30.}}, storage_root=tmp_path, settings=settings, job_id='JOB-T')
    sequences = [r for r in requests if r['response_format']['json_schema']['name'] == 'stage_A']
    contexts = list({json.loads(r['messages'][1]['content'][0]['text']).get('sequence_id', 'FINAL_WINDOW'): json.loads(r['messages'][1]['content'][0]['text']) for r in sequences}.values())
    assert len(contexts) == 3  # Two overlapping batches, then window-level synthesis.
    frame_sets = [{e['frame_seq'] for e in c['evidence']} for c in contexts[:2]]
    assert frame_sets[0] & frame_sets[1] == {5, 6}
    assert frame_sets[0] | frame_sets[1] == set(range(1, 9))
    assert all('time_s' not in e for c in contexts for e in c['evidence'])
    assert requests[-1]['response_format']['json_schema']['name'] == 'video_summary'
    assert result.analysis.model_metadata['video_summary']['overall_status'] == ('INCONCLUSIVE' if invalid_sequence else 'NO_INCIDENT_IN_OBSERVED_COVERAGE')
    assert (tmp_path / 'INC-T/output/JOB-T.frame-map.json').is_file()


def test_video_only_historical_sequence_evidence_survives_candidate_and_final(monkeypatch, tmp_path):
    import json

    import httpx

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline
    from backend.services.frame_clock import FrameClock

    source = tmp_path / 'INC-T/source'
    source.mkdir(parents=True)
    (source / 'video.mp4').write_bytes(b'video')
    clock = FrameClock([i/4 for i in range(8)], 2.)
    observed = []
    def blank(value):
        if isinstance(value, dict):
            return {k: blank(v) for k, v in value.items()}
        if isinstance(value, list):
            return []
        if isinstance(value, str):
            return value.split(' | ')[0] or 'Chưa rõ.'
        return value
    text = Path('backend/data/promt.txt').read_text(encoding='utf-8')
    section = text.split('## STAGE B')[1]
    template = json.JSONDecoder().raw_decode(section[section.index('{\n'):])[0]
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            context = __import__('json').loads(json['messages'][1]['content'][0]['text'])
            name = json['response_format']['json_schema']['name']
            refs = context.get('evidence', [])
            if name == 'video_summary':
                assert next(r for r in context['records'] if r['candidate_id']=='A0-0')['status'] == 'INCONCLUSIVE'
                result = {'overall_status': 'CONFIRMED', 'summary': 'Có xung đột được quan sát.',
                          'events': [{'candidate_ids': [r['candidate_id'] for r in context['records'] if r['status']!='NO_INCIDENT'],
                                      'status': 'CONFIRMED', 'event_type': 'OTHER', 'summary': 'Có xung đột.',
                                      'evidence_ids': [item['evidence_id'] for item in observed]}],
                          'unknowns': [], 'review_status': 'DRAFT'}
            elif name == 'stage_B':
                wire_schema = json['response_format']['json_schema']['schema']
                timing_schema = wire_schema['$defs'][wire_schema['properties']['timing']['$ref'].split('/')[-1]]
                assert timing_schema['properties']['clip_end_frame_seq']['const'] == 9
                assert {item['evidence_id'] for item in observed} <= {r['evidence_id'] for r in context['historical_evidence']}
                result = blank(template)
                result.update(analysis_status='CONFIRMED', event_type='OTHER', summary='Có xung đột được quan sát.')
                result['timing'].update(clip_start_s=0., clip_end_s=2., onset_s=.25, critical_s=.75, end_s=1.)
                result['evidence'] = [{**item, 'certainty': 'OBSERVED', 'supports': ['Xung đột.']} for item in observed]
                result = clock.encode(result)
            else:
                if not observed:
                    observed.extend({'evidence_id': ref['evidence_id'], 'time_s': at, 'source': 'VIDEO_FRAME', 'observation': 'Có xung đột.'}
                                    for ref, at in [(refs[1], .25), (refs[3], .75)])
                use = context.get('decision_scope') == 'FINAL_WINDOW' or context['clip_start_frame_seq'] == 1
                event = {'incident_id': 'I1', 'status': 'CONFIRMED', 'event_type': 'OTHER', 'onset_s': .25,
                         'critical_s': .75, 'end_s': 1., 'clip_window': {'start_s': None, 'end_s': None},
                         'confidence': .7, 'event_summary': 'Có xung đột được quan sát.', 'evidence': observed, 'unknowns': []}
                result = clock.encode({'schema_version': 'incident_detection_v3', 'time_basis': 'video_seconds',
                          'review_status': 'DRAFT', 'video_duration_s': 2.,
                          'analyzed_intervals': [{'start_s': clock.timestamp(context['clip_start_frame_seq']),
                                                  'end_s': clock.timestamp(context['clip_end_frame_seq'])}],
                          'overall_status': 'CONFIRMED' if use else 'NO_INCIDENT', 'incidents': [event] if use else [],
                          'coverage_limitations': ['Chỉ xem ảnh lấy mẫu.']})
            return httpx.Response(200, json={'choices': [{'message': {'content': __import__('json').dumps(result)}}]}, request=httpx.Request('POST', url))
    def extract(self, source, at, *args):
        path = args[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at).encode())
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    monkeypatch.setattr(pipeline.VideoService, 'extract_clip', extract)
    settings = Settings(_env_file=None, qwen_runtime='ollama', qwen_video_summary=True,
                        qwen_batch_frames=6, qwen_outputs_path=str(tmp_path / 'output.txt'))
    result = pipeline.process_prompt_incident({'incident_id': 'INC-T', 'video_uri': 'INC-T/source/video.mp4',
             'video_metadata': {'duration': 2., 'fps': 30.}}, storage_root=tmp_path, settings=settings, job_id='JOB-T')
    assert result.analysis.incident_detected
    assert result.analysis.incident_window.critical == 0.
    assert result.analysis.model_metadata['video_summary']['events'][0]['evidence_ids']
