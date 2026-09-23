"""Run analysis outside HTTP requests. Tests inject a fake VLM adapter."""

from __future__ import annotations

import logging
import time
from threading import Event, Lock, Thread

from src.config import get_settings
from src.api.errors import ApiError
from src.services.incidents import get_incident
from src.services.jobs import claim_job, fail_job, heartbeat
import src.services.jobs as jobs
from src.services.processing import InsufficientEvidence, VLMAdapter, process_incident
from src.services.reports import complete_analysis
from src.services.vlm import OpenAIVLMAdapter


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


def run_once(*, vlm: VLMAdapter | None = None) -> bool:
    claim = claim_job()
    if claim is None:
        return False
    try:
        adapter = vlm if vlm is not None else OpenAIVLMAdapter()
        with LeaseHeartbeat(claim.job_id, claim.attempt) as lease:
            lease.update(1, 0, 2)
            incident = get_incident(claim.incident_id)
            result = process_incident(
                incident,
                storage_root=get_settings().incident_storage_dir,
                vlm=adapter,
                on_progress=lease.update,
            )
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
