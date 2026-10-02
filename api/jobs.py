from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from backend.models.contracts import AnalyzeAccepted, JobResponse
from backend.services.jobs import create_job, get_job

router = APIRouter(tags=["jobs"])


@router.post("/incidents/{incident_id}/analyze", status_code=202, response_model=AnalyzeAccepted)
async def analyze_incident(incident_id: str):
    return await run_in_threadpool(create_job, incident_id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_route(job_id: str):
    return await run_in_threadpool(get_job, job_id)
