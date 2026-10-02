# ADR index

Lifecycle PROPOSED → ACCEPTED → SUPERSEDED; REJECTED dành cho lựa chọn chủ động bỏ. Status quyết định độc lập status implementation. Không tự accept storage/provider production.

| ADR | Status |
| --- | --- |
| [ADR-001 Hybrid incident analysis pipeline](ADR-001-hybrid-incident-analysis-pipeline.md) | ACCEPTED |
| [ADR-002 Background job processing](ADR-002-background-job-processing.md) | ACCEPTED |
| [ADR-003 Evidence-first analysis](ADR-003-evidence-first-analysis.md) | ACCEPTED |
| [ADR-004 VLM provider abstraction](ADR-004-vlm-provider-abstraction.md) | ACCEPTED |
| [ADR-005 Versioned API migration](ADR-005-versioned-api-migration.md) | ACCEPTED |
| [ADR-006 Large media storage](ADR-006-large-media-storage.md) | PROPOSED |
| [ADR-007 Privacy before external inference](ADR-007-privacy-before-external-inference.md) | ACCEPTED |
| [ADR-008 Versioned analysis schema](ADR-008-versioned-analysis-schema.md) | ACCEPTED |
| [ADR-009 Report versioning and audit](ADR-009-report-versioning-and-audit.md) | ACCEPTED |
| [ADR-010 AI evaluation strategy](ADR-010-ai-evaluation-strategy.md) | ACCEPTED |

Có đúng 9 ACCEPTED và 1 PROPOSED (ADR-006). Hai phương án inference xem [comparison](../docs/inference-options.md), không tạo thêm ADR khi chưa có quyết định. ADR-011 để dành cho quyết định tương lai.

Không sửa lịch sử quyết định. Khi supersede, giữ nội dung cũ, thêm status/link Superseded By và ADR mới ghi Supersedes. Chọn self-host theo adapter chung không tự làm ADR-004 bị supersede; chỉ thay khi kiến trúc abstraction thật sự đổi.
