# ADR-007: Privacy before external inference

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Raw restricted → extract → face/plate mask → validate → external boundary. Self-host nội bộ có thể dùng raw theo policy; frontend vẫn masked.

## Alternatives Considered

### Option A

Gửi raw media/log hoặc coi blur tự động luôn đạt: không đáp ứng privacy.

### Option B

Mask + validate trước external, frontend dùng masked; self-host theo internal policy. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Thêm preprocess và kiểm tra; privacy failure chặn egress. Quyết định pipeline không đồng nghĩa đã cho phép dùng external API với dữ liệu thật.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-004](ADR-004-vlm-provider-abstraction.md).

## Related Tasks

[RAV-005](../tasks/RAV-005-anonymization.md), [RAV-007](../tasks/RAV-007-external-vlm.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
