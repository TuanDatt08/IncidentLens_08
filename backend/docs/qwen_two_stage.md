# Thử Qwen hai bước: quan sát ảnh rồi tổng hợp

Áp dụng cho đường MP4 + CSV / incident V1 hiện tại. Bật bằng `QWEN_TWO_STAGE=true` trong Compose APP; V2 giữ provider cũ để không thay budgets/checkpoints ngoài phạm vi thử nghiệm này.

## Luồng mới

1. Flag telemetry khoanh vùng nghi vấn như trước. Backend trích frame tại 4 FPS trong vùng đó.
2. Mỗi request quan sát chỉ chứa **một ảnh**. Model mô tả người, vị trí tương đối với đường/xe, đối tượng khác, contact nhìn thấy và che khuất. Không gửi telemetry, flag, tên file hay nhãn dataset vào bước quan sát.
3. Schema quan sát không có `incident_detected`, loại sự kiện hoặc kết luận near miss. Backend gắn evidence ID, timestamp và hash ảnh đã xác minh; model không tự tạo các định danh này.
4. Sau khi **tất cả frame của candidate** được quan sát hợp lệ, backend gửi một request text tổng hợp: quan sát theo thời gian + telemetry đã đồng bộ + flags + registry evidence.
5. Chỉ bước tổng hợp trả schema incident V2/DRAFT. Backend vẫn kiểm tra schema, thời gian, evidence, collision không có contact quan sát được và mâu thuẫn telemetry.

Với candidate 27 frame, có 27 request quan sát và 1 request quyết định. `QWEN_BATCH_FRAMES=16` không chia quyết định thành từng nhóm trong chế độ này. Nếu có nhiều candidate, mỗi candidate có một quyết định riêng rồi dùng cơ chế tổng hợp hiện có; không giả vờ đã quan sát ngoài vùng flag.

## Audit và lỗi

Mỗi request/response được journal với stage `frame_observation` hoặc `incident_decision`. File `<candidate>.observations.json` được cập nhật sau từng frame, có `complete` và `expected_frames`. Provenance của kết luận chứa toàn bộ quan sát và hash input. Giới hạn ảnh, telemetry, byte output và timeout vẫn được kiểm tra. Không tiếp tục quyết định nếu quan sát lỗi/thiếu; không coi model output lỗi là không có incident.

Không sửa báo cáo cũ. Test live dùng một incident mới từ cùng source video/CSV. Hệ thống giữ `DRAFT`; không ép kết luận dương tính. Quan sát một ảnh chỉ thể hiện pose/position, không chứng minh hướng chạy hoặc tốc độ; motion là suy luận ở bước tổng hợp, cần nêu uncertainty.

## Vì sao thử cách này?

Lượt trước nhận nhiều ảnh nhưng vừa mô tả vừa phán quyết ngay, thường dùng thiếu va chạm để phủ nhận sự kiện. Tách schema loại bỏ kết luận đó khỏi bước quan sát, tạo một chuỗi dữ kiện để bước tổng hợp đánh giá người đi vào quỹ đạo và phanh tránh, độc lập với contact.

Cách này có thể cải thiện reasoning, nhưng có thể chậm hơn batching vì gọi model nhiều lần và vẫn có thể sai. Quyết định text-only không nhìn lại ảnh; lỗi nhận diện ở bước đầu có thể truyền sang bước cuối. Cần đánh giá quan sát, evidence và kết luận trên nhiều clip có nhãn trước khi chọn làm mặc định lâu dài.

Rollback thử nghiệm: đặt `QWEN_TWO_STAGE=false` trong Compose rồi recreate APP. Không cần đổi FE, Neon hoặc model GPU.

## Kết quả thử live ngày 13/10/2026

Incident `INC-0ED0FA4F43DF` có 27 quan sát hợp lệ trong candidate 53.375–60.042s. Quan sát tại 57.625s ghi người ở “center lane, directly in front of the ego vehicle”. Dữ liệu nhận diện mỗi frame không có boolean incident. File checkpoint giữ cả output có cấu trúc và mô tả thô để kiểm tra.

Lượt đầu gián đoạn HTTP 502 sau 4 ảnh. Đã bổ sung reuse quan sát khi model/revision, prompt hash, evidence ID, timestamp và hash ảnh khớp. Lượt tổng hợp tiếp theo trả HTTP 200 nhưng vi phạm invariant âm tính (false kèm window/timeline); output lỗi được lưu, không được biến thành kết quả hợp lệ.

Lượt cuối dùng JSON grammar cho invariant quyết định và bỏ mô tả tự do khỏi input tổng hợp để loại các câu “no incident” ngoài nhiệm vụ. Chỉ trường quan sát có cấu trúc được gửi, tất cả mô tả gốc vẫn giữ trong audit. Job `JOB-EA804773D8FA` succeeded và giữ 27 quan sát; lượt này reuse toàn bộ nên không thể dùng thời gian job để so sánh tốc độ end-to-end với batching.

Model tổng hợp đã thừa nhận telemetry gợi ý phanh khẩn cấp, nhưng vẫn trả false và nói người không trực tiếp trước xe — mâu thuẫn với một quan sát đã có. Backend giữ `REVIEW_REQUIRED_TELEMETRY_CONFLICT` và DRAFT. Vì vậy thử nghiệm xác nhận luồng hai bước hoạt động, chưa chứng minh cải thiện độ chính xác hoặc phát hiện near miss. Test toàn repo 281 pass, Ruff pass; không coi các test này là xác nhận chất lượng model.
