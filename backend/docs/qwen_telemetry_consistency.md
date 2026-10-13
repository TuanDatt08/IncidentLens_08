# Kiểm tra kết luận Qwen với telemetry

## Vấn đề đã xác nhận

Trong incident `INC-8520FEAA5D22`, Qwen nhận ra người giữa đường nhưng trả `incident_detected=false` và nói không có phanh bất thường. Request thực tế đã chứa tốc độ giảm từ khoảng 8.875 m/s xuống 0 trong 1.25 giây, brake 0.902 và acceleration -27.043 m/s². Đây là mâu thuẫn giữa dữ liệu được cung cấp và lời giải thích model, không phải lỗi kết nối GPU.

Kiểm tra cũ dựa vào các flag `brake` và `acceleration`. Sau khi lọc ưu tiên cao, chỉ flag giảm tốc còn lại; giá trị phanh trong telemetry vẫn có nhưng kiểm tra cũ không đọc nó. Vì vậy mâu thuẫn không được đánh dấu.

## Cách xử lý mới

1. Prompt yêu cầu đánh giá riêng phanh khẩn cấp, chuyển động người đi bộ và xung đột quỹ đạo; không yêu cầu phải có va chạm mới được xem xét incident.
2. Sau mỗi batch đã qua validation, backend chọn telemetry nằm trong khoảng timestamp của các frame batch đó.
3. Nếu model trả âm tính nhưng đồng thời có brake >= 0.8, acceleration <= -8 m/s² và tốc độ giảm ít nhất 3 m/s trong tối đa 2 giây, backend thêm `MODEL_TELEMETRY_CONFLICT`.
4. Bằng chứng kiểm tra được ghi trong record batch của `local-analysis.json`: khoảng thời gian, phanh lớn nhất, gia tốc nhỏ nhất và mức giảm tốc độ.
5. Kết quả âm tính có mâu thuẫn mang `detection_state=REVIEW_REQUIRED_TELEMETRY_CONFLICT` trong model metadata; draft thêm lời giải thích và unknowns bằng tiếng Việt. `review_status` vẫn là `DRAFT`.

Các giá trị này là kiểm tra nhất quán ban đầu, chưa được hiệu chỉnh trên nhiều dữ liệu. Nó phân biệt âm tính cần review với âm tính không có mâu thuẫn telemetry theo rule, không tự chứng minh near miss.

## Những gì không bị thay đổi

Backend không sửa output thô hoặc ép `incident_detected=true`. Giá trị false vẫn phản ánh kết luận model; metadata cho biết kết luận đó chưa giải quyết được nguy cơ và cần kỹ sư xem lại. Không suy ra va chạm, thương tích hoặc quan hệ nhân quả giữa người và phanh từ telemetry đơn thuần.

Schema V1 chỉ có boolean incident_detected nên không thể dùng nó một mình để biểu diễn ba trạng thái: xác nhận có, chưa xác nhận và kết luận âm tính có mâu thuẫn. Consumer nên đọc thêm `model_metadata.detection_state`, `consistency_checks`, `draft_v2.summary` và `draft_v2.unknowns`. Tác vụ này chưa thay giao diện hoặc cơ chế phê duyệt.

Chỉ dữ liệu thuộc batch được xét; flag ở cuối video không làm tất cả batch trước đó bị gắn mâu thuẫn. Không có telemetry đủ ba tín hiệu thì rule không kích hoạt. Điều đó không chứng minh không có sự kiện. Một request một frame không đủ khoảng thời gian cho kiểm tra này; cấu hình hiện tại dùng 8 frame/request.

## Kiểm tra và vận hành

Unit test gồm âm tính với phanh khẩn cấp, phanh thông thường, timestamp ngoài batch và kết quả model dương tính. Build lại APP để cập nhật prompt/code; các báo cáo cũ không tự thay đổi. Lượt chạy mới cần đối chiếu output thô và cảnh báo, chưa coi test giả lập là bằng chứng model đã cải thiện độ chính xác.

## Thử 16 frame/request ngày 13/10/2026

Cấu hình APP hiện tăng lên 16 frame/request, giữ 4 FPS. Lượt `INC-2A0050D7494B` xử lý 27 frame bằng hai request 16 và 11 frame, hoàn tất trong 73.17 giây. Input lần lượt 20,855 và 14,843 tokens, dưới context 32K. Một snapshot trong lúc inference đo VRAM 8,500/22,528 MiB; đây không phải đo peak. Không thấy lỗi OOM hoặc lỗi request.

Model vẫn trả âm tính, đồng thời ghi người nằm trong đường xe đi và nói thiếu va chạm/contact. Backend đánh dấu REVIEW_REQUIRED_TELEMETRY_CONFLICT vì dữ liệu phanh/tốc độ phản bác phần phủ nhận phanh khẩn cấp. Thí nghiệm này cho thấy thiếu số lượng frame/VRAM không phải lời giải thích đầy đủ cho lỗi; không xác định được nguyên nhân nội bộ của model chỉ từ output.

Tăng batch giảm số request nhưng không bảo đảm cải thiện reasoning. Bước đánh giá tiếp theo nên phân tách quan sát hình ảnh, số liệu phanh và phân loại nguy cơ, rồi benchmark có nhãn trên nhiều clip hoặc so sánh model khác. Không tiếp tục tăng frame vô hạn: thêm ảnh có thể vượt context hoặc làm loãng đoạn quan trọng. Không đổi âm tính thành dương tính chỉ để khớp kỳ vọng người dùng.
