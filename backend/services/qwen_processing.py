"""Local evidence pipeline for the existing V1 single-report contract."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

from backend.config import Settings, get_settings
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
from backend.services.video import VideoService
from backend.services.vlm_provider import AnalysisContext, batch_registry, filtered_telemetry


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
    service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin, max_output_bytes=2 * 1024**3)
    log = alignment = None
    if incident.get("telemetry_uri"):
        log = normalize_log(scoped(incident["telemetry_uri"]))
        anchors = [TimeAnchor(**item) for item in metadata.get("anchors", [])]
        offset = settings.qwen_v1_log_offset_s
        if not anchors and offset is not None:
            # A configured offset is explicit provenance, never inferred from CSV names.
            anchors = [TimeAnchor(-offset, 0.0, "configured_v1_log_offset"), TimeAnchor(duration - offset, duration, "configured_v1_log_offset")]
        alignment = align(metadata, log, anchors)
    detection = detect_candidates(log, alignment, DetectionConfig(identity, duration, signal_thresholds=settings.qwen_signal_thresholds, delta_thresholds=settings.qwen_delta_thresholds))
    candidates = list(detection.candidates)
    unknowns = list(detection.unknowns)
    calls = 0
    def analyze(context):
        nonlocal calls
        if calls >= 200:
            raise InsufficientEvidence("Local analysis call budget exhausted; remaining coverage is unknown.")
        calls += 1
        if on_progress:
            on_progress(2, calls - 1, None)
        result = provider.analyze(context)
        validate_analysis(result.analysis, batch_registry(context), duration)
        return result
    if detection.scan_times_s or not candidates:
        # Preserve V1's bounded visual localization when log alignment is unavailable.
        sampled = []
        for index, at_s in enumerate(pass1_sample_times(metadata)):
            frame = service.extract_frame(source, at_s, directory / "frames" / f"local-scan-{index}.jpg")
            sampled.append(EvidenceAsset(f"EVD-SCAN-{index}", identity, "scan", frame, file_hash(frame), at_s, at_s, "VIDEO", "image/jpeg", index))
        localized_times = set()
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
        for start in range(0, len(bundle.frames), settings.qwen_batch_frames):
            context = AnalysisContext(registry, duration, bundle.frames[start:start + settings.qwen_batch_frames], tuple(rows), job_id, candidate.flags, (candidate.start_s, candidate.critical_s, candidate.end_s))
            result = analyze(context)
            if result.analysis.window and not candidate.start_s <= result.analysis.window.start_s < result.analysis.window.end_s <= candidate.end_s:
                raise InsufficientEvidence("Local report window is outside candidate.")
            records.append({"candidate": asdict(candidate), "analysis": result.analysis.model_dump(mode="json"), "provenance": result.provenance, "usage": result.usage})
            unknowns.extend(result.analysis.unknowns)
            if result.analysis.incident_detected:
                results.append(result.analysis)
        evidence_assets.extend(assets)
    service.write_json(directory / "local-analysis.json", {"coverage": asdict(detection.coverage), "alignment": asdict(alignment) if alignment else {"quality": "UNKNOWN"}, "unknowns": list(dict.fromkeys(unknowns)), "calls": calls, "results": records})
    if on_progress:
        on_progress(2, calls, calls)
    if not results:
        if calls == 0:
            raise InsufficientEvidence("No candidate was analyzed; inspect local-analysis.json for missing coverage.")
        # V1 requires an empty no-detection report; retain unknowns in the private manifest.
        return ProcessedResult(AnalysisResult(incident_detected=False), [], None)
    offset = results[0].window.critical_s
    timeline = [{**item.model_dump(mode="json"), "time_s": item.time_s - offset} for result in results for item in result.timeline]
    analysis = AnalysisResult(incident_detected=True, incident_type=results[0].event_type, incident_window={"start": min(result.window.start_s for result in results) - offset, "critical": 0.0, "end": max(result.window.end_s for result in results) - offset}, summary="\n".join(result.summary for result in results), timeline=sorted(timeline, key=lambda item: item["time_s"]), key_factors=[item.model_dump(mode="json") for result in results for item in result.factors], unknowns=list(dict.fromkeys(unknowns)), model_metadata={"provider": "qwen_local", "manifest": f"{identity}/local-analysis.json", "time_basis": "incident_relative", "video_offset_s": offset})
    evidence = [EvidenceV1(evidence_id=asset.evidence_id, kind="telemetry" if asset.source == "TELEMETRY" else "frame" if asset.frame_order is not None else "video", uri=asset.path.relative_to(root).as_posix(), sha256=asset.sha256, time_range_s=(asset.time_start_s - offset, asset.time_end_s - offset), bytes=asset.path.stat().st_size, media_type=asset.media_type) for asset in evidence_assets]
    return ProcessedResult(analysis, evidence, offset)
