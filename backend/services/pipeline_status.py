"""Durable, job-scoped diagnostics without changing the legacy jobs contract."""
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def read_status(directory: Path, job_id: str) -> dict:
    path = directory / f'{job_id}.pipeline.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'job_id': job_id, 'stage': 'backend', 'message': 'Đang chờ worker; chưa có chẩn đoán mới.', 'events': []}


def update_status(directory: Path, job_id: str, stage: str, message: str, **details) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    state = read_status(directory, job_id)
    event = {'stage': stage, 'message': message, 'at': datetime.now(UTC).isoformat(), **details}
    state.update(event)
    state['events'] = [*state['events'], event]
    path = directory / f'{job_id}.pipeline.json'
    temporary = path.with_suffix(f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
    return state
