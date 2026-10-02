# RAV-004 — Clip and ordered frame extraction

Status: **DONE (local AC)**

Delivery Status: **Local verified; remote CI/merge pending**

Technical lead: Backend; phối hợp: không cần role khác cho scope chính.

Role docs: [Backend](../../backend/docs/work-items.md).

Priority: P0

Owner: chưa giao; không tự suy người phụ trách.

Sprint: [Sprint 02](../planning/sprints/sprint-02-incident-detection.md)

## Goal

Hoàn thành capability **Clip and ordered frame extraction** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-EVD-001](../specs/incident-analysis-v2.md).

ADR: [ADR-001](../adrs/ADR-001-hybrid-incident-analysis-pipeline.md), [ADR-003](../adrs/ADR-003-evidence-first-analysis.md).

Dependencies: [RAV-003](RAV-003-candidate-detection.md).

## Background / baseline evidence

`backend/services/processing.py`, `video.py`: clip/keyframe/hash có, chưa multiple candidates/order manifest V2. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

extract_candidate(video, candidate, sampling) -> EvidenceBundle.

Paths create/modify (đích kế hoạch; path mới chưa tồn tại): backend/services/video.py; backend/services/processing.py.

Test: `tests/backend/test_services/test_processing.py`.

## Acceptance criteria

- [x] Clip/frame đúng time.
- [x] timestamp và frame order lưu manifest.
- [x] không vượt duration.
- [x] asset hash và stable candidate key.
- [x] mock ffmpeg test kèm real fixture kiểm seek.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [ ] Viết regression/contract test cho từng acceptance, thêm negative case tương ứng trước implementation.
- [ ] Chạy test mới, xác nhận failure vì behavior chưa có; giữ v1 regression.
- [x] Implement tối thiểu theo interface trên, ưu tiên stdlib/framework và adapter hiện có.
- [x] Chạy targeted tests; Python: `python -m pytest tests/backend/test_services/test_processing.py -q` (tạo test file trước). Frontend RAV-017 dùng `npm --prefix frontend run typecheck` và `npm --prefix frontend run build`, cộng E2E theo acceptance.
- [x] Chạy gates cần thiết: `python -m ruff check backend/ api/` và `python -m pytest tests/ -q`; PG/media/provider thực chỉ ghi PASS khi có bằng chứng chạy thật.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff có scope, migration/backward compatibility được review.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi ngày, command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: Ordered manifest, video_seconds/hash/scope; real FFmpeg red/blue fixture kiểm seek và clip tolerance 100ms.

Evidence: [test_evidence_extraction.py](../../tests/backend/test_services/test_evidence_extraction.py), [execution ledger](../docs/task-execution-2026-10-03.md), [V2 operating limits](../../backend/docs/v2-implementation.md). Targeted + final local gates ghi trong ledger. Remote CI/merge pending. Execution RED checklist chỉ tick khi có record đủ từng acceptance; không suy RED từ test GREEN. Repo audit bên dưới là baseline trước implementation này.

## Repo audit evidence — 2026-10-03

Clip + frame + telemetry slice/hash có. Còn thiếu: Multiple candidate ID/order manifest; real media seek evidence. Source: [video.py](../../backend/services/video.py). Test fixture: [test_processing.py](../../tests/backend/test_services/test_processing.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
