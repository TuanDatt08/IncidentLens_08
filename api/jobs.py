import hashlib
import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from api.dependencies import permission
from backend.config import get_settings
from backend.db import session_scope
from backend.models.contracts import AnalyzeAccepted, JobResponse
from backend.models.tables import Incident, Job
from backend.services.access import Principal
from backend.services.incidents import get_incident
from backend.services.jobs import create_job, get_job
from backend.services.pipeline_status import read_status

router = APIRouter(tags=["jobs"], dependencies=[Depends(permission("incident:read"))])


@router.post("/incidents/{incident_id}/analyze", status_code=202, response_model=AnalyzeAccepted)
async def analyze_incident(incident_id: str, principal: Principal = Depends(permission("analysis:create"))):
    return await run_in_threadpool(create_job, incident_id, principal=principal)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_route(job_id: str):
    return await run_in_threadpool(get_job, job_id)


@router.get('/incidents/{incident_id}/latest-job')
async def latest_incident_job(incident_id: str):
    def read():
        get_incident(incident_id)
        with session_scope() as session:
            latest = session.scalar(select(Job).join(Incident, Job.incident_id == Incident.id).where(Incident.incident_id == incident_id).order_by(Job.created_at.desc()).limit(1))
            return {'job_id': latest.job_id if latest else None, 'status': latest.status if latest else None}
    return await run_in_threadpool(read)


@router.get('/jobs/{job_id}/diagnostics')
async def get_job_diagnostics(job_id: str):
    def read():
        job = get_job(job_id)
        with session_scope() as session:
            incident_id = session.scalar(select(Incident.incident_id).join(Job, Job.incident_id == Incident.id).where(Job.job_id == job_id))
        state = read_status(Path(get_settings().incident_storage_dir) / incident_id / 'output', job_id)
        request_id = state.get('request_id', '')
        if re.fullmatch('[0-9a-f]{32}', request_id):
            request_file = Path(get_settings().incident_storage_dir) / incident_id / 'output' / 'requests' / f'{request_id}.request.json'
            try:
                payload = json.loads(request_file.read_text(encoding='utf-8'))
                system = '\n'.join(message['content'] for message in payload['messages'] if message['role'] == 'system' and isinstance(message['content'], str))
                if not system:
                    system = '\n'.join(item['text'] for message in payload['messages'] if message['role'] == 'user' and isinstance(message['content'], list) for item in message['content'] if item.get('type') == 'text')
                if system:
                    state['prompt_snapshot_sha256'] = state.get('prompt_sha256')
                    state['prompt_text'] = system
                    state['prompt_sha256'] = hashlib.sha256(system.encode()).hexdigest()
            except (OSError, ValueError, KeyError):
                state['diagnostics_warning'] = 'Không đọc được raw request; prompt đang hiển thị là snapshot worker.'
        if job['status'] == 'failed' and state['stage'] != 'error':
            state.update(stage='error', message=job['error']['message'], error_code=job['error']['code'])
        result = None
        if job['status'] == 'succeeded':
            from backend.services.reports import get_model_metadata
            result = get_model_metadata(incident_id).get('draft_v3')
        return {**state, 'job_status': job['status'], 'job_error': job['error'], 'result': result}
    return await run_in_threadpool(read)
