# ADR-003: Evidence-first analysis

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Mọi claim có căn cứ dẫn evidence/time/source; trạng thái OBSERVED, SUPPORTED_INFERENCE, HYPOTHESIS, UNKNOWN. AI không approve.

## Alternatives Considered

### Option A

VLM sinh báo cáo văn xuôi không có evidence: khó kiểm chứng.

### Option B

Schema claim/time/source/evidence + HITL. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Report văn xuôi tự do khó truy vết. Schema không đủ chứng minh ngữ nghĩa; validator và human review vẫn cần.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-008](ADR-008-versioned-analysis-schema.md), [ADR-009](ADR-009-report-versioning-and-audit.md).

## Related Tasks

[RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-004](../tasks/RAV-004-clip-extraction.md), [RAV-009](../tasks/RAV-009-evidence-validation.md), [RAV-010](../tasks/RAV-010-review-workflow.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
