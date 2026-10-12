"""Ollama packaging contracts; no weights downloaded by tests."""
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy/qwen-local"


def test_one_local_ollama_and_one_worker():
    commands = runpy.run_path(str(DEPLOY / "unified.py"))["commands"]()
    assert commands["ollama"] == ["ollama", "serve"]
    assert "worker" in commands
    assert "worker_v2" not in commands
    assert "postgres" not in commands
    assert "qwen" not in commands


def test_frontend_binds_loopback(monkeypatch):
    monkeypatch.setenv("HOSTNAME", "container-id")
    env = runpy.run_path(str(DEPLOY / "unified.py"))["frontend_environment"]()
    assert env["HOSTNAME"] == "127.0.0.1"
    assert env["PORT"] == "3000"


def test_worker_polls_both_queues_without_short_circuit():
    poll = runpy.run_path(str(DEPLOY / "worker.py"))["poll_once"]
    calls = []
    assert poll(lambda: calls.append("v1") or True, lambda: calls.append("v2") or False)
    assert calls == ["v1", "v2"]
    assert not poll(lambda: False, lambda: False)


def test_missing_model_returns_false(monkeypatch):
    import urllib.error
    import urllib.request
    def missing(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", missing)
    assert not runpy.run_path(str(DEPLOY / "unified.py"))["model_available"]()


def test_text_only_model_cannot_be_ready(monkeypatch):
    import io
    import urllib.request
    import pytest
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b'{"capabilities":["completion"]}'))
    with pytest.raises(RuntimeError, match="vision"):
        runpy.run_path(str(DEPLOY / "unified.py"))["model_available"]()
