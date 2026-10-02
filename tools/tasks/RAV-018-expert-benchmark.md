# RAV-018 — Expert dataset and protocol

Status: **TODO**

Delivery Status: **Todo**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 05](../planning/sprints/sprint-05-evaluation-hardening.md)

## Goal

Hoàn thành capability **Expert dataset and protocol** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-EVAL-001](../specs/evaluation.md).

ADR: [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-010](../adrs/ADR-010-ai-evaluation-strategy.md).

Dependencies: không có task prerequisite; kiểm tra decision gates bên dưới.

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

Versioned BenchmarkCase manifest + rubric + threshold sign-off.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): eval/datasets/manifest.json; eval/protocol.md.

Test: `tests/eval/test_manifest.py`.

## Acceptance criteria

- [ ] 50–100 case mục tiêu, số thực công bố.
- [ ] licence/consent.
- [ ] GT window/factor/evidence.
- [ ] disagreement resolution.
- [ ] calibration/test split.
- [ ] IoU/tolerance/threshold ký trước đo.

## Execution and verification

- [ ] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [ ] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [ ] Chạy targeted tests; Python: `python -m pytest tests/eval/test_manifest.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [ ] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [ ] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [ ] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

Chưa hoàn thành acceptance V2. Điền tại đây khi thực hiện; không dùng bản kế hoạch này làm bằng chứng DONE.

## Repo audit evidence — 2026-10-03

Evaluation report template, không expert dataset/rubric. Còn thiếu: Licenced manifest/GT/splits/disagreements/threshold sign-off. Source: [report.md](../../eval/results/report.md). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
