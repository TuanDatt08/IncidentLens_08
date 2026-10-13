from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_uncertain_output_and_video_clock_survive_negative_report(client, monkeypatch, tmp_path):
    from backend.services import review_context
    path = tmp_path / 'log.csv'
    path.write_text('t_video_s,speed_kmh,brake\n0,32,0\n1,10,0.9\n2,0,0.9\n')
    monkeypatch.setattr(review_context, 'require_demo_access', lambda: None)
    monkeypatch.setattr(review_context, 'get_incident', lambda i: {'telemetry_uri': 'INC-test/source/log.csv', 'video_metadata': {'duration': 2.1}})
    monkeypatch.setattr(review_context, 'get_model_metadata', lambda i: {'detection_state': 'REVIEW_REQUIRED_TELEMETRY_CONFLICT', 'draft_v2': {'summary': 'Output Qwen cần review', 'incident_detected': False}, 'consistency_checks': [{'window_s': [0., 2.]}]})
    monkeypatch.setattr(review_context, '_resolve_asset', lambda i, uri: path)
    response = await client.get('/api/v1/incidents/INC-test/review-context')
    assert response.status_code == 200
    body = response.json()
    assert body['review_required'] is True
    assert body['model_output']['incident_detected'] is False
    assert body['summary'] == 'Output Qwen cần review'
    assert body['alignment'] == 'VERIFIED'
    assert body['points'][0]['speed_kmh'] == 32
    assert body['points'][1]['brake_pct'] == 90


@pytest.mark.asyncio
async def test_context_keeps_production_access_closed(client, monkeypatch):
    from backend.services import access
    monkeypatch.setattr(access, 'get_settings', lambda: SimpleNamespace(app_env='production'))
    response = await client.get('/api/v1/incidents/INC-test/review-context')
    assert response.status_code == 403
