# ADR-005: Versioned API migration

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Đưa /api/v2 riêng, migrate FE, kiểm regression, thông báo deprecation rồi mới xóa v1 bằng thay đổi riêng.

## Alternatives Considered

### Option A

Thay payload v1 tại chỗ: phá client/time semantics.

### Option B

Namespace v2 riêng, migration explicit và regression v1. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

V1 collision-relative và single report khác V2 video_seconds/multiple candidates; chuyển đổi mất nghĩa phải explicit hoặc báo không chuyển được.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-008](ADR-008-versioned-analysis-schema.md).

## Related Tasks

[RAV-016](../tasks/RAV-016-api-v2-migration.md), [RAV-017](../tasks/RAV-017-frontend-v2-integration.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
