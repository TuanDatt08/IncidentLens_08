from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import ApiError, api_error_handler, http_error_handler, internal_error_handler, validation_error_handler
from src.api.incidents import router as incident_router
from src.api.jobs import router as job_router
from src.api.reports import router as report_router
from src.api.evidence import router as evidence_router
from src.api.audit import router as audit_router
from src.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")


app = FastAPI(
    title="RAV18 IncidentLens API",
    description="Incident ingestion, analysis jobs, reports, evidence, and audit",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, internal_error_handler)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incident_router, prefix="/api/v1")
app.include_router(job_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/v1/health")
async def v1_health():
    return {"status": "ok"}
