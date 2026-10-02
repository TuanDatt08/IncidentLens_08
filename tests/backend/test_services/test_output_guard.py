from backend.services.video import VideoService


def test_guard_recomputes_remaining_for_each_artifact_and_metadata(tmp_path, monkeypatch):
    limits = []
    def remaining():
        return 100 - sum(path.stat().st_size for path in tmp_path.iterdir())
    service = VideoService(output_guard=remaining)
    def render(args):
        limits.append(service.max_output_bytes)
        from pathlib import Path
        Path(args[-1]).write_bytes(b"x" * 40)
    monkeypatch.setattr(service, "_run_ffmpeg", render)
    service.extract_frame(tmp_path / "source", 0, tmp_path / "one.jpg")
    service.extract_frame(tmp_path / "source", 1, tmp_path / "two.jpg")
    assert limits == [100, 60]
    import pytest
    with pytest.raises(ValueError, match="budget"):
        service.write_json(tmp_path / "manifest.json", {"payload": "x" * 30})
    assert not (tmp_path / "manifest.json").exists()
