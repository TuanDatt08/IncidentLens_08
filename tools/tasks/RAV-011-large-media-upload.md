# RAV-011 — Resumable large-media upload

Status: **TODO**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: API, Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 01](../planning/sprints/sprint-01-foundation.md)

## Goal

Hoàn thành capability **Resumable large-media upload** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-ING-001](../specs/api-contracts.md), [REQ-ING-002](../specs/api-contracts.md).

ADR: [ADR-002](../adrs/ADR-002-background-job-processing.md), [ADR-006](../adrs/ADR-006-large-media-storage.md).

Dependencies: không có task prerequisite; kiểm tra decision gates bên dưới.
Decision gate: chỉ production storage adapter BLOCKED tới ADR-006 được accept. Contract/mock/resume/checksum/local prototype vẫn TODO, có thể thực hiện và review trước quyết định.

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

init_upload/resume/complete_upload với part hash và expiry.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/storage.py; backend/services/incidents.py; api/uploads_v2.py; frontend/components/incidents/upload-form.tsx.

Test: `tests/api/test_upload_v2.py`.

## Acceptance criteria

- [ ] Contract/mock và local prototype độc lập SDK production.
- [ ] Production adapter chỉ được chọn sau ADR-006 ACCEPTED.
- [ ] restart client resume.
- [ ] part corrupt bị reject.
- [ ] complete replay không trùng.
- [ ] size/expiry/scope được kiểm.
- [ ] test workload dài + giới hạn memory có bằng chứng.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/api/test_upload_v2.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Single request FormData; storage stream chunk/size limit. Còn thiếu: Upload session/parts/resume/checksum; production adapter chờ ADR-006. Source: [storage.py](../../backend/services/storage.py). Test fixture: [test_incident_upload.py](../../tests/api/test_incident_upload.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
