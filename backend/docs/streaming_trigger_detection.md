# Tìm trigger telemetry O(n) và ánh xạ video

## Luồng dùng chung cho upload và folder

MP4 + CSV → validate/probe → Incident → persistent job → worker/heartbeat →
normalize CSV → `find_log_triggers` → alignment → candidate clip/frame →
Qwen local → validate schema/evidence → transaction SQL → DRAFT chờ kỹ sư review.

Chỉ MP4 dùng Stage A/B. Có CSV nhưng thiếu đồng bộ vẫn tìm trigger trên đồng hồ
log, lưu `output/log-triggers.json`, rồi dừng trước Qwen với lỗi thiếu anchors/offset.
Không suy đồng bộ bằng tên file, dòng đầu CSV hoặc nhãn expected.

## Thuật toán

`backend/services/trigger_detection.py` đọc tuần tự từng dòng. Số tín hiệu cố định,
không sort, không load toàn CSV vào RAM; mỗi dòng có chi phí cố định: O(n).
Normalize kiểm tra CSV trong một lượt riêng, detector đọc lượt thứ hai; tổng vẫn O(n).
Trạng thái gồm dòng trước, vận tốc trước, EWMA từng tín hiệu và output có giới hạn.
Mặc định giữ 100 trigger, 32 flag/trigger. Adapter candidate giữ tối đa ít nhất 1000
trigger để có thể ghi overflow `UNANALYZED`; vẫn quét hết CSV và báo phần vượt budget.

| Quy tắc | Ngưỡng ban đầu / bằng chứng |
|---|---|
| HARD_BRAKING | brake ≥ 0.8 |
| BRAKE_RISE | brake ≥ 0.3 và d(brake)/dt ≥ 1.5/s |
| DECELERATION | accel_x (canonical acceleration) ≤ −6 m/s² |
| COLLISION_SENSOR | collision_intensity > 0; chưa tự xác nhận tiếp xúc hình ảnh |
| SHARP_TURN | speed ≥ 3 m/s; yaw ≥ 20°/s hoặc |d(steer)/dt| ≥ 0.8/s; |accel_y| ≥ 2 m/s² |
| VERTICAL_SHOCK | |d²(loc_z)/dt²| ≥ 3 m/s² và accel_z lệch baseline ≥ 2 m/s² |
| EWMA_ANOMALY | residual ≥ max(absolute floor, 6σ), warmup 1s, tau 1s |

CARLA speed_kmh được đổi sang m/s. loc_x/y/z cần đơn vị mét, accel_* m/s²,
compass_deg độ, brake/steer theo hợp đồng CARLA. Không dùng raw delta vị trí như
incident vì chuyển động đều cũng đổi vị trí: tính vận tốc từ x/y, rồi hướng và tốc
độ đổi hướng; dùng gia tốc ngang để kiểm tra chéo. Z dùng sai phân vận tốc và IMU
để giảm nhiễu tọa độ. Thiếu các tín hiệu kiểm tra chéo thì quy tắc tương ứng không
đủ điều kiện; brake, deceleration và EWMA vẫn chạy nếu có cột cần thiết.

Đạo hàm dùng **dt thật của CSV**, không chia cứng cho 1/24. Khoảng trống > 2s
reset đạo hàm/EWMA; timestamp trùng hoặc lùi bị normalizer từ chối. Chênh góc
compass/hướng được wrap về ±180° để tránh spike giả tại 359°→0°.

EWMA dùng alpha = 1 − exp(−dt/tau), cập nhật mean và variance. Không gọi rebound
acceleration về 0 là đỉnh mạnh mới. Gộp excursion nếu khoảng cách đến flag cuối
≤ 1s, **không gộp chỉ vì clip pre/post chồng nhau**. Clip thêm 5s trước/3s sau.
Đỉnh ưu tiên collision > deceleration > turn/vertical > brake > EWMA, rồi mới so
score trong cùng nhóm. Các ngưỡng này cần calibration, chưa phải tiêu chuẩn an toàn.

## Clock và frame

Sau anchors/offset có provenance: video_time = alignment(log_time).
Frame gần nhất = round(video_time × fps), giới hạn trong số frame hợp lệ;
thời gian ngoài video giữ frame=null. Clip được cắt trong [0, duration].
FPS mặc định 24 nếu metadata thiếu; FPS probe của video được ưu tiên. Hai clip cũ
thực tế 30fps, clip 60s 24fps. Không ép 30fps thành 24fps hoặc dùng FPS để đoán offset.

`log-triggers.json` chứa rows, overflow, unknowns và từng trigger: log start/peak/end,
video start/peak/end, frame indices, FPS, sync_status, clip bounds, reasons,
flags (signal/value/threshold/time/score/priority), flag_count và omitted_flags.
Trigger là vùng nghi vấn; thời gian này chưa phải onset/end incident đã xác nhận.
Prompt snapshot/hash, request/response, validation và lịch sử output giữ ở artifacts
pipeline; chỉ output hợp lệ mới lưu AnalysisReport DRAFT/ReportVersion/AuditEvent.

## Kiểm tra ba video thật

Các số dưới đây ghi lại lượt kiểm tra đã thực hiện. Script dùng một lần và
artifacts kiểm tra đã được xoá khi cleanup; không nằm trong pipeline ứng dụng.
Regression hiện hành: `python -m pytest tests/backend/test_services/test_streaming_triggers.py -q`.

| Video | CSV rows | FPS | Trigger | Alignment | Normalize + detector |
|---|---:|---:|---:|---|---:|
| 20260927_030603 (9.533s) | 291 | 30 | 1 | UNKNOWN | 0.0288s |
| 20260927_031741 (9.533s) | 291 | 30 | 2 | UNKNOWN | 0.0222s |
| 20261011_133619 (60.042s) | 1446 | 24 | 9 | VERIFIED offset 58.458s | 0.1005s |

Cả ba có trigger gần reaction timestamp của expected (tolerance 0.5s); expected
chỉ đọc **sau** detection, verified_by=null nên đây chưa phải recall benchmark.
Không có collision sensor trigger. Đỉnh phanh chính lần lượt là log 0.3s, −0.1s,
−0.083s. Với clip 60s, đỉnh cuối ánh xạ 58.375s/frame1401, ảnh thấy người đi bộ sát
đầu xe. Các đỉnh trước đó có phanh/chuyển hướng và cả EWMA yếu: chưa thể gọi tất cả
là incident. Hai video 10s chưa có mapping xác nhận, không trích clip theo log bằng
offset đoán. Kiểm tra này xác minh detector/extraction, **không tuyên bố ba report
Qwen đã hoàn thành**. Review ảnh thưa không chứng minh không có incident khác.

## Throughput 1 triệu dòng

Bản cuối với merge theo khoảng cách flag xử lý 1,000,000 dòng (157,104,490 bytes)
trong **32.34s**: normalize 7.92s + detector 24.42s. Giữ 100 trigger, báo 3336
interval vượt output budget; vẫn kiểm tra đủ 1M dòng. Ba lượt trước khi đổi quy tắc
gộp có tổng 52.97s, 116.61s, 37.65s, cho thấy tải máy/cache làm timing dao động.
Đây là throughput synthetic, không là cam kết latency hay benchmark chất lượng.
Không gồm upload, FFmpeg, Qwen/token, SQL hoặc parse các JSON khác. Bộ nhớ detector
bounded; file benchmark 157MB vượt default max_log_size_mb=100 nên muốn upload
cần cấu hình giới hạn phù hợp. Benchmark đọc trực tiếp local, không bỏ qua validate
CSV. Trigger scanner không sử dụng token model.

## Gửi AI log lên Phoenix khi git push

AI log nằm local trong .ai-log/session.jsonl, không đưa vào GitHub.
Cài hook gốc bằng `powershell -ExecutionPolicy Bypass -File scripts/setup_hooks.ps1`.
Không đặt core.hooksPath sang thư mục khác vì sẽ bỏ qua .git/hooks/pre-push.
Hook gọi scripts/submit_log.py; cấu hình local trong .env:
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY lấy từ tài khoản Phoenix, không commit key.
Submit thành công archive local; lỗi giữ log để retry. Push Git thành công chưa
chứng minh Phoenix đã nhận: cần kiểm tra thông báo submit và trang AI Logs.
