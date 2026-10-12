"""Supervise a local Ollama application with persistent SQLite and artifacts."""
import json
import os
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DATA = Path("/data")


def frontend_environment():
    return {**os.environ, "HOSTNAME": "127.0.0.1", "PORT": "3000"}


def commands():
    result = {
        "ollama": ["ollama", "serve"],
        "api": [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "frontend": ["node", "/app/frontend/server.js"],
        "worker": [sys.executable, "/app/deploy/worker.py"],
        "gateway": ["nginx", "-c", "/app/deploy/unified-nginx.conf", "-g", "daemon off;"],
    }
    if os.getenv("QWEN_REMOTE_OLLAMA", "false").lower() == "true":
        result.pop("ollama")
    return result


def wait_ready(check, processes, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for name, process in processes.items():
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited with status {process.returncode}")
        try:
            if check():
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Service startup deadline exceeded")


def http_ready(url):
    with urllib.request.urlopen(url, timeout=3) as response:
        return response.status == 200


def model_available():
    request = urllib.request.Request("http://127.0.0.1:11434/api/show", data=b'{"model":"qwen2.5vl:7b"}', headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if "vision" not in json.load(response).get("capabilities", []):
                raise RuntimeError("qwen2.5vl:7b must support vision")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def main():
    processes = {}
    streams = []

    def stopping(signum, frame):
        raise SystemExit(0)

    def start(name, command=None):
        for suffix in ("stdout", "stderr"):
            streams.append((DATA / f"logs/runtime/{name}.{suffix}.log").open("ab", buffering=0))
        process = subprocess.Popen(command or commands()[name], cwd="/app/frontend" if name == "frontend" else "/app", env=frontend_environment() if name == "frontend" else None, stdout=streams[-2], stderr=streams[-1])
        processes[name] = process
        return process

    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    try:
        for directory in ("run", "incidents", "logs/runtime", "logs/qwen"):
            (DATA / directory).mkdir(parents=True, exist_ok=True)
        secret = DATA / "identity-secret"
        if not secret.exists():
            descriptor = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(secrets.token_urlsafe(48))
        defaults = {
            "V2_IDENTITY_SECRET": secret.read_text().strip(),
            "APP_ENV": "development", "DATABASE_URL": "sqlite:////data/incidentlens.db",
            "INCIDENT_STORAGE_DIR": "/data/incidents", "RUNTIME_LOG_DIR": "/data/logs/runtime",
            "QWEN_RUNTIME": "ollama", "QWEN_OLLAMA_MODEL": "qwen2.5vl:7b",
            "QWEN_ENDPOINT": "http://127.0.0.1:11434/v1/chat/completions",
            "QWEN_PROMPT_PATH": "/app/backend/data/promt.txt",
            "QWEN_LOG_PROMPT_PATH": "/app/backend/prompts/ollama_incident.txt",
            "QWEN_OUTPUTS_PATH": "/data/logs/qwen/outputs.txt",
            "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MODELS": "/models", "OLLAMA_NO_CLOUD": "1",
        }
        for key, value in defaults.items():
            os.environ.setdefault(key, value)
        from backend.config import get_settings
        from backend.services.qwen_local import ensure_ollama_runtime
        if not get_settings().qwen_remote_ollama:
            start("ollama")
            wait_ready(lambda: http_ready("http://127.0.0.1:11434/api/tags"), processes, 60)
            if not model_available():
                if os.getenv("OLLAMA_AUTO_PULL", "true").lower() != "true":
                    raise RuntimeError("Missing qwen2.5vl:7b; enable OLLAMA_AUTO_PULL or import the model volume")
                print("Downloading qwen2.5vl:7b; see /data/logs/runtime/model-pull.*.log", flush=True)
                pull = start("model-pull", ["ollama", "pull", "qwen2.5vl:7b"])
                if pull.wait(timeout=1800) != 0:
                    raise RuntimeError("Model download failed; inspect model-pull.stderr.log")
                del processes["model-pull"]
            ensure_ollama_runtime(get_settings())
        migration = start("migration", [sys.executable, "-m", "alembic", "upgrade", "head"])
        if migration.wait(timeout=120) != 0:
            raise RuntimeError("Database migration failed; inspect migration.stderr.log")
        del processes["migration"]
        for name in ("api", "frontend"):
            start(name)
        wait_ready(lambda: http_ready("http://127.0.0.1:8000/health") and http_ready("http://127.0.0.1:3000/incidents"), processes)
        for name in ("worker", "gateway"):
            start(name)
        wait_ready(lambda: http_ready("http://127.0.0.1:8088/api/v1/health"), processes, 30)
        (DATA / "run/pids.json").write_text(json.dumps({name: process.pid for name, process in processes.items()}))
        database = "PostgreSQL cloud" if get_settings().database_cloud else "SQLite"
        print(f"IncidentLens ready: Ollama qwen2.5vl:7b, API, frontend, worker, {database}", flush=True)
        while True:
            for name, process in processes.items():
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited with status {process.returncode}; inspect /data/logs/runtime")
            time.sleep(1)
    finally:
        (DATA / "run/pids.json").unlink(missing_ok=True)
        for process in reversed(list(processes.values())):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for stream in streams:
            stream.close()


if __name__ == "__main__":
    sys.path.insert(0, "/app")
    main()
