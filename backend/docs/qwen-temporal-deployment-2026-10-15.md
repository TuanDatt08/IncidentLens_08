# Triển khai prompt và chuỗi frame Qwen — 2026-10-15

## Thay đổi

Hai nhánh GPU dùng batch ảnh theo thứ tự, phân tích candidate rồi tổng hợp toàn video. Video-only có frame_seq toàn cục; video + log có t_video_s. Backend giữ API theo giây video và không đổi giao diện FE.

Prompt Stage A/B ở backend/data/promt.txt; prompt có log ở backend/prompts/ollama_incident.txt; prompt cuối ở backend/prompts/video_summary.txt. Thiết kế đã duyệt: qwen-temporal-prompt-design.md; cấu hình: vast-worker.md.

Các lớp kiểm tra giữ ID/tọa độ thật, không coi model notes là bằng chứng độc lập, không OR kết quả sơ bộ thành kết luận cuối. Một kết luận xác nhận phải viện dẫn bằng chứng của candidate đã xác nhận cùng loại. Nghi vấn bị model bỏ qua ở summary được giữ lại thành INCONCLUSIVE có mã SUMMARY_OMITTED_CANDIDATE, không tự xác nhận hoặc âm thầm xóa.

## Kiểm chứng

- Suite đầy đủ: 431 passed, 4 skipped; Ruff toàn repository đạt. Ba file test cũ chỉ được sắp xếp import để vượt lint, không đổi hành vi.
- 38 kiểm tra tập trung đạt, gồm gửi đủ frame, đánh số ổn định, roundtrip giây/frame, biên clip, giữ bằng chứng qua tổng hợp, request lỗi, chống mượn bằng chứng, tổng hợp phân cấp và giữ nghi vấn bị bỏ sót.
- GPU đang dùng Ollama qwen2.5vl:7b, context 32768, một model/luồng xử lý, 100% GPU theo ollama ps tại thời điểm kiểm tra.
- Đã chạy đoạn video thật 2 giây trích từ recording có sẵn, không log: Stage A/B và FINAL_VIDEO hoàn thành; model kết luận PEDESTRIAN_CONFLICT ở DRAFT. Đây là kết luận model trên clip kiểm thử, chưa có nhãn độc lập để xác nhận đúng/sai.
- Cùng đoạn hình ảnh với log đồng bộ đã quy đổi theo video kiểm thử: pipeline và tổng hợp cuối hoàn thành; giữ INCONCLUSIVE/REVIEW_REQUIRED_TELEMETRY_CONFLICT khi Qwen phủ nhận bằng chứng phanh, không tự ép incident_detected=true.
- Các lần thử ban đầu làm lộ lỗi ngôn ngữ, tọa độ phân số và nhầm frame cuối với biên clip. Đã sửa chỉ dẫn cuối request, schema integer và const cho hai biên clip; raw attempts được giữ trên GPU.

## Giới hạn và rollback

Chưa đo precision/recall hoặc kết luận cần fine-tune. Video-only đang lấy mẫu đều 4 FPS, chưa tự lấy thêm 8 FPS quanh nghi vấn như nhánh log. Sự cố giữa hai mẫu có thể bị bỏ sót; tăng FPS cần đánh giá chi phí/recall.

Bật QWEN_VIDEO_SUMMARY=true trên GPU; Render chỉ chạy API. Tắt biến này cho rollback chiến lược tổng hợp; rollback đầy đủ cần phục hồi code/prompt và worker.env từ backup riêng trên GPU. Không xóa hoặc chạy lại job cũ để triển khai. Các lần smoke nằm ở thư mục validation riêng, không ghi report vào Neon.

Bản test đầy đủ, commit chạy thật và trạng thái dịch vụ được xác nhận trong kết quả triển khai của phiên làm việc; không dùng tài liệu này để suy ra một instance luôn online.
