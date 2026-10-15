"""Private GPU file/API adapter. Bind to loopback and reach it through SSH only."""
from starlette.responses import JSONResponse

from api.gpu_media_proxy import is_gpu_media_request
from api.main import app


@app.middleware('http')
async def media_only(request, call_next):
    if request.method == 'GET' and request.url.path == '/health':
        return JSONResponse({'status': 'ok', 'service': 'gpu-media'})
    if not is_gpu_media_request(request.method, request.url.path):
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return await call_next(request)
