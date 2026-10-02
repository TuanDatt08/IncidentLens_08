# API local development

Từ root P-076, cài requirements và cấu hình DATABASE_URL/local env theo [backend development](../../backend/docs/development.md).

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
.\.venv\Scripts\python.exe -m pytest tests/api/ -q
```

Hoặc `docker compose up --build` để postgres/API/worker cùng chạy. Swagger http://localhost:8000/docs; `/api/v1/health` chỉ liveness.

Các test dùng ASGITransport + Alembic temporary SQLite; FFmpeg/VLM ở test E2E thường mocked. Không tự kết luận browser integration hay PostgreSQL multiworker pass. Public contract v1.1 ở [contract](backend-contract-v1.1.md). [SPEC V2](../../tools/specs/api-contracts.md) là đích plan, chưa route.
