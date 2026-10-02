# Đối chiếu implementation với tools — 2026-10-03

Checkout `C:/Su/T076/P-076`, branch `develop`, code HEAD `1387662c3a79cbc43d340377ee78218669a51dd9`. Tài liệu tools còn untracked trước audit; không suy đã merge từ delivery status. Audit dùng active callers, models/routes/frontend services và tests; không dùng memory checkout cũ để xác nhận hiện trạng.

## Kết luận

Repo có đường đi demo v1.1: MP4 + optional canonical CSV → job nền hai pass → report/evidence → Engineer edit/version → submit → approve/reject + audit. Media có Range và path/scope checks. Phần mềm baseline có test; MVP V2 trong tools chưa hoàn chỉnh.

Baseline trước triển khai: **11 PARTIAL, 8 TODO, 1 BLOCKED**, chưa task nào đạt toàn bộ acceptance V2 để DONE. RAV-007 được điều chỉnh từ TODO sang PARTIAL vì đã có external OpenAI adapter; privacy/V2 vẫn thiếu. Baseline tính riêng: các checks đã pass được ghi DONE trong phạm vi kiểm tra, không dùng làm DONE cho capability production. Cập nhật sau RAV-001 ở cuối file, giữ bảng audit ban đầu để truy lịch sử.

## Verification

| Check | Result | Phạm vi/giới hạn |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests/ -q` | 58 passed, 1 cache warning, 15.32s | SQLite/Alembic, fake VLM, media phần lớn mocked |
| `.\.venv\Scripts\python.exe -m ruff check backend/ api/` | PASS | Python lint |
| `npm --prefix frontend run typecheck` | PASS, exit 0 | TypeScript compile check |
| `npm --prefix frontend run lint` | PASS, no ESLint warnings/errors | Static lint |
| `npm --prefix frontend run build` | PASS, production compilation + route generation | Chưa browser/network E2E |
| PostgreSQL multiworker/FFmpeg smoke | NOT_RUN | Có opt-in test riêng, không trong pytest default discovery |
| Live VLM/self-host GPU, anonymization, expert benchmark | NOT_RUN / MISSING | Chưa quality/cost/latency production evidence |

Frontend ban đầu thiếu dependencies; cài đúng lockfile bằng npm ci, không thay package versions. Impeccable context engine chưa cài, bị chặn cache; kiểm UI từ source trực tiếp, không chấm điểm visual/contrast/performance khi chưa browser evidence.

## Task-by-task coverage

| Task / status | Đã có | Còn thiếu | Evidence |
| --- | --- | --- | --- |
| [RAV-001](../tasks/RAV-001-analysis-schema-v2.md) TODO | Chỉ v1 Pydantic; nested lists Any. | V2 enum/object đóng/time/evidence contract. | [contracts.py](../../backend/models/contracts.py); [test_contracts.py](../../tests/api/test_contracts.py) |
| [RAV-002](../tasks/RAV-002-log-normalization.md) PARTIAL | Active CSV parser streaming, clock strict. Legacy pandas path không được API gọi. | ROS2/epoch/unit/signals normalization. | [telemetry.py](../../backend/services/telemetry.py); [test_telemetry.py](../../tests/backend/test_services/test_telemetry.py) |
| [RAV-003](../tasks/RAV-003-candidate-detection.md) TODO | Pass1 chỉ 5 frames và single candidate. | Log/rule whole route, multi-window/sparse coverage/budget. | [processing.py](../../backend/services/processing.py); [test_processing.py](../../tests/backend/test_services/test_processing.py) |
| [RAV-004](../tasks/RAV-004-clip-extraction.md) PARTIAL | Clip + frame + telemetry slice/hash có. | Multiple candidate ID/order manifest; real media seek evidence. | [video.py](../../backend/services/video.py); [test_processing.py](../../tests/backend/test_services/test_processing.py) |
| [RAV-005](../tasks/RAV-005-anonymization.md) TODO | Không mask/validation gate. | Face/plate detector, privacy quality và fail-closed outbound/frontend. | [vlm.py](../../backend/services/vlm.py) |
| [RAV-006](../tasks/RAV-006-vlm-adapter.md) PARTIAL | Protocol pass1/pass2 và OpenAI adapter có. | Provider.analyze V2, frame timestamps/provenance/usage. | [processing.py](../../backend/services/processing.py); [test_vlm.py](../../tests/backend/test_services/test_vlm.py) |
| [RAV-007](../tasks/RAV-007-external-vlm.md) PARTIAL | External OpenAI keyframe inference đã có và mocked contract test. | Privacy/allowlist/V2/evidence checks; chưa live benchmark. | [vlm.py](../../backend/services/vlm.py); [test_vlm.py](../../tests/backend/test_services/test_vlm.py) |
| [RAV-008](../tasks/RAV-008-self-hosted-vlm.md) TODO | Không self-host adapter/runtime config. | Internal endpoint adapter, model revision/GPU benchmark. | [config.py](../../backend/config.py) |
| [RAV-009](../tasks/RAV-009-evidence-validation.md) PARTIAL | EvidenceV1 path/hash/size/window asset checks có. | Per-claim ID/time/source/cross scope semantic gate trong edit/approve. | [reports.py](../../backend/services/reports.py); [test_results.py](../../tests/api/test_results.py) |
| [RAV-010](../tasks/RAV-010-review-workflow.md) PARTIAL | Submit/approve/reject reason/state, stale edit 409, demo audit có. | Role thật, separate submitter/reviewer, reopen/transition snapshots. | [review.py](../../backend/services/review.py); [test_e2e.py](../../tests/api/test_e2e.py) |
| [RAV-011](../tasks/RAV-011-large-media-upload.md) TODO | Single request FormData; storage stream chunk/size limit. | Upload session/parts/resume/checksum; production adapter chờ ADR-006. | [storage.py](../../backend/services/storage.py); [test_incident_upload.py](../../tests/api/test_incident_upload.py) |
| [RAV-012](../tasks/RAV-012-timestamp-synchronization.md) PARTIAL | Collision offset relative↔video conversion và bounds có. | Anchor/drift/residual/quality + unknown alignment. | [video-time.ts](../../frontend/lib/video-time.ts); [test_processing.py](../../tests/backend/test_services/test_processing.py) |
| [RAV-013](../tasks/RAV-013-report-versioning-audit.md) PARTIAL | Generation và edit snapshots; read không gọi VLM. | Transition snapshots + real actor, immutable approved version reads. | [reports.py](../../backend/services/reports.py); [test_e2e.py](../../tests/api/test_e2e.py) |
| [RAV-014](../tasks/RAV-014-authentication-rbac.md) TODO | Demo production guard cho media/review, chưa identity. | Auth/scope/RBAC tất cả sensitive routes, no self approval. | [access.py](../../backend/services/access.py); [test_e2e.py](../../tests/api/test_e2e.py) |
| [RAV-015](../tasks/RAV-015-job-resume-budget.md) PARTIAL | Lease heartbeat/3 attempts/reclaim/stale attempt fencing có. | Segment checkpoint/resume/partial/cancel/budget. | [jobs.py](../../backend/services/jobs.py); [test_worker.py](../../tests/api/test_worker.py) |
| [RAV-016](../tasks/RAV-016-api-v2-migration.md) TODO | Public routes chỉ /api/v1. | Separate V2 schemas/OpenAPI/fixtures, regression giữ v1. | [main.py](../../api/main.py); [test_contracts.py](../../tests/api/test_contracts.py) |
| [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) PARTIAL | Polling/job storage/PATCH version/409/media seek v1 có. Audit chưa shape/render đúng. | V2/multipart/auth/privacy/structured claim editor/keyboard/browser E2E. | [analysis.service.ts](../../frontend/services/analysis.service.ts) |
| [RAV-018](../tasks/RAV-018-expert-benchmark.md) TODO | Evaluation report template, không expert dataset/rubric. | Licenced manifest/GT/splits/disagreements/threshold sign-off. | [report.md](../../eval/results/report.md) |
| [RAV-019](../tasks/RAV-019-provider-cost-comparison.md) BLOCKED | Không measured provider comparison. | Chờ data/threshold/GPU/API policy/usage metrics trước quality-cost test. | [inference-options.md](../../tools/docs/inference-options.md) |
| [RAV-020](../tasks/RAV-020-observability-runbook.md) PARTIAL | pass/progress/error + backend CI có. | stage coverage/cost/usage metrics, frontend CI, PG/drills/retention. | [jobs.py](../../backend/services/jobs.py); [test_jobs.py](../../tests/api/test_jobs.py) |

## Requirement coverage

Requirement index [functional requirements](../specs/functional-requirements.md) vẫn 10 Partial / 11 Missing: không có complete V2 requirement chỉ từ baseline demo. Các sub-behavior đã có: MP4/CSV input validation, report DRAFT persistence, edit optimistic version, source/evidence Range, read report không gọi VLM, attempt fencing. Chưa đủ để mark toàn REQ-ING/SYNC/EVD/REV/AUD/JOB implemented.

NFR hiện đạt một phần reliability/hash/path protection và đọc không regenerate. Chưa có segment resume, resource budget, authenticated scope/privacy, stage coverage/cost metrics hay full model/prompt/schema/config provenance. NFR-AI-002 phần GET không regenerate đã có; explicit rerun/version lineage chưa có.

## Những gap cụ thể cần xử lý

1. **Privacy/external boundary — RAV-005/007:** adapter gửi raw image blocks và telemetry, không mask/validate/allowlist. Production 403 media không ngăn worker gọi provider bên ngoài.
2. **Auth — RAV-014/010:** chỉ demo guard cho review/media; upload/analyze/read chưa principal/scoped auth. Không phân tách submitter/reviewer thật.
3. **Localization dài — RAV-003/015:** đúng 5 frame toàn video, chỉ một window. Kết quả false hiện không có coverage; không chứng minh không có incident.
4. **Evidence/schema — RAV-001/009:** danh sách Any, chưa enum claim_status/per-claim ID/time/source. Hash/path kiểm tài sản khác với xác nhận ngữ nghĩa nhận định.
5. **Snapshot — RAV-013:** initial/edit tạo ReportVersion; transitions chỉ đổi row + audit, không snapshot mới. GET đọc row hiện tại + max version, không immutable approved snapshot V2.
6. **Frontend audit — RAV-017/020:** API audit trả object items nhưng service mong mảng; types yêu cầu event_id/role/incident_id mà API event không trả. AuditSection chưa được mount ở review workspace. V1 integration chỉ phần lớn đã làm.
7. **Frontend reload/claims — RAV-017:** sessionStorage không dùng qua tab/device; editor đổi structured object thành string lists; không đảm bảo evidence/claim fidelity.
8. **Legacy — Backend:** JSON workflow và pandas log parser không nằm trên active route; comment “no Postgres” đã cũ. Không coi legacy support là API feature.
9. **Operations — RAV-020:** CI chỉ ruff/pytest backend, trigger PR main; chưa frontend gate và PR develop gate. Expert evaluation report còn placeholder.

## Có thể hoàn thiện tiếp theo

Common pipeline làm được trước quyết định provider/storage: schema → normalization/alignment → candidates → extraction/privacy → evidence validator/provider contract. API V2 fixtures sau schema; auth/snapshot/review/FE theo dependencies. Contract/mock/local multipart prototype không bị ADR-006 chặn; chỉ production storage adapter cần accept ADR đó.

Hai inference options giữ mở theo [comparison](inference-options.md); mock contract có thể triển khai, real comparison chờ dataset/threshold/hardware/egress approval. Cần benchmark chuyên gia trước production claim.

## Hoàn thiện trong lượt này

Tổ chức docs cho Backend/API/Frontend, chuyển docs implementation/contract về đúng role, thêm hướng dẫn role/ownership, cập nhật backlog/task evidence và bỏ mô tả FE SSE đã lỗi thời. Runtime logic giữ cấu trúc active hiện có; các gap nêu trên được cập nhật task, chưa tự triển khai feature V2 hoặc sửa code legacy.

## Implementation follow-up — RAV-001

[Analysis schema V2](../../backend/docs/analysis-schema-v2.md) có runtime strict và business/AI JSON Schema exports; 55 contract regressions mới. Full suite: 113 passed trong 9.41s, `ruff check .` pass. Local acceptance RAV-001 DONE; remote CI/PR/merge pending. Coverage mới: 1 DONE (local), 11 PARTIAL, 7 TODO, 1 BLOCKED. Schema chưa được active VLM/API tích hợp; requirement REQ-AI-001 chuyển Partial, không suy output pipeline đã V2.
