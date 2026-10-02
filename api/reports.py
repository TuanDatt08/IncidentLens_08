from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from backend.models.contracts import AnalysisReportV1, RejectRequest, ReportPatch, ReviewActionResponse
from backend.services.reports import get_report
from backend.services.review import approve_report, edit_report, reject_report, submit_report

router = APIRouter(tags=["reports"])


@router.get("/incidents/{incident_id}/report", response_model=AnalysisReportV1)
async def get_report_route(incident_id: str):
    return await run_in_threadpool(get_report, incident_id)


@router.patch("/incidents/{incident_id}/report", response_model=AnalysisReportV1)
async def edit_report_route(incident_id: str, patch: ReportPatch):
    return await run_in_threadpool(edit_report, incident_id, patch)


@router.post("/incidents/{incident_id}/report/submit", response_model=ReviewActionResponse)
async def submit_report_route(incident_id: str):
    return await run_in_threadpool(submit_report, incident_id)


@router.post("/incidents/{incident_id}/report/approve", response_model=ReviewActionResponse)
async def approve_report_route(incident_id: str):
    return await run_in_threadpool(approve_report, incident_id)


@router.post("/incidents/{incident_id}/report/reject", response_model=ReviewActionResponse)
async def reject_report_route(incident_id: str, request: RejectRequest):
    return await run_in_threadpool(reject_report, incident_id, request)
