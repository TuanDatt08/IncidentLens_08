# ADR-001: Hybrid incident analysis pipeline

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Quét log/rule rẻ, đề cử windows; khi log thiếu dùng sparse segment rồi dense quanh candidate. VLM chỉ phân tích evidence liên quan.

## Alternatives Considered

### Option A

Gửi toàn bộ video dài đến VLM: baseline nhỏ nhưng chi phí/riêng tư khó kiểm soát.

### Option B

Log/rule → candidate windows → VLM; video fallback có coverage. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Gửi video dài toàn bộ và tự-host quét toàn bộ có chi phí/latency khó kiểm soát. Candidate budget cần coverage để không che mất phần chưa phân tích.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-002](ADR-002-background-job-processing.md), [ADR-003](ADR-003-evidence-first-analysis.md), [ADR-004](ADR-004-vlm-provider-abstraction.md), [ADR-006](ADR-006-large-media-storage.md), [ADR-007](ADR-007-privacy-before-external-inference.md), [ADR-010](ADR-010-ai-evaluation-strategy.md).

## Related Tasks

[RAV-001](../tasks/RAV-001-analysis-schema-v2.md), [RAV-002](../tasks/RAV-002-log-normalization.md), [RAV-003](../tasks/RAV-003-candidate-detection.md), [RAV-004](../tasks/RAV-004-clip-extraction.md), [RAV-006](../tasks/RAV-006-vlm-adapter.md), [RAV-007](../tasks/RAV-007-external-vlm.md), [RAV-010](../tasks/RAV-010-review-workflow.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
