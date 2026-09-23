from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.services.audit import get_audit


router = APIRouter(tags=["audit"])


@router.get("/incidents/{incident_id}/audit")
async def get_audit_route(incident_id: str):
    return await run_in_threadpool(get_audit, incident_id)
