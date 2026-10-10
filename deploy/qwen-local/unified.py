"""One local container: supervised services, persistent PostgreSQL and Qwen."""

import json
import os
import secrets
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path("/data")
PG = "/usr/lib/postgresql/16/bin/"


def read_model_manifest(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def frontend_environment():
    # Docker supplies HOSTNAME=container-id; standalone must bind our private loopback.
    return {**os.environ, "HOSTNAME": "127.0.0.1", "PORT": "3000"}


def commands():
    return {
        "postgres": [PG + "postgres", "-D", "/data/postgres", "-k", "/data/run", "-c", "listen_addresses=", "-c", "unix_socket_permissions=0700"],
        "qwen": ["/opt/llama/llama-server", "-m", "/models/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", "--mmproj", "/models/mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf", "--alias", "incidentlens-qwen-local", "--host", "127.0.0.1", "--port", "8081", "-c", os.getenv("QWEN_CONTEXT_SIZE", "32768"), "-np", "1", "-b", "512", "-ub", "128", "-t", os.getenv("QWEN_THREADS", "6"), "-ngl", "0", "--no-mmproj-offload", "--image-min-tokens", "1024", "--image-max-tokens", "1024"],
        "api": [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "frontend": ["node", "/app/frontend/server.js"],
        "worker": [sys.executable, "-m", "backend.worker"],
        "worker_v2": [sys.executable, "-m", "backend.worker_v2"],
        "gateway": ["nginx", "-c", "/app/deploy/unified-nginx.conf", "-g", "daemon off;"],
    }


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


def main():
    processes = {}
    def stopping(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    try:
        DATA.mkdir(exist_ok=True)
        (DATA / "run").mkdir(exist_ok=True, mode=0o700)
        (DATA / "run").chmod(0o700)
        (DATA / "incidents").mkdir(exist_ok=True)
        secret = DATA / "identity-secret"
        if not secret.exists():
            descriptor = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(secrets.token_urlsafe(48))
        os.environ.setdefault("V2_IDENTITY_SECRET", secret.read_text().strip())
        os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://appuser@/incidentlens?host=/data/run")
        for key, value in {"APP_ENV": "development", "INCIDENT_STORAGE_DIR": "/data/incidents", "QWEN_ENDPOINT": "http://127.0.0.1:8081/v1/chat/completions", "QWEN_MODEL_DIR": "/models", "QWEN_SERVER_BIN": "/opt/llama/llama-server", "QWEN_PROMPT_PATH": "/app/backend/data/promt.txt", "QWEN_OUTPUTS_PATH": "/app/backend/data/outputs.txt"}.items():
            os.environ.setdefault(key, value)
        manifest = read_model_manifest(Path("/models/model-manifest.json"))
        # Validate immutable weight hashes once per startup, before accepting work.
        import hashlib
        for item in manifest["files"]:
            path = (Path("/models") / item["name"]).resolve()
            if path.parent != Path("/models") or not path.is_file() or path.stat().st_size != item["size_bytes"]:
                raise RuntimeError("Model manifest/file mismatch")
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != item["sha256"]:
                    raise RuntimeError("Model checksum mismatch")
        cmds = commands()
        fresh_database = False
        if "host=/data/run" in os.environ["DATABASE_URL"]:
            if not (DATA / "postgres/PG_VERSION").exists():
                subprocess.run([PG + "initdb", "-D", "/data/postgres", "--auth-local=trust", "--auth-host=reject", "--no-locale", "--encoding=UTF8"], check=True)
            processes["postgres"] = subprocess.Popen(cmds["postgres"])
            wait_ready(lambda: subprocess.run([PG + "pg_isready", "-h", "/data/run", "-d", "postgres"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, processes, 60)
            result = subprocess.run([PG + "psql", "-h", "/data/run", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='incidentlens'"], check=True, capture_output=True, text=True)
            if not result.stdout.strip():
                fresh_database = True
                subprocess.run([PG + "createdb", "-h", "/data/run", "incidentlens"], check=True)
        # QL tasks do not change the database schema. Preserve the existing volume
        # and its historical migration marker; initialize schema only for a fresh DB.
        if fresh_database:
            subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
        for name in ("qwen", "api", "frontend"):
            processes[name] = subprocess.Popen(cmds[name], cwd="/app/frontend" if name == "frontend" else "/app", env=frontend_environment() if name == "frontend" else None)
        wait_ready(lambda: http_ready("http://127.0.0.1:8081/health") and http_ready("http://127.0.0.1:8000/health") and http_ready("http://127.0.0.1:3000/incidents"), processes)
        for name in ("worker", "worker_v2", "gateway"):
            processes[name] = subprocess.Popen(cmds[name])
        (DATA / "run/pids.json").write_text(json.dumps({name: process.pid for name, process in processes.items()}))
        print("IncidentLens Qwen local ready (container :8088, host :8089)", flush=True)
        while True:
            for name, process in processes.items():
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited with status {process.returncode}")
            time.sleep(1)
    finally:
        (DATA / "run/pids.json").unlink(missing_ok=True)
        # Stop consumers first; database last. Never delete persistent data.
        for process in reversed(list(processes.values())):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
