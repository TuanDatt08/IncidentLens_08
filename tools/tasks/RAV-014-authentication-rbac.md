# RAV-014 — Authentication and RBAC

Status: **PARTIAL**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: API, Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 04](../planning/sprints/sprint-04-review-workflow.md)

## Goal

Hoàn thành capability **Authentication and RBAC** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-REV-002](../specs/user-roles.md), [REQ-AUD-001](../specs/non-functional-requirements.md).

ADR: [ADR-007](../adrs/ADR-007-privacy-before-external-inference.md), [ADR-009](../adrs/ADR-009-report-versioning-and-audit.md).

Dependencies: không có task prerequisite; kiểm tra decision gates bên dưới.

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

authenticated principal + server-side role/scope guard.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/access.py; api/main.py; frontend/components/.

Test: `tests/api/test_authorization.py`.

## Acceptance criteria

- [x] Credential thật hoặc test identity signed fixture.
- [x] không tin role header.
- [x] thiếu login 401.
- [x] sai quyền 403.
- [x] cross-recording denied.
- [x] không self-approve.
- [ ] identity provider review trước production integration.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/api/test_authorization.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: HMAC fixture issuer/audience/expiry/roles/scope được ký, missing401/role403/scope404/selfreview403; cookie CSRF header, không tin role header. Production authenticate503 tới khi IdP được review; chưa có review production.

Evidence: [test_authorization.py](../../tests/api/test_authorization.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Demo production guard cho media/review, chưa identity. Còn thiếu: Auth/scope/RBAC tất cả sensitive routes, no self approval. Source: [access.py](../../backend/services/access.py). Test fixture: [test_e2e.py](../../tests/api/test_e2e.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
