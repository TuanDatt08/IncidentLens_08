"""OpenAI image VLM adapter for the two validated analysis passes."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from backend.models.contracts import AnalysisResult, LocalizationResult
from backend.services.llm import get_llm
from backend.services.processing import PreparedPass2, pass1_sample_times


def _image_blocks(paths: list[Path]) -> list[dict]:
    return [
        {
            "type": "image_url",
            "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")},
        }
        for path in paths
    ]


class OpenAIVLMAdapter:
    def __init__(self):
        self.model = get_llm()

    def pass1(self, video_path: Path, sampled_frames: list[Path], metadata: dict) -> LocalizationResult:
        times = pass1_sample_times(metadata)
        prompt = (
            "Localize a traffic incident from these sampled video frames. "
            "Frame times in MP4 seconds: " + json.dumps(times[: len(sampled_frames)]) + ". "
            "Return incident_detected=false when visual evidence is insufficient. "
            "When detected, return collision_offset_in_video_s (collision position in the MP4), "
            "candidate_start, critical_time, candidate_end and evidence_timestamps in seconds relative to collision. "
            "Set critical_time=0. Do not invent observations absent from frames."
        )
        result = self.model.with_structured_output(LocalizationResult).invoke(
            [{"role": "user", "content": [{"type": "text", "text": prompt}, *_image_blocks(sampled_frames)]}]
        )
        return LocalizationResult.model_validate(result)

    def pass2(self, prepared: PreparedPass2) -> AnalysisResult:
        prompt = (
            "Analyze this traffic incident using keyframes and telemetry. Times are seconds relative to collision; "
            "0 is collision, not video start. Candidate window: "
            f"{prepared.candidate_start} to {prepared.candidate_end}; critical {prepared.critical_time}. "
            "Return only observations supported by visual or telemetry evidence; put uncertainty in unknowns. "
            "Do not approve the report. Telemetry rows: "
            + json.dumps(prepared.telemetry_rows, ensure_ascii=False)
        )
        result = self.model.with_structured_output(AnalysisResult).invoke(
            [{"role": "user", "content": [{"type": "text", "text": prompt}, *_image_blocks(prepared.frame_paths)]}]
        )
        return AnalysisResult.model_validate(result)
