# Traceability và kiểm tra coverage

Master index: [functional requirements](../specs/functional-requirements.md). Mỗi requirement có task liên kết; mỗi task có SPEC/ADR/sprint/dependencies và test path kế hoạch. [NFR index](../specs/non-functional-requirements.md) nối reliability/privacy/provenance/performance tới task.

## Ví dụ xuyên suốt

Product goal evidence-grounded draft → REQ-DET-001 → [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md) → [Sprint 02](../planning/sprints/sprint-02-incident-detection.md) → [RAV-003](../tasks/RAV-003-candidate-detection.md) → dự kiến `backend/services/candidate_detection.py` → dự kiến `tests/backend/test_services/test_candidate_detection.py` → AC nhiều cửa sổ, merge deterministic, coverage/budget.

Code/test paths dự kiến chưa phải implementation evidence. Khi task hoàn thành, ghi command/artifact/commit thực tế vào task, cập nhật sprint rồi backlog.

## Dependency order để bắt đầu

1. RAV-001 schema và RAV-002 normalization; chuẩn bị RAV-014 identity và RAV-018 expert protocol sớm.
2. RAV-012 time alignment → RAV-003 candidates → RAV-004 extraction → RAV-005 privacy.
3. RAV-006 provider contract và RAV-009 evidence validator → RAV-007 external/RAV-008 self-host adapters. Real runs chờ policy/hardware, mock contract vẫn thực hiện được.
4. RAV-016 API V2 có thể bắt đầu sau RAV-001, fixture hợp đồng được pin trước FE. RAV-013 snapshot sau schema/auth → RAV-010 review → RAV-017 FE.
5. RAV-015 checkpoint/budget sau candidates/extraction → RAV-020 observability; RAV-019 measured comparison sau hai adapter, expert data và metrics.

RAV-011 contract/mock/local upload prototype có thể làm sớm. Production storage adapter cần ADR-006 ACCEPTED; không gate toàn pipeline. RAV-017 full upload flow chờ RAV-011 đủ acceptance.

## Những điểm còn cần owner

Production storage, identity issuer/claims/session, data egress policy, dataset consent/labels, GPU/API access, threshold/budget/retention và estimates/capacity. Giữ hai inference modes mở; không diễn giải API reference implementation thành lựa chọn production.

## Closure

Coverage DONE phải có code/test đúng AC. Delivery Done yêu cầu review/merge; sprint Closed yêu cầu toàn bộ scope đã hoàn thành hoặc được owner chuyển scope có ghi lịch sử. Release AI cần benchmark chuyên gia riêng; 58 software tests không thay thế gate này.
