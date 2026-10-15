import httpx
import pytest
from fastapi import FastAPI, Request

from api.gpu_media_proxy import GpuMediaProxy, is_gpu_media_request


@pytest.mark.parametrize(('method', 'path', 'expected'), [
    ('POST', '/api/v1/incidents/upload', True),
    ('GET', '/api/v1/incidents/INC-ABC/video', True),
    ('GET', '/api/v1/incidents/INC-ABC/telemetry', True),
    ('GET', '/api/v1/incidents/INC-ABC/evidence/EVD-ABC/media', True),
    ('GET', '/api/v1/jobs/JOB-ABC/diagnostics', True),
    ('POST', '/api/v1/incidents/INC-ABC/analyze', False),
    ('GET', '/api/v1/auth/me', False),
    ('GET', '/api/v2/recordings', False),
])
def test_media_route_scope(method, path, expected):
    assert is_gpu_media_request(method, path) == expected


@pytest.mark.asyncio
async def test_proxy_preserves_upload_auth_and_range_response():
    upstream = FastAPI()

    @upstream.post('/api/v1/incidents/upload')
    async def upload(request: Request):
        assert request.headers['cookie'] == 'session=opaque'
        assert request.headers['x-csrf-token'] == 'csrf'
        assert request.headers['origin'] == 'https://frontend.example'
        assert await request.body() == b'video bytes'
        return {'incident_id': 'INC-NEW'}

    @upstream.get('/api/v1/incidents/INC-ABC/video')
    async def video(request: Request):
        from starlette.responses import Response
        assert request.headers['range'] == 'bytes=0-2'
        return Response(b'mp4', status_code=206, headers={'Content-Range': 'bytes 0-2/100'})

    app = FastAPI()
    app.add_middleware(GpuMediaProxy, base_url='http://gpu', transport=httpx.ASGITransport(app=upstream))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://render') as c:
        r = await c.post('/api/v1/incidents/upload', content=b'video bytes', headers={
            'cookie': 'session=opaque', 'x-csrf-token': 'csrf', 'origin': 'https://frontend.example'})
        assert r.json() == {'incident_id': 'INC-NEW'}
        r = await c.get('/api/v1/incidents/INC-ABC/video', headers={'range': 'bytes=0-2'})
        assert r.status_code == 206
        assert r.headers['content-range'] == 'bytes 0-2/100'
        assert r.content == b'mp4'


@pytest.mark.asyncio
async def test_gpu_offline_returns_service_unavailable_without_local_upload():
    def offline(request):
        raise httpx.ConnectError('private endpoint must not leak', request=request)
    app = FastAPI()
    app.add_middleware(GpuMediaProxy, base_url='http://gpu', transport=httpx.MockTransport(offline))
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=['https://frontend.example'], allow_credentials=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://render') as c:
        r = await c.post('/api/v1/incidents/upload', content=b'video', headers={'origin': 'https://frontend.example'})
        assert r.status_code == 503
        assert r.headers['access-control-allow-origin'] == 'https://frontend.example'
        assert 'private endpoint' not in r.text
