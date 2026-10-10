"""Run analysis outside HTTP requests. Tests inject a fake VLM adapter."""

from __future__ import annotations

import logging
import time
from threading import Event, Lock, Thread

import backend.services.jobs as jobs
from backend.config import get_settings
from backend.errors import ApiError
from backend.services.incidents import get_incident
from backend.services.jobs import claim_job, fail_job, heartbeat
from backend.services.processing import InsufficientEvidence, VLMAdapter, process_incident
from backend.services.qwen_local import create_local_provider
from backend.services.qwen_processing import process_local_incident
from backend.services.reports import complete_analysis

logger = logging.getLogger(__name__)


class LeaseHeartbeat:
    """Keep a worker lease fresh while a VLM call is blocking."""

    def __init__(self, job_id: str, attempt: int):
        self.job_id = job_id
        self.attempt = attempt
        self.state = (1, 0, 2)
        self.lock = Lock()
        self.stop = Event()
        self.thread = Thread(target=self._keep_alive, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.stop.set()
        self.thread.join(timeout=5)

    def update(self, pass_number: int, done: int, total: int | None) -> None:
        with self.lock:
            self.state = (pass_number, done, total)
        heartbeat(self.job_id, pass_number=pass_number, done=done, total=total, expected_attempt=self.attempt)

    def _keep_alive(self) -> None:
        interval = min(30.0, max(0.02, jobs.LEASE_SECONDS / 3))
        while not self.stop.wait(interval):
            with self.lock:
                pass_number, done, total = self.state
            try:
                heartbeat(self.job_id, pass_number=pass_number, done=done, total=total, expected_attempt=self.attempt)
            except ApiError as exc:
                if exc.code == "JOB_LEASE_LOST":
                    return
                logger.warning("Heartbeat failed for %s: %s", self.job_id, exc.code)
            except Exception:
                logger.exception("Heartbeat failed for %s", self.job_id)


def run_once(*, vlm: VLMAdapter | None = None, job_id: str | None = None) -> bool:
    claim = claim_job(job_id)
    if claim is None:
        return False
    try:
        with LeaseHeartbeat(claim.job_id, claim.attempt) as lease:
            lease.update(1, 0, 2)
            incident = get_incident(claim.incident_id)
            settings = get_settings()
            if vlm is None:
                result = process_local_incident(incident, storage_root=settings.incident_storage_dir, provider=create_local_provider(settings), settings=settings, on_progress=lease.update, job_id=claim.job_id)
            else:
                result = process_incident(incident, storage_root=settings.incident_storage_dir, vlm=vlm, on_progress=lease.update)
        complete_analysis(claim.job_id, result, expected_attempt=claim.attempt)
    except InsufficientEvidence as exc:
        _mark_failed(claim.job_id, claim.attempt, "INSUFFICIENT_EVIDENCE", str(exc))
    except Exception:
        logger.exception("Analysis job %s failed", claim.job_id)
        _mark_failed(claim.job_id, claim.attempt, "VLM_FAILED", "Analysis could not be completed.")
    return True


def _mark_failed(job_id: str, attempt: int, code: str, message: str) -> None:
    try:
        fail_job(job_id, code, message, expected_attempt=attempt)
    except ApiError as exc:
        if exc.code != "JOB_LEASE_LOST":
            raise


def run_forever() -> None:
    while True:
        if not run_once():
            time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
