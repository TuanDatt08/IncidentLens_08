# Backend role

- Đọc [governance](../tools/AGENTS.md), task/SPEC/ADR trước sửa code.
- Domain logic, database, worker, privacy/evidence validation ở đây. HTTP parsing/response routing ở `../api`; UX ở `../frontend`.
- Role-specific docs đặt `docs/`; requirement/ADR/task canonical giữ ở `../tools`, liên kết thay vì copy.
- Public models hiện ở `models/contracts.py` và được API dùng chung. Migration V2 phải phối hợp API; không đổi payload v1 hoặc move model chỉ để đổi folder.
- Chỉ sửa active path sau trace callers; legacy JSON store không phải database hiện hành.
- Từ root chạy `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; lựa chọn thêm PG/FFmpeg/live tests theo task. Không suy quality AI từ fake VLM.
- Privacy, auth, resource budgets, immutable snapshots theo SPEC; chỉ đánh dấu task DONE khi toàn bộ AC đạt.
