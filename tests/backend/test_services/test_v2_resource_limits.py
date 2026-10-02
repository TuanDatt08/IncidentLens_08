import pytest

from backend.services.video import VideoService


def test_ffmpeg_output_budget_is_enforced(tmp_path, monkeypatch):
    import subprocess
    destination = tmp_path / "frame.jpg"
    commands = []
    def fake(command, **kwargs):
        commands.append(command)
        destination.write_bytes(b"x" * 1024)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(subprocess, "run", fake)
    service = VideoService(max_output_bytes=1024)
    with pytest.raises(ValueError, match="budget"):
        service.extract_frame(tmp_path / "video.mp4", 1.0, destination)
    assert "-fs" in commands[0]
