from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.services.reports import get_evidence


router = APIRouter(tags=["evidence"])


@router.get("/incidents/{incident_id}/evidence")
async def get_evidence_route(incident_id: str):
    return await run_in_threadpool(get_evidence, incident_id)
