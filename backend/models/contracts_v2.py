"""V2 public envelopes are independent of collision-relative V1 contracts."""

from typing import Annotated, Literal

from pydantic import Field

from backend.models.analysis_v2 import (
    AnalysisFactorV2,
    ClosedModel,
    IncidentAnalysisV2,
    NonblankText,
    TimelineObservationV2,
)

VersionNumber = Annotated[int, Field(ge=1)]


class ReportEnvelopeV2(ClosedModel):
    recording_id: str
    candidate_id: str
    report_id: str
    version: VersionNumber
    analysis: IncidentAnalysisV2
    provenance: dict
    submitted_by: str | None = None


class ReportEditV2(ClosedModel):
    expected_version: VersionNumber
    summary: NonblankText | None = None
    timeline: list[TimelineObservationV2] | None = None
    factors: list[AnalysisFactorV2] | None = None
    unknowns: list[NonblankText] | None = None


class TransitionV2(ClosedModel):
    expected_version: VersionNumber
    reason: NonblankText | None = None


class UploadRequestV2(ClosedModel):
    recording_id: NonblankText
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    bytes: Annotated[int, Field(gt=0)]
    media_type: Literal["video/mp4"]
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    part_size: Annotated[int, Field(ge=1024, le=16 * 1024 * 1024)] = 8 * 1024 * 1024


class AnalyzeRequestV2(ClosedModel):
    provider_profile: Literal["external_api", "self_hosted"]
