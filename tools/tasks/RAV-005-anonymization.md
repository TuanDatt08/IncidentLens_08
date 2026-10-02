# RAV-005 — Anonymization and privacy gate

Status: **PARTIAL**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: API, Frontend.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md), [Frontend](../../frontend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 02](../planning/sprints/sprint-02-incident-detection.md)

## Goal

Hoàn thành capability **Anonymization and privacy gate** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-PRV-001](../specs/security-privacy.md), [REQ-PRV-002](../specs/security-privacy.md).

ADR: [ADR-007](../adrs/ADR-007-privacy-before-external-inference.md).

Dependencies: [RAV-004](RAV-004-clip-extraction.md).

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

mask_and_validate(bundle, policy) -> PrivacyResult.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/anonymization.py; backend/services/media.py.

Test: `tests/backend/test_services/test_anonymization.py`.

## Acceptance criteria

- [ ] Mặt/biển số thuộc tập fixture được che và review.
- [x] detector failure chặn egress/playback.
- [x] external telemetry allowlist.
- [x] raw URI không phát public.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_anonymization.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Real FFmpeg che vùng FACE/PLATE synthetic với detector/review callback, failure chặn output; telemetry allowlist và RAW media 403. Chưa có detector accuracy trên annotated face/plate thật hoặc full-motion clip masking; chưa đủ AC đầu.

Evidence: [test_anonymization.py](../../tests/backend/test_services/test_anonymization.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Không mask/validation gate. Còn thiếu: Face/plate detector, privacy quality và fail-closed outbound/frontend. Source: [vlm.py](../../backend/services/vlm.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
