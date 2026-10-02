# RAV-017 — Frontend V2 integration

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Frontend; phối hợp: API, Backend.

Role docs: [Frontend](../../frontend/docs/work-items.md), [API](../../api/docs/work-items.md), [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 04](../planning/sprints/sprint-04-review-workflow.md)

## Goal

Hoàn thành capability **Frontend V2 integration** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-API-001](../specs/api-contracts.md), [REQ-EVD-002](../specs/incident-analysis-v2.md), [REQ-REV-003](../specs/user-roles.md).

ADR: [ADR-005](../adrs/ADR-005-versioned-api-migration.md), [ADR-007](../adrs/ADR-007-privacy-before-external-inference.md), [ADR-009](../adrs/ADR-009-report-versioning-and-audit.md).

Dependencies: [RAV-010](RAV-010-review-workflow.md), [RAV-011](RAV-011-large-media-upload.md), [RAV-016](RAV-016-api-v2-migration.md).

## Background / baseline evidence

`frontend/components/review/review-workspace.tsx`, `frontend/lib/config.ts`: UI/mock default. Source v1 đã có job polling/session job ID, PATCH version/409 và evidence seek; audit envelope/rendering còn thiếu, chưa V2 integration. Typecheck/lint/build pass ở audit lần này; browser E2E chưa verified. Không coi source/static checks là production/live-provider evidence.

## Scope and interfaces

Typed V2 client, resume upload, polling, evidence seek, role UI.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): frontend/services/; frontend/types/; frontend/components/incidents/; frontend/components/review/.

Test: `tests/frontend/v2-workflow (test harness chọn trong task)`.

## Acceptance criteria

- [x] Loading/empty/error/cancel/partial/UNANALYZED.
- [x] reload không reanalyze.
- [x] seek time đúng.
- [x] keyboard/accessibility/responsive.
- [x] 401/403/409 có UX.
- [x] typecheck/build và E2E với API thật.
- [x] UI không thay server auth.

- [x] Audit v1/v2 client unwrap đúng envelope và type event fields theo contract; AuditSection được mount, kiểm empty/loading/error bằng API fixture.
- [x] Editor giữ typed claim/source/time/evidence khi sửa, không serialize object rồi lưu lại string.
- [x] Confirmation dialog có accessible title, focus trap/restore và Escape; overlay video play có accessible name.
- [x] Tab/device mới recover active job hoặc hiển thị 409 rõ, không tự tạo analysis trùng.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/frontend/v2-workflow (test harness chọn trong task) -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Real API+production Next E2E: upload, durable job reload/cancel, typed edit, clip-relative seek1.5s từ video2.5s, dialog Escape/focus, two-actor approve, audit,401; desktop1440/mobile390 screenshot inspection không overflow. Node typed-editor/client checks kiểm fields,401/403/409 và expired-upload recovery; audit envelopes/types/mount và loading/empty/error states đã sửa. UI dùng server auth, không role header. Không là exhaustive accessibility audit hoặc production IdP/storage proof.

Evidence: [v2-workflow.py](../../tests/frontend/v2-workflow.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Polling/job storage/PATCH version/409/media seek v1 có. Audit chưa shape/render đúng. Còn thiếu: V2/multipart/auth/privacy/structured claim editor/keyboard/browser E2E. Source: [analysis.service.ts](../../frontend/services/analysis.service.ts). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
