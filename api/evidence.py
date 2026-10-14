from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from api.dependencies import permission
from backend.services.reports import get_evidence

router = APIRouter(tags=["evidence"], dependencies=[Depends(permission("incident:read"))])


@router.get("/incidents/{incident_id}/evidence")
async def get_evidence_route(incident_id: str):
    return await run_in_threadpool(get_evidence, incident_id)
