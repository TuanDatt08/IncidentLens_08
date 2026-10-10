"""Run the local provider on paired CARLA samples, with explicit clock assumptions."""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict
from pathlib import Path

from backend.config import get_settings
from backend.services.candidate_detection import DetectionConfig, detect_candidates
from backend.services.evidence_extraction import (
    EvidenceAsset,
    SamplingConfig,
    extract_candidate,
    file_hash,
    window_sample_times,
)
from backend.services.evidence_validation import EvidenceRegistry
from backend.services.log_normalization import normalize_log
from backend.services.qwen_local import create_local_provider
from backend.services.synchronization import TimeAnchor, align
from backend.services.video import VideoService
from backend.services.vlm_provider import AnalysisContext, filtered_telemetry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("backend/data/vlm"))
    parser.add_argument("--log-offset", type=float, required=True, help="Explicit assumed log-to-video offset; this is not measured alignment")
    parser.add_argument("--max-batches", type=int, default=0, help="0 runs all batches; a positive value records remaining frames as unexamined")
    args = parser.parse_args()
    settings = get_settings()
    output = Path("backend/data/qwen-smoke")
    output.mkdir(parents=True, exist_ok=True)
    service = VideoService(settings.ffprobe_bin, settings.ffmpeg_bin)
    provider = create_local_provider(settings)
    records = []
    for source in sorted(args.input.glob("*.mp4")):
        metadata = service.probe(source).as_dict()
        duration = metadata["duration"]
        log = normalize_log(source.with_suffix(".csv"))
        offset = args.log_offset
        alignment = align(metadata, log, [TimeAnchor(-offset, 0.0, "smoke_configured_offset_not_measured"), TimeAnchor(duration - offset, duration, "smoke_configured_offset_not_measured")])
        discovery = detect_candidates(log, alignment, DetectionConfig(source.stem, duration, signal_thresholds=settings.qwen_signal_thresholds, delta_thresholds=settings.qwen_delta_thresholds))
        record = {"source": source.name, "scope": "CARLA synthetic integration only", "alignment_assumption": offset, "alignment_measured": False, "candidates": [asdict(item) for item in discovery.candidates], "results": [], "errors": [], "unanalyzed_frame_times_s": []}
        for candidate in discovery.candidates:
            times = window_sample_times(candidate, metadata, settings.qwen_sampling_fps)
            bundle = extract_candidate(source, candidate, SamplingConfig(times, 256), recording_id=source.stem, output_root=output / source.stem, metadata=metadata, video_service=service)
            rows = []
            for row in log.iter_rows():
                at_s = alignment.to_video_seconds(row["time_s"])
                if candidate.start_s <= at_s <= candidate.end_s:
                    rows.append({"time_s": at_s, **{key: float(row[key]) for key in ("speed", "brake", "acceleration", "collision_intensity") if key in row}})
            telemetry_file = bundle.manifest_path.parent / "telemetry.json"
            service.write_json(telemetry_file, filtered_telemetry(tuple(rows)))
            telemetry = EvidenceAsset("EVD-" + file_hash(telemetry_file)[:24], source.stem, candidate.candidate_id, telemetry_file, file_hash(telemetry_file), rows[0]["time_s"], rows[-1]["time_s"], "TELEMETRY", "application/json")
            registry = EvidenceRegistry(source.stem, candidate.candidate_id, (bundle.clip, *bundle.frames, telemetry))
            for start in range(0, len(bundle.frames), settings.qwen_batch_frames):
                if args.max_batches > 0 and start // settings.qwen_batch_frames >= args.max_batches:
                    record["unanalyzed_frame_times_s"].extend(frame.time_start_s for frame in bundle.frames[start:])
                    break
                batch = bundle.frames[start:start + settings.qwen_batch_frames]
                begun = time.monotonic()
                print(f"{source.name}: {len(times)} extracted frames, batch {start}, {len(batch)} frames", flush=True)
                try:
                    result = provider.analyze(AnalysisContext(registry, duration, batch, tuple(rows), "CARLA-SMOKE", candidate.flags, (candidate.start_s, candidate.critical_s, candidate.end_s)))
                    record["results"].append({"batch": start, "analysis": result.analysis.model_dump(mode="json"), "usage": result.usage, "provenance": result.provenance})
                    print(f"  schema/evidence passed; incident_detected={result.analysis.incident_detected}; {time.monotonic() - begun:.1f}s", flush=True)
                except Exception as exc:
                    record["errors"].append({"batch": start, "error": str(exc), "elapsed_s": time.monotonic() - begun})
                    record["unanalyzed_frame_times_s"].extend(frame.time_start_s for frame in bundle.frames[start:])
                    print(f"  error: {exc}", flush=True)
                    break  # Do not repeatedly spend CPU after an actionable failure.
        records.append(record)
        service.write_json(output / "results.json", records)
    if not records or any(item["errors"] for item in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
