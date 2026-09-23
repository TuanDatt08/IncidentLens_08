"""Incident upload and factual metadata routes."""

from fastapi import APIRouter, File, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from src.models.contracts import UploadResponse
from src.services.incidents import create_incident, get_incident, list_incidents


router = APIRouter(tags=["incidents"])


@router.post("/incidents/upload", status_code=201, response_model=UploadResponse)
async def upload_incident(video: UploadFile = File(...), log: UploadFile | None = File(default=None)):
    return await run_in_threadpool(create_incident, video, log)


@router.get("/incidents")
async def list_incidents_route(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    return await run_in_threadpool(list_incidents, limit, offset)


@router.get("/incidents/{incident_id}")
async def get_incident_route(incident_id: str):
    return await run_in_threadpool(get_incident, incident_id)
