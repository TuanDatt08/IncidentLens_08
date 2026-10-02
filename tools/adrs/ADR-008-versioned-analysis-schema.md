# ADR-008: Versioned analysis schema

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

IncidentAnalysisV2 strict + provenance; không reinterpret/regenerate snapshot cũ khi đọc. Migration explicit tạo version.

## Alternatives Considered

### Option A

Dùng schema mới để đọc lại/regenerate report cũ: mất provenance.

### Option B

Versioned schema/snapshot và explicit migration. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Output constrained giảm lỗi format, vẫn cần semantic/evidence/time validation. Giữ v1 model riêng để compatibility.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-003](ADR-003-evidence-first-analysis.md), [ADR-005](ADR-005-versioned-api-migration.md), [ADR-009](ADR-009-report-versioning-and-audit.md).

## Related Tasks

[RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-009](../tasks/RAV-009-evidence-validation.md), [RAV-013](../tasks/RAV-013-report-versioning-audit.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
