# Backend — domain logic, dữ liệu và worker

Role Backend sở hữu nghiệp vụ IncidentLens, persistence, media processing, VLM và worker. HTTP endpoints ở [api](../api/README.md); UI ở [frontend](../frontend/README.md).

| Folder/file | Trách nhiệm |
| --- | --- |
| `services/` | Ingestion, video/telemetry, jobs, reports, evidence, review, access policy |
| `models/` | SQLAlchemy tables và Pydantic models dùng chung với API |
| `alembic/` | Database migrations |
| `worker.py` | Lease/heartbeat và thực thi analysis |
| `agents/` | LangGraph scaffold; chưa orchestrate pipeline production |
| `docs/` | Tài liệu implementation, development, vận hành của Backend |

Đọc [AGENTS](AGENTS.md) → [docs](docs/README.md) → task liên quan trong [tools/tasks](../tools/tasks/README.md). [SPEC/ADR](../tools/README.md) vẫn là nguồn chuẩn dùng chung.

Luồng active: `api/incidents.py` → `services/incidents.py` → database + LocalStorage; worker → `services/processing.py` → VLM → `services/reports.py`. `incident_ingestion.py`, `logs.py`, `package_repository.py`, `workflow_repository.py` là đường legacy, không được API hiện tại gọi. Xem [implementation](docs/implementation.md) trước khi sửa.
