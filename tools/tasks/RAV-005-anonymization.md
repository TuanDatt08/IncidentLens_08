# RAV-005 — Anonymization and privacy gate

Status: **TODO**

Delivery Status: **Todo**

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
- [ ] detector failure chặn egress/playback.
- [ ] external telemetry allowlist.
- [ ] raw URI không phát public.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_anonymization.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Không mask/validation gate. Còn thiếu: Face/plate detector, privacy quality và fail-closed outbound/frontend. Source: [vlm.py](../../backend/services/vlm.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
