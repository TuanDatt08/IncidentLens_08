from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from api.dependencies import permission
from backend.models.contracts import AnalysisReportV1, RejectRequest, ReportPatch, ReviewActionResponse
from backend.services.access import Principal
from backend.services.reports import get_report
from backend.services.review import approve_report, edit_report, reject_report, submit_report
from backend.services.review_context import get_review_context

router = APIRouter(tags=["reports"], dependencies=[Depends(permission("incident:read"))])


@router.get('/incidents/{incident_id}/review-context')
async def review_context_route(incident_id: str, principal: Principal = Depends(permission("incident:read"))):
    return await run_in_threadpool(get_review_context, incident_id, principal=principal)


@router.get("/incidents/{incident_id}/report", response_model=AnalysisReportV1)
async def get_report_route(incident_id: str):
    return await run_in_threadpool(get_report, incident_id)


@router.patch("/incidents/{incident_id}/report", response_model=AnalysisReportV1)
async def edit_report_route(incident_id: str, patch: ReportPatch, principal: Principal = Depends(permission("report:edit"))):
    return await run_in_threadpool(edit_report, incident_id, patch, principal=principal)


@router.post("/incidents/{incident_id}/report/submit", response_model=ReviewActionResponse)
async def submit_report_route(incident_id: str, principal: Principal = Depends(permission("report:submit"))):
    return await run_in_threadpool(submit_report, incident_id, principal=principal)


@router.post("/incidents/{incident_id}/report/approve", response_model=ReviewActionResponse)
async def approve_report_route(incident_id: str, principal: Principal = Depends(permission("report:approve"))):
    return await run_in_threadpool(approve_report, incident_id, principal=principal)


@router.post("/incidents/{incident_id}/report/reject", response_model=ReviewActionResponse)
async def reject_report_route(incident_id: str, request: RejectRequest, principal: Principal = Depends(permission("report:reject"))):
    return await run_in_threadpool(reject_report, incident_id, request, principal=principal)
