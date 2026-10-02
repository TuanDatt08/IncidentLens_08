# ADR-010: AI evaluation strategy

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Cùng expert cases đo recall/factor/evidence/completeness/acceptance/latency/cost; cost per accepted incident tính preprocess/storage/inference/retry/review.

## Alternatives Considered

### Option A

Chọn model theo cảm nhận/giá token hoặc LLM judge duy nhất.

### Option B

Expert-labelled benchmark trên cùng cases + full cost. Chọn phương án này.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Tests fake VLM không chứng minh quality. Nhãn, thresholds, GPU và policy là dependency còn mở; không chốt provider bằng giá token.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-001](ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-004](ADR-004-vlm-provider-abstraction.md), [ADR-007](ADR-007-privacy-before-external-inference.md).

## Related Tasks

[RAV-018](../tasks/RAV-018-expert-benchmark.md), [RAV-019](../tasks/RAV-019-provider-cost-comparison.md), [RAV-020](../tasks/RAV-020-observability-runbook.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
