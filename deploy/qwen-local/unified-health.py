"""Readiness for the existing app routes and local Qwen, without a login page."""
import json
import os
import urllib.request
from pathlib import Path

for pid in json.loads(Path("/data/run/pids.json").read_text()).values():
    os.kill(pid, 0)
for url in ("http://127.0.0.1:8081/health", "http://127.0.0.1:8000/health", "http://127.0.0.1:3000/incidents", "http://127.0.0.1:8088/api/v1/health"):
    with urllib.request.urlopen(url, timeout=3) as response:
        assert response.status == 200
