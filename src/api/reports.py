from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.services.reports import get_report


router = APIRouter(tags=["reports"])


@router.get("/incidents/{incident_id}/report")
async def get_report_route(incident_id: str):
    return await run_in_threadpool(get_report, incident_id)
