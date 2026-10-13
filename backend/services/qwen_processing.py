"""Local evidence pipeline for the existing V1 single-report contract."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

from pydantic import ValidationError

from backend.config import Settings, get_settings
from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.models.contracts import AnalysisResult, EvidenceV1
from backend.services.candidate_detection import Candidate, DetectionConfig, detect_candidates
from backend.services.evidence_extraction import (
    EvidenceAsset,
    SamplingConfig,
    extract_candidate,
    file_hash,
    window_sample_times,
)
from backend.services.evidence_validation import EvidenceRegistry, validate_analysis
from backend.services.log_normalization import normalize_log
from backend.services.processing import InsufficientEvidence, ProcessedResult, pass1_sample_times
from backend.services.synchronization import TimeAnchor, align
from backend.services.telemetry_consistency import negative_telemetry_conflict
from backend.services.video import VideoService
from backend.services.vlm_provider import AnalysisContext, batch_registry, filtered_telemetry


class UnsupportedModelClaimError(ValueError):
    """A collision category without an observed visual claim cannot be persisted."""


def require_supported_collision(analysis: AIIncidentAnalysisV2) -> None:
    if analysis.incident_detected and analysis.event_type == "COLLISION" and not any(item.certainty == "OBSERVED" and item.source in {"VIDEO", "FUSED"} for item in analysis.timeline):
        raise UnsupportedModelClaimError("COLLISION requires an OBSERVED visual contact claim; UNKNOWN-only output remains unconfirmed and needs engineer review.")


def process_local_incident(incident: dict, *, storage_root: str | Path, provider, settings: Settings | None = None, on_progress=None, job_id: str | None = None) -> ProcessedResult:
    settings = settings or get_settings()
    root = Path(storage_root).resolve()
    def scoped(uri):
        path = (root / uri).resolve()
        if root not in path.parents or not path.is_file():
            raise InsufficientEvidence("Incident asset is unavailable or outside storage.")
        return path
    source = scoped(incident["video_uri"])
    metadata = incident["video_metadata"]
    duration = float(metadata["duration"])
    identity = incident["incident_id"]
    directory = root / identity
    if settings.qwen_artifact_subdir:
        if settings.qwen_artifact_subdir != "output":
            raise ValueError("Qwen artifact subdir must be output")
        directory = directory / "output"
    directory.mkdir(parents=True, exist_ok=True)
    service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin, max_output_bytes=2 * 1024**3, frame_max_width=640 if settings.qwen_runtime == "ollama" else None)
    log = alignment = None
    if incident.get("telemetry_uri"):
        log = normalize_log(scoped(incident["telemetry_uri"]))
        anchors = [TimeAnchor(**item) for item in metadata.get("anchors", [])]
        offset = metadata.get('log_offset_s', settings.qwen_v1_log_offset_s)
        if not anchors and offset is not None:
            # A configured offset is explicit provenance, never inferred from CSV names.
            anchors = [TimeAnchor(-offset, 0.0, "configured_v1_log_offset"), TimeAnchor(duration - offset, duration, "configured_v1_log_offset")]
        alignment = align(metadata, log, anchors)
    signal_thresholds = dict(settings.qwen_signal_thresholds)
    if settings.qwen_candidate_min_acceleration is not None:
        signal_thresholds.setdefault("acceleration", settings.qwen_candidate_min_acceleration)
    detection = detect_candidates(log, alignment, DetectionConfig(identity, duration, signal_thresholds=signal_thresholds, delta_thresholds=settings.qwen_delta_thresholds, fps=metadata.get('fps',24.), trigger_min_priority=settings.qwen_trigger_min_priority, trigger_deceleration=settings.qwen_trigger_deceleration))
    candidates = list(detection.candidates)
    unknowns = list(detection.unknowns)
    if detection.log_trigger_data is not None:
        service.write_json(directory / 'log-triggers.json', detection.log_trigger_data)
    service.write_json(directory / "candidates.json", {"candidates": [asdict(candidate) for candidate in candidates], "coverage": asdict(detection.coverage), "config_hash": detection.config_hash, "alignment": asdict(alignment) if alignment else {"quality": "UNKNOWN"}, "additional_acceleration_threshold": settings.qwen_candidate_min_acceleration, "unknowns": unknowns})
    if job_id and settings.qwen_artifact_subdir == 'output':
        from backend.services.pipeline_status import update_status
        update_status(directory, job_id, 'backend', f'Nhánh log: đã tìm {len(candidates)} candidate; chuẩn bị clip/frame.', alignment=asdict(alignment) if alignment else {'quality':'UNKNOWN'}, unknowns=unknowns)
    if log is not None and alignment.quality != 'VERIFIED':
        count = len(detection.log_trigger_data['triggers'])
        raise InsufficientEvidence(f'Đã tìm {count} trigger trên đồng hồ CSV; thiếu anchors/offset để ánh xạ sang video. Xem log-triggers.json; bổ sung đồng bộ trước khi gọi Qwen.')
    calls = 0
    extracted_frame_count = 0
    inspected_times = []
    submitted_times = []
    model_summaries = []
    consistency_checks = []
    def analyze(context):
        nonlocal calls
        if calls >= 200:
            raise InsufficientEvidence("Local analysis call budget exhausted; remaining coverage is unknown.")
        calls += 1
        if on_progress:
            on_progress(2, calls - 1, None)
        submitted_times.extend(frame.time_start_s for frame in context.frames)
        result = provider.analyze(context)
        validate_analysis(result.analysis, batch_registry(context), duration)
        require_supported_collision(result.analysis)
        inspected_times.extend(frame.time_start_s for frame in context.frames)
        model_summaries.append(result.analysis.summary)
        return result
    if not settings.qwen_flag_only and (detection.scan_times_s or not candidates):
        # Preserve V1's bounded visual localization when log alignment is unavailable.
        sampled = []
        for index, at_s in enumerate(pass1_sample_times(metadata)):
            frame = service.extract_frame(source, at_s, directory / "frames" / f"local-scan-{index}.jpg")
            sampled.append(EvidenceAsset(f"EVD-SCAN-{index}", identity, "scan", frame, file_hash(frame), at_s, at_s, "VIDEO", "image/jpeg", index))
        localized_times = set()
        extracted_frame_count += len(sampled)
        for start in range(0, len(sampled), settings.qwen_batch_frames):
            batch = tuple(sampled[start:start + settings.qwen_batch_frames])
            context = AnalysisContext(EvidenceRegistry(identity, "scan", batch), duration, batch, job_id=job_id, candidate_window=(0.0, 0.0, duration))
            localized = analyze(context).analysis
            unknowns.extend(localized.unknowns)
            if localized.incident_detected:
                localized_times.add(localized.window.critical_s)
        unknowns.append("Visual localization inspected five sparse timestamps; events between them remain unknown.")
        for at_s in sorted(localized_times):
            candidate = Candidate(f"visual-local-{at_s:.6f}", max(0.0, at_s - 5), at_s, min(duration, at_s + 3), ("VISUAL_CANDIDATE",), "PENDING")
            if candidates and candidate.start_s <= candidates[-1].end_s:
                candidates[-1] = replace(candidates[-1], end_s=max(candidates[-1].end_s, candidate.end_s))
            else:
                candidates.append(candidate)
    records = []
    evidence_assets = []
    results = []
    for candidate in candidates:
        if candidate.analysis_state == "UNANALYZED":
            unknowns.append(f"{candidate.candidate_id}: UNANALYZED")
            continue
        try:
            times = window_sample_times(candidate, metadata, settings.qwen_sampling_fps)
        except ValueError as exc:
            if "extraction budget" not in str(exc):
                raise
            unknowns.append(f"{candidate.candidate_id}: frame budget exhausted; UNANALYZED")
            continue
        bundle = extract_candidate(source, candidate, SamplingConfig(times, 256), recording_id=identity, output_root=directory / "local-evidence", metadata=metadata, video_service=service)
        extracted_frame_count += len(bundle.frames)
        rows = []
        assets = [bundle.clip, *bundle.frames]
        if log is not None and alignment.quality == "VERIFIED":
            for row in log.iter_rows():
                at_s = alignment.to_video_seconds(row["time_s"])
                if candidate.start_s <= at_s <= candidate.end_s:
                    selected = {"time_s": at_s}
                    for key in ("speed", "brake", "acceleration", "jerk", "collision_intensity"):
                        if key in row:
                            selected[key] = float(row[key])
                    if "mode" in row:
                        selected["mode"] = row["mode"]
                    rows.append(selected)
                    if len(rows) > 1000:
                        raise InsufficientEvidence("Candidate telemetry exceeds context budget.")
            if rows:
                path = bundle.manifest_path.parent / "telemetry.json"
                service.write_json(path, filtered_telemetry(tuple(rows)))
                assets.append(EvidenceAsset("EVD-" + file_hash(path)[:24], identity, candidate.candidate_id, path, file_hash(path), rows[0]["time_s"], rows[-1]["time_s"], "TELEMETRY", "application/json"))
        registry = EvidenceRegistry(identity, candidate.candidate_id, tuple(assets))
        inference_frames = bundle.frames
        limit = settings.qwen_inference_frame_limit
        if limit and len(inference_frames) > limit:
            indices = sorted({round(i * (len(inference_frames) - 1) / (limit - 1)) for i in range(limit)})
            critical_index = min(range(len(inference_frames)), key=lambda index: abs(inference_frames[index].time_start_s - candidate.critical_s))
            if critical_index not in indices:
                replaceable = indices[1:-1] or indices
                indices.remove(min(replaceable, key=lambda index: abs(index - critical_index)))
                indices = sorted([*indices, critical_index])
            inference_frames = tuple(inference_frames[index] for index in indices)
            unknowns.append(f"{candidate.candidate_id}: extracted {len(bundle.frames)} frames at {settings.qwen_sampling_fps} FPS; model inspected {len(inference_frames)} selected frames including the nearest critical timestamp. Events between inspected frames remain unknown.")
        batch_size = len(inference_frames) if getattr(provider, 'two_stage', False) else settings.qwen_batch_frames
        for start in range(0, len(inference_frames), batch_size):
            context = AnalysisContext(registry, duration, inference_frames[start:start + batch_size], tuple(rows), job_id, candidate.flags, (candidate.start_s, candidate.critical_s, candidate.end_s))
            try:
                result = analyze(context)
            except (ValidationError, UnsupportedModelClaimError) as exc:
                # Keep independent batches useful without treating malformed output as absence.
                code = "UNSUPPORTED_MODEL_CLAIM" if isinstance(exc, UnsupportedModelClaimError) else "INVALID_MODEL_OUTPUT"
                records.append({"candidate": asdict(candidate), "frame_times_s": [frame.time_start_s for frame in context.frames], "error": {"code": code, "message": str(exc)}})
                unknowns.append(f"{candidate.candidate_id}: {code} for frame times {[frame.time_start_s for frame in context.frames]}; this batch remains unknown. See raw request/response journal.")
                continue
            if result.analysis.window and not candidate.start_s <= result.analysis.window.start_s < result.analysis.window.end_s <= candidate.end_s:
                raise InsufficientEvidence("Local report window is outside candidate.")
            records.append({"candidate": asdict(candidate), "frame_times_s": [frame.time_start_s for frame in context.frames], "analysis": result.analysis.model_dump(mode="json"), "provenance": result.provenance, "usage": result.usage})
            conflict = negative_telemetry_conflict(rows, context.frames[0].time_start_s, context.frames[-1].time_start_s, result.analysis.incident_detected)
            if conflict:
                records[-1]['consistency_check'] = conflict
                consistency_checks.append(conflict)
                unknowns.append(conflict['code'] + ': ' + conflict['message'])
            unknowns.extend(result.analysis.unknowns)
            if result.analysis.incident_detected:
                results.append(result.analysis)
        evidence_assets.extend(assets)
    unknowns.append("Visual analysis covers only supplied candidate frames, not every source video frame. Events outside candidate windows or between inspected frames remain unknown.")
    if consistency_checks:
        model_summaries.insert(0, consistency_checks[0]['message'])
    service.write_json(directory / "local-analysis.json", {"coverage": asdict(detection.coverage), "visual_coverage": {"complete": False, "source_duration_s": duration, "candidate_windows": [[candidate.start_s, candidate.end_s] for candidate in candidates], "extracted_frame_count": extracted_frame_count, "model_frame_times_s": sorted(set(submitted_times)), "model_frame_count": len(set(submitted_times)), "validated_model_frame_times_s": sorted(set(inspected_times)), "validated_model_frame_count": len(set(inspected_times))}, "alignment": asdict(alignment) if alignment else {"quality": "UNKNOWN"}, "unknowns": list(dict.fromkeys(unknowns)), "calls": calls, "results": records})
    if on_progress:
        on_progress(2, calls, calls)
    if calls and not inspected_times:
        raise InsufficientEvidence("No valid model batch was analyzed; inspect local-analysis.json and raw responses.")
    if inspected_times:
        # V1 intentionally empties negative reports; preserve the complete V2 draft separately.
        model_draft = AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": bool(results), "event_type": results[0].event_type if results else "UNKNOWN", "time_basis": "video_seconds", "window": {"start_s": min(result.window.start_s for result in results), "critical_s": results[0].window.critical_s, "end_s": max(result.window.end_s for result in results)} if results else None, "summary": "\n".join(result.summary for result in results) if results else "\n".join(model_summaries), "timeline": [item.model_dump() for result in results for item in result.timeline], "factors": [item.model_dump() for result in results for item in result.factors], "unknowns": list(dict.fromkeys(unknowns)), "review_status": "DRAFT"}, context={"video_duration_s": duration})
        service.write_json(directory / "draft-v2.json", model_draft.model_dump(mode="json"))
    if not results:
        if calls == 0:
            if settings.qwen_flag_only and not candidates:
                return ProcessedResult(AnalysisResult(incident_detected=False, model_metadata={'detection_state': 'NOT_ANALYZED_NO_FLAGS', 'requires_engineer_review': True, 'unknowns': ['No qualifying telemetry flags; video was not analyzed.']}), [], None)
            raise InsufficientEvidence("No candidate was analyzed; inspect local-analysis.json for missing coverage.")
        # V1 requires an empty no-detection report; retain unknowns in the private manifest.
        return ProcessedResult(AnalysisResult(incident_detected=False, model_metadata={"provider": settings.qwen_runtime, "model": settings.qwen_ollama_model if settings.qwen_runtime == "ollama" else settings.qwen_model_file, "manifest": (directory.relative_to(root) / "local-analysis.json").as_posix(), "detection_state": "REVIEW_REQUIRED_TELEMETRY_CONFLICT" if consistency_checks else "NO_DETECTION_IN_SAMPLED_EVIDENCE", "consistency_checks": consistency_checks, "requires_engineer_review": True, "draft_v2": model_draft.model_dump(mode="json"), "unknowns": list(dict.fromkeys(unknowns))}), [], None)
    offset = results[0].window.critical_s
    timeline = [{**item.model_dump(mode="json"), "time_s": item.time_s - offset} for result in results for item in result.timeline]
    analysis = AnalysisResult(incident_detected=True, incident_type=results[0].event_type, incident_window={"start": min(result.window.start_s for result in results) - offset, "critical": 0.0, "end": max(result.window.end_s for result in results) - offset}, summary="\n".join(result.summary for result in results), timeline=sorted(timeline, key=lambda item: item["time_s"]), key_factors=[item.model_dump(mode="json") for result in results for item in result.factors], unknowns=list(dict.fromkeys(unknowns)), model_metadata={"provider": settings.qwen_runtime, "model": settings.qwen_ollama_model if settings.qwen_runtime == "ollama" else settings.qwen_model_file, "manifest": (directory.relative_to(root) / "local-analysis.json").as_posix(), "time_basis": "incident_relative", "video_offset_s": offset, "requires_engineer_review": True, "draft_v2": model_draft.model_dump(mode="json")})
    evidence = [EvidenceV1(evidence_id=asset.evidence_id, kind="telemetry" if asset.source == "TELEMETRY" else "frame" if asset.frame_order is not None else "video", uri=asset.path.relative_to(root).as_posix(), sha256=asset.sha256, time_range_s=(asset.time_start_s - offset, asset.time_end_s - offset), bytes=asset.path.stat().st_size, media_type=asset.media_type) for asset in evidence_assets]
    return ProcessedResult(analysis, evidence, offset)
