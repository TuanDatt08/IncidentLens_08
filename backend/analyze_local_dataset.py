"""Import a local MP4/log directory, analyze with Ollama, persist an engineer draft.

Run from repository root: python -m backend.analyze_local_dataset --help
Database schema is initialized separately with Alembic.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import UploadFile
from sqlalchemy import select

from backend.config import get_settings
from backend.db import session_scope
from backend.models.tables import Incident
from backend.services.evidence_extraction import file_hash
from backend.services.incidents import create_incident
from backend.services.jobs import create_job, get_job
from backend.services.log_normalization import normalize_log
from backend.services.reports import get_evidence, get_model_metadata, get_report
from backend.worker import run_once


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_directory(source: Path, offset_s: float, offset_source: str) -> list[dict]:
    settings = get_settings()
    if settings.qwen_runtime != "ollama":
        raise ValueError("Set QWEN_RUNTIME=ollama for this local dataset command")
    files = sorted(source.resolve().iterdir())
    videos = [path for path in files if path.is_file() and path.suffix.lower() == ".mp4"]
    if not videos:
        raise ValueError("Input directory must contain MP4 video")
    outputs = []
    for video in videos:
        log = video.with_suffix(".csv")
        with video.open("rb") as stream:
            if log.is_file():
                with log.open("rb") as telemetry:
                    created = create_incident(UploadFile(stream, filename=video.name), UploadFile(telemetry, filename=log.name))
            else:
                created = create_incident(UploadFile(stream, filename=video.name))
        identity = created["incident_id"]
        directory = Path(settings.incident_storage_dir).resolve() / identity
        output = directory / "output"
        output.mkdir(parents=True)
        records = []
        for path in files:
            if not path.is_file() or (path.suffix.lower() == ".mp4" and path != video):
                continue
            target = directory / "input" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            records.append({"file": target.relative_to(directory).as_posix(), "bytes": target.stat().st_size, "sha256": file_hash(target), "role": "video" if path == video else "telemetry" if path == log else "reference_only", "sent_to_model": path in (video, log)})
        duration = created["video_metadata"]["duration"]
        metadata = {**created["video_metadata"], "data_origin": "local_dataset", "alignment_provenance": offset_source, "anchors": [{"log_s": -offset_s, "video_s": 0.0, "source": offset_source}, {"log_s": duration - offset_s, "video_s": duration, "source": offset_source}]}
        with session_scope() as session:
            row = session.scalar(select(Incident).where(Incident.incident_id == identity))
            row.video_uri = f"{identity}/input/{video.name}"
            row.telemetry_uri = f"{identity}/input/{log.name}" if log.is_file() else None
            row.video_metadata = metadata
            row.source = {"kind": "LOCAL_DATASET", "directory": str(source.resolve()), "manifest_uri": f"{identity}/input/manifest.json", "reference_labels_sent_to_model": False}
            row.raw_incident_data = {"schema_version": "1.0", "source": row.source, "archive_files": records, "reference_documents": {path.name: json.loads(path.read_text(encoding="utf-8-sig")) for path in files if path.is_file() and path.suffix.lower() == ".json"}, "reference_documents_role": "SOURCE_METADATA_ONLY_NOT_MODEL_EVIDENCE"}
        write_json(directory / "input" / "manifest.json", {"incident_id": identity, "source_directory": str(source.resolve()), "files": records, "video_metadata": metadata, "notes": ["JSON labels and README archived for review only, never sent to model", "Only selected JPEG frames and synchronized allowlisted telemetry are sent to Ollama; MP4 itself is decoded by FFmpeg"]})
        if log.is_file():
            normalized = normalize_log(log)
            write_json(output / "normalized-telemetry.json", {"metadata": normalized.metadata.model_dump(), "offset_s": offset_s, "offset_source": offset_source, "rows": [{**row, "video_s": row["time_s"] + offset_s} for row in normalized.iter_rows()]})
        settings.qwen_artifact_subdir = "output"
        settings.qwen_requests_dir = str(output / "requests")
        settings.qwen_outputs_path = str(output / "outputs.txt")
        endpoint = urlparse(settings.qwen_endpoint)
        with httpx.Client(trust_env=False, timeout=10) as client:
            response = client.get(f"{endpoint.scheme}://{endpoint.netloc}/api/tags")
            response.raise_for_status()
            tags = response.json()
        write_json(output / "runtime.json", {"endpoint": settings.qwen_endpoint, "model": settings.qwen_ollama_model, "tags": tags, "settings": {"sampling_fps": settings.qwen_sampling_fps, "batch_frames": settings.qwen_batch_frames, "inference_frame_limit": settings.qwen_inference_frame_limit, "candidate_min_acceleration": settings.qwen_candidate_min_acceleration}, "database_url": settings.database_url.split("@")[-1]})
        job = create_job(identity)
        write_json(output / "job.json", job)
        logging.info("Analyzing %s job=%s output=%s", identity, job["job_id"], output)
        run_once(job_id=job["job_id"])
        state = get_job(job["job_id"])
        write_json(output / "job.json", state)
        if state["status"] != "succeeded":
            raise RuntimeError(f"Analysis failed; inspect {output / 'job.json'} and outputs.txt")
        draft = get_report(identity)
        write_json(output / "draft.json", draft)
        write_json(output / "model-metadata.json", get_model_metadata(identity))
        write_json(output / "evidence.json", get_evidence(identity))
        write_json(output / "review.json", {"incident_id": identity, "review_status": draft["review_status"], "next_action": "Engineer reviews draft, video, telemetry, evidence and unknowns; edit then submit manually", "approved_by": None, "report_api": f"/api/v1/incidents/{identity}/report"})
        outputs.append({"incident_id": identity, "job_id": job["job_id"], "output": str(output), "review_status": draft["review_status"], "incident_detected": draft["incident_detected"]})
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("vlm/data"))
    parser.add_argument("--log-offset-s", type=float, required=True)
    parser.add_argument("--offset-source", required=True, help="Evidence establishing frame/log clock mapping")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(analyze_directory(args.input, args.log_offset_s, args.offset_source), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
