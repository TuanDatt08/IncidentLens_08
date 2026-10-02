# ADR-006: Large media storage

- Status: PROPOSED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

Behavior đã chốt: multipart/resume/checksum + playback Range/stream. Chưa chọn S3-compatible, cloud managed hoặc filesystem dev + object production.

## Alternatives Considered

### Option A

S3-compatible object storage: cần đo vận hành, request/egress và resume.

### Option B

Cloud managed object storage: cần đo giá, region, policy và SDK. Cả hai chưa chọn. Filesystem dev là phương án bổ sung, không mặc nhiên production.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Cần deployment region, capacity/retention, access model, egress, request/storage cost và resume proof. Owner accept ADR sau bảng so và thử representative upload; trước đó task production adapter BLOCKED.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Chỉ production storage adapter bị block; contract/mock/dev foundation vẫn triển khai được.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-002](ADR-002-background-job-processing.md), [ADR-007](ADR-007-privacy-before-external-inference.md).

## Related Tasks

[RAV-011](../tasks/RAV-011-large-media-upload.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
