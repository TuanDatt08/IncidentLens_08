# ADR-002: Background job processing

- Status: ACCEPTED
- Date: 2026-10-03
- Decision Owners: chủ dự án RAV-18 theo thiết kế đã xác nhận; chưa chỉ định tên cá nhân

## Context

IncidentLens cần evidence-grounded draft từ video/log dài và human review. Implementation hiện tại được kiểm tra ở [baseline](../docs/baseline-evidence.md); status ADR là decision status, không phải implementation status.

## Decision

API nhận command/metadata/status; worker xử lý FFmpeg/log/privacy/model/validation ngoài HTTP lifecycle. Giữ PostgreSQL job lease hiện có làm nền; chưa chọn queue mới.

## Alternatives Considered

### Option A

Xử lý dài trong HTTP request: dễ timeout, khó resume.

### Option B

API tạo job; worker riêng. Chọn phương án này; queue mới chưa được chốt.

## Consequences

### Positive

Behavior và boundary rõ, task/validator/benchmark có thể kiểm tra theo SPEC.

### Negative

Video dài cần checkpoint/heartbeat/resource cap. Không thêm Redis/Celery nếu PostgreSQL worker hiện đáp ứng; chỉ đổi sau đo.

## Constraints

Giữ compatibility v1.1, AI chỉ tạo DRAFT, privacy trước external inference, scope/actor được kiểm server. Không tự mua GPU/chọn cloud hoặc bật egress với dữ liệu thật. Provider production và resource budget cần bằng chứng trước release.

## Related Specifications

[Vision](../specs/product-vision.md), [workflow](../specs/incident-workflow.md), [requirements](../specs/functional-requirements.md), [schema](../specs/incident-analysis-v2.md), [API](../specs/api-contracts.md), [privacy](../specs/security-privacy.md), [evaluation](../specs/evaluation.md).

## Related ADRs

[ADR-001](ADR-001-hybrid-incident-analysis-pipeline.md).

## Related Tasks

[RAV-015](../tasks/RAV-015-job-resume-budget.md), [RAV-020](../tasks/RAV-020-observability-runbook.md).

## Supersedes

None.

## Superseded By

None. Quyết định mới thực sự thay thế phải có ADR mới; giữ nội dung quyết định cũ và thêm link/status, không viết lại lịch sử.
