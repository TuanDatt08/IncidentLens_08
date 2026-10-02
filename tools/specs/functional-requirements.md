# Functional requirements — master index

SHALL là nghĩa vụ đích. Trạng thái là snapshot ngày 2026-10-03, không làm yếu requirement; Partial là existing chưa đạt toàn bộ, Missing là chưa có bằng chứng implementation. Implemented chỉ dùng khi acceptance được chứng minh.

| ID | System SHALL | Status | Tasks |
| --- | --- | --- | --- |
| REQ-ING-001 | Nhận video + telemetry được hỗ trợ, kiểm tra format/checksum/size | Partial | [RAV-002](../tasks/RAV-002-log-normalization.md), [RAV-011](../tasks/RAV-011-large-media-upload.md) |
| REQ-ING-002 | Upload lớn multipart/resume không giữ toàn file trong RAM | Missing | [RAV-011](../tasks/RAV-011-large-media-upload.md) |
| REQ-SYNC-001 | Thiết lập common video time basis trước fusion | Partial | [RAV-002](../tasks/RAV-002-log-normalization.md), [RAV-012](../tasks/RAV-012-timestamp-synchronization.md) |
| REQ-SYNC-002 | Công bố offset/drift/quality và unknown khi thiếu anchor | Missing | [RAV-012](../tasks/RAV-012-timestamp-synchronization.md) |
| REQ-DET-001 | Tìm zero hoặc nhiều candidate bằng log/rule hoặc video fallback | Missing | [RAV-003](../tasks/RAV-003-candidate-detection.md) |
| REQ-DET-002 | Lưu coverage và candidate chưa phân tích vì budget | Missing | [RAV-003](../tasks/RAV-003-candidate-detection.md), [RAV-015](../tasks/RAV-015-job-resume-budget.md) |
| REQ-PRV-001 | Che và validate trước external egress, fail closed | Missing | [RAV-005](../tasks/RAV-005-anonymization.md), [RAV-007](../tasks/RAV-007-external-vlm.md) |
| REQ-PRV-002 | Frontend chỉ phát media qua privacy gate | Missing | [RAV-005](../tasks/RAV-005-anonymization.md), [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) |
| REQ-AI-001 | Output canonical IncidentAnalysisV2, phân biệt claim status | Partial | [RAV-001](../tasks/RAV-001-analysis-schema-v2.md) schema local DONE; [RAV-006](../tasks/RAV-006-vlm-adapter.md) integration còn thiếu |
| REQ-AI-002 | Thay external/self-host qua một contract, giữ provenance | Partial | [RAV-006](../tasks/RAV-006-vlm-adapter.md), [RAV-007](../tasks/RAV-007-external-vlm.md), [RAV-008](../tasks/RAV-008-self-hosted-vlm.md) |
| REQ-EVD-001 | Claim có căn cứ tham chiếu evidence hợp lệ/time/source | Partial | [RAV-004](../tasks/RAV-004-clip-extraction.md), [RAV-009](../tasks/RAV-009-evidence-validation.md) |
| REQ-EVD-002 | Evidence tua lại đúng thời điểm trong video | Partial | [RAV-009](../tasks/RAV-009-evidence-validation.md), [RAV-012](../tasks/RAV-012-timestamp-synchronization.md), [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) |
| REQ-REV-001 | AI chỉ tạo DRAFT, không approve | Partial | [RAV-010](../tasks/RAV-010-review-workflow.md) |
| REQ-REV-002 | Approve/reject chỉ Reviewer thật khác người submit | Missing | [RAV-010](../tasks/RAV-010-review-workflow.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md) |
| REQ-REV-003 | Engineer sửa/reopen có version, reject có reason | Partial | [RAV-010](../tasks/RAV-010-review-workflow.md), [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) |
| REQ-AUD-001 | Mọi thay đổi review gắn authenticated actor | Partial | [RAV-013](../tasks/RAV-013-report-versioning-audit.md), [RAV-014](../tasks/RAV-014-authentication-rbac.md) |
| REQ-AUD-002 | Snapshot approved immutable; GET không regenerate | Partial | [RAV-013](../tasks/RAV-013-report-versioning-audit.md) |
| REQ-API-001 | V2 typed/versioned, giữ regression v1.1 | Missing | [RAV-016](../tasks/RAV-016-api-v2-migration.md), [RAV-017](../tasks/RAV-017-frontend-v2-integration.md) |
| REQ-JOB-001 | Job nền có stage/retry/resume/idempotency | Partial | [RAV-015](../tasks/RAV-015-job-resume-budget.md), [RAV-020](../tasks/RAV-020-observability-runbook.md) |
| REQ-EVAL-001 | Benchmark nhãn chuyên gia + metric quality | Missing | [RAV-018](../tasks/RAV-018-expert-benchmark.md), [RAV-019](../tasks/RAV-019-provider-cost-comparison.md) |
| REQ-EVAL-002 | Đo cost/accepted incident và latency, không chỉ API bill | Missing | [RAV-019](../tasks/RAV-019-provider-cost-comparison.md), [RAV-020](../tasks/RAV-020-observability-runbook.md) |
