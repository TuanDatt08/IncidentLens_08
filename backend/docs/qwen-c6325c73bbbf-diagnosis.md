# Chẩn đoán Qwen cho JOB-C6325C73BBBF

Kiểm tra trực tiếp ngày 2026-10-15. Incident: `INC-F306B828ACE1`.
Phần nguyên nhân bên dưới ghi nhận chẩn đoán trước sửa. Pipeline đã được sửa và
triển khai; kết quả kiểm chứng được bổ sung cuối tài liệu. Report gốc được giữ nguyên.

## Kết luận

Không phải lỗi kết nối GPU. Job `succeeded`, nhưng kết quả nhận diện chưa đáng tin
vì pipeline đang phân tích từng ảnh độc lập và bỏ lọt kiểm tra mâu thuẫn telemetry.
`succeeded` chỉ chứng minh tiến trình hoàn tất, không chứng minh kết luận đúng.
Chưa có cơ sở kết luận chắc chắn có va chạm hoặc near miss chỉ từ phản hồi model.

## Bằng chứng đã xác minh

- Đồng bộ log/video được ghi `VERIFIED`, offset 0 giây.
- Có 1 candidate, từ 52,458 đến 60,041667 giây; đỉnh telemetry 58,375 giây.
- Trích 31 frame ở 4 FPS và gọi model 31 lần, mỗi lần đúng 1 frame.
- Các frame quanh đỉnh: 58,208 và 58,458 giây; không có frame đúng 58,375 giây.
- Request tại 58,458 giây đã chứa dữ liệu brake 0,902 và acceleration −27,043 m/s²;
  telemetry không bị mất hoàn toàn trên đường truyền.
- Phản hồi model tự mô tả người đi bộ trên đường đi của xe, nhưng vẫn phủ định
  incident vì không thấy contact/collision và không quan sát được quỹ đạo.
  Đây là nội dung model nói, không phải xác nhận độc lập về cảnh thực tế.
- Report lưu `incident_detected=false`, `NO_DETECTION_IN_SAMPLED_EVIDENCE`,
  `requires_engineer_review=true`, nhưng `consistency_checks=[]`.
- Chạy lại hàm kiểm tra hiện có trên toàn candidate phát hiện
  `MODEL_TELEMETRY_CONFLICT`: brake cực đại 0,902; acceleration cực tiểu
  −27,043 m/s²; tốc độ giảm tối đa 8,875 m/s trong một khoảng không quá 2 giây.

## Nguyên nhân và vị trí sửa

### 1. P0: Kiểm tra telemetry trên cả candidate

`backend/services/qwen_processing.py` gọi `negative_telemetry_conflict` bằng timestamp
của frame đầu/cuối trong mỗi batch. Batch 1 frame tạo khoảng có độ dài 0.
`backend/services/telemetry_consistency.py` yêu cầu ít nhất 2 dòng telemetry,
nên kiểm tra thường trả None ngay trước khi xét phanh/giảm tốc.

Sửa bằng một phép kiểm tra độc lập trên toàn candidate sau khi tổng hợp các batch.
Nếu model phủ định nhưng telemetry mâu thuẫn, lưu trạng thái
`REVIEW_REQUIRED_TELEMETRY_CONFLICT`, số liệu và lý do; không tự ép
`incident_detected=true`, không tự kết luận nguyên nhân do người đi bộ.
Giữ tương thích hợp đồng V1, dùng metadata hiện có để phân biệt kết quả âm tính
với kết quả còn mâu thuẫn. UI cần hiển thị rõ trạng thái này.

### 2. P1: Gửi chuỗi ảnh có thứ tự thay vì ảnh rời

Trong `qwen_processing.py`, batch size đang lấy từ `qwen_batch_frames`, hiện bằng 1.
Đổi sang batch nhiều frame có phần chồng lấn và một bước kết luận toàn candidate.
Thử trước 6–8 frame/request trên RTX 2080 Ti; đo VRAM, thời gian và chất lượng
trước khi tăng. Không mặc định tăng toàn bộ 31 ảnh vào một request.

Chuỗi cần có ảnh trước phanh, lúc người/xe tiến gần, quanh đỉnh và sau khi xe dừng.
Mỗi ảnh giữ evidence ID và timestamp. Tổng hợp quan sát trước/sau rồi mới quyết định
loại sự kiện; không dùng phép OR của những kết luận ảnh rời làm kết luận cuối cùng.

### 3. P1: Bổ sung frame đúng đỉnh và quanh diễn biến nhanh

Giữ sampling nền; bổ sung frame đúng critical timestamp 58,375 giây và lấy dày
hơn gần đoạn giảm tốc 57,4–58,6 giây, có giới hạn số frame và bytes.
Tần số 4 FPS có bước 0,25 giây, thưa hơn chuỗi giảm tốc mạnh khoảng 0,083 giây
đã dùng để xác nhận trigger. Giữ ảnh trước/sau, không chỉ lấy đúng một điểm đỉnh.

Chưa có bằng chứng cần đổi model hoặc tăng độ phân giải toàn bộ. Nếu xem lại ảnh
thấy đối tượng quá nhỏ, thử độ phân giải/crop bổ sung và đo ảnh hưởng riêng.

### 4. P1: Tách sự kiện phanh mạnh khỏi kết luận va chạm

Prompt hiện đã nói HARD_BRAKING và near miss không bắt buộc có collision.
Vì vậy chỉ bổ sung thêm câu nhắc tương tự sẽ không giải quyết lỗi mất ngữ cảnh thời gian.

Đề xuất hai bước: mô tả quan sát theo thời gian và số liệu telemetry; sau đó
phân loại HARD_BRAKING, xung đột nghi vấn, hoặc COLLISION theo bằng chứng phù hợp.
Thiếu bằng chứng contact thì không xác nhận COLLISION; điều đó không tự phủ định
phanh khẩn cấp hay giải quyết được xung đột quỹ đạo. Trường hợp chưa đủ bằng chứng
phải chuyển review thay vì phát biểu chắc chắn không có incident.

### 5. P2: Tổng hợp report thay vì nối 31 summary

Hiện summary của các batch âm tính được nối bằng newline, tạo đoạn lặp dài và
chứa cả phát biểu mâu thuẫn nhau. unknowns cũng có các câu phủ định mang tính kết luận.

Tạo một summary ở cấp candidate gồm: tín hiệu đã xác minh, quan sát hình ảnh,
điểm chưa xác định, yêu cầu review. Deduplicate không chỉ theo nguyên chuỗi;
không xóa bằng chứng mâu thuẫn. Giữ toàn bộ raw output trong journal riêng.

## Kiểm tra trước khi triển khai

1. Regression: batch một frame vẫn phát hiện xung đột khi toàn candidate đủ telemetry.
2. Regression: phanh bình thường không bị chuyển thành incident chỉ vì brake cao.
3. Kiểm tra schema, evidence ID, thời gian và giới hạn VRAM cho batch nhiều ảnh.
4. Chạy lại cùng recording bằng cấu hình mới; đối chiếu cả raw output và clip thực tế.
5. Thêm video không có sự cố, phanh thường, phanh gấp, người băng đường, near miss,
   va chạm và thiếu hình ảnh; có nhãn con người trước khi báo precision/recall.
6. Đo số model calls, latency, VRAM và kết luận theo từng loại sự kiện.

## Có cần fine-tune không?

Chưa nên. Hai lỗi đã xác minh thuộc pipeline, không cần fine-tune để sửa.
Chỉ cân nhắc LoRA/fine-tune sau khi sửa ngữ cảnh thời gian và consistency check,
nhưng model vẫn sai có hệ thống trên tập video được gán nhãn, tách train/test
theo recording/scenario. Không dùng chính video hiệu chỉnh ngưỡng làm bằng chứng
chất lượng tổng quát; không huấn luyện để luôn trả incident khi thấy phanh mạnh.

## Kết quả triển khai

- Kiểm tra telemetry ở cấp candidate thay cho khoảng thời gian của từng ảnh.
- Bật temporal context trên GPU: 6 ảnh/request, chồng lấn 2 ảnh, thêm lượt kết luận
  cuối với các quan sát sơ bộ và overview trước/đỉnh/sau.
- Bổ sung ảnh chính xác tại 58,375 giây và lưới 8 FPS quanh đỉnh ±1 giây.
- Candidate-level verdict được kiểm tra riêng; không OR các kết luận sơ bộ.
  Kết luận cuối thiếu hoặc không hợp lệ được đánh dấu cần review.
- Thêm telemetry_findings tính sẵn từ log, kèm đơn vị và evidence ID;
  không tự biến bằng chứng phanh thành bằng chứng va chạm hoặc nguyên nhân do người đi bộ.
- Summary ngắn ở cấp candidate, bảo toàn nhận định dương tính độc lập nếu một
  candidate khác có mâu thuẫn. UI không lặp warnings đã có trong unknowns và
  hiển thị trạng thái cần review thay cho trường trạng thái V3 bị trống trên output V2.
- Review-context được chuyển qua tunnel đến GPU để đọc telemetry/artifacts đúng nơi lưu.

Chạy lại cùng dữ liệu, giữ report gốc làm baseline:

- Job mới: `JOB-C53DC5BB33B5`, incident `INC-5268A0B3FB51`.
- Job succeeded, 13 model calls thay vì 31; request cuối có các timestamp
  `[52.458, 57.875, 58.375, 58.5, 58.875, 59.958]`.
- Quan sát khoảng 8,5 GB VRAM, Ollama báo 100% GPU.
- Model vẫn trả âm tính. Backend phát hiện mâu thuẫn và lưu
  `REVIEW_REQUIRED_TELEMETRY_CONFLICT`; UI hiển thị cảnh báo và biểu đồ tốc độ/phanh.
- Thử thêm một lượt kết luận có telemetry_findings tính sẵn: model vẫn phủ định.
  Phản hồi thử được lưu riêng, không ghi đè report production hoặc dùng để tự xác nhận incident.

Giới hạn còn lại: thay đổi pipeline sửa được ngữ cảnh và lỗi bỏ lọt cảnh báo,
nhưng chưa chứng minh Qwen nhận diện đúng sự kiện này. Cần đánh giá độc lập
clip thực tế và tập có nhãn trước khi đổi model, fine-tune hoặc công bố chất lượng.

Kiểm thử: full backend suite 416 passed/4 skipped trước bổ sung measurements;
22 kiểm tra provider/telemetry/temporal sau bổ sung đều đạt. Frontend typecheck,
lint, production build và 31 kiểm tra regression đã đạt; phần copy cuối được
kiểm lại bằng typecheck, lint và regression AnalysisContext.
