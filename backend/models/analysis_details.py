"""Local candidate details; published V2 contracts stay unchanged."""
from typing import Literal

from pydantic import Field

from backend.models.analysis_v2 import AIIncidentAnalysisV2, ClosedModel, NonblankText


class SceneContext(ClosedModel):
    road_environment: NonblankText = 'UNKNOWN'
    road_condition: NonblankText = 'UNKNOWN'
    weather_visibility: NonblankText = 'UNKNOWN'
    traffic_conditions: NonblankText = 'UNKNOWN'
    ego_vehicle_motion: NonblankText = 'UNKNOWN'
    other_participants: list[NonblankText] = Field(default_factory=list)


class PhaseSummary(ClosedModel):
    before: NonblankText = 'UNKNOWN'
    onset: NonblankText = 'UNKNOWN'
    escalation: NonblankText = 'UNKNOWN'
    critical: NonblankText = 'UNKNOWN'
    response: NonblankText = 'UNKNOWN'
    after: NonblankText = 'UNKNOWN'


class EventDetails(ClosedModel):
    what_happened: NonblankText = 'UNKNOWN'
    participants: list[NonblankText] = Field(default_factory=list)
    trigger: NonblankText = 'UNKNOWN'
    relative_motion: NonblankText = 'UNKNOWN'
    ego_vehicle_response: NonblankText = 'UNKNOWN'
    other_responses: NonblankText = 'UNKNOWN'


class CausalAnalysis(ClosedModel):
    supported_immediate_cause: NonblankText | None = None
    root_cause: NonblankText | None = None
    contributing_factors: list[NonblankText] = Field(default_factory=list)
    hypotheses: list[NonblankText] = Field(default_factory=list)
    causal_uncertainty: NonblankText = 'UNKNOWN'


class Outcome(ClosedModel):
    immediate_result: NonblankText = 'UNKNOWN'
    collision_occurred: bool | None = None
    near_miss_occurred: bool | None = None
    incident_resolved: bool | None = None
    observed_damage: NonblankText = 'UNKNOWN'
    observed_injury: NonblankText = 'UNKNOWN'
    consequences: list[NonblankText] = Field(default_factory=list)
    potential_risks: list[NonblankText] = Field(default_factory=list)


class DataQuality(ClosedModel):
    video_coverage: Literal['PARTIAL', 'UNKNOWN'] = 'PARTIAL'
    telemetry_available: bool = False
    time_sync_reliable: bool | None = None
    sensor_disagreements: list[NonblankText] = Field(default_factory=list)
    limitations: list[NonblankText] = Field(default_factory=list)


class DetailEvidence(ClosedModel):
    evidence_id: NonblankText
    time_s: float = Field(ge=0)
    source: Literal['VIDEO', 'TELEMETRY']
    observation: NonblankText
    certainty: Literal['OBSERVED', 'SUPPORTED_INFERENCE', 'HYPOTHESIS', 'UNKNOWN']


class AnalysisDetails(ClosedModel):
    severity: Literal['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'UNKNOWN'] = 'UNKNOWN'
    confidence: float | None = Field(default=None, ge=0, le=1)
    scene_context: SceneContext = Field(default_factory=SceneContext)
    phase_summary: PhaseSummary = Field(default_factory=PhaseSummary)
    event_details: EventDetails = Field(default_factory=EventDetails)
    causal_analysis: CausalAnalysis = Field(default_factory=CausalAnalysis)
    outcome: Outcome = Field(default_factory=Outcome)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    evidence: list[DetailEvidence] = Field(default_factory=list)


class DetailedAIIncidentAnalysisV2(AIIncidentAnalysisV2):
    details: AnalysisDetails
