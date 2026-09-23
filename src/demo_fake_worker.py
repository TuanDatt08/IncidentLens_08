"""Explicit local demo worker: generate a labeled fake report for one queued job."""

from __future__ import annotations

import argparse
import json

from src.config import get_settings
from src.models.contracts import AnalysisResult, LocalizationResult
from src.services.jobs import get_job
from src.services.processing import PreparedPass2
from src.worker import run_once


class DemoVLM:
    def pass1(self, video_path, sampled_frames, metadata) -> LocalizationResult:
        duration = float(metadata["duration"])
        half_window = min(0.5, duration / 4)
        return LocalizationResult(
            incident_detected=True,
            candidate_start=-half_window,
            critical_time=0,
            candidate_end=half_window,
            evidence_timestamps=[0],
            collision_offset_in_video_s=duration / 2,
        )

    def pass2(self, prepared: PreparedPass2) -> AnalysisResult:
        return AnalysisResult(
            incident_detected=True,
            incident_type="demo_synthetic",
            incident_window={
                "start": prepared.candidate_start,
                "critical": 0,
                "end": prepared.candidate_end,
            },
            summary="DEMO: Báo cáo giả lập để kiểm thử; chưa phân tích nội dung video.",
            timeline=[{"sec_from_incident": 0, "event": "Mốc giữa video được chọn giả lập."}],
            observations=[f"DEMO: Đã đọc {len(prepared.telemetry_rows)} dòng telemetry trong cửa sổ giả lập."],
            unknowns=["Vị trí và loại sự cố thực tế chưa được xác minh."],
            model_metadata={"provider": "fake-demo"},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one queued RAV18 job with a fake VLM report.")
    parser.add_argument("job_id", help="The job_id returned by POST /incidents/{incident_id}/analyze")
    args = parser.parse_args()
    if get_settings().app_env == "production":
        parser.error("fake reports are disabled in production")
    if not run_once(vlm=DemoVLM(), job_id=args.job_id):
        parser.error("job is not queued or available")
    job = get_job(args.job_id)
    print(json.dumps(job, ensure_ascii=False))
    return 0 if job["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
