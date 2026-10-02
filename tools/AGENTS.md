# Quy tắc cho người và coding agent

## Trước mỗi task

1. Kiểm tra Skill/Plugin; ưu tiên Superpowers cho workflow, Ponytail khi sửa code, Impeccable khi sửa UI. Giữ giao tiếp ngắn gọn theo yêu cầu Caveman của người dùng.
2. Đọc task, SPEC, ADR và sprint được task liên kết. Xem trạng thái dependency và Git trước khi sửa.
3. Source-of-truth: SPEC định nghĩa hành vi; ADR giải thích quyết định; planning lên lịch; task thực hiện; code/test chứng minh acceptance.
4. Giữ scope nhỏ; dùng native/framework hiện có; bảo toàn thay đổi ngoài task.

## Ranh giới

- Code ở `backend/`, `api/`, `frontend/`; test ở `tests/`. Không tạo app thứ hai trong `tools/`.
- Docs implementation/vận hành của từng role đặt `backend/docs`, `api/docs`, `frontend/docs`. SPEC/ADR/planning/task dùng chung giữ ở tools; role docs và work-items chỉ liên kết tới canonical. Xem [role ownership](docs/repository-roles.md).
- Không tự rewrite code để khớp tài liệu. Chênh lệch phải có task và migration.
- API `/api/v1` theo [contract v1.1](../api/docs/backend-contract-v1.1.md). V2 phải có schema/OpenAPI riêng và regression v1.
- `ACCEPTED` ADR là quyết định của thiết kế; không chứng minh implementation đã xong. `PROPOSED` không được dùng như quyết định đã chốt.
- Không tự chọn storage, identity provider, mua GPU hoặc bật external egress. Chuẩn bị phương án và bằng chứng để người dùng quyết định.
- External inference phải qua anonymization + privacy validation; mọi lần thất bại chặn egress. Frontend chỉ phát media đã được duyệt privacy.
- Claim OBSERVED/SUPPORTED_INFERENCE phải dẫn evidence hợp lệ. Thiếu dữ liệu ghi UNKNOWN; không suy lỗi nội tại từ hình ảnh ngoài xe.
- AI không approve; actor thật, quyền truy cập và phân tách người submit/người approve phải được kiểm tra phía server.

## Hoàn thành

Cập nhật trạng thái và evidence trong task/backlog; nêu command, ngày, kết quả và giới hạn. Không đổi DONE chỉ vì đọc thấy function hoặc vì fake VLM pass. Phân biệt unit/SQLite, PostgreSQL smoke, live provider và benchmark chuyên gia. Không ghi secret, video riêng tư hoặc danh tính thật vào Git. Commit/push theo phạm vi người dùng yêu cầu.

## Lifecycle theo repository mẫu

Coverage DONE/PARTIAL/TODO/BLOCKED ở backlog độc lập delivery workflow:

- Backlog delivery: New → Refined → Sprint Ready → In Sprint → Done. Owner/PM xác nhận scope, estimates và capacity trước chuyển Sprint Ready.
- Sprint: Planned → Active → Review → Closed. Bộ sprint này khởi tạo Planned, chưa cam kết lịch ngày.
- Task delivery: Todo → In Progress → Review → Done. Chọn task ready, gán owner trước In Progress; PR tạo thì Review; merge + acceptance verified mới Done.
- Top-down: backlog chọn sprint → tạo task; bottom-up: task completion cập nhật sprint và backlog. Không gộp coverage Partial với workflow In Progress.
- Thay priority ở backlog trước đổi sprint. Task chưa hoàn tất được chuyển sprint/backlog có ghi lý do.

Đọc theo thứ tự: AGENTS → task → SPEC → ADR → planning → source/tests → gitflow khi liên quan Git. Không tự pull/rebase đè dirty work; xác minh branch/remote trước đồng bộ. Repository mẫu dùng main; checkout này dùng develop theo docs/gitflow.md.
