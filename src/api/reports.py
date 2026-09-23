from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.models.contracts import AnalysisReportV1
from src.services.reports import get_report


router = APIRouter(tags=["reports"])


@router.get("/incidents/{incident_id}/report", response_model=AnalysisReportV1)
async def get_report_route(incident_id: str):
    return await run_in_threadpool(get_report, incident_id)
