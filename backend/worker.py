"""Run analysis outside HTTP requests. Tests inject a fake VLM adapter."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from threading import Event, Lock, Thread

import backend.services.jobs as jobs
from backend.config import get_settings
from backend.errors import ApiError
from backend.services.incidents import get_incident
from backend.services.jobs import claim_job, fail_job, get_job, heartbeat
from backend.services.processing import InsufficientEvidence, VLMAdapter, process_incident
from backend.services.qwen_local import create_local_provider
from backend.services.qwen_processing import process_local_incident
from backend.services.reports import complete_analysis, get_evidence, get_model_metadata, get_report
from backend.services.video import VideoService

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
    output = None
    try:
        with LeaseHeartbeat(claim.job_id, claim.attempt) as lease:
            lease.update(1, 0, 2)
            incident = get_incident(claim.incident_id)
            settings = get_settings()
            if vlm is None and settings.qwen_runtime == "ollama" and settings.qwen_artifact_subdir == "output":
                output = Path(settings.incident_storage_dir).resolve() / claim.incident_id / "output"
                output.mkdir(parents=True, exist_ok=True)
                settings = settings.model_copy(update={"qwen_requests_dir": str(output / "requests"), "qwen_outputs_path": str(output / "outputs.txt")})
            if vlm is None:
                from backend.services.prompt_io import read_prompt
                has_log = bool(incident.get('telemetry_uri'))
                if output is not None:
                    from backend.services.pipeline_status import update_status
                    update_status(output, claim.job_id, 'backend', 'MP4 + CSV: tìm trigger từ log, trích clip/frame và gọi provider.' if has_log else 'Chỉ MP4: phát hiện và phân tích bằng Stage A/B.', pipeline='log_triggers' if has_log else 'video_stages')
                if settings.qwen_runtime == 'ollama' and not has_log:
                    from backend.services.prompt_pipeline import process_prompt_incident
                    result = process_prompt_incident(incident, storage_root=settings.incident_storage_dir, settings=settings, on_progress=lease.update, job_id=claim.job_id)
                else:
                    if has_log and '## STAGE A' in read_prompt(settings.qwen_prompt_path):
                        settings = settings.model_copy(update={'qwen_prompt_path': settings.qwen_log_prompt_path})
                    result = process_local_incident(incident, storage_root=settings.incident_storage_dir, provider=create_local_provider(settings), settings=settings, on_progress=lease.update, job_id=claim.job_id)
            else:
                result = process_incident(incident, storage_root=settings.incident_storage_dir, vlm=vlm, on_progress=lease.update)
        complete_analysis(claim.job_id, result, expected_attempt=claim.attempt)
        if output is not None:
            from backend.services.pipeline_status import update_status
            update_status(output, claim.job_id, 'complete', 'Draft và evidence đã lưu vào database; chờ kỹ sư review.')
        if output is not None:
            try:
                service = VideoService()
                service.write_json(output / "draft.json", get_report(claim.incident_id))
                service.write_json(output / "model-metadata.json", get_model_metadata(claim.incident_id))
                service.write_json(output / "evidence.json", get_evidence(claim.incident_id))
                service.write_json(output / "review.json", {"incident_id": claim.incident_id, "review_status": "DRAFT", "approved_by": None, "next_action": "Engineer reviews evidence, video, logs and unknowns before manual submit"})
            except OSError:
                logger.exception("Analysis %s saved to SQL; artifact export failed", claim.job_id)
    except InsufficientEvidence as exc:
        if output is not None:
            from backend.services.pipeline_status import update_status
            update_status(output, claim.job_id, 'error', str(exc), error_code='INSUFFICIENT_EVIDENCE')
        _mark_failed(claim.job_id, claim.attempt, "INSUFFICIENT_EVIDENCE", str(exc))
    except Exception as exc:
        logger.exception("Analysis job %s failed", claim.job_id)
        if output is not None:
            from backend.services.pipeline_status import update_status
            update_status(output, claim.job_id, 'error', str(exc)[:2000], error_code=type(exc).__name__)
        _mark_failed(claim.job_id, claim.attempt, "VLM_FAILED", "Analysis could not be completed.")
    finally:
        if output is not None:
            try:
                VideoService().write_json(output / "job.json", get_job(claim.job_id))
            except OSError:
                logger.exception("Cannot export job state for %s", claim.job_id)
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
