"""Reuse a loopback llama.cpp process for the user's local vision GGUF files."""

from __future__ import annotations

import atexit
import ipaddress
import os
import shutil
import subprocess
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import httpx

from backend.config import Settings, get_settings
from backend.services.prompt_io import locked_file, read_prompt
from backend.services.vlm_provider import ProviderConfig, SelfHostedVLMProvider, create_provider

_startup_lock = Lock()
_processes: dict[str, subprocess.Popen] = {}


def _stop_owned_servers():
    for process in _processes.values():
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


atexit.register(_stop_owned_servers)


def validate_local_endpoint(endpoint: str):
    parsed = urlparse(endpoint)
    try:
        loopback = parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = False
    if not loopback or parsed.scheme != "http" or parsed.path != "/v1/chat/completions" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Qwen endpoint must be an HTTP loopback /v1/chat/completions endpoint")
    return parsed


def ensure_qwen_runtime(settings: Settings) -> None:
    parsed = validate_local_endpoint(settings.qwen_endpoint)
    base = f"{parsed.scheme}://{parsed.netloc}"
    directory = Path(settings.qwen_model_dir).resolve()
    model, projector = directory / settings.qwen_model_file, directory / settings.qwen_projector_file
    for path in (model, projector):
        if path.parent != directory or not path.is_file():
            raise ValueError(f"Qwen model/projector missing: {path}")
        with path.open("rb") as stream:
            if stream.read(4) != b"GGUF":
                raise ValueError(f"Invalid GGUF model/projector: {path}")
    runtime_data = Path(settings.qwen_outputs_path).resolve().parent
    with _startup_lock, locked_file(runtime_data / "qwen-runtime.lock", settings.qwen_startup_timeout_s + 5), httpx.Client(trust_env=False, timeout=2, follow_redirects=False) as client:
        def ready():
            try:
                health = client.get(base + "/health")
                models = client.get(base + "/v1/models")
                return health.status_code == 200 and models.status_code == 200 and any(item.get("id") == "incidentlens-qwen-local" for item in models.json().get("data", []))
            except (httpx.HTTPError, ValueError):
                return False
        if ready():
            return
        process = _processes.get(base)
        if process is None or process.poll() is not None:
            binary = shutil.which(settings.qwen_server_bin)
            if binary is None and settings.qwen_server_bin == "llama-server":
                bundled = directory.parent / "runtime" / ("llama-server.exe" if os.name == "nt" else "llama-server")
                if bundled.is_file():
                    binary = str(bundled)
            if binary is None:
                raise ValueError("llama-server runtime missing; set QWEN_SERVER_BIN to its executable path")
            command = [binary, "-m", str(model), "--mmproj", str(projector), "--host", parsed.hostname, "--port", str(parsed.port or 80), "--alias", "incidentlens-qwen-local", "-c", str(settings.qwen_context_size), "--parallel", "1", "--no-mmproj-offload", "-ngl", "0", "--image-min-tokens", "1024", "--image-max-tokens", "1024"]
            log = runtime_data / "qwen-runtime.log"
            with log.open("ab") as stream:
                process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            _processes[base] = process
        deadline = time.monotonic() + settings.qwen_startup_timeout_s
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError("Qwen runtime exited; inspect backend/data/qwen-runtime.log")
            if ready():
                return
            time.sleep(0.25)
        process.terminate()
        raise ValueError("Qwen runtime startup timed out")


class LocalQwenProvider(SelfHostedVLMProvider):
    def __init__(self, config: ProviderConfig, settings: Settings):
        super().__init__(config)
        self.settings = settings

    def analyze(self, context):
        # Fail before launching a model when the user's editable prompt is unavailable.
        read_prompt(self.config.prompt_path)
        ensure_qwen_runtime(self.settings)
        return super().analyze(context)


def create_local_provider(settings: Settings | None = None) -> LocalQwenProvider:
    settings = settings or get_settings()
    validate_local_endpoint(settings.qwen_endpoint)
    config = ProviderConfig("self_hosted", settings.qwen_endpoint, "incidentlens-qwen-local", settings.qwen_model_file, timeout_s=settings.qwen_timeout_s, max_attempts=1, max_frames=settings.qwen_batch_frames, prompt_version="qwen-local-1", prompt_path=settings.qwen_prompt_path, outputs_path=settings.qwen_outputs_path)
    create_provider(config)  # Reuse existing config validation without creating a client.
    return LocalQwenProvider(config, settings)
