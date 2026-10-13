"""Packaging keeps application and inference runtime independently movable."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def compose(filename):
    result = subprocess.run(
        ['docker', 'compose', '--env-file', '.env.example', '-f', filename, 'config', '--format', 'json'],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, 'P076_DATABASE_URL': 'postgresql://test:test@example.invalid/test?sslmode=require'},
        check=True,
    )
    return json.loads(result.stdout)


def test_app_is_remote_only_and_uses_cloud_database():
    config = compose('docker-compose.app.yml')
    app = config['services']['app']
    assert app['environment']['DATABASE_CLOUD'] == 'true'
    assert app['environment']['QWEN_REMOTE_OLLAMA'] == 'true'
    assert app['environment']['QWEN_ENDPOINT'] == 'http://127.0.0.1:11434/v1/chat/completions'
    assert set(config['services']) == {'app'}
    assert config['networks']['ai']['external'] is True
    dockerfile = (ROOT / 'deploy/app/Dockerfile').read_text()
    assert 'FROM python:3.11-slim' in dockerfile
    assert 'FROM ollama/' not in dockerfile
    proxy = (ROOT / 'deploy/app/nginx.conf').read_text()
    assert 'listen 127.0.0.1:11434' in proxy
    assert 'resolver 127.0.0.11' in proxy
    assert 'http://ollama:11434' in proxy


def test_ai_has_persistent_models_without_database_or_app():
    config = compose('docker-compose.ai.yml')
    assert set(config['services']) == {'ollama'}
    service = config['services']['ollama']
    assert service['image'].startswith('ollama/ollama:')
    assert 'DATABASE_URL' not in service['environment']
    assert service['volumes'][0]['target'] == '/root/.ollama'
    assert config['networks']['ai']['name'] == 'incidentlens-ai'
