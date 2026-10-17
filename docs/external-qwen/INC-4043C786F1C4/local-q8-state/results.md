# Qwen local Q8 — trạng thái từng frame + chuỗi 3 frame — INC-4043C786F1C4

Model `qwen2.5vl:7b` trên Ollama 0.40.3 local, import từ `Qwen2.5-VL-7B-Instruct-Q8_0.gguf` + `mmproj-…-f16.gguf` (không phải bản Q4_K_M trên Vast). RTX 4050 Laptop 6 GB qua Vulkan, model chạy 66% CPU / 34% GPU. temperature=0, seed=42, output ép bằng JSON schema của Ollama (`format`).

Cùng 13 ảnh của `1frame1contextwindow`, hai biến thể:

- **A** — cả khung hình thu về 640×360 (giống backend gửi Ollama).
- **B** — crop vùng đường 1200×480 (x 400–1600, y 380–860), che xám đồ trang trí trên kính. Tọa độ che chọn tay cho clip này.

[Script per-frame](run_test.py) · [Kết quả per-frame](results.json) · [Script chuỗi](run_sequence.py) · [Kết quả chuỗi](sequence_results.json) · [Ảnh đã xử lý](images/)

## Test 1: hỏi trạng thái từng frame, code kết luận

Mỗi frame một request; Qwen trả `state` (upright/tilted/fallen/unclear), `place`, `position`, `distance`. Code gắn `LOSS_OF_CONTROL_CANDIDATE` khi ≥2 frame có xe máy/người `tilted` hoặc `fallen`.

| Giây | A — full 640 | B — crop + che |
|---|---|---|
| 8.3 | xe máy upright/road; **người unclear/roadside/right** (nhiều khả năng là đồ trang trí) | xe máy upright/road; không còn "người" ảo |
| 9.5–9.9 | xe máy upright/road/center | xe máy upright/road/center, near |
| 10.0 | xe máy upright/road/center | **xe máy + người unclear/roadside/right** ("parked on the right side") |
| 10.1–10.2 | xe máy upright/road/center | xe máy upright/road/center |
| 10.5 | người upright/roadside | xe máy upright/road/right |
| 10.9 | chỉ ô tô | xe máy upright/**roadside**/right |
| 11.5–13.5 | chỉ ô tô | chỉ ô tô |

**Kết luận code: cả A và B đều `NO_ABNORMAL_STATE_SEEN`.** Frame 10.2s xe đang đổ rõ ràng nhưng cả hai biến thể vẫn trả `upright`. Model gần như luôn chọn `upright`.

B tốt hơn A ở hai điểm: hết nhận nhầm đồ trang trí thành người, và có ghi nhận xe máy dạt sang lề phải (10.0s, 10.9s). Tín hiệu này không ổn định (10.1–10.2s quay lại road/center).

Thời gian: 20–46 giây/frame khi model đã nạp (request đầu 78 giây gồm nạp model); khoảng 1.220–1.260 token/ảnh cho cả A và B.

## Test 2: 3 crop B trong một request, câu hỏi trắc nghiệm

| Bộ | Frame | Qwen chọn | Đúng? |
|---|---|---|---|
| Sự kiện | 9.5 / 10.0 / 10.2 | **B** — "swerves to the roadside but remains upright and in control" | Một phần: thấy đánh lái gấp vào lề, không thấy ngã |
| Đối chứng | 11.5 / 12.5 / 13.5 | **E** — không thấy xe máy | Đúng |

Đưa nhiều frame vào cùng request cho model thấy thay đổi mà per-frame không thấy. Đối chứng hiện chỉ là cảnh không có xe máy; chưa có clip xe máy đi qua bình thường nên chưa kiểm chứng được model có chọn B/C bừa hay không.

## Test 3: crop sát xe máy (biến thể C)

Khung cố định 720×440 (x 700–1420, y 400–840) bám đường đi của xe máy 9.3–10.5s, che phần đồ trang trí còn lọt vào khung. Đối chứng mới: 9.3 / 9.5 / 9.7s — cùng xe máy khi còn chạy bình thường trên đường.

[Script](run_zoom.py) · [Per-frame](zoom_frame_results.json) · [Chuỗi](zoom_sequence_results.json) · [Cặp trước/sau](zoom_pair_results.json)

Per-frame:

| Giây | Qwen | Thực tế |
|---|---|---|
| 9.3 / 9.5 / 9.7 | upright, road | đúng — xe chạy bình thường |
| 9.9 / 10.0 / 10.1 | upright, road | 10.0–10.1 xe đã đánh lái, nghiêng |
| 10.2 | **tilted** — "leaning slightly to the right" | đúng hướng — xe đang đổ |
| 10.5 | upright, road | **sai** — xe và người nằm dưới lề |

Code: 1 frame bất thường → `INCONCLUSIVE` (quy tắc cần ≥2).

Trắc nghiệm nhiều ảnh:

| Bộ | Frame | Qwen chọn |
|---|---|---|
| Sự kiện, 5 ảnh | 9.9 / 10.0 / 10.1 / 10.2 / 10.5 | **B** — đánh lái vào lề, vẫn đứng thẳng |
| Đối chứng, 3 ảnh | 9.3 / 9.5 / 9.7 | **A** — chạy bình thường |
| Cặp sự kiện | 9.9 → 10.5 | **B** |
| Cặp đối chứng | 9.3 → 9.7 | **A** |

Model phân biệt đúng "chạy bình thường" và "đánh lái bất thường" trên cùng một xe máy, nhất quán qua 4 request. Chưa lần nào chọn C (mất thăng bằng, ngã), kể cả khi ảnh 10.5s cho thấy rõ người nằm trên xe đổ.

## Test 4: thử thêm mọi cách (vòng D–I, tự động hóa)

Ảnh: T = crop vuông 448×448 sát xe máy (chọn tay), auto = crop vuông quanh bbox do Qwen tự tìm trên ảnh B. Đối chứng: 9.3 / 9.5 / 9.7s, cùng xe máy khi còn chạy bình thường.

[run_tricks.py](run_tricks.py) · [run_tricks2.py](run_tricks2.py) · [run_tricks3.py](run_tricks3.py) · [run_auto.py](run_auto.py) · kết quả `tricks*_results.json`, `auto_results.json` · [kiểm tra bbox](images/grounding_check.png)

| Cách | Đối chứng | Sự kiện | Kết luận |
|---|---|---|---|
| D — câu hỏi có/không về tư thế (T) | 9.3/9.5: "nghiêng mạnh, không ngồi vững" | 10.5: không nằm nghiêng | Loại — trả lời như nhau cho mọi frame |
| F — mô tả rồi phân loại (T) | 9.7 → B | 10.2, 10.5 → B, mô tả giống hệt nhau | Loại |
| G — tham chiếu "đứng thẳng" + enum | 9.3→9.7: leaning | 9.5→10.2: text "now on its side… fallen over" nhưng enum `same_upright_ridden` | Text đúng, nhãn sai |
| G2 — như G, khóa suy luận trước | leaning | 9.5→10.5: text "now on its side, rider is off the bike", enum `upright_riding` | Text đúng, nhãn vẫn sai |
| H/H2 — 3 frame ghép một ảnh dải | **C (ngã)** | C | Loại — báo ngã cả đối chứng |
| S2 — nhiều ảnh, suy luận trước | A | B | Ổn định như Test 2–3, không ra C |
| I — bbox xe máy | khoanh đúng | khoanh đúng cả 8 frame | **Tin được** cho định vị |
| J — 2 bbox xe + người, so hình học | — | — | Loại — tỉ lệ khung người không theo quy luật |
| G3 — tham chiếu, chỉ text, code dò từ khóa, temperature 0 (T) | 0/3 cặp báo ngã | 9.5→10.0 "off the seat, indicating a fall", 9.5→10.5 "on its side, rider off the bike"; 9.5→10.2 trượt | Có tín hiệu |
| Tự động — bbox → crop → so cặp liền nhau, câu hỏi trung tính, 3 mẫu | 0 | 0/16 | Loại — 0.1–0.3s quá ít thay đổi; không nhãn tham chiếu thì Qwen không chú ý tư thế |
| Tự động — G3 trên crop auto, temperature 0.7, 3 mẫu | 9.5→9.7: một mẫu "on its side, rider is falling off" | 9.5→10.5: 3/3 mẫu "overturned"/"sideways" | Bắt được trạng thái đã ngã, nhưng có báo ngã sai ở đối chứng |

### Vòng 5 ([run_round5.py](run_round5.py), `round5_results.json`)

| Cách | Đối chứng 9.3–9.7 | Sự kiện | Kết luận |
|---|---|---|---|
| Keypoint → code tính góc nghiêng | 1° / 18° / 26° | 9.9–10.1: 27° → 42°; 10.2, 10.5: 0° | Loại — đối chứng đã nghiêng 18–26°, frame ngã ra 0° |
| Hỏi góc nghiêng bằng số | 60–85° | 60–80° | Loại |
| Khung đỏ trên ảnh đường | `fallen_on_its_side` | `fallen_on_its_side` | Loại |
| Tranh luận (bằng chứng hai phía rồi kết luận) | `falling_or_fallen` | `falling_or_fallen` | Loại |
| Ảnh đôi "BEFORE: upright \| AFTER" | 9.7: `fallen_on_its_side` | `fallen_on_its_side` | Loại |
| Ví dụ mẫu tổng hợp (ảnh xoay 90°) | upright | upright, kể cả 10.5 | Loại |
| System prompt vai chuyên gia tai nạn | B | B | Loại — làm đối chứng thành bất thường |
| Bỏ phiếu 5 mẫu trắc nghiệm | B,A,C,B,A | B,B,B,B,C | Loại — C xuất hiện cả hai bên |
| LLM đọc lại mọi mô tả tự do đã thu | 4/15 nói "ngã" | 10.0–10.2: 2/16; **10.5: 5/7** | Tín hiệu thống kê cho trạng thái đã ngã; một lần gọi không tin được |

Phát hiện phụ: với `format` JSON schema, Ollama sinh các khóa theo thứ tự chữ cái (thấy ở mọi output). Schema `choice` + `evidence` khiến model chốt đáp án trước khi viết lý do. Chưa kiểm chứng trên đường `/v1/chat/completions` mà backend dùng.

**Tổng kết Test 1–4.** Qwen2.5-VL 7B Q8 phân biệt ổn định "chạy bình thường" và "đánh lái bất thường vào lề" khi so nhiều frame (A vs B, nhất quán ở mọi biến thể có đối chứng). Trạng thái "xe đã đổ" chỉ xuất hiện trong mô tả tự do khi so với tham chiếu được gán nhãn "đứng thẳng"; tín hiệu này thật (lặp lại qua 4 prompt và 3/3 mẫu ở 10.5s) nhưng đi kèm báo ngã sai ở đối chứng khi lấy mẫu, nên chưa đủ tin cậy để tự kết luận. Định vị bằng bbox chính xác và tự động được.

## Giới hạn

Một clip, chưa có ground truth chính thức, chưa có clip âm tính tương đương. Vùng che chọn tay. Kết quả không suy rộng cho bản Q4_K_M trên Vast.
