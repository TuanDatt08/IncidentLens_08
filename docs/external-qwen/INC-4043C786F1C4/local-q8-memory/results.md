    # Bộ nhớ sự kiện, quét cả video và đổi model — INC-4043C786F1C4 + CARLA v16–v18

Tiếp nối [local-q8-state](../local-q8-state/results.md) (vòng 1–5, Qwen2.5-VL 7B). Ở đây dùng **video gốc** `test_incident_60s.mp4` (SHA256 khớp `metadata.json`, 30 fps, 1920×1080) và 3 clip CARLA `version_16..18` (1280×720, 24 fps, người đi bộ bất ngờ băng qua, ego phanh, **near miss, không va chạm**; đáp án trong `*.expected.json`).

Ollama 0.40.3 local, RTX 4050 Laptop 6 GB. Model: `qwen2.5vl:7b` (GGUF Q8_0 tự import) và `qwen3.5:9b` (Ollama library, Q4_K_M, thinking tắt). temperature 0 trừ khi ghi khác.

## Tiền xử lý tự động (không còn tọa độ chọn tay)

[frames.py](frames.py) · [ornament.py](ornament.py) · [qwen.py](qwen.py)

- **Mép capo:** hàng pixel đầu tiên ở nửa dưới mà ≥60% pixel gần như không đổi trong lúc xe chạy; không cao hơn 75% chiều cao (mặt đường CARLA phẳng cũng "tĩnh"). Video xe máy: y=810; CARLA: 697 / 540 / 561. Ảnh kiểm tra: `*/hood_check.jpg`.
- **Đồ trang trí trên kính:** hỏi Qwen một lần mỗi video trên 3 ảnh, lấy hợp các box + lề 30 px. Video xe máy: tìm thấy ở 1/3 ảnh ("A yellow and red plush toy…"), box [1312, 642, 1542, 834] — trùng vùng chọn tay trước đây. CARLA: không có, Qwen không khoanh nhầm gì.
- Thử độ lệch chuẩn pixel để tìm vùng tĩnh: che được táp-lô, không che được đồ trang trí (vật đung đưa, cảnh sau nó thay đổi) và che nhầm mặt đường — bỏ.

## Vòng 6 — bộ nhớ sự kiện (Qwen2.5-VL 7B)

[pipeline.py](pipeline.py), 21 frame toàn cảnh 9.0–11.0s @10 fps. M0 không bộ nhớ, M1 bộ nhớ JSON trong prompt, M2 lịch sử hội thoại (2 frame trước kèm ảnh và câu trả lời).

| Biến thể | Kết quả 9.0–11.0s |
|---|---|
| M0 | `NORMAL` cả 21 frame |
| M1 | `NORMAL` cả 21 frame; lặp nguyên văn "A person on a motorcycle is riding on the road, moving forward" 9.9–10.5s |
| M2 | `NORMAL` cả 21 frame; lặp "The motorcycle is now closer to the camera car" 15 frame |

Đưa câu trả lời cũ vào prompt làm model bám theo nó thay vì nhìn frame mới. Bộ nhớ vẫn nằm ở backend, nhưng chỉ dùng cho rule engine và bước đánh giá lại, không đưa mô tả cũ vào prompt.

Cũng ở vòng này: bỏ phiếu 6 mẫu + LLM chấm mô tả ([run_vote6.py](../local-q8-state/run_vote6.py)) — đối chứng 1/6, 1/6, 2/6 "ngã", frame đã ngã 2/6 → không tách được. Hỏi bằng tiếng Trung ([run_chinese.py](../local-q8-state/run_chinese.py)) — mọi frame "正常直立行驶", mọi cặp "倾斜或转弯" → không tách được.

## Vòng 7–8 — trắc nghiệm chung cho mọi đối tượng, có đối chứng

[windows.py](windows.py). 15 cửa sổ 4 frame: 4 sự kiện (xe máy 9.5–10.3s; CARLA quanh mốc `actor_enters_road_s`), 10 lái bình thường (gồm pha đổi làn bình thường ở 29s của v16). Đáp án đúng: sự kiện → B (CARLA, **không được C**) hoặc C (xe máy); bình thường → A hoặc D.

A) bình thường · B) đối tượng bất ngờ đi vào đường xe camera / đánh lái gấp · C) ngã, lật hoặc va chạm · D) không có đối tượng gần.

| | 7B toàn cảnh | 7B crop theo đối tượng | **3.5-9B toàn cảnh** | **3.5-9B crop theo đối tượng** |
|---|---|---|---|---|
| Xe máy (ngã) | D | A | B | **C** — "loses control and swerves sharply into vegetation, causing the motorcycle to tip over" |
| CARLA v16 / v17 / v18 | B / B / D | A / ? / ? | **B / B / B** | A / A / B |
| 10 cửa sổ bình thường | 9 đúng, 1 B (v18 42s, người trên vỉa hè) | 8/15 output vòng lặp lặp chữ | 9 đúng, 1 B (v17 28s, xe làn đối diện) | **10/10 A** |

Qwen3.5 9B 3 mẫu temperature 0.7 ([windows_results_s3_qwen35-9b.json](windows_results_s3_qwen35-9b.json)): sự kiện xe máy B,B,B; CARLA v16 B,B,B; v17 B,B,B; v18 C,B,B; bình thường 8/10 cửa sổ A,A,A, v17 28s C,B,A, v18 12s/28s một mẫu B.

Crop theo đối tượng: Qwen khoanh đối tượng gần đường đi nhất ở từng frame, code lấy hợp các box của loại đối tượng xuất hiện nhiều nhất thành một khung cố định, crop mọi frame theo khung đó. Tọa độ: Qwen2.5-VL trả pixel trên ảnh đã smart_resize; Qwen3.5 trả thang 0–1000 (đã kiểm bằng vẽ box: [check_qwen35_box.jpg](../local-q8-state/images/check_qwen35_box.jpg)).

## Đổi model: Qwen3.5 9B ([battery.py](battery.py), [battery_qwen35-9b.json](battery_qwen35-9b.json))

Cùng ảnh crop và đối chứng như các vòng với 7B:

| Bài | Đối chứng 9.3–9.7 | Sự kiện | 7B cùng bài |
|---|---|---|---|
| Trắc nghiệm nhiều frame (khung C) | **A** | **C** — "the bike tilts significantly and begins to fall sideways" | A / B |
| Trạng thái từng frame | upright, leaning, leaning (0/3 "ngã") | 9.9 ngã, 10.0 leaning, 10.1 / 10.2 / 10.5 **falling_or_fallen** | upright mọi frame |
| Cặp tham chiếu có nhãn | `falling_or_fallen` | lẫn lộn | text đúng, nhãn sai |

Thời gian: 7–15 s/request (7B Q8: 20–60 s) vì Q4_K_M vừa VRAM hơn.

## Quét cả video 60 s (Qwen3.5 9B)

[scan.py](scan.py) · [rules.py](rules.py) · bộ nhớ từng video: `*/memory_scan_qwen35-9b.json` · điểm: [rules_qwen35-9b.json](rules_qwen35-9b.json)

1. Frame mỗi 0,6 s trên dải đường (cắt capo, che đồ trang trí tự động).
2. **Tầng 1:** cửa sổ 4 frame (1,8 s, bước 1,2 s, ~49 cửa sổ/video), trắc nghiệm A/B/C/D trên ảnh toàn cảnh.
3. **Bộ nhớ backend:** lưu kết quả mọi cửa sổ; rule engine chạy trên bộ nhớ, không đưa mô tả cũ vào prompt.
4. **B (suýt va chạm):** ≥ 2 cửa sổ liên tiếp. Tùy chọn: hỏi lại chặt theo khoảng cách ("trong ~2 thân xe, buộc phanh/né").
5. **C (ngã/va chạm):** thường chỉ 1 cửa sổ → **tầng 2** phải độc lập trả C: Qwen khoanh đối tượng chính ở frame 4 fps, ưu tiên loại đối tượng tầng 1 đã nêu, crop khung cố định, hỏi lại.

Đáp án: xe máy ngã ~10.0–10.5 s; CARLA người đi bộ vào đường ở 56.04 / 56.13 / 57.29 s (video), near miss, không va chạm.

| Quy tắc | Phát hiện | Đúng loại | Sự kiện giả |
|---|---|---|---|
| R1 quét thô | 4/4 | 4/4 | 4 |
| R2 + hỏi lại chặt cửa sổ B | 3/4 (mất v18) | 3/4 | 1 |
| **R3** R2 + bỏ B khi tầng 2 trả A | 3/4 (mất v18) | 3/4 | **0** |
| **R4** R1 + bỏ B khi tầng 2 trả A | **4/4** | **4/4** | 3 |

Kết quả từng video (R3 / R4):

- **Xe máy:** cả hai: **FALL_OR_COLLISION 9.9–11.7 s** — tầng 1 "the motorcyclist loses balance and falls off their bike onto the side of the road", tầng 2 "swerves sharply into a large plant, causing the bike to tip over". C nhầm ở 36.3 s (nhóm người đứng) bị tầng 2 bác (A).
- **v16:** cả hai bắt NEAR_MISS 54.3–59.7 s. R4 còn 0.3–3.3 s (xe nhập làn) và 44.7–48.9 s (xe làn đối diện; Qwen tưởng lấn vạch — kiểm ảnh: không lấn).
- **v17:** cả hai bắt NEAR_MISS 55.5–59.7 s; sự kiện giả 23–26 s (SUV làn đối diện) bị loại.
- **v18:** R3 mất sự cố (hỏi lại chặt: "staying well clear"); R4 bắt 55.5–58.5 s và thêm 36.3–39.3 s — người thật đi trên vạch qua đường ở xa bên trái ([ảnh](../local-q8-state/images/check_v18_36s.jpg)), không nguy hiểm.

Đề xuất xuất kết quả theo hai mức: **tin cậy cao** = R3 (3/4, 0 giả); **cần xem lại** = chỉ R4 có (sự cố v18 + 3 trường hợp nhập làn / qua đường ở xa). Không bỏ sót sự cố, kỹ sư biết nên xem gì trước.

Thời gian: tầng 1 ~20–27 s/cửa sổ trên RTX 4050 → ~17–20 phút/video 60 s; hỏi lại + tầng 2 thêm vài phút. Có một request treo ~4 giờ (máy ngủ hoặc Ollama kẹt) rồi tự chạy tiếp.

## Backend thật với Qwen3.5 9B

Thay đổi để backend chạy được (441 test pass):

- `QWEN_OLLAMA_MODEL` chấp nhận `qwen2.5vl:7b` hoặc `qwen3.5:9b`; bỏ ép tên trong `ensure_ollama_runtime`, vẫn kiểm `vision`.
- `QWEN_REASONING_EFFORT` (gửi `reasoning_effort` trong 4 payload). Đo trên Ollama `/v1`: mặc định qwen3.5 suy nghĩ (130 token cho câu "OK"); `reasoning_effort: "none"` → 2 token; `think: false` bị bỏ qua ở `/v1`.
- `pin_evidence_ids`: JSON schema Stage A/B chỉ cho phép đúng evidence ID của request (như `video_summary.py` đã làm). Lần chạy đầu thất bại "unknown evidence ID" (Qwen chép sai ID dạng `FRAME-<hash>-<t>` hai lần liên tiếp); sau sửa chạy thành công.

`python -m backend.analyze_local_dataset` trên video xe máy (incident `INC-6402A69006F6`, job `JOB-CC2373C11336`):

| Stage A lô 8 s (33 frame 640 px/request) | Kết quả |
|---|---|
| 0–8 s | NO_INCIDENT |
| **6–14 s (có cú ngã)** | **NO_INCIDENT** |
| 12–20 s | INCONCLUSIVE, PEDESTRIAN_CONFLICT |
| 18–60 s (7 lô) | NO_INCIDENT |

Draft cuối: `incident_detected: true`, **PEDESTRIAN_CONFLICT 12.0–23.0 s, critical 19.25 s** — "Một người đàn ông xuất hiện từ bên phải đường và bước vào làn xe của camera car…". Đó là người dân chạy ra sau vụ ngã; **cú ngã bị bỏ sót** vì luồng hiện tại gửi 33 ảnh toàn cảnh 640 px mỗi request. Cùng model, pipeline hai tầng ở trên bắt đúng cú ngã.
