import json

import pytest

from backend.services.video import VideoProbeResult, VideoService


@pytest.mark.asyncio
@pytest.mark.parametrize('with_log', [True, False])
async def test_worker_routes_by_uploaded_log(db_client, monkeypatch, with_log):
    import backend.worker as worker
    from backend.config import get_settings
    from backend.models.contracts import AnalysisResult
    from backend.services.processing import ProcessedResult

    monkeypatch.setattr(VideoService, 'probe', lambda self, path: VideoProbeResult(10,30,1280,720))
    files = {'video': ('a.mp4', b'video', 'video/mp4')}
    if with_log:
        files['log'] = ('a.csv', b'sec_from_incident,speed_kmh\n0,20\n1,10\n', 'text/csv')
    iid = (await db_client.post('/api/v1/incidents/upload', files=files)).json()['incident_id']
    job = (await db_client.post(f'/api/v1/incidents/{iid}/analyze')).json()['job_id']
    settings = get_settings().model_copy(update={'qwen_runtime':'ollama','qwen_prompt_path':'backend/data/promt.txt','qwen_artifact_subdir':'output','qwen_video_pipeline':'stages'})
    monkeypatch.setattr(worker, 'get_settings', lambda: settings)
    used = []
    def provider(config):
        from pathlib import Path
        assert 'schema_version 2.0' in Path(config.qwen_prompt_path).read_text(encoding='utf-8')
        used.append('provider')
        return object()
    def local(incident, **kwargs):
        used.append('log')
        return ProcessedResult(AnalysisResult(incident_detected=False), [], None)
    def stages(incident, **kwargs):
        used.append('video')
        return ProcessedResult(AnalysisResult(incident_detected=False), [], None)
    monkeypatch.setattr(worker, 'create_local_provider', provider)
    monkeypatch.setattr(worker, 'process_local_incident', local)
    monkeypatch.setattr('backend.services.prompt_pipeline.process_prompt_incident', stages)
    assert worker.run_once(job_id=job)
    assert used == (['provider', 'log'] if with_log else ['video'])
    assert (await db_client.get(f'/api/v1/jobs/{job}')).json()['status'] == 'succeeded'
    assert (await db_client.get(f'/api/v1/jobs/{job}/diagnostics')).json()['pipeline'] == ('log_triggers' if with_log else 'video_stages')


@pytest.mark.asyncio
async def test_upload_explicit_sync_and_diagnostics(db_client, monkeypatch):
    monkeypatch.setattr(VideoService, 'probe', lambda self, path: VideoProbeResult(10, 30, 1280, 720))
    uploaded = await db_client.post('/api/v1/incidents/upload', data={'sync_offset_s': '7.967'}, files={'video': ('a.mp4', b'video', 'video/mp4'), 'log': ('a.csv', b'sec_from_incident,speed_kmh\n-7.967,30\n1.5,0\n', 'text/csv')})
    assert uploaded.status_code == 201
    iid = uploaded.json()['incident_id']
    detail = (await db_client.get(f'/api/v1/incidents/{iid}')).json()
    assert detail['video_metadata']['log_offset_s'] == 7.967
    job = (await db_client.post(f'/api/v1/incidents/{iid}/analyze')).json()['job_id']
    assert (await db_client.get(f'/api/v1/incidents/{iid}/latest-job')).json()['job_id'] == job
    status = await db_client.get(f'/api/v1/jobs/{job}/diagnostics')
    assert status.status_code == 200
    assert status.json()['job_status'] == 'queued'
    assert status.json()['events'] == []
    assert (await db_client.get('/api/v1/jobs/JOB-MISSING/diagnostics')).status_code == 404


@pytest.mark.asyncio
async def test_sync_json_rejects_answer_labels_and_accepts_anchors(db_client, monkeypatch):
    monkeypatch.setattr(VideoService, 'probe', lambda self, path: VideoProbeResult(10, 30, 1280, 720))
    base = {'video': ('a.mp4', b'video', 'video/mp4')}
    bad = await db_client.post('/api/v1/incidents/upload', files={**base, 'sync_metadata': ('expected.json', b'{"outcome":"near_miss"}', 'application/json')})
    assert bad.status_code == 422
    anchors = {'anchors': [{'log_s': -8., 'video_s': 0., 'source': 'recording_manifest'}, {'log_s': 2., 'video_s': 10., 'source': 'recording_manifest'}]}
    ok = await db_client.post('/api/v1/incidents/upload', files={**base, 'sync_metadata': ('sync.json', json.dumps(anchors).encode(), 'application/json')})
    assert ok.status_code == 201
    iid = ok.json()['incident_id']
    assert (await db_client.get(f'/api/v1/incidents/{iid}')).json()['video_metadata']['anchors'] == anchors['anchors']


@pytest.mark.asyncio
async def test_full_inconclusive_draft_sql_readback(db_client, monkeypatch):
    import backend.worker as worker
    from backend.config import get_settings
    from backend.models.contracts import AnalysisResult
    from backend.services.pipeline_status import update_status
    from backend.services.processing import ProcessedResult

    monkeypatch.setattr(VideoService, 'probe', lambda self, path: VideoProbeResult(10,30,1280,720))
    uploaded = await db_client.post('/api/v1/incidents/upload', files={'video':('a.mp4',b'video','video/mp4')})
    iid = uploaded.json()['incident_id']
    job_id = (await db_client.post(f'/api/v1/incidents/{iid}/analyze')).json()['job_id']
    settings = get_settings().model_copy(update={'qwen_runtime':'ollama','qwen_prompt_path':'backend/data/promt.txt','qwen_artifact_subdir':'output','qwen_video_pipeline':'stages'})
    monkeypatch.setattr(worker,'get_settings',lambda:settings)
    draft = {'schema_version':'incident_pipeline_v3','review_status':'DRAFT','detection_state':'INCONCLUSIVE','stage_a':[],'stage_b':[],'unknowns':['Không đủ coverage.']}
    def process(incident, **kwargs):
        from pathlib import Path
        output = Path(kwargs['storage_root'])/incident['incident_id']/'output'
        update_status(output, job_id, 'qwen', 'Gửi Stage A.', model='qwen2.5vl:7b')
        return ProcessedResult(AnalysisResult(incident_detected=False,model_metadata={'draft_v3':draft}),[],None)
    monkeypatch.setattr('backend.services.prompt_pipeline.process_prompt_incident',process)
    assert worker.run_once(job_id=job_id)
    diagnostics = (await db_client.get(f'/api/v1/jobs/{job_id}/diagnostics')).json()
    assert diagnostics['job_status'] == 'succeeded'
    assert diagnostics['stage'] == 'complete'
    assert diagnostics['result'] == draft
    report = (await db_client.get(f'/api/v1/incidents/{iid}/report')).json()
    assert report['review_status'] == 'DRAFT'
    assert report['version'] == 1
