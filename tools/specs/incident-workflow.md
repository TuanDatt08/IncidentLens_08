# Incident workflow

## Ba lifecycle độc lập

- Incident ingestion/processing V2: CREATED → UPLOADING → READY → PROCESSING → COMPLETED hoặc FAILED. Hoàn tất upload mới READY; job succeeded có thể không tìm được sự cố.
- Job: queued → running → succeeded/failed/cancelled. Stage chi tiết tách khỏi trạng thái incident.
- Report: DRAFT → IN_REVIEW → APPROVED hoặc REJECTED; Engineer reopen REJECTED → DRAFT với snapshot mới. APPROVED bất biến; amendment tạo version DRAFT mới và phải duyệt lại.

V1.1 hiện có UPLOADED/READY/PROCESSING/COMPLETED/FAILED và REJECTED terminal; thay đổi reopen chỉ thuộc V2.

## Pipeline

Validation → synchronization → candidate detection → extraction → anonymization → privacy validation → VLM → schema validation → evidence validation → DRAFT. Có thể có nhiều report ứng viên trong một recording, mỗi report có candidate ID ổn định. Không nhập lẫn report với bản ghi factual.

Quét log toàn tuyến theo luồng, tìm disengagement/phanh/jerk/collision/lỗi điều khiển khi tín hiệu có sẵn. Không có tín hiệu không được bịa sự kiện. Gộp cửa sổ chồng/gần nhau bằng tham số cấu hình được version hóa. Nếu log thiếu/không tin cậy, quét video từng segment với mẫu thưa rồi tăng mật độ quanh candidate. Lưu segment hoàn thành, checkpoint, candidate chưa phân tích và giới hạn tài nguyên để resume.

Không thấy ở mẫu thưa = chưa phát hiện trong phạm vi mẫu, không phải chứng minh không có sự cố. Output không có candidate phải kèm coverage và unknowns. Giới hạn candidate/call/retry theo budget; vượt budget lưu UNANALYZED, không bỏ âm thầm.

Retry lỗi tạm thời có giới hạn; lỗi file/schema không hợp lệ hoặc privacy không đạt dừng với mã lỗi/stage. Lease/attempt cũ không được publish. Idempotency key và transaction đảm bảo replay không tạo report/evidence trùng. Cancel giữ kết quả đã commit, không tự submit/approve.

Time basis V2 là video_seconds; mapping log có offset, drift, nguồn mốc, residual/quality. Không xác minh được thì ghi unknown và vô hiệu inference cần đồng bộ chính xác.
