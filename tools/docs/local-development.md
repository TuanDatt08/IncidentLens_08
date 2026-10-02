# Local development

Chạy từ root P-076, không từ tools. Xem [backend runbook hiện có](../../backend/docs/runbook.md).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up --build
```

Điền secret chỉ ở local env; không overwrite .env hiện có. Compose khởi postgres, migrations, backend/worker; API http://localhost:8000/docs. Không chạy live VLM trên media riêng tư trước privacy/egress gate; dùng fake worker theo runbook hiện có cho demo.

Frontend chạy riêng:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

`frontend/lib/config.ts` mặc định USE_MOCK_API=true, base http://localhost:8000/api/v1. Integration v1 dùng NEXT_PUBLIC_USE_MOCK_API=false, đối chiếu contract v1.1; V2 chưa tồn tại runtime.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe -m ruff check backend/ api/
```

Test thông thường dùng temporary SQLite/fake VLM. PostgreSQL+FFmpeg smoke cần DB riêng và opt-in theo runbook; không chạy trên DB production. [Baseline](baseline-evidence.md) ghi checks thực chạy lần tạo bộ docs.

Role-specific guides: [Backend](../../backend/docs/development.md), [API](../../api/docs/development.md), [Frontend](../../frontend/docs/development.md). Shared root setup ở đây; thay implementation guides tại role tương ứng.
