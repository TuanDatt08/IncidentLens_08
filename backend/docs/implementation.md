# Backend implementation map

Đối chiếu ngày 2026-10-03. Source inspection + Python suite hiện tại; chưa live VLM/GPU/PG deployment.

## Active path

| Stage | Source | Đã có | Còn thiếu theo tools |
| --- | --- | --- | --- |
| Upload | [incidents.py](../services/incidents.py), [storage.py](../services/storage.py) | MP4/optional CSV, stream 1 MiB chunks, size cap, ffprobe, READY, cleanup lỗi | Multipart sessions/resume/checksum đầu vào/object storage |
| Telemetry | [telemetry.py](../services/telemetry.py) | UTF-8 BOM, `sec_from_incident` numeric/finite/strict increasing, select window | ROS2, epoch/unit normalization, signal quality |
| Localization | [processing.py](../services/processing.py) | 5 sampled frames, validated single incident window, collision offset bounds | Rule/log whole-recording detection, nhiều candidates, sparse segments/coverage |
| Evidence | [video.py](../services/video.py), [reports.py](../services/reports.py) | Clip/frame/telemetry slice; hash/size/path validation và atomic persistence | Per-claim source/time links, stable candidate manifest, privacy gate |
| VLM | [vlm.py](../services/vlm.py) | OpenAI image blocks + structured output hai pass | V2 contract, timestamp từng Pass2 frame, privacy, second provider, usage/cost |
| Jobs | [jobs.py](../services/jobs.py), [worker.py](../worker.py) | Database lease, heartbeat, reclaim, attempt limit, stale attempt rejection | Segment checkpoints/resume/cancel operation/resource/call budgets |
| Review | [review.py](../services/review.py) | DRAFT edit, optimistic version, submit/approve/reject reason + audit | Authenticated RBAC, different submitter/reviewer, reopen, transition snapshots |
| Reads | [reports.py](../services/reports.py), [media.py](../services/media.py) | Report read không gọi model; evidence scopes/hash, media paths guarded | Approved snapshot read model V2, masked playback, authenticated scopes |

## Data ownership

[tables.py](../models/tables.py) chứa six tables và unique/index guards; [migration](../alembic/versions/20260923_rav18_initial.py) tạo schema. SQLAlchemy dùng `DATABASE_URL`; compose triển khai PostgreSQL, tests thông thường dùng SQLite. PostgreSQL locking/concurrency không được suy là verified từ SQLite.

Public v1 models ở [contracts.py](../models/contracts.py) được Backend và API import; timeline/factors v1 còn `Any`. [IncidentAnalysisV2/AIIncidentAnalysisV2](../models/analysis_v2.py) và JSON Schema strict đã thêm qua RAV-001, chưa được provider/routes v1 tiêu thụ tới migration RAV-006/016. Factual IncidentRecord tách AnalysisReport, không gộp collision/ego thành kết luận VLM.

## Legacy code cần phân biệt

`incident_ingestion.py` → `package_repository.py`/`logs.py` là package/JSON ingestion cũ. `workflow_repository.py` là JSON store và comment “no SQLAlchemy/Postgres” đã lỗi thời với active path. `logs.py` dùng pandas, nhưng pandas không nằm trong requirements hiện tại. Không coi timestamp support ở code không được route gọi là capability của API active. Chưa xóa/move logic legacy vì cần task cleanup và caller/import check riêng.

## Boundaries còn thiếu

`require_demo_access` chỉ deny production media/review, chưa identity thật. Upload/analyze/metadata/report reads chưa có authenticated scope; production không an toàn chỉ vì media 403. `vlm.py` gửi image/telemetry chưa che sang API; external pipeline hiện không đáp ứng privacy SPEC. Không dùng dữ liệu thật nhạy cảm trước hoàn tất RAV-005/014.
