import pytest


@pytest.mark.asyncio
async def test_uncertain_output_and_video_clock_survive_negative_report(db_client, monkeypatch, tmp_path):
    from backend.services import review_context
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,speed_kmh,brake\n0,32,0\n1,10,0.9\n2,0,0.9\n')
    monkeypatch.setattr(review_context, 'get_incident', lambda i: {'telemetry_uri': 'INC-test/source/log.csv', 'video_metadata': {'duration': 2.1}})
    monkeypatch.setattr(review_context, 'get_model_metadata', lambda i: {'detection_state': 'REVIEW_REQUIRED_TELEMETRY_CONFLICT', 'draft_v2': {'summary': 'Output Qwen cần review', 'incident_detected': False}, 'consistency_checks': [{'window_s': [0., 2.]}]})
    monkeypatch.setattr(review_context, '_resolve_asset', lambda i, uri: path)
    response = await db_client.get('/api/v1/incidents/INC-test/review-context')
    assert response.status_code == 200
    body = response.json()
    assert body['review_required'] is True
    assert body['model_output']['incident_detected'] is False
    assert body['summary'] == 'Output Qwen cần review'
    assert body['alignment'] == 'VERIFIED'
    assert body['points'][0]['speed_kmh'] == 32
    assert body['points'][1]['brake_pct'] == 90


@pytest.mark.asyncio
async def test_context_requires_verified_session(auth_client):
    response = await auth_client.get('/api/v1/incidents/INC-test/review-context')
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'AUTHENTICATION_REQUIRED'


@pytest.mark.asyncio
async def test_v3_context_preserves_independent_analyses_and_video_clock(db_client, monkeypatch):
    from backend.services import review_context
    uncertain = {'schema_version': 'incident_analysis_v3', 'analysis_status': 'INCONCLUSIVE',
                 'summary': 'Chưa rõ tương tác.', 'unknowns': ['Thiếu góc nhìn.']}
    confirmed = {'schema_version': 'incident_analysis_v3', 'analysis_status': 'CONFIRMED',
                 'summary': 'Xe tránh chướng ngại vật.', 'unknowns': ['Thiếu góc nhìn.', 'Chưa rõ kết quả.'],
                 'timing': {'critical_s': 42.5},
                 'timeline': [{'time_s': 42.5, 'evidence_ids': ['FRAME-42']}],
                 'causal_analysis': {'root_cause': None, 'hypotheses': ['Có thể tầm nhìn bị che.']}}
    bundle = {'stage_b': [uncertain, confirmed], 'unknowns': ['Mẫu thưa.']}
    monkeypatch.setattr(review_context, 'get_incident', lambda i: {'telemetry_uri': None})
    monkeypatch.setattr(review_context, 'get_model_metadata', lambda i: {
        'draft_v3': bundle, 'draft_v2': {'summary': 'Old draft'}, 'video_offset_s': 42.5})
    response = await db_client.get('/api/v1/incidents/INC-test/review-context')
    assert response.status_code == 200
    body = response.json()
    assert body['primary_analysis'] == confirmed
    assert body['analyses'] == [uncertain, confirmed]
    assert body['model_output'] == bundle
    assert body['summary'] == confirmed['summary']
    assert body['warnings'] == ['Mẫu thưa.', 'Thiếu góc nhìn.', 'Chưa rõ kết quả.']
    assert body['time_basis'] == 'video_seconds'
    assert body['primary_analysis']['timeline'][0]['time_s'] == 42.5
