# RAV-019 — Provider quality and cost comparison

Status: **BLOCKED**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P1

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 05](../planning/sprints/sprint-05-evaluation-hardening.md)

## Goal

Hoàn thành capability **Provider quality and cost comparison** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-EVAL-001](../specs/evaluation.md), [REQ-EVAL-002](../specs/evaluation.md).

ADR: [ADR-004](../adrs/ADR-004-vlm-provider-abstraction.md), [ADR-010](../adrs/ADR-010-ai-evaluation-strategy.md).

Dependencies: [RAV-007](RAV-007-external-vlm.md), [RAV-008](RAV-008-self-hosted-vlm.md), [RAV-018](RAV-018-expert-benchmark.md), [RAV-020](RAV-020-observability-runbook.md).
Decision blocker: cần expert data/threshold, egress approval/API access và GPU; lựa chọn inference production còn mở.

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

Benchmark runner + measured comparison report.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): eval/run_benchmark.py; eval/results/.

Test: `tests/eval/test_metrics.py`.

## Acceptance criteria

- [ ] Cùng cases/budget.
- [ ] token/GPU/preprocess/storage/retry/review cost.
- [x] p50/p95.
- [ ] evidence quality + acceptance.
- [x] zero accepted không chia 0.
- [x] blocked tới khi có hardware/API policy/dataset/threshold.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/eval/test_metrics.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [ ] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Comparison/ratio/percentile/complete cost components/zeroaccepted safeguards và synthetic negative tests đã có; runner checked-in manifest trả BLOCKED actual0. Không có real comparison/p50/p95/evidence quality. Cần licensed expert data, lock/signoff, API policy và GPU hardware.

Evidence: [test_metrics.py](../../tests/eval/test_metrics.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Không measured provider comparison. Còn thiếu: Chờ data/threshold/GPU/API policy/usage metrics trước quality-cost test. Source: [inference-options.md](../../tools/docs/inference-options.md). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
