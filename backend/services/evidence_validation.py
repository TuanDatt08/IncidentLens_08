"""Shared generation/edit/approval gate for immutable, scoped evidence."""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.analysis_v2 import IncidentAnalysisV2
from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.synchronization import finite


@dataclass(frozen=True)
class EvidenceRegistry:
    recording_id: str
    candidate_id: str
    assets: tuple[EvidenceAsset, ...]


def validate_analysis(analysis: dict | IncidentAnalysisV2, registry: EvidenceRegistry, duration: float) -> IncidentAnalysisV2:
    result = IncidentAnalysisV2.model_validate(analysis.model_dump() if isinstance(analysis, IncidentAnalysisV2) else analysis, context={"video_duration_s": duration})
    by_id: dict[str, EvidenceAsset] = {}
    for asset in registry.assets:
        if asset.evidence_id in by_id or (asset.recording_id, asset.candidate_id) != (registry.recording_id, registry.candidate_id):
            raise ValueError("evidence ID duplicated or outside recording/candidate scope")
        if asset.source not in {"VIDEO", "TELEMETRY"} or not all(finite(value) for value in (asset.time_start_s, asset.time_end_s)) or not 0 <= asset.time_start_s <= asset.time_end_s <= duration:
            raise ValueError("evidence time/source invalid")
        if not asset.path.is_file() or file_hash(asset.path) != asset.sha256:
            raise ValueError("evidence bytes unavailable or hash changed")
        by_id[asset.evidence_id] = asset

    def resolve(ids: list[str], at_s: float | None = None) -> set[str]:
        sources = set()
        for evidence_id in ids:
            asset = by_id.get(evidence_id)
            if asset is None:
                raise ValueError("evidence ID does not resolve")
            window = result.window
            if window is None or asset.time_end_s < window.start_s or asset.time_start_s > window.end_s:
                raise ValueError("evidence is outside report window")
            if at_s is not None and not asset.time_start_s <= at_s <= asset.time_end_s:
                raise ValueError("observation time is outside evidence time range")
            sources.add(asset.source)
        return sources

    for item in result.timeline:
        sources = resolve(item.evidence_ids, item.time_s)
        required = {"VIDEO", "TELEMETRY"} if item.source == "FUSED" else {item.source}
        if item.evidence_ids and not required.issubset(sources):
            raise ValueError("observation source does not match referenced evidence")
    for factor in result.factors:
        sources = resolve(factor.evidence_ids)
        if factor.category == "VEHICLE_OR_SYSTEM" and factor.claim_status in {"OBSERVED", "SUPPORTED_INFERENCE"} and "TELEMETRY" not in sources:
            raise ValueError("internal vehicle/system claim requires telemetry evidence; use HYPOTHESIS or UNKNOWN")
    return result
