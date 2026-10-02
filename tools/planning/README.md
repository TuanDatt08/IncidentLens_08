# Planning

Backlog là trạng thái capability; SPEC là hành vi, ADR là quyết định. Sprint là thứ tự mục tiêu, không cam kết lịch ngày hoặc velocity khi chưa giao owner/capacity.

- DONE: implementation và checks phù hợp phạm vi đã verified.
- PARTIAL: có implementation nhưng thiếu acceptance của SPEC mới.
- TODO: chưa có; dependency chưa done thì chưa ready.
- BLOCKED: external resource/decision còn thiếu, ghi unblock action.

Task trạng thái V2 không phủ nhận baseline demo đã được test. Requirement status Implemented/Partial/Missing ánh xạ sang coverage, không thay backlog. Xem [baseline evidence](../docs/baseline-evidence.md) và [backlog](backlog.md).

Sprint dependencies: 01 → 02 → 03 → 04 → 05. RAV-014 auth và RAV-018 nhãn có thể chuẩn bị sớm; RAV-013 bắt đầu khi schema/auth ready. Self-host và external chuẩn bị ngang hàng, production choice chờ kết quả benchmark và quyết định owner.

## Delivery lifecycle

Theo [reference mapping](../docs/reference-mapping.md): backlog New/Refined/Sprint Ready/In Sprint/Done; sprint Planned/Active/Review/Closed; task Todo/In Progress/Review/Done. Coverage và delivery dùng hai field khác nhau. Backlog khởi tạo Refined cho các task đã có scope/AC; chưa Sprint Ready khi chưa estimate/capacity/decision. Tasks khởi tạo Todo, sprint Planned.
