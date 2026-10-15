"""Stream media over the private SSH tunnel; ordinary API requests stay local."""
import re

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse

from backend.config import get_settings

HOP_HEADERS = {'host', 'connection', 'keep-alive', 'proxy-authenticate',
               'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade'}


def is_gpu_media_request(method: str, path: str) -> bool:
    if method == 'POST':
        return path == '/api/v1/incidents/upload'
    return method in {'GET', 'HEAD'} and bool(re.fullmatch(
        r'/api/v1/(?:incidents/[^/]+/(?:video|telemetry|evidence/[^/]+/media)|jobs/[^/]+/diagnostics)', path))


class GpuMediaProxy:
    def __init__(self, app, *, base_url=None, transport=None):
        self.app, self.base_url, self.transport = app, base_url, transport

    async def __call__(self, scope, receive, send):
        base = self.base_url if self.base_url is not None else get_settings().gpu_media_base_url
        if scope['type'] != 'http' or not base or not is_gpu_media_request(scope['method'], scope['path']):
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        client = httpx.AsyncClient(timeout=httpx.Timeout(600, connect=10),
                                   trust_env=False, follow_redirects=False, transport=self.transport)
        try:
            upstream_request = client.build_request(
                request.method, base.rstrip('/') + request.url.path,
                params=request.query_params,
                headers=[(k, v) for k, v in request.headers.items() if k.lower() not in HOP_HEADERS],
                content=request.stream())
            upstream = await client.send(upstream_request, stream=True)
        except httpx.HTTPError:
            await client.aclose()
            response = JSONResponse({'error': {'code': 'GPU_UNAVAILABLE',
                'message': 'GPU media service is unavailable. Try again when the GPU is online.',
                'details': None}}, status_code=503, headers={'Retry-After': '30'})
            return await response(scope, receive, send)

        async def chunks():
            try:
                async for chunk in upstream.aiter_raw():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        response = StreamingResponse(chunks(), status_code=upstream.status_code)
        response.raw_headers = [(k, v) for k, v in upstream.headers.raw
                                if k.decode().lower() not in HOP_HEADERS]
        await response(scope, receive, send)
