import pytest


@pytest.mark.asyncio
async def test_search_filters_before_pagination(db_client):
    from backend.db import session_scope
    from backend.models.tables import AnalysisReport, Incident

    with session_scope() as session:
        for index in range(25):
            item = Incident(incident_id=f"INC-{index:02}", processing_status="COMPLETED", video_uri=f"INC-{index:02}/source.mp4", scenario="pedestrian" if index == 0 else "road")
            session.add(item)
            session.flush()
            session.add(AnalysisReport(incident_id=item.id, review_status="APPROVED" if index == 0 else "DRAFT"))
    response = await db_client.get('/api/v1/incidents', params={'q': 'pedestrian', 'review_status': 'APPROVED', 'processing_status': 'COMPLETED', 'limit': 20})
    assert response.status_code == 200
    body = response.json()
    assert body['total'] == 1
    assert [item['incident_id'] for item in body['items']] == ['INC-00']
    assert body['summary']['total'] == 25
    assert body['summary']['reviews']['APPROVED'] == 1
    assert body['items'][0]['review_status'] == 'APPROVED'


@pytest.mark.asyncio
async def test_literal_search_and_invalid_filters(db_client):
    from backend.db import session_scope
    from backend.models.tables import Incident

    with session_scope() as session:
        session.add(Incident(incident_id="INC-ONE", processing_status="READY", video_uri="INC-ONE/source.mp4"))
    response = await db_client.get('/api/v1/incidents', params={'q': '%'})
    assert response.json()['total'] == 0
    assert (await db_client.get('/api/v1/incidents', params={'review_status': 'INVALID'})).status_code == 422
