# Thiết kế chọn frame và prompt Qwen theo chuỗi hành động

Trạng thái: thiết kế đã được duyệt. Nội dung dưới đây ghi lại thiết kế tại thời điểm duyệt; chi tiết mã triển khai và giới hạn thực tế xem [vast-worker.md](vast-worker.md#chuỗi-frame-và-kết-luận-toàn-video).

## 1. Phân biệt hiện tại và đề xuất

Code hiện tại có hai đường xử lý:

- Có log: `worker.py` chọn `qwen_processing.py`; chọn candidate từ telemetry, chia chuỗi frame chồng lấn, rồi có một lượt tổng hợp **cho từng candidate** khi bật temporal context.
- Không log, runtime Ollama: `worker.py` chọn `prompt_pipeline.py`; Stage A tìm sự cố, Stage B phân tích từng sự cố. Chưa có lượt tổng hợp toàn bộ các cửa sổ thành một kết luận cuối cho video.

Nhánh không log hiện chia cửa sổ 8 giây, bước 6 giây, tức chồng lấn 2 giây. Hàm `frames()` trích theo `qwen_sampling_fps` nhưng chỉ trả khoảng 4 frame trải đều cho request. Vì vậy trích 4 FPS không đồng nghĩa Qwen đã xem tất cả frame ở 4 FPS. Nhánh này chưa dùng cùng cơ chế batch 6 ảnh, chồng 2 ảnh của nhánh có log.

Việc chuyển worker và Qwen lên cùng GPU không tự thay đổi hai cách chọn frame này.

## 2. Hai loại chỉ số frame

### Có log đồng bộ

Mỗi ảnh được gắn `evidence_id`, `sequence_index` và `t_video_s`. `t_video_s` là số giây tính từ đầu video, không phải timestamp của log chưa quy đổi và không phải thời gian bắt đầu clip.

Ví dụ ảnh có `t_video_s=58.375` phải được ghép với các dòng log quanh 58.375 giây sau khi backend đã xác nhận ánh xạ đồng hồ. Nếu log chưa đồng bộ, không ghép gia tốc/phanh với ảnh như bằng chứng cùng thời điểm.

### Không có log

Theo yêu cầu, prompt dùng `frame_seq` là thứ tự **toàn cục của các ảnh đã lấy mẫu**, bắt đầu từ 1; không đưa `t_video_s` vào prompt video-only. Không đánh số lại từ 1 ở mỗi batch.

Ví dụ batch đầu chứa F000001–F000006, batch sau F000005–F000010. F000005 ở hai batch phải là cùng một ảnh.

`frame_seq=10` không có nghĩa là frame thứ 10 của file MP4 gốc. Backend giữ ánh xạ riêng từ `frame_seq` sang timestamp và chỉ số frame gốc để cắt clip, seek player và lưu bằng chứng. Các API/report hiện dùng giây vẫn do backend quy đổi; không yêu cầu Qwen tự đoán giây từ thứ tự ảnh.

Thứ tự ảnh chỉ biểu diễn trước/sau. Muốn biểu diễn nhịp chuyển động, ảnh trong cùng chuỗi cần được lấy mẫu đều. Với chuỗi lấy mẫu khác nhịp, phải ghi rõ ranh giới chuỗi; không giả vờ mọi ảnh cách đều nhau. Không suy vận tốc m/s, gia tốc hoặc TTC từ `frame_seq`.

## 3. Chọn frame khi có log

1. Backend đọc và đồng bộ log; phát hiện các khoảng nghi vấn bằng logic số liệu. Flag chỉ chọn vùng để xem, chưa phải kết luận incident.
2. Lấy frame nền trong cửa sổ candidate ở 4 FPS; thêm frame dày ở 8 FPS quanh critical ±1 giây. Sắp xếp theo thời gian, loại timestamp trùng và giữ giới hạn 256 frame/candidate hiện có.
3. Chia theo 4 ảnh CORE liên tiếp, thêm 1 ảnh BEFORE và 1 ảnh AFTER thực tế nếu có: CORE 1–4 + AFTER 5; BEFORE 4 + CORE 5–8 + AFTER 9; BEFORE 8 + CORE 9–12 + AFTER 13… Batch ở biên có thể ít ảnh hơn. Chồng lấn giúp nhìn được chuyển động qua ranh giới batch, không biến hai batch thành hai sự cố.
4. Mỗi request gửi lại bộ nhớ riêng của trigger (`trigger_memory`, khóa recording/job/candidate), timestamp `t_video_s`, vai trò từng ảnh, telemetry và số đo backend tính. API Qwen vẫn stateless; worker giữ và truyền lịch sử. Bộ nhớ không trộn giữa các trigger. Lưu kết quả có dẫn chứng, kể cả batch lỗi thành khoảng chưa biết.
5. Hết trigger, gửi `FINAL_CANDIDATE` với toàn bộ lịch sử trigger và bộ ảnh OVERVIEW. Lịch sử được giới hạn 32.000 ký tự bằng rút gọn văn bản; giữ timestamp, ID bằng chứng, thứ tự, lỗi và unknowns. Nếu metadata vẫn vượt ngưỡng thì dừng rõ lỗi, không âm thầm bỏ lịch sử. Bản đầy đủ ở `trigger-context-CND-*.json` và journal request/response. Đây là giới hạn ký tự bảo thủ, không phải phép đếm token chính xác; cấu hình Qwen hiện tại vẫn 32.768 token. Nhận định mới cần ảnh đính kèm; nhận định dùng ảnh lịch sử phải khớp nguyên văn timeline/factor đã xác thực trước đó. Nếu các ghi chú mâu thuẫn, xem lại chuỗi liên quan trước khi kết luận.

Ngưỡng chọn candidate hiện được hiệu chỉnh cho dữ liệu đã cung cấp; không tuyên bố phù hợp mọi nguồn log. Prompt không nên ép xác nhận một sự cố cụ thể bằng tên file hay đáp án mong đợi.

## 4. Chọn frame khi không có log

1. Quét các cửa sổ 8 giây, chồng 2 giây để có bối cảnh trước/sau và tránh cắt sự cố đúng ranh giới.
2. Đề xuất lấy mẫu đều 4 FPS trong mỗi cửa sổ rồi gửi **tất cả ảnh đã chọn** bằng batch 6 ảnh, chồng 2 ảnh. Không trích hàng chục ảnh rồi chỉ gửi 4 ảnh trải đều như hiện tại.
3. Gán `frame_seq` toàn cục, giữ nguyên ID khi ảnh xuất hiện lại ở cửa sổ hoặc batch chồng lấn.
4. Qwen nhận biết diễn biến: người đi bộ từ vỉa hè tiến vào làn; xe khác cắt ngang; khoảng cách tương đối thu hẹp; xe đổi hướng; tiếp xúc hoặc tách khỏi nhau. Không chỉ mô tả riêng từng ảnh.
5. Khi có nghi vấn nhưng chưa rõ, gửi chuỗi dày hơn quanh vùng đó ở 8 FPS nếu còn ngân sách. Đây là bước bổ sung dự kiến, không phải tính năng đang chạy.
6. Tổng hợp theo candidate rồi tổng hợp toàn video. Các khoảng chưa quét hoặc request lỗi phải đi vào phần thiếu coverage.

4 FPS/6 ảnh là cấu hình khởi đầu để đánh giá trên GPU, không phải ngưỡng đã chứng minh tối ưu. Video dài làm tăng số request và chi phí; phải kiểm tra trước ngân sách số ảnh, request và thời gian. Không im lặng bỏ phần còn lại rồi trả “không có incident”.

## 5. Prompt 1: quan sát một chuỗi liên tiếp

Đây là mẫu đề xuất, chưa phải prompt production. Nội dung chỉ dẫn nên ngắn; schema máy đọc được do backend cung cấp riêng.

```text
Bạn phân tích một chuỗi ảnh giao thông theo thứ tự được cung cấp.
Đọc tất cả ảnh như các quan sát nối tiếp của cùng một diễn biến.
Chỉ mô tả thay đổi thực sự nhìn thấy giữa các ảnh; phân biệt chuyển động
camera với chuyển động của người và phương tiện khi có thể.

Với INPUT_MODE=VIDEO_WITH_SYNCED_LOG, dùng t_video_s và telemetry đã đồng bộ.
Với INPUT_MODE=VIDEO_ONLY, dùng frame_seq. Không yêu cầu log để phát hiện
xung đột nhìn thấy; không tự tạo timestamp, vận tốc hoặc gia tốc.

Tìm bằng chứng về: tiếp xúc thực tế; quỹ đạo xung đột/suýt va chạm;
cắt ngang nguy hiểm; người đi bộ vào đường đi của xe; tránh vật cản đột ngột;
lệch làn nguy hiểm; mất kiểm soát; chướng ngại gây nguy hiểm.
Người xuất hiện, khoảng cách gần, xe quay hoặc phanh thông thường chưa đủ
để xác nhận sự cố. Không thấy tiếp xúc không phủ nhận một xung đột đã thấy.

Nêu bối cảnh trước, thay đổi chính và trạng thái cuối của chuỗi.
Giữ ID đối tượng nhất quán khi nhận dạng được; nếu không chắc thì nói rõ.
Trích evidence_id và t_video_s hoặc frame_seq cho từng nhận xét chính.
Tách OBSERVED, SUPPORTED_INFERENCE và UNKNOWN.
Chưa kết luận thay cho toàn bộ video; không coi phần chưa xem là bình thường.
Trả JSON đúng schema được cung cấp, mô tả tiếng Việt, review_status=DRAFT.
```

Ví dụ metadata có log, mỗi bản ghi đặt ngay trước ảnh tương ứng:

```json
{"input_mode":"VIDEO_WITH_SYNCED_LOG","sequence_id":"S012","frames":[
  {"evidence_id":"E101","sequence_index":1,"t_video_s":57.875},
  {"evidence_id":"E102","sequence_index":2,"t_video_s":58.000}
]}
```

Ví dụ không log:

```json
{"input_mode":"VIDEO_ONLY","sequence_id":"S012","frames":[
  {"evidence_id":"F000045","frame_seq":45},
  {"evidence_id":"F000046","frame_seq":46}
],"sampling":"ordered_uniform_within_sequence"}
```

Ngoài metadata, request phải chứa ảnh thực tế. Gửi tên frame hoặc JSON đơn thuần không giúp Qwen nhìn được cảnh.

Đầu ra quan sát đề xuất: `sequence_id`, `observations`, `candidate_events`, `continuity_notes`, `unknowns`, `evidence_ids`, `review_status`. Mỗi nhận xét/candidate có tham chiếu ảnh; không chỉ một đoạn summary chung khó kiểm chứng.

## 6. Prompt 2: kết luận một candidate

Chạy sau khi các chuỗi liên quan đã hoàn thành. Đây là bước phân tích sâu thay cho việc coi một batch dương tính là kết luận cuối.

```text
Bạn đánh giá một sự kiện nghi vấn từ các chuỗi ảnh đã xử lý.
Ghi chú trước là nhận xét có thể sai của model, không phải bằng chứng mới.
Đối chiếu các ghi chú với ảnh overview và dẫn chứng được cung cấp.
Ảnh overview là các ảnh chọn lọc, không mặc định là các frame liên tiếp.
Không bỏ phiếu theo số batch và không đếm các frame chồng lấn như bằng chứng độc lập.

Xác định diễn biến trước, xung đột chính và kết quả quan sát được.
Phân biệt COLLISION với xung đột/suýt va chạm và với hoạt động bình thường.
Nếu có log đồng bộ, đánh giá phanh mạnh riêng với nguyên nhân và va chạm.
Nếu không có log, chỉ xác nhận những gì chuỗi hình ảnh hỗ trợ.
Nêu rõ ghi chú mâu thuẫn, thiếu coverage và bằng chứng cần xem lại.

Chọn CONFIRMED, INCONCLUSIVE hoặc NO_INCIDENT_IN_OBSERVED_COVERAGE.
Chỉ CONFIRMED khi có diễn biến nguy hiểm được chứng minh bằng evidence.
Trả một kết luận cho candidate, không bịa thời điểm hoặc nguyên nhân.
Dùng t_video_s nếu có log đồng bộ; dùng frame_seq nếu video-only.
Trả JSON theo schema, tiếng Việt, review_status=DRAFT.
```

Input gồm toàn bộ ghi chú chuỗi thuộc candidate, danh sách request thất bại, giới hạn quan sát và ảnh đại diện trước–xung đột–sau. Khi ảnh đại diện không đủ giải quyết bất đồng, backend cần chọn chuỗi gốc liên quan để xem lại; không ép model kết luận chỉ từ summary.

## 7. Prompt 3: tổng hợp cuối toàn video

Đây là bước người dùng yêu cầu bổ sung sau khi tất cả chuỗi/candidate đã hoàn thành. Nhánh có log hiện chỉ tổng hợp từng candidate; nhánh không log chưa có bước kết luận toàn video độc lập.

```text
Bạn lập kết luận cuối cho video từ các kết quả candidate và ghi chú chuỗi.
Kiểm tra mọi kết quả và coverage, kể cả các chuỗi âm tính, chưa rõ hoặc lỗi.
Gộp các candidate thực sự thuộc cùng một diễn biến, dựa trên frame/evidence
và sự liên tục quan sát được. Giữ riêng các sự cố độc lập.
Không gộp chỉ vì hai sự kiện ở gần nhau và không bỏ phiếu theo số summary.

Với từng sự kiện: nêu có xác nhận incident không, loại sự kiện,
chuỗi diễn biến, dẫn chứng chính và điều chưa xác định.
Giữ nguyên t_video_s nếu có log đồng bộ hoặc frame_seq nếu video-only.
Không coi ghi chú model như bằng chứng trực tiếp. Không coi thiếu va chạm
là lý do phủ nhận xung đột hoặc phanh khẩn cấp có bằng chứng.

Nếu có ít nhất một sự cố xác nhận, overall_status=CONFIRMED.
Nếu chưa có sự cố xác nhận nhưng còn nghi vấn chưa giải quyết, coverage thiếu
hoặc request lỗi ảnh hưởng kết luận, overall_status=INCONCLUSIVE.
Chỉ dùng NO_INCIDENT_IN_OBSERVED_COVERAGE khi các phần đã xử lý không còn
nghi vấn; trạng thái này không khẳng định sự cố vắng mặt giữa các ảnh lấy mẫu.
Trả JSON đúng schema, mô tả tiếng Việt, review_status=DRAFT.
```

Input cuối gồm sổ ghi chú của tất cả batch, kết quả candidate, evidence map và coverage map. Đính kèm ảnh then chốt cho các sự kiện/nghi vấn; không cần gửi lại toàn bộ ảnh cùng lúc. Qwen không tự nhớ các request trước: backend phải đưa ngữ cảnh vào request cuối.

Nếu tổng ghi chú vượt context budget, tổng hợp theo cửa sổ trước rồi tổng hợp các bản đó. Phải giữ evidence IDs, mâu thuẫn và các phần chưa quan sát xuyên suốt; không cắt bỏ ghi chú âm tính hoặc chưa rõ để vừa context.

Đầu ra cuối đề xuất: `overall_status`, `incidents`, `unresolved_candidates`, `coverage`, `summary`, `unknowns`, `review_status`. Dùng ba trạng thái thay vì ép boolean khiến “chưa rõ” bị hiểu thành “không có”. Adapter backend tiếp tục phục vụ contract UI hiện có; thay đổi schema cần được kiểm tra tương thích.

## 8. Ví dụ chuỗi video-only

- F000041–F000044: người đi bộ đứng ngoài làn, xe đang tiến tới.
- F000045–F000048: người đi bộ vào đường đi của xe; khoảng cách tương đối giảm.
- F000049–F000052: xe có phản ứng quan sát được, người đi bộ đi qua phía trước.
- F000053–F000056: hai bên tách nhau, không thấy tiếp xúc trong ảnh được cung cấp.

Chỉ kết luận xung đột/suýt va chạm khi chuỗi thực sự cho thấy đường đi xung đột và mức nguy hiểm, không chỉ vì có người trước camera. Không tự kết luận COLLISION. Không có log thì không khẳng định lực phanh, vận tốc chính xác hoặc lỗi điều khiển. Nếu các ảnh không chứng minh đủ diễn biến, giữ INCONCLUSIVE.

## 9. Phạm vi sửa và kiểm chứng sau khi duyệt

- Chỉnh hai prompt hiện hành, bổ sung prompt tổng hợp với schema xác định; tránh sửa JSON ví dụ tùy tiện vì `prompt_contracts()` hiện tạo model trực tiếp từ ví dụ Stage A/B.
- Sửa cách chọn/gửi frame video-only và thêm nhãn từng ảnh; giữ ánh xạ backend sang giây để không phá player/cắt clip.
- Bổ sung lượt tổng hợp cuối ở cả hai nhánh; giữ raw request/response và hash prompt để so sánh.
- Kiểm tra thứ tự frame, ảnh chồng lấn, t_video_s, quy đổi frame_seq, log chưa đồng bộ, tổng hợp không có candidate, request lỗi, và ngân sách context/request.
- Đánh giá trước/sau trên cùng video có nhãn: va chạm, suýt va chạm, người đi bộ bình thường, phanh thường, quay xe; cả có log và không log. Báo false positive, false negative, sai mốc sự kiện và độ trễ.
- Chưa có kết quả GPU mới trong tài liệu này. Prompt tốt hơn không phải bằng chứng chất lượng đã tăng và không bảo đảm mọi incident đều được phát hiện.
