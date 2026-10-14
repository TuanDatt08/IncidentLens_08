from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.audit import router as audit_router
from api.auth import router as auth_router
from api.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    internal_error_handler,
    validation_error_handler,
)
from api.evidence import router as evidence_router
from api.incidents import router as incident_router
from api.jobs import router as job_router
from api.media import router as media_router
from api.reports import router as report_router
from api.uploads_v2 import router as uploads_v2_router
from api.users import router as user_router
from api.v2 import router as v2_router
from backend.config import get_settings


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
    docs_url=None if get_settings().app_env == "production" else "/docs",
    redoc_url=None if get_settings().app_env == "production" else "/redoc",
    openapi_url=None if get_settings().app_env == "production" else "/openapi.json",
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, internal_error_handler)

settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if settings.app_env != "production":
    cors_origins = list(dict.fromkeys([*cors_origins, "http://localhost:3000", "http://127.0.0.1:3000"]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incident_router, prefix="/api/v1")
app.include_router(job_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")


@app.middleware("http")
async def auth_cache_control(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/v1/auth", "/api/v1/admin/users")):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(v2_router)
app.include_router(uploads_v2_router)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/v1/health")
async def v1_health():
    return {"status": "ok"}
