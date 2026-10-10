from backend.models.analysis_v2 import AIIncidentAnalysisV2
from backend.services.vlm_provider import ProviderResult


def test_v1_local_processing_flags_log_before_any_model_call(tmp_path, monkeypatch):
    from backend.config import Settings
    from backend.services.qwen_processing import process_local_incident
    from backend.services.video import VideoService
    root = tmp_path / "storage"
    directory = root / "INC-1" / "source"
    directory.mkdir(parents=True)
    (directory / "video.mp4").write_bytes(b"video")
    (directory / "log.csv").write_text("sec_from_incident,brake\n0,0\n10,1\n11,0\n20,0\n")
    def output(self, source, at_s, *args):
        target = args[-1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(str(at_s).encode())
        return target
    monkeypatch.setattr(VideoService, "extract_frame", output)
    monkeypatch.setattr(VideoService, "extract_clip", output)
    calls = []
    class Provider:
        def analyze(self, context):
            calls.append(context)
            assert len(context.frames) == 32
            assert context.candidate_window == (5.0, 10.0, 13.0)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Only supplied frames checked", "timeline": [], "factors": [], "unknowns": ["Coverage limited"], "review_status": "DRAFT"}), {}, {})
    incident = {"incident_id": "INC-1", "video_uri": "INC-1/source/video.mp4", "telemetry_uri": "INC-1/source/log.csv", "video_metadata": {"duration": 30.0, "fps": 30.0}}
    settings = Settings(_env_file=None, qwen_v1_log_offset_s=0, qwen_batch_frames=32)
    result = process_local_incident(incident, storage_root=root, provider=Provider(), settings=settings)
    assert not result.analysis.incident_detected and result.evidence == []
    assert len(calls) == 1
    assert (root / "INC-1" / "local-analysis.json").is_file()


def test_stable_log_without_flags_still_uses_visual_localization(tmp_path, monkeypatch):
    from backend.config import Settings
    from backend.services.qwen_processing import process_local_incident
    from backend.services.video import VideoService
    root = tmp_path / "storage"
    source = root / "INC-1" / "source"
    source.mkdir(parents=True)
    (source / "video.mp4").write_bytes(b"video")
    (source / "log.csv").write_text("sec_from_incident,brake\n0,0\n1,0\n2,0\n")
    def frame(self, video, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"image")
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", frame)
    calls = []
    class Provider:
        def analyze(self, context):
            calls.append(context)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Supplied sparse samples only", "timeline": [], "factors": [], "unknowns": ["Not full coverage"], "review_status": "DRAFT"}), {}, {})
    incident = {"incident_id": "INC-1", "video_uri": "INC-1/source/video.mp4", "telemetry_uri": "INC-1/source/log.csv", "video_metadata": {"duration": 10.0, "fps": 30.0}}
    result = process_local_incident(incident, storage_root=root, provider=Provider(), settings=Settings(_env_file=None, qwen_v1_log_offset_s=0))
    assert not result.analysis.incident_detected
    assert len(calls) == 5
    assert all(len(context.frames) == 1 for context in calls)
    timestamps = [context.frames[0].time_start_s for context in calls]
    assert timestamps == sorted(set(timestamps))


def test_wholly_unanalyzed_candidates_fail_instead_of_no_detection(tmp_path):
    import pytest

    from backend.config import Settings
    from backend.services.processing import InsufficientEvidence
    from backend.services.qwen_processing import process_local_incident
    root = tmp_path / "storage"
    source = root / "INC-1" / "source"
    source.mkdir(parents=True)
    (source / "video.mp4").write_bytes(b"video")
    (source / "log.csv").write_text("sec_from_incident,brake\n" + "".join(f"{i},{1 if i % 6 == 0 else 0}\n" for i in range(100)))
    incident = {"incident_id": "INC-1", "video_uri": "INC-1/source/video.mp4", "telemetry_uri": "INC-1/source/log.csv", "video_metadata": {"duration": 110.0, "fps": 30.0}}
    with pytest.raises(InsufficientEvidence, match="No candidate was analyzed"):
        process_local_incident(incident, storage_root=root, provider=object(), settings=Settings(_env_file=None, qwen_v1_log_offset_s=0))
    assert (root / "INC-1" / "local-analysis.json").is_file()
