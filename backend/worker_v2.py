"""Recording worker with durable discovery and per-candidate atomic publication."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from pathlib import Path
from threading import Event, Thread

from sqlalchemy import select

from backend.config import get_settings
from backend.db import session_scope
from backend.errors import ApiError
from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.models.tables_v2 import CandidateV2, JobV2, RecordingV2
from backend.services import jobs_v2
from backend.services.candidate_detection import Candidate, DetectionConfig, detect_candidates
from backend.services.evidence_extraction import (
    EvidenceAsset,
    SamplingConfig,
    extract_candidate,
    file_hash,
    window_sample_times,
)
from backend.services.evidence_validation import EvidenceRegistry, validate_analysis
from backend.services.identity import Principal, authorize
from backend.services.log_normalization import LogNormalizationConfig, normalize_log
from backend.services.qwen_local import create_local_provider
from backend.services.reports_v2 import create_report
from backend.services.synchronization import TimeAnchor, align
from backend.services.video import VideoService
from backend.services.vlm_provider import (
    AnalysisContext,
    ProviderResult,
    VLMProvider,
    batch_registry,
    batch_signature,
    filtered_telemetry,
)

logger = logging.getLogger(__name__)


def combine_batch_results(results: list[ProviderResult]) -> ProviderResult:
    detected = [result.analysis for result in results if result.analysis.incident_detected]
    data = results[0].analysis.model_dump(mode="json")
    if detected:
        data = detected[0].model_dump(mode="json")
        data["window"] = {"start_s": min(item.window.start_s for item in detected), "critical_s": detected[0].window.critical_s, "end_s": max(item.window.end_s for item in detected)}
        if len({item.event_type for item in detected}) > 1:
            data["event_type"] = "OTHER"
        data["timeline"] = sorted([entry.model_dump(mode="json") for item in detected for entry in item.timeline], key=lambda entry: entry["time_s"])
        data["factors"] = [entry.model_dump(mode="json") for item in detected for entry in item.factors]
    data["summary"] = "\n".join(result.analysis.summary for result in results)
    data["unknowns"] = list(dict.fromkeys(note for result in results for note in result.analysis.unknowns))
    if len(results) == 1:
        return results[0]
    return ProviderResult(AIIncidentAnalysisV2.model_validate(data), {**results[0].provenance, "batches": [result.provenance for result in results]}, {"attempts": sum(result.usage.get("attempts", 1) for result in results), "batches": [result.usage for result in results]})


def resume_failed(job_id: str, actor: Principal) -> dict:
    with session_scope() as session:
        job = session.scalar(select(JobV2).where(JobV2.job_id == job_id).with_for_update())
        if job is None:
            raise ApiError("NOT_FOUND", "Job not found.", 404)
        authorize(actor, job.recording_id, "Engineer")
        if job.status != "failed" or job.attempt >= job.budget["max_attempts"]:
            raise ApiError("JOB_NOT_RESUMABLE", "Failed job has no remaining attempts.", 409)
        active = session.scalar(select(JobV2).where(JobV2.recording_id == job.recording_id, JobV2.status.in_(["queued", "running"])))
        if active is not None:
            raise ApiError("ANALYSIS_ALREADY_RUNNING", "Another job is active.", 409)
        job.status, job.error_code = "queued", None
        return jobs_v2.job_envelope(job)


def scoped_path(root: Path, uri: str) -> Path:
    path = (root / uri).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("recording asset is unavailable or outside storage")
    return path


def disk_used(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) if root.exists() else 0


def run_once(*, provider: VLMProvider | None = None, job_id: str | None = None, scanner=None, privacy=None) -> bool:
    claim = jobs_v2.claim_job(job_id)
    if claim is None:
        return False
    stop = Event()
    def renew():
        while not stop.wait(jobs_v2.LEASE_SECONDS / 3):
            try:
                jobs_v2.heartbeat(claim.job_id, claim.attempt)
            except Exception:
                return
    renewal = Thread(target=renew, daemon=True)
    renewal.start()
    try:
        settings = get_settings()
        root = Path(settings.incident_storage_dir).resolve()
        job_output = root / "processed-v2" / claim.job_id
        output = job_output / f"attempt-{claim.attempt}"
        def guard():
            jobs_v2.heartbeat(claim.job_id, claim.attempt)
        def remaining():
            guard()
            available = claim.budget["max_disk_bytes"] - disk_used(job_output)
            if available <= 0:
                raise ApiError("DISK_BUDGET_EXHAUSTED", "Evidence disk budget exhausted.", 429)
            return available
        with session_scope() as session:
            recording = session.get(RecordingV2, claim.recording_id)
            metadata = dict(recording.metadata_json)
            duration = recording.duration_s
            video_uri = recording.video_uri
        source = scoped_path(root, video_uri)
        jobs_v2.set_stage(claim.job_id, claim.attempt, "VALIDATION")
        service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin, output_guard=remaining)
        log = None
        alignment = None
        if metadata.get("telemetry_uri"):
            jobs_v2.set_stage(claim.job_id, claim.attempt, "SYNCHRONIZATION")
            log_path = scoped_path(root, metadata["telemetry_uri"])
            expected_hash = metadata.get("telemetry_provenance", {}).get("sha256")
            if expected_hash and file_hash(log_path) != expected_hash:
                raise ApiError("LOG_HASH_MISMATCH", "Stored telemetry changed after validation.", 422)
            log = normalize_log(log_path, config=LogNormalizationConfig(**metadata.get("log_config", {})), guard=guard)
            alignment = align({"duration": duration}, log, [TimeAnchor(**point) for point in metadata.get("anchors", [])])
        detection_config = DetectionConfig(claim.recording_id, duration, max_candidates=claim.budget["max_calls"], max_scan_frames=claim.budget["max_scan_frames"], signal_thresholds=settings.qwen_signal_thresholds, delta_thresholds=settings.qwen_delta_thresholds)
        if "discovery" in claim.checkpoints and not claim.checkpoints["discovery"].get("scan_pending"):
            discovery = claim.checkpoints["discovery"]
            candidates = [Candidate(**{**item, "reasons": tuple(item["reasons"]), "flags": tuple(item.get("flags", ()))}) for item in discovery["candidates"]]
            coverage = discovery["coverage"]
        else:
            jobs_v2.set_stage(claim.job_id, claim.attempt, "DETECTION")
            def scan(at_s):
                service.prepare_output()
                frame = service.extract_frame(source, at_s, output / "scan" / f"{at_s:.6f}.jpg")
                if disk_used(job_output) > claim.budget["max_disk_bytes"]:
                    raise ApiError("DISK_BUDGET_EXHAUSTED", "Evidence disk budget exhausted.", 429)
                guard()
                return scanner(frame, at_s)
            discovered = detect_candidates(log, alignment, detection_config, scan=scan if scanner is not None else None, guard=guard)
            candidates = list(discovered.candidates)
            coverage = {**asdict(discovered.coverage), "unknowns": list(discovered.unknowns)}
            scan_pending = bool(discovered.scan_times_s and scanner is None)
            discovery = {"candidates": [asdict(item) for item in candidates], "coverage": coverage, "config_hash": discovered.config_hash, "scan_pending": scan_pending}
            with session_scope() as session:
                jobs_v2.owned_job(session, claim.job_id, claim.attempt)
                for item in candidates:
                    existing = session.get(CandidateV2, item.candidate_id)
                    if existing is None:
                        session.add(CandidateV2(candidate_id=item.candidate_id, recording_id=claim.recording_id, window={"start_s": item.start_s, "critical_s": item.critical_s, "end_s": item.end_s}, reasons=list(item.reasons), analysis_state=item.analysis_state))
                jobs_v2.checkpoint(claim.job_id, claim.attempt, "discovery", stage="DETECTION", coverage=coverage, result=discovery, session=session)
            if scan_pending:
                raise ApiError("SPARSE_SCANNER_NOT_CONFIGURED", "Sparse discovery requires a reviewed internal scanner.", 503)
        for candidate in candidates:
            if candidate.candidate_id in claim.checkpoints or candidate.analysis_state == "UNANALYZED":
                continue
            jobs_v2.heartbeat(claim.job_id, claim.attempt)
            if disk_used(job_output) >= claim.budget["max_disk_bytes"]:
                raise ApiError("DISK_BUDGET_EXHAUSTED", "Evidence disk budget exhausted.", 429)
            try:
                times = window_sample_times(candidate, metadata, settings.qwen_sampling_fps)
            except ValueError as exc:
                if "extraction budget" not in str(exc):
                    raise
                coverage["unknowns"].append(f"{candidate.candidate_id}: frame budget exceeded; UNANALYZED")
                with session_scope() as session:
                    jobs_v2.owned_job(session, claim.job_id, claim.attempt)
                    session.get(CandidateV2, candidate.candidate_id).analysis_state = "UNANALYZED"
                    jobs_v2.checkpoint(claim.job_id, claim.attempt, candidate.candidate_id, stage="EXTRACTION", coverage=coverage, result={"candidate_id": candidate.candidate_id, "analysis_state": "UNANALYZED"}, session=session)
                continue
            jobs_v2.set_stage(claim.job_id, claim.attempt, "EXTRACTION")
            bundle = extract_candidate(source, candidate, SamplingConfig(times, max_frames=256), recording_id=claim.recording_id, output_root=output, metadata=metadata, video_service=service)
            if disk_used(job_output) > claim.budget["max_disk_bytes"]:
                raise ApiError("DISK_BUDGET_EXHAUSTED", "Evidence disk budget exhausted.", 429)
            frames = bundle.frames
            if privacy is not None:
                jobs_v2.set_stage(claim.job_id, claim.attempt, "PRIVACY")
                # Reviewed adapters must write through the guarded service in this attempt namespace.
                frames = tuple(privacy(frame, service=service, output_root=output / "privacy") for frame in frames)
                remaining()
            telemetry_rows = []
            assets = [bundle.clip, *frames]
            if log is not None and alignment.quality == "VERIFIED":
                # ponytail: sequential reread per candidate; add a time index if measured large-log latency requires it.
                for row_index, row in enumerate(log.iter_rows()):
                    if row_index % 1000 == 0:
                        guard()
                    at_s = alignment.to_video_seconds(row["time_s"])
                    if candidate.start_s <= at_s <= candidate.end_s:
                        selected = {"time_s": at_s}
                        for key in ("speed", "brake", "acceleration", "jerk", "collision_intensity"):
                            if key in row:
                                selected[key] = float(row[key])
                        if "mode" in row:
                            selected["mode"] = row["mode"]
                        telemetry_rows.append(selected)
                        if len(telemetry_rows) > 1000:
                            raise ApiError("TELEMETRY_BUDGET_EXHAUSTED", "Candidate telemetry exceeds context budget.", 429)
                if telemetry_rows:
                    sanitized = filtered_telemetry(tuple(telemetry_rows))
                    path = bundle.manifest_path.parent / "telemetry.json"
                    service.write_json(path, sanitized)
                    assets.append(EvidenceAsset("EVD-" + file_hash(path)[:24], claim.recording_id, candidate.candidate_id, path, file_hash(path), sanitized[0]["time_s"], sanitized[-1]["time_s"], "TELEMETRY", "application/json"))
            registry = EvidenceRegistry(claim.recording_id, candidate.candidate_id, tuple(assets))
            if provider is None:
                provider = create_local_provider(settings)
            batch_size = min(settings.qwen_batch_frames, getattr(getattr(provider, "config", None), "max_frames", 32))
            results = []
            for start in range(0, len(frames), batch_size):
                batch_key = f"{candidate.candidate_id}:batch:{start}"
                batch = frames[start:start + batch_size]
                context = AnalysisContext(registry, duration, batch, tuple(telemetry_rows), claim.job_id, candidate.flags, (candidate.start_s, candidate.critical_s, candidate.end_s))
                signature = batch_signature(context, getattr(provider, "config", None))
                saved = claim.checkpoints.get(batch_key)
                if saved and saved.get("input_signature") == signature:
                    batch_result = ProviderResult(AIIncidentAnalysisV2.model_validate(saved["analysis"]), saved["provenance"], saved["usage"])
                else:
                    for _ in range(getattr(getattr(provider, "config", None), "max_attempts", 1)):
                        jobs_v2.reserve_call(claim.job_id, claim.attempt)
                    jobs_v2.set_stage(claim.job_id, claim.attempt, "ANALYSIS")
                    batch_result = provider.analyze(context)
                    validate_analysis(batch_result.analysis, batch_registry(context), duration)
                    if batch_result.analysis.window is not None and not candidate.start_s <= batch_result.analysis.window.start_s < batch_result.analysis.window.end_s <= candidate.end_s:
                        raise ValueError("provider report window must fit candidate window")
                    jobs_v2.checkpoint(claim.job_id, claim.attempt, batch_key, stage="ANALYSIS", coverage=coverage, result={"candidate_id": candidate.candidate_id, "input_signature": signature, "analysis": batch_result.analysis.model_dump(mode="json"), "provenance": batch_result.provenance, "usage": batch_result.usage})
                results.append(batch_result)
            result = combine_batch_results(results)
            jobs_v2.set_stage(claim.job_id, claim.attempt, "EVIDENCE_VALIDATION")
            validated = validate_analysis(result.analysis, registry, duration)
            if validated.window is not None and not candidate.start_s <= validated.window.start_s < validated.window.end_s <= candidate.end_s:
                raise ValueError("provider report window must fit candidate window")
            with session_scope() as session:
                jobs_v2.owned_job(session, claim.job_id, claim.attempt)
                partial = {"candidate_id": candidate.candidate_id, "usage": result.usage}
                if result.analysis.incident_detected:
                    report = create_report(result.analysis, registry, duration_s=duration, provenance={**result.provenance, "usage": result.usage, "detection_config_hash": discovery["config_hash"], "alignment": asdict(alignment) if alignment else {"quality": "UNKNOWN"}}, session=session)
                    partial["report_id"] = report["report_id"]
                candidate_row = session.get(CandidateV2, candidate.candidate_id)
                candidate_row.analysis_state = "ANALYZED" if result.analysis.incident_detected else "NO_DETECTION"
                jobs_v2.checkpoint(claim.job_id, claim.attempt, candidate.candidate_id, stage="ANALYSIS", coverage=coverage, result=partial, session=session)
        jobs_v2.finish(claim.job_id, claim.attempt)
    except Exception as exc:
        logger.exception("Local Qwen job %s failed", claim.job_id)
        try:
            jobs_v2.finish(claim.job_id, claim.attempt, error_code=exc.code if isinstance(exc, ApiError) else "PROCESSING_FAILED")
        except ApiError:
            pass  # Cancelled/stale attempts cannot publish failure or overwrite newer state.
    finally:
        stop.set()
        renewal.join(timeout=5)
    return True


if __name__ == "__main__":
    while True:
        if not run_once():
            time.sleep(2)
