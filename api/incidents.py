"""Incident upload and factual metadata routes."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from api.dependencies import permission
from backend.models.contracts import UploadResponse
from backend.services.access import Principal
from backend.services.incidents import create_incident, get_incident, list_incidents

router = APIRouter(tags=["incidents"], dependencies=[Depends(permission("incident:read"))])


@router.post("/incidents/upload", status_code=201, response_model=UploadResponse)
async def upload_incident(video: UploadFile = File(...), log: UploadFile | None = File(default=None), sync_offset_s: float | None = Form(default=None), sync_metadata: UploadFile | None = File(default=None), principal: Principal = Depends(permission("incident:create"))):
    return await run_in_threadpool(create_incident, video, log, sync_offset_s=sync_offset_s, sync_metadata=sync_metadata, principal=principal)


@router.get("/incidents")
async def list_incidents_route(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    q: str = Query(default="", max_length=255),
    processing_status: Literal["UPLOADED", "READY", "PROCESSING", "COMPLETED", "FAILED"] | None = None,
    review_status: Literal["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"] | None = None,
):
    return await run_in_threadpool(list_incidents, limit, offset, q=q, processing_status=processing_status, review_status=review_status)


@router.get("/incidents/{incident_id}")
async def get_incident_route(incident_id: str):
    return await run_in_threadpool(get_incident, incident_id)
