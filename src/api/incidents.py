from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from src.models.incident import ProcessingStatus, ReviewStatus
from src.schemas.incident import (
    AnalysisReport,
    AnalyzeResponse,
    AuditEventResponse,
    Evidence,
    IncidentRecordResponse,
    IncidentUploadResponse,
    JobResponse,
    RejectReportRequest,
    ReportPatch,
)
from src.services.errors import IncidentIngestionError
from src.services.incident_ingestion import get_ingestion_service
from src.services.workflow_repository import WorkflowRepository, incident_to_record

router = APIRouter(tags=["incidents"])


def get_workflow_repository() -> WorkflowRepository:
    return WorkflowRepository(_package_repository().root)


def _package_repository():
    return get_ingestion_service().repository


def _get_package(incident_id: str):
    package = _package_repository().get(incident_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Incident was not found.")
    return package


def _save_review_status(incident_id: str, status: ReviewStatus) -> None:
    package = _get_package(incident_id)
    package.review_status = status
    _package_repository().save(package)


def _job_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        status=job.status.value,
        **{"pass": job.pass_number},
        progress={"done": job.progress_done, "total": job.progress_total},
        updated_at=job.updated_at,
        result_uri=job.result_uri,
        error=job.error,
    )


@router.get("/incidents", response_model=list[IncidentRecordResponse])
async def list_incidents() -> list[IncidentRecordResponse]:
    packages = sorted(_package_repository().list(), key=lambda item: item.created_at, reverse=True)
    return [IncidentRecordResponse(**incident_to_record(package)) for package in packages]


@router.post("/incidents/upload", response_model=IncidentUploadResponse, status_code=201)
async def upload_incident(
    video: UploadFile = File(...),
    log: UploadFile | None = File(default=None),
) -> IncidentUploadResponse:
    """Validate and prepare an incident media package for later analysis."""
    try:
        package = await run_in_threadpool(get_ingestion_service().ingest, video, log)
    except IncidentIngestionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail()) from exc

    return IncidentUploadResponse(
        package_id=package.package_id,
        incident_id=package.package_id,
        status=package.status,
        processing_status=package.processing_status,
        review_status=package.review_status,
        sync_offset=package.sync_offset,
        frame_count=package.frame_count,
        video_metadata=package.video_metadata,
        warnings=package.warnings,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentRecordResponse)
async def get_incident(incident_id: str) -> IncidentRecordResponse:
    return IncidentRecordResponse(**incident_to_record(_get_package(incident_id)))


@router.post("/incidents/{incident_id}/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze_incident(incident_id: str) -> AnalyzeResponse:
    package = _get_package(incident_id)
    if package.processing_status == ProcessingStatus.FAILED:
        raise HTTPException(status_code=409, detail="A failed incident package must be uploaded again.")
    if package.processing_status == ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Incident analysis has already completed.")

    repository = get_workflow_repository()
    job = repository.create_job(incident_id)
    package.processing_status = ProcessingStatus.PROCESSING
    _package_repository().save(package)
    repository.add_audit(incident_id, "analysis_queued", metadata={"job_id": job.job_id})
    return AnalyzeResponse(job_id=job.job_id, status=job.status.value)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = get_workflow_repository().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job was not found.")
    return _job_response(job)


@router.get("/incidents/{incident_id}/report", response_model=AnalysisReport)
async def get_incident_report(incident_id: str) -> AnalysisReport:
    _get_package(incident_id)
    return AnalysisReport(**get_workflow_repository().get_report(incident_id))


@router.get("/incidents/{incident_id}/evidence", response_model=list[Evidence])
async def get_incident_evidence(incident_id: str) -> list[Evidence]:
    _get_package(incident_id)
    return [Evidence(**item) for item in get_workflow_repository().get_evidence(incident_id)]


@router.patch("/incidents/{incident_id}/report", response_model=AnalysisReport)
async def patch_incident_report(incident_id: str, patch: ReportPatch) -> AnalysisReport:
    _get_package(incident_id)
    repository = get_workflow_repository()
    report = repository.get_report(incident_id)
    review_status = ReviewStatus(report["review_status"])
    if review_status not in {ReviewStatus.DRAFT, ReviewStatus.REJECTED}:
        raise HTTPException(status_code=409, detail="Only draft or rejected reports can be edited.")
    report.update(patch.model_dump(exclude_none=True))
    report["updated_at"] = datetime.now(UTC).isoformat()
    return AnalysisReport(**repository.save_report(incident_id, report))


@router.post("/incidents/{incident_id}/report/submit", response_model=AnalysisReport)
async def submit_incident_report(incident_id: str) -> AnalysisReport:
    return _transition_report(incident_id, ReviewStatus.IN_REVIEW, {ReviewStatus.DRAFT, ReviewStatus.REJECTED})


@router.post("/incidents/{incident_id}/report/approve", response_model=AnalysisReport)
async def approve_incident_report(incident_id: str) -> AnalysisReport:
    return _transition_report(incident_id, ReviewStatus.APPROVED, {ReviewStatus.IN_REVIEW})


@router.post("/incidents/{incident_id}/report/reject", response_model=AnalysisReport)
async def reject_incident_report(incident_id: str, request: RejectReportRequest) -> AnalysisReport:
    _get_package(incident_id)
    repository = get_workflow_repository()
    report = repository.get_report(incident_id)
    if ReviewStatus(report["review_status"]) != ReviewStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="Only reports in review can be rejected.")
    report["review_status"] = ReviewStatus.REJECTED.value
    report["rejection_reason"] = request.reason
    report["updated_at"] = datetime.now(UTC).isoformat()
    saved = repository.save_report(incident_id, report)
    _save_review_status(incident_id, ReviewStatus.REJECTED)
    repository.add_audit(incident_id, "report_rejected", metadata={"reason": request.reason})
    return AnalysisReport(**saved)


def _transition_report(incident_id: str, target: ReviewStatus, allowed: set[ReviewStatus]) -> AnalysisReport:
    _get_package(incident_id)
    repository = get_workflow_repository()
    report = repository.get_report(incident_id)
    current = ReviewStatus(report["review_status"])
    if current not in allowed:
        raise HTTPException(status_code=409, detail=f"Invalid review transition from {current.value} to {target.value}.")
    report["review_status"] = target.value
    report["rejection_reason"] = None
    report["updated_at"] = datetime.now(UTC).isoformat()
    saved = repository.save_report(incident_id, report)
    _save_review_status(incident_id, target)
    repository.add_audit(incident_id, f"report_{target.value.lower()}")
    return AnalysisReport(**saved)


@router.get("/incidents/{incident_id}/audit", response_model=list[AuditEventResponse])
async def get_incident_audit(incident_id: str) -> list[AuditEventResponse]:
    _get_package(incident_id)
    return [AuditEventResponse(**item) for item in get_workflow_repository().get_audit(incident_id)]
