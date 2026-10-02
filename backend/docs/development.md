# Backend development

Chạy từ root repository. Settings: [config.py](../config.py); database/migrations: [db.py](../db.py), `alembic.ini` ở root. Secret ở local env, không commit.

```powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.worker
```

Worker thật dùng OPENAI_API_KEY/model config; chỉ chạy external với dữ liệu được policy cho phép. Fake job demo: [runbook](runbook.md). Test nhanh:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/ tests/api/ -q
.\.venv\Scripts\python.exe -m ruff check backend/ api/
```

SQLite/fake VLM pass xác minh wiring/contracts. PG+FFmpeg smoke dùng DB riêng/opt-in theo runbook, không main DB. Public contract ở [API docs](../../api/docs/backend-contract-v1.1.md); thay contract phải phối hợp API và frontend.
