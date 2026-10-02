import hashlib
import importlib
import json
import shutil
import subprocess

import pytest

from backend.services.candidate_detection import Candidate
from backend.services.video import VideoService


def candidate():
    return Candidate("CND-fixture", 1.0, 2.5, 3.0, ("HARD_BRAKING",), "PENDING")


def test_manifest_orders_frames_hashes_and_replay_is_stable(tmp_path, monkeypatch):
    module = importlib.import_module("backend.services.evidence_extraction")
    video = tmp_path / "source.mp4"
    video.write_bytes(b"source")
    def write_frame(self, source, time_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(str(time_s).encode())
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", write_frame)
    monkeypatch.setattr(VideoService, "extract_clip", lambda self, source, start, end, dest: write_frame(self, source, start, dest))
    bundle = module.extract_candidate(video, candidate(), module.SamplingConfig((2.5, 1.5, 2.0)), recording_id="rec", output_root=tmp_path / "out", metadata={"duration": 4.0, "fps": 10.0})
    assert [frame.time_start_s for frame in bundle.frames] == [1.5, 2.0, 2.5]
    assert [frame.frame_order for frame in bundle.frames] == [0, 1, 2]
    assert bundle.frames[0].sha256 == hashlib.sha256(b"1.5").hexdigest()
    assert json.loads(bundle.manifest_path.read_text())["candidate_id"] == candidate().candidate_id
    again = module.extract_candidate(video, candidate(), module.SamplingConfig((2.5, 1.5, 2.0)), recording_id="rec", output_root=tmp_path / "out", metadata={"duration": 4.0, "fps": 10.0})
    assert bundle.frames == again.frames


@pytest.mark.parametrize("times", [(0.0,), (4.0,), (float("nan"),), (2.0, 2.0)])
def test_outside_or_duplicate_frame_times_rejected_before_ffmpeg(tmp_path, times):
    module = importlib.import_module("backend.services.evidence_extraction")
    with pytest.raises(ValueError):
        module.extract_candidate(tmp_path / "source.mp4", candidate(), module.SamplingConfig(times), recording_id="rec", output_root=tmp_path, metadata={"duration": 4.0, "fps": 10.0})


def test_real_ffmpeg_seeks_blue_frame_and_clip_duration(tmp_path):
    assert shutil.which("ffmpeg") and shutil.which("ffprobe"), "real FFmpeg fixture is required for acceptance"
    module = importlib.import_module("backend.services.evidence_extraction")
    source = tmp_path / "colors.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=64x64:r=10:d=2", "-f", "lavfi", "-i", "color=blue:s=64x64:r=10:d=2", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0", "-c:v", "libx264", str(source)], check=True, capture_output=True, timeout=30)
    bundle = module.extract_candidate(source, candidate(), module.SamplingConfig((2.5,)), recording_id="rec", output_root=tmp_path / "out")
    pixels = subprocess.run(["ffmpeg", "-v", "error", "-i", str(bundle.frames[0].path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True, timeout=30).stdout
    assert pixels[2] > 200 and pixels[0] < 30
    assert VideoService().probe(bundle.clip.path).duration == pytest.approx(2.0, abs=0.1)
