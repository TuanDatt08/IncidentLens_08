"""Run analysis outside HTTP requests. Tests inject a fake VLM adapter."""

from __future__ import annotations

import logging
import time

from src.config import get_settings
from src.api.errors import ApiError
from src.services.incidents import get_incident
from src.services.jobs import claim_job, fail_job, heartbeat
from src.services.processing import InsufficientEvidence, VLMAdapter, process_incident
from src.services.reports import complete_analysis
from src.services.vlm import OpenAIVLMAdapter


logger = logging.getLogger(__name__)


def run_once(*, vlm: VLMAdapter | None = None) -> bool:
    claim = claim_job()
    if claim is None:
        return False
    try:
        adapter = vlm if vlm is not None else OpenAIVLMAdapter()
        heartbeat(claim.job_id, pass_number=1, done=0, total=2, expected_attempt=claim.attempt)
        incident = get_incident(claim.incident_id)
        result = process_incident(
            incident,
            storage_root=get_settings().incident_storage_dir,
            vlm=adapter,
            on_progress=lambda pass_number, done, total: heartbeat(claim.job_id, pass_number=pass_number, done=done, total=total, expected_attempt=claim.attempt),
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
