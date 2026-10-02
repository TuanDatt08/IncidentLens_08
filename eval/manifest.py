"""Expert dataset contract and pre-measurement release prerequisites."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from backend.models.analysis_v2 import AnalysisFactorV2, AnalysisWindowV2, ClosedModel, EventType, NonblankText


class ExpertEvidence(ClosedModel):
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    source: Literal["VIDEO", "TELEMETRY"]
    window: AnalysisWindowV2


class ExpertLabel(ClosedModel):
    event_type: EventType
    window: AnalysisWindowV2
    factors: list[AnalysisFactorV2]
    evidence: list[ExpertEvidence]
    expected_unknowns: list[NonblankText]


class BenchmarkCase(ClosedModel):
    case_id: NonblankText
    recording_id: NonblankText
    scenario_group: NonblankText
    split: Literal["calibration", "test"]
    video_ref: NonblankText
    video_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    licence_ref: NonblankText
    consent_ref: NonblankText
    annotator_ids: Annotated[list[NonblankText], Field(min_length=2)]
    resolution_ref: NonblankText
    ground_truth: list[ExpertLabel]

    @model_validator(mode="after")
    def distinct_annotators(self) -> Self:
        if len(set(self.annotator_ids)) < 2:
            raise ValueError("independent annotators required")
        return self


class BenchmarkManifest(ClosedModel):
    version: NonblankText
    target_cases: Annotated[int, Field(ge=50, le=100)]
    cases: list[BenchmarkCase]
    min_iou: Annotated[float, Field(gt=0, le=1)]
    tolerance_s: Annotated[float, Field(gt=0)]
    test_locked_at: datetime | None
    threshold_signoff: dict[str, str] | None
    hardware_profile: str | None
    api_policy_ref: str | None

    @model_validator(mode="after")
    def split_integrity(self) -> Self:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("duplicate case IDs")
        groups: dict[tuple[str, str], str] = {}
        for case in self.cases:
            for kind, group in (("recording", case.recording_id), ("scenario", case.scenario_group), ("hash", case.video_sha256)):
                key = (kind, group)
                if key in groups and groups[key] != case.split:
                    raise ValueError("recording/scenario/hash split leakage")
                groups[key] = case.split
        return self

    def blockers(self) -> list[str]:
        return [name for name, passed in {
            "expert_cases": len(self.cases) >= 50,
            "calibration_and_test_split": {case.split for case in self.cases} == {"calibration", "test"},
            "locked_test_set": self.test_locked_at is not None,
            "threshold_signoff": self.threshold_signoff is not None and all(self.threshold_signoff.get(key, "").strip() for key in ("owner", "reviewer", "signed_at", "thresholds_ref")),
            "hardware": bool(self.hardware_profile),
            "api_policy": bool(self.api_policy_ref),
        }.items() if not passed]

    @property
    def release_ready(self) -> bool:
        return not self.blockers()


def load_manifest(path: Path) -> BenchmarkManifest:
    return BenchmarkManifest.model_validate_json(path.read_text(encoding="utf-8"))
