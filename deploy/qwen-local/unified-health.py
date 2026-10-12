"""Readiness for the existing app routes and local Qwen, without a login page."""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, "/app")
from sqlalchemy import text  # noqa: E402

from backend.db import get_session_factory  # noqa: E402

with get_session_factory()() as session:
    assert session.scalar(text("SELECT 1")) == 1

for pid in json.loads(Path("/data/run/pids.json").read_text()).values():
    os.kill(pid, 0)
urls = ["http://127.0.0.1:8000/health", "http://127.0.0.1:3000/incidents", "http://127.0.0.1:8088/api/v1/health"]
if os.getenv("QWEN_REMOTE_OLLAMA", "false").lower() != "true":
    urls.append("http://127.0.0.1:11434/api/tags")
for url in urls:
    with urllib.request.urlopen(url, timeout=3) as response:
        assert response.status == 200
