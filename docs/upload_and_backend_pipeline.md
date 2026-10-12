# Upload frontend và pipeline phân tích backend

## Yêu cầu đúng

Frontend chỉ chọn MP4, CSV và metadata đồng bộ cần thiết, upload qua API, tạo job,
theo dõi trạng thái và mở kết quả review. Đọc dữ liệu từ folder và upload từ frontend
phải dùng chung một pipeline backend sau bước nhập dữ liệu.

Không cần một thuật toán phân tích riêng cho frontend. Cùng input, metadata,
prompt, model và cấu hình phải đi qua cùng cách xử lý. Output model vẫn có thể biến
thiên; dùng chung pipeline không bảo đảm mọi lần chạy cho kết quả giống từng ký tự.

## Hai nhánh trước khi điều chỉnh nghĩa là gì?

`backend.worker.run_once` chọn một trong hai nhánh; một job không chạy cả hai nhánh.

| Nhánh | Điều kiện / xử lý |
|---|---|
| Stage A/B mới | Runtime Ollama và prompt có `## STAGE A`: gọi `prompt_pipeline.process_prompt_incident` |
| Local provider trước đó | Các cấu hình còn lại: gọi `qwen_processing.process_local_incident`, `create_local_provider`, rồi provider `analyze` |

Trước thay đổi lựa chọn input, lựa chọn này dựa trên cấu hình và nội dung prompt,
không dựa vào việc input đến từ frontend hay folder. CLI `backend.analyze_local_dataset.analyze_directory` cũng tạo
Incident, tạo job và gọi `backend.worker.run_once`. Với cấu hình hiện tại, chạy CLI
từ folder tại thời điểm trước khi điều chỉnh cũng chọn nhánh Stage A/B mới.

Khác biệt được quan sát là giữa **lượt video 60s chạy trước khi thêm nhánh mới** và
**lượt upload chạy sau khi thêm nhánh mới**. Không phải frontend tự phân tích video.

## Stage A và Stage B

- Stage A phát hiện các sự kiện nghi vấn, loại sự kiện, onset/critical/end, evidence
  và trạng thái CONFIRMED / INCONCLUSIVE / NO_INCIDENT.
- Stage B phân tích chi tiết từng candidate: diễn biến, các bên tham gia, phản ứng,
  nguyên nhân được evidence hỗ trợ, kết quả, timeline và những điều chưa biết.

Đây là hai giai đoạn trong cùng một pipeline. Chúng khác với hai nhánh triển khai
nói trên. Có thể thực hiện A/B bên trong pipeline chung; không cần tạo pipeline
riêng vì có frontend.

## Vì sao hiện tại khác lượt 60s trước?

Trong lần bổ sung prompt Stage A/B, implementation đã tạo một hàm điều phối mới
thay vì tích hợp vào `process_local_incident` và provider hiện có.

Nhánh trước dùng log đã đồng bộ để tìm candidate, trích clip/frame và gọi provider.
Nhánh mới quét các cửa sổ 8 giây chồng lấn với stride 6 giây, gọi Stage A, rồi gọi
Stage B cho candidate; tự gửi HTTP và kiểm tra output. Nhánh mới vẫn tái sử dụng
normalize log, FFmpeg, heartbeat và transaction lưu report, nhưng thay đổi cách
điều phối, số lượt gọi model và hợp đồng output. Do đó thời gian xử lý khác.

## Quy tắc đã thống nhất và triển khai

Backend hiện chọn theo input đã được upload/import và validate:

- **MP4 + CSV:** `process_local_incident` tìm trigger/candidate từ log, trích
  clip/frame, dùng `create_local_provider` / `HTTPVLMProvider.analyze`, rồi lưu SQL.
- **Chỉ MP4, runtime Ollama:** `process_prompt_incident` xử lý Stage A/B rồi lưu SQL.

Quy tắc đặt trong worker chung, nên FE và CLI nhập folder đều sử dụng được.
`QWEN_PROMPT_PATH` là prompt Stage A/B cho video-only; `QWEN_LOG_PROMPT_PATH`
trỏ tới `backend/prompts/ollama_incident.txt` cho nhánh log khi prompt chính là A/B.
Prompt V2 tùy chỉnh đã cấu hình trực tiếp vẫn được giữ cho nhánh log.
Không gửi prompt A/B vào validator V2 của provider cũ.

CSV không hợp lệ bị từ chối ở upload; không âm thầm chuyển sang nhánh video-only.
CSV hợp lệ nhưng thiếu anchors/offset vẫn chọn nhánh log; pipeline cũ ghi rõ
UNKNOWN, lưu log-triggers.json rồi dừng với lỗi thiếu đồng bộ trước khi gọi Qwen.
Không tự chuyển sang quét vài frame và không suy offset từ dòng đầu CSV.
Offset khai báo khi upload được nhánh log sử dụng cùng với anchors đã xác nhận.
Diagnostics ghi pipeline, candidate, prompt thực, request, trạng thái gọi Qwen và
validation cho cả hai nhánh. Các job đã failed không tự đổi thành succeeded.

## Hướng hợp nhất nếu sau này chỉ cần một pipeline

1. Giữ hai cách nhập dữ liệu: API upload và CLI nhập folder.
2. Cả hai tạo cùng Incident, metadata đồng bộ, job persistent và audit.
3. Worker gọi một pipeline phân tích chung, không tự chọn thuật toán bằng cách
   tìm marker trong prompt.
4. Pipeline chung dùng một provider adapter cho cấu hình loopback, request/response,
   schema/evidence validation và raw output history.
5. Nếu giữ prompt A/B, tích hợp hai stage vào pipeline chung và hỗ trợ đúng schema
   A/B trong adapter. Không chỉ đổi tên hàm rồi gửi prompt A/B vào validator V2.
6. Chỉ sau khi toàn bộ output hợp lệ mới gọi `reports.complete_analysis` để lưu
   DRAFT, evidence, ReportVersion, AuditEvent và job succeeded.

Đây là phương án hợp nhất hoàn toàn nếu cần sau này. Quy tắc hiện hành giữ hai
pipeline theo input đúng yêu cầu người dùng, không thực hiện phương án này.

## Điều kiện input phải tương đương

MP4 và CSV cần cùng mốc đồng bộ được xác nhận để ghép log vào thời gian video.
Lượt 60s trước có offset/anchors; clip C858 upload chưa có mốc được xác nhận.
Không được đoán offset từ dòng đầu CSV hoặc dùng offset của video 60s cho clip khác.
Thiếu đồng bộ phải được ghi UNKNOWN trong kết quả, dù dùng pipeline chung.

## Trạng thái C858 lúc kiểm tra

Job `JOB-B66E50F273E1` đã gọi Qwen local bằng nhánh Stage A/B, nhưng failed do output
không qua kiểm tra mô tả tiếng Việt / coverage. Raw request và response được giữ.
Job này chưa tới `complete_analysis`, nên chưa có DRAFT hoàn chỉnh lưu qua transaction.
