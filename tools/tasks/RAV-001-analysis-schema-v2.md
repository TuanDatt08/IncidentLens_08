# RAV-001 — Analysis schema V2

Status: **DONE** (implementation và acceptance đã kiểm tra local)

Delivery Status: **In Progress** (chờ PR/remote CI và merge; không tự ghi Done)

Technical lead: Backend; phối hợp: API.

Role docs: [Backend](../../backend/docs/work-items.md), [API](../../api/docs/work-items.md).

Priority: P0

Owner: Codex thực hiện theo yêu cầu người dùng; chưa gán human reviewer.

Sprint: [Sprint 01](../planning/sprints/sprint-01-foundation.md)

## Goal

Hoàn thành capability **Analysis schema V2** theo acceptance V2 bên dưới.

## Traceability

SPEC: [REQ-AI-001](../specs/incident-analysis-v2.md).

ADR: [ADR-003](../adrs/ADR-003-evidence-first-analysis.md), [ADR-008](../adrs/ADR-008-versioned-analysis-schema.md).

Dependencies: không có task prerequisite; kiểm tra decision gates bên dưới.

## Background / baseline evidence

Chưa có implementation đạt acceptance trong checkout kiểm tra ngày 2026-10-03. TODO có dependency chưa xong nghĩa là chưa ready; BLOCKED dùng cho decision/resource bên ngoài. Không coi source inspection là production/live-provider evidence.

## Scope and interfaces

`IncidentAnalysisV2` cho human review snapshot; `AIIncidentAnalysisV2` cho output AI chỉ DRAFT. JSON Schema object đóng và enum uppercase. Schema ở module riêng để giữ v1 compatibility.

Paths: [analysis_v2.py](../../backend/models/analysis_v2.py), [business JSON Schema](../../backend/models/json_schema/incident-analysis-v2.json), [AI JSON Schema](../../backend/models/json_schema/ai-incident-analysis-v2.json). `contracts.py` v1 giữ nguyên vì không cần thêm alias/import chưa có consumer.

Test: `tests/backend/test_services/test_analysis_v2.py`.

## Acceptance criteria

- [x] Enum lạ/extra field/NaN bị từ chối.
- [x] window có thứ tự.
- [x] false detection có null window.
- [x] output AI APPROVED bị từ chối.

## Execution and verification

- [x] Đọc linked SPEC/ADR; xác nhận dependencies và quyết định cần thiết.
- [x] Viết regression/contract test cho từng acceptance, thêm negative case trước implementation.
- [x] RED: 37 tests fail do module V2 chưa có; export tests sau đó fail vì JSON files chưa xuất.
- [x] Implement tối thiểu bằng Pydantic hiện có, không thêm dependency.
- [x] Targeted V2 coverage: 55 tests pass trong suite toàn repo.
- [x] `python -m ruff check .` sạch; `python -m pytest -q -p no:cacheprovider`: 113 passed, 9.41s.

## Definition of Done

- [x] Implementation đạt mọi acceptance và dependency; tests + docs cập nhật.
- [x] Diff được self-review; v1 routes/models giữ nguyên và suite hồi quy pass.
- [ ] Required CI passes; chưa CI thì ghi pending, không tự khẳng định pass.
- [x] Evidence ghi command, kết quả, artifact và limitations; cập nhật backlog/status.

## Completion evidence

2026-10-03: 55 V2 contract regressions + 58 baseline tests = 113 passed. Ruff toàn repo pass sau khi sửa hai import-order lỗi cũ trong test fixture/migration tests. JSON Schema checked-in được đối chiếu với runtime schema để tránh drift.

Schema tách business review states và AI-only DRAFT. Timestamp là JSON number (int/float), không nhận string/bool; mọi số hữu hạn. Window có độ dài dương; timeline trong window. Truyền `context={"video_duration_s": duration}` từ media metadata để check duration; context không phải model-generated field. Dynamic ID/source/time resolution và privacy/auth policy thuộc RAV-009/014, không giả đã được schema chứng minh.

Chưa remote CI/PR/merge; checklist đó giữ unchecked. Provider hiện tại vẫn v1 tới RAV-006/016. Các capability V2 tiếp theo chưa được đánh dấu DONE từ task schema này.

## Historical repo audit evidence — trước triển khai

Chỉ v1 Pydantic; nested lists Any. Còn thiếu: V2 enum/object đóng/time/evidence contract. Source: [contracts.py](../../backend/models/contracts.py). Test fixture: [test_contracts.py](../../tests/api/test_contracts.py). Kết quả kiểm tra và giới hạn: [implementation audit](../docs/implementation-audit.md). Coverage chưa đủ toàn AC; Delivery Status vẫn Todo.
