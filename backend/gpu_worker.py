"""Single GPU consumer; missing source files and offline Qwen never consume jobs."""
import logging
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import and_, or_, select

from backend.config import get_settings
from backend.db import session_scope
from backend.models.tables import Incident, Job
from backend.services.qwen_local import ensure_ollama_runtime
from backend.worker import run_once

logger = logging.getLogger(__name__)


def next_local_job():
    root = Path(get_settings().incident_storage_dir).resolve()
    with session_scope() as session:
        rows = session.execute(select(Job.job_id, Incident.video_uri, Incident.telemetry_uri)
            .join(Incident, Job.incident_id == Incident.id)
            .where(or_(Job.status == 'queued', and_(Job.status == 'running', Job.lease_until < datetime.now(UTC))))
            .order_by(Job.created_at, Job.id)).all()
    for job_id, video, telemetry in rows:
        paths = [(root / uri).resolve() for uri in (video, telemetry) if uri]
        if paths and all(root in path.parents and path.is_file() for path in paths):
            return job_id
    return None


def main():
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.qwen_runtime != 'ollama' or settings.gpu_media_base_url:
        raise ValueError('GPU worker requires local Ollama and local media storage')
    logger.info('GPU worker started on host=%s', socket.gethostname())
    while True:
        try:
            ensure_ollama_runtime(settings)
            job_id = next_local_job()
            if job_id:
                logger.info('Processing %s on host=%s', job_id, socket.gethostname())
                run_once(job_id=job_id)
                continue
        except Exception:
            logger.exception('GPU worker preflight failed; retrying without claiming another job')
        time.sleep(settings.worker_poll_s)


if __name__ == '__main__':
    main()
