"""Local-demo media routes. Production access remains closed until auth is chosen."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from src.services.media import evidence_asset, source_video

router = APIRouter(tags=["media"])


def _response(asset: tuple) -> FileResponse:
    path, media_type = asset
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/incidents/{incident_id}/video")
async def source_video_route(incident_id: str):
    return _response(await run_in_threadpool(source_video, incident_id))


@router.get("/incidents/{incident_id}/evidence/{evidence_id}/media")
async def evidence_media_route(incident_id: str, evidence_id: str):
    return _response(await run_in_threadpool(evidence_asset, incident_id, evidence_id))
