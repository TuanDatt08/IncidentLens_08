# ADR-009: Report versioning and audit

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Generation/edit/submit/reject/reopen/approve có immutable snapshots và audit cùng transaction; optimistic version conflict; approved amendment duyệt lại.

## Alternatives Considered

### Option A

Overwrite report row và mất lịch sử transition: khó audit.

### Option B

Snapshot cho generation/edit/transition và actor thật. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Code hiện tại chỉ edit tạo ReportVersion, transition chưa tạo version và actor demo. Chênh lệch được task hóa, không coi đã done.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-008](ADR-008-versioned-analysis-schema.md).

## Related Tasks

[RAV-010](../tasks/RAV-010-review-workflow.md), [RAV-013](../tasks/RAV-013-report-versioning-audit.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
