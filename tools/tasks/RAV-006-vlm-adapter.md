# RAV-006 — VLM provider contract

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 03](../planning/sprints/sprint-03-vlm-analysis.md)

## Goal

Hoàn thành capability **VLM provider contract** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-AI-001](../specs/incident-analysis-v2.md), [REQ-AI-002](../specs/incident-analysis-v2.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-004](../adrs/ADR-004-vlm-provider-abstraction.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md).

Dependencies: [RAV-001](RAV-001-analysis-schema-v2.md), [RAV-004](RAV-004-clip-extraction.md).

## Background / baseline evidence

`backend/services/processing.py`: VLMAdapter Protocol pass1/pass2; `vlm.py`: OpenAI keyframes, chưa contract V2. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

VLMProvider.analyze(context: AnalysisContext) -> AnalysisV2; Usage được trả trong envelope.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/vlm.py; backend/services/vlm_provider.py.

Test: `tests/backend/test_services/test_vlm_provider.py`.

## Acceptance criteria

- [x] Hai adapter dùng cùng context/schema.
- [x] frame timestamp theo thứ tự.
- [x] chỉ factory chọn provider.
- [x] timeout/retry bounded.
- [x] provenance/config hash lưu.
- [x] fake test không gọi network.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_vlm_provider.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Một provider context/schema/factory, hai transport profiles, ordered/hash-verified frames, bounded timeout/retry/context/output, provenance; mock HTTP không dùng live service.

Evidence: [test_vlm_provider.py](../../tests/backend/test_services/test_vlm_provider.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Protocol pass1/pass2 và OpenAI adapter có. Còn thiếu: Provider.analyze V2, frame timestamps/provenance/usage. Source: [processing.py](../../backend/services/processing.py). Test fixture: [test_vlm.py](../../tests/backend/test_services/test_vlm.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
