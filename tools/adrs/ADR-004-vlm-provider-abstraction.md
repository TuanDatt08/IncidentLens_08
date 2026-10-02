# ADR-004: VLM provider abstraction

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Một VLMProvider.analyze(context) trả AnalysisV2; provider specifics trong adapter, chọn ở factory. External và self-host có cùng schema/evaluation.

## Alternatives Considered

### Option A

Couple business vào một provider: thay model buộc sửa nhiều nơi.

### Option B

Một adapter contract cho external_api và self_hosted. Chọn phương án này; nơi inference production chưa chọn.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Protocol hiện có pass1/pass2 cần migration, không rewrite toàn bộ business. Một adapter API làm reference đầu tiên không khóa production lựa chọn.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-007](ADR-007-privacy-before-external-inference.md), [ADR-008](ADR-008-versioned-analysis-schema.md), [ADR-010](ADR-010-ai-evaluation-strategy.md).

## Related Tasks

[RAV-006](../tasks/RAV-006-vlm-adapter.md), [RAV-007](../tasks/RAV-007-external-vlm.md), [RAV-008](../tasks/RAV-008-self-hosted-vlm.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
