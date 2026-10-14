"""Authenticated incident media with streaming and Range support."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from api.dependencies import permission
from backend.services.access import Principal
from backend.services.media import evidence_asset, source_telemetry, source_video

router = APIRouter(tags=["media"])


def _response(asset: tuple) -> FileResponse:
    path, media_type = asset
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/incidents/{incident_id}/video")
async def source_video_route(incident_id: str, principal: Principal = Depends(permission("incident:read"))):
    return _response(await run_in_threadpool(source_video, incident_id, principal=principal))


@router.get("/incidents/{incident_id}/telemetry")
async def source_telemetry_route(incident_id: str, principal: Principal = Depends(permission("incident:read"))):
    return _response(await run_in_threadpool(source_telemetry, incident_id, principal=principal))


@router.get("/incidents/{incident_id}/evidence/{evidence_id}/media")
async def evidence_media_route(incident_id: str, evidence_id: str, principal: Principal = Depends(permission("incident:read"))):
    return _response(await run_in_threadpool(evidence_asset, incident_id, evidence_id, principal=principal))
