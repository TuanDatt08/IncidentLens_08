# Baseline evidence — 2026-10-03

> Historical baseline before recording V2 implementation. Current status/evidence: [execution ledger](task-execution-2026-10-03.md) and canonical tasks.

Workspace: C:/Su/T076/P-076; branch develop; commit 1387662c3a79cbc43d340377ee78218669a51dd9. Git trước thao tác không có thay đổi hiển thị. Không tái dùng đường dẫn checkout cũ C:/Su/P-076/P-076.

Source inspected: backend/services/processing.py (5 frames), telemetry.py (CSV sec_from_incident), vlm.py (image inputs), jobs.py/worker.py (lease/heartbeat/retry), review.py/access.py (demo actors, production deny, edit versions), config.py (video 2048 MiB), docker-compose.yml, frontend/lib/config.ts (mock default), contract v1.1, CI, eval/results/report.md (placeholder metrics).

## Verification

| Check | Command | Result |
| --- | --- | --- |
| Backend/API suite | `.\.venv\Scripts\python.exe -m pytest tests/ -q` | 58 passed, 1 warning, 11.60s |
| Backend/API lint | `.\.venv\Scripts\python.exe -m ruff check backend/ api/` | All checks passed |

Lượt test trong sandbox ban đầu có 14 passed/44 setup errors vì Temp bị từ chối quyền. Chạy lại ngoài sandbox sau khi người dùng cho phép đạt 58 passed; warning còn lại là pytest cache không ghi được, không phải test failure. Suite dùng fake VLM và temporary SQLite; không verified live provider, GPU, browser E2E, production auth/storage/privacy, PostgreSQL deployment hoặc quality benchmark trong lần này. Những mục đó không được đánh dấu DONE từ kiểm tra source.

## Reference adaptation

[workshop-demo-coworking README](https://github.com/dzungtri/workshop-demo-coworking) và [AGENTS](https://github.com/dzungtri/workshop-demo-coworking/blob/base/AGENTS.md) đã đọc trực tiếp: specs/adrs/planning/tasks/docs, reading order, task context và lifecycle nhiều cấp. Repo mẫu dùng LMS/Vite; ở đây áp dụng taxonomy tài liệu vào IncidentLens/FastAPI/Next.js hiện có. Không sao chép app LMS hoặc khẳng định đã đọc templates chưa truy cập được. Xem [reference mapping](reference-mapping.md).

## Follow-up repo audit

[Implementation audit](implementation-audit.md) kiểm active/legacy callers và frontend v1 integration; cập nhật role docs và task coverage. Python suite follow-up: 58 passed/1 cache warning trong 15.32s; Ruff pass; frontend typecheck/lint/production build pass. Browser E2E/PG/live VLM/expert benchmark chưa chạy. Xem audit cho command và giới hạn.
