"""Remote GPU downtime must not consume queued work."""
import runpy
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy/qwen-local"


def test_offline_gpu_does_not_claim_either_queue():
    poll = runpy.run_path(str(DEPLOY / "worker.py"))["poll_once"]
    calls = []
    assert not poll(lambda: calls.append("v1"), lambda: calls.append("v2"), ready=lambda: False)
    assert calls == []
    assert poll(lambda: calls.append("v1") or True, lambda: calls.append("v2") or False, ready=lambda: True)
    assert calls == ["v1", "v2"]


def test_remote_mode_excludes_local_model_process(monkeypatch):
    monkeypatch.setenv("QWEN_REMOTE_OLLAMA", "true")
    commands = runpy.run_path(str(DEPLOY / "unified.py"))["commands"]()
    assert "ollama" not in commands
    assert {"api", "frontend", "worker", "gateway"} <= commands.keys()
