# Áp dụng workshop-demo-coworking vào tools

Nguồn đã đọc: [README](https://github.com/dzungtri/workshop-demo-coworking), [AGENTS.md nhánh base](https://github.com/dzungtri/workshop-demo-coworking/blob/base/AGENTS.md), ngày 2026-10-03. README xác định thư mục trách nhiệm; AGENTS mô tả workflow nhiều cấp, reading order và task context. Áp dụng ý tưởng, không copy nội dung LMS hay thay framework IncidentLens.

| Repo mẫu | IncidentLens | Tài liệu |
| --- | --- | --- |
| specs là behavior | tools/specs | functional-requirements + workflow/schema/security/evaluation |
| adrs là decision | tools/adrs | 10 ADR và template người dùng yêu cầu |
| planning backlog/sprints | tools/planning | coverage riêng delivery lifecycle, 5 Planned sprints |
| tasks giao agent | tools/tasks | RAV namespace, Goal/Background/Scope/AC/DoD/dependencies |
| docs hỗ trợ | tools/docs | architecture/data-flow/gitflow/dev/deploy/runbook |
| src/tests | root backend/api/frontend/tests | Giữ code hiện có, không tạo duplicate app |
| Backlog → Sprint → Task → Implementation → Close | Giữ lifecycle và cập nhật hai chiều | AGENTS + planning README |
| main feature branches/PR | develop integration, main release | Theo branch checkout thực tế, chưa tự tạo/push |

Đích thiết kế người dùng (DONE/PARTIAL/TODO/BLOCKED, ADR format, hai provider) có ưu tiên hơn taxonomy demo. Delivery state là field riêng, không dùng Done của PR để chứng minh benchmark quality. Owner chưa giao, ngày sprint/estimate chưa chốt được ghi rõ.

ADR lịch sử giữ nguyên quyết định; supersession chỉ thay status/link và tạo quyết định mới. Storage PROPOSED chỉ gate production adapter, không dừng common pipeline/dev prototype. Hai phương án inference: [comparison](inference-options.md).

## Role documentation extension

Theo yêu cầu người dùng, role-specific supporting docs nằm trong backend/docs, api/docs, frontend/docs; shared governance/spec/adrs/planning/tasks giữ trong tools. [Repository roles](repository-roles.md) mô tả ownership và forwarding links. Đây là mở rộng từ cấu trúc mẫu, không nhân bản nguồn chuẩn.
