# Vai trò người dùng

| Operation | Engineer | Reviewer | System/AI |
| --- | --- | --- | --- |
| Upload, analyze | Có | Không trong MVP | Chạy job được tạo |
| Đọc incident/evidence/audit | Trong phạm vi được cấp | Trong phạm vi được cấp | Theo job |
| Sửa DRAFT, submit | Có | Không | Chỉ tạo DRAFT ban đầu |
| Reopen REJECTED | Có, tạo version | Không | Không |
| Approve/reject | Không | Có, khác người submit | Không |

Server xác minh danh tính/quyền, không tin role header từ client. Reviewer không duyệt báo cáo chính mình submit, kể cả tài khoản có hai role. Reject phải có lý do. Người không đăng nhập không được đọc media hoặc sửa report. Identity provider là quyết định còn mở; role behavior là requirement đã xác định.
