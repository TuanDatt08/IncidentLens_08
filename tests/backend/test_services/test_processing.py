from pathlib import Path

import pytest

from backend.models.contracts import AnalysisResult, LocalizationResult
from backend.services.processing import InsufficientEvidence, process_incident
from backend.services.video import VideoService


class FakeVLM:
    def __init__(self, localization, analysis=None):
        self.localization = localization
        self.analysis = analysis
        self.pass2_calls = 0
        self.prepared = None

    def pass1(self, video_path, sampled_frames, metadata):
        assert video_path.exists()
        assert sampled_frames
        return self.localization

    def pass2(self, prepared):
        self.pass2_calls += 1
        self.prepared = prepared
        return self.analysis


@pytest.fixture(autouse=True)
def fake_ffmpeg(monkeypatch):
    def extract_frame(self, video_path, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return destination

    def extract_clip(self, video_path, start_s, end_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"clip")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", extract_frame, raising=False)
    monkeypatch.setattr(VideoService, "extract_clip", extract_clip, raising=False)


def _incident(tmp_path, with_csv=True):
    root = tmp_path / "storage"
    source = root / "INC-001" / "source"
    source.mkdir(parents=True)
    (source / "video.mp4").write_bytes(b"video")
    if with_csv:
        (source / "telemetry.csv").write_text(
            "sec_from_incident,sim_time_s,wall_clock_ts\n-2,8,t0\n-1,9,t1\n0,10,t2\n1,11,t3\n2,12,t4\n",
            encoding="utf-8",
        )
    return root, {
        "incident_id": "INC-001",
        "video_uri": "INC-001/source/video.mp4",
        "telemetry_uri": "INC-001/source/telemetry.csv" if with_csv else None,
        "video_metadata": {"duration": 10.0, "fps": 30.0, "width": 320, "height": 240},
    }


def test_pass2_gets_clip_frames_and_relative_telemetry_window(tmp_path):
    root, incident = _incident(tmp_path)
    fake = FakeVLM(
        LocalizationResult(
            incident_detected=True,
            candidate_start=-1.5,
            critical_time=0,
            candidate_end=1.5,
            evidence_timestamps=[-1, 0, 1],
            collision_offset_in_video_s=5.0,
        ),
        AnalysisResult(
            incident_detected=True,
            incident_type="pedestrian_collision",
            incident_window={"start": -1.5, "critical": 0, "end": 1.5},
            summary="Vehicle struck pedestrian.",
        ),
    )
    result = process_incident(incident, storage_root=root, vlm=fake)
    assert fake.pass2_calls == 1
    assert [row["sec_from_incident"] for row in fake.prepared.telemetry_rows] == [-1.0, 0.0, 1.0]
    assert fake.prepared.clip_path.read_bytes() == b"clip"
    assert result.analysis.incident_window.start == -1.5
    assert result.collision_offset_in_video_s == 5.0
    assert any(e.kind == "video" and e.time_range_s == (-1.5, 1.5) for e in result.evidence)
    assert all(not Path(e.uri).is_absolute() for e in result.evidence)


def test_no_incident_skips_pass2(tmp_path):
    root, incident = _incident(tmp_path, with_csv=False)
    fake = FakeVLM(LocalizationResult(incident_detected=False))
    result = process_incident(incident, storage_root=root, vlm=fake)
    assert result.analysis.incident_detected is False
    assert fake.pass2_calls == 0
    assert result.evidence == []


def test_pass1_sampling_avoids_video_end_without_a_decodable_frame(tmp_path, monkeypatch):
    root, incident = _incident(tmp_path, with_csv=False)
    incident["video_metadata"] = {"duration": 4.0, "fps": 10.0, "width": 160, "height": 120}
    sampled_at = []

    def extract_frame(self, video_path, at_s, destination):
        sampled_at.append(at_s)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", extract_frame)
    process_incident(incident, storage_root=root, vlm=FakeVLM(LocalizationResult(incident_detected=False)))
    assert len(sampled_at) == 5
    assert sampled_at[-1] <= 3.85


def test_missing_video_collision_offset_rejects_unsafe_timestamp_mapping(tmp_path):
    root, incident = _incident(tmp_path)
    fake = FakeVLM(
        LocalizationResult(incident_detected=True, candidate_start=-1, critical_time=0, candidate_end=1),
    )
    with pytest.raises(InsufficientEvidence):
        process_incident(incident, storage_root=root, vlm=fake)
    assert fake.pass2_calls == 0

@pytest.mark.parametrize('metadata', [{'duration': 1.0, 'fps': 2.0}, {'duration': 0.1, 'fps': 10.0}, {'duration': 10.0, 'fps': 30.0}])
def test_scan_times_are_unique_ordered_and_decodable(metadata):
    from backend.services.processing import pass1_sample_times
    times = pass1_sample_times(metadata)
    assert times == sorted(set(times))
    assert times[0] == 0.0
    assert all(0 <= value <= max(0, metadata['duration'] - 1.5 / metadata['fps']) for value in times)
