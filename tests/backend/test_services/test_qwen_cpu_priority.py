import json

import pytest

from backend.config import Settings
from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.services.qwen_processing import process_local_incident
from backend.services.video import VideoService
from backend.services.vlm_provider import ProviderResult


def test_priority_keeps_unreviewed_windows_unknown_and_analyzes_strong_braking(tmp_path, monkeypatch):
    source = tmp_path / "INC-1" / "input"
    source.mkdir(parents=True)
    (source / "video.mp4").write_bytes(b"video")
    (source / "log.csv").write_text("sec_from_incident,brake,accel_x,speed_kmh\n0,0,0,36\n10,1,-1,36\n11,0,0,35\n20,0,0,36\n30,1,-8,36\n31,0,0,0\n39,0,0,0\n")

    def extract(self, source, at_s, *args):
        path = args[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at_s).encode())
        return path

    monkeypatch.setattr(VideoService, "extract_frame", extract)
    monkeypatch.setattr(VideoService, "extract_clip", extract)
    calls = []

    class Provider:
        def analyze(self, context):
            calls.append(context)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Not confirmed", "timeline": [], "factors": [], "unknowns": [], "review_status": "DRAFT"}), {}, {})

    settings = Settings(_env_file=None, qwen_v1_log_offset_s=0, qwen_batch_frames=8, qwen_inference_frame_limit=8, qwen_candidate_min_acceleration=4)
    incident = {"incident_id": "INC-1", "video_uri": "INC-1/input/video.mp4", "telemetry_uri": "INC-1/input/log.csv", "video_metadata": {"duration": 40.0, "fps": 30.0}}
    result = process_local_incident(incident, storage_root=tmp_path, provider=Provider(), settings=settings)
    assert len(calls) == 2 and calls[1].candidate_window == (25.0, 30.0, 33.0)
    assert any(frame.time_start_s == 30.0 for frame in calls[1].frames)
    manifest = json.loads((tmp_path / "INC-1" / "local-analysis.json").read_text())
    assert not any("UNANALYZED" in item for item in manifest["unknowns"])
    assert result.analysis.model_metadata['unknowns']
    assert any("MODEL_TELEMETRY_CONFLICT" in item for item in result.analysis.model_metadata["draft_v2"]["unknowns"])


@pytest.mark.parametrize("all_invalid", [False, True])
def test_invalid_batch_is_unknown_and_cannot_become_no_detection(tmp_path, monkeypatch, all_invalid):
    from backend.services.processing import InsufficientEvidence

    (tmp_path / "video.mp4").write_bytes(b"video")
    (tmp_path / "log.csv").write_text("sec_from_incident,brake\n0,0\n10,1\n11,0\n20,0\n")
    def extract(self, source, at_s, *args):
        path = args[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at_s).encode())
        return path
    monkeypatch.setattr(VideoService, "extract_frame", extract)
    monkeypatch.setattr(VideoService, "extract_clip", extract)
    calls = []
    class Provider:
        def analyze(self, context):
            calls.append(context)
            data = {"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Not confirmed", "timeline": [], "factors": [], "unknowns": [], "review_status": "DRAFT"}
            if all_invalid or len(calls) == 1:
                data["event_type"] = "OTHER"
            return ProviderResult(AIIncidentAnalysisV2.model_validate(data), {}, {})
    settings = Settings(_env_file=None, qwen_v1_log_offset_s=0, qwen_batch_frames=4, qwen_inference_frame_limit=8, qwen_candidate_min_acceleration=None)
    incident = {"incident_id": "INC-1", "video_uri": "video.mp4", "telemetry_uri": "log.csv", "video_metadata": {"duration": 21.0, "fps": 30.0}}
    if all_invalid:
        with pytest.raises(InsufficientEvidence, match="No valid model batch"):
            process_local_incident(incident, storage_root=tmp_path, provider=Provider(), settings=settings)
    else:
        result = process_local_incident(incident, storage_root=tmp_path, provider=Provider(), settings=settings)
        assert any("INVALID_MODEL_OUTPUT" in item for item in result.analysis.model_metadata["unknowns"])
    manifest = json.loads((tmp_path / "INC-1" / "local-analysis.json").read_text())
    assert len(calls) == 2
    assert manifest["results"][0]["error"]["code"] == "INVALID_MODEL_OUTPUT"
    assert manifest["visual_coverage"]["model_frame_count"] == 8
    assert manifest["visual_coverage"]["validated_model_frame_count"] == (0 if all_invalid else 4)


def test_unknown_collision_claim_is_rejected_but_observed_video_claim_can_proceed():
    from backend.services.qwen_processing import UnsupportedModelClaimError, require_supported_collision
    value = {"schema_version": "2.0", "incident_detected": True, "event_type": "COLLISION", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.0, "end_s": 3.0}, "summary": "Collision claimed", "timeline": [{"time_s": 2.0, "observation": "Contact claimed", "evidence_ids": ["EVD-1"], "source": "VIDEO", "certainty": "UNKNOWN"}], "factors": [], "unknowns": [], "review_status": "DRAFT"}
    with pytest.raises(UnsupportedModelClaimError):
        require_supported_collision(AIIncidentAnalysisV2.model_validate(value))
    value["timeline"][0]["certainty"] = "OBSERVED"
    require_supported_collision(AIIncidentAnalysisV2.model_validate(value))
