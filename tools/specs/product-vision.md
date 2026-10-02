# Product vision

IncidentLens hỗ trợ Engineer và Reviewer phân tích video/telemetry đã ghi, tạo bản nháp có bằng chứng và báo cáo được con người duyệt. Không phải hệ thống quyết định trách nhiệm pháp lý hoặc tự kết luận nguyên nhân gốc.

Input video + log tùy chọn → tìm cửa sổ nghi vấn → evidence → DRAFT → Engineer sửa/submit → Reviewer approve/reject. Phân biệt quan sát, suy luận có hỗ trợ, giả thuyết và chưa xác định. Mọi claim có căn cứ phải truy lại timestamp/evidence. Thiếu log nội tại phải ghi chưa xác định nguyên nhân nội tại.

MVP gồm upload lớn có resume, đồng bộ có chất lượng đo được, nhiều candidate, privacy, VLM có thể thay thế, schema/version/audit, hai vai trò thật và benchmark. Video 3–5 giờ là workload mục tiêu cần đo; không cam kết thời gian 30 giây. Ngoài scope: online vehicle control, batch similarity search, training detector incident riêng, tự động phân xử lỗi.

Hai nơi chạy inference là phương án ngang hàng để quyết định chi phí/chính sách; một bộ requirement và benchmark dùng cho cả hai.
