# Kế hoạch phân tích incident bằng log và Qwen local

Ngày: 2026-10-09. Trạng thái: đã triển khai backend và kiểm thử; kiểm chứng CARLA/local CPU đang được ghi ở mục 7.

## 1. Mục tiêu và phạm vi đã chốt

- Giữ nguyên cách triển khai FE, BE, API, giao diện, endpoint và luồng sử dụng hiện tại.
- Chỉ thay đổi xử lý video/log và suy luận VLM trong backend; tận dụng service, worker và adapter hiện có.
- Dùng log để đề cử thời điểm nghi ngờ; Qwen kiểm tra bằng hình ảnh và log. Flag không phải kết luận incident.
- Với flag tại `t` giây trên video, lấy đoạn `[max(0, t - 5), min(duration, t + 3)]`.
- Lấy **4 frame/giây**, khoảng **32 frame cho đoạn đủ 8 giây**, theo thứ tự thời gian. Cho phép cấu hình tốc độ lấy mẫu theo tài nguyên và kết quả thực tế.
- Không gọi dịch vụ VLM bên ngoài trong luồng phân tích này, kể cả khi local lỗi.
- Người dùng cung cấp Qwen có khả năng xử lý ảnh/video, khoảng 3B tham số, tại `backend/data/model/`.
- Đọc hướng dẫn phân tích từ `backend/data/promt.txt`, giữ đúng tên `promt.txt`.
- Append phản hồi vào `backend/data/outputs.txt`; không xoá, truncate hay ghi đè output cũ.

Tài liệu này nằm tại `docs/qwen_local.md` theo yêu cầu trực tiếp của người dùng. Các SPEC/ADR/task hiện có vẫn là nguồn tham chiếu; không tạo bản sao của chúng.

## 2. Luồng xử lý dự kiến

Upload qua luồng hiện có → chuẩn hoá log → đồng bộ log/video → phát hiện bất thường → flag → đoạn trước 5 giây/sau 3 giây → frame ở 4 FPS → đọc promt.txt → Qwen local → append outputs.txt → kiểm tra output → trả kết quả qua contract hiện có.

Mỗi flag cần lưu thời điểm trên video, tín hiệu gây flag, giá trị/biến động và lý do. Kết quả phải phân biệt quan sát, suy luận có bằng chứng và phần chưa xác định. Không suy nguyên nhân nội tại của xe chỉ từ hình ảnh ngoài xe.

### Quy tắc lấy mẫu và tránh trùng

- Lấy mẫu từ đầu đoạn, mỗi 0,25 giây, không lấy mốc kết thúc: `start + k / 4 < end`. Đoạn đủ 8 giây có 32 mốc; đoạn bị cắt ở đầu/cuối có ít mốc hơn.
- Giới hạn mốc theo frame thực tế giải mã được; không yêu cầu frame nằm ngoài video.
- Khử flag lặp do cùng một đợt bất thường và tái sử dụng frame trùng. Giữ thông tin tất cả flag gốc và lý do khi nhóm các sự kiện.
- Nếu nhóm nhiều cửa sổ thành đoạn dài hơn 8 giây, số frame phải theo chiều dài đoạn ở 4 FPS; chia thành batch theo giới hạn model, không âm thầm ép cả đoạn xuống 32 frame.
- Đặt giới hạn số candidate/frame/lần gọi và timeout; phần vượt ngân sách phải ghi rõ chưa phân tích.

## 3. Hiện trạng đã đọc và điểm cần xác minh

- `backend/services/candidate_detection.py` đã có candidate, reasons, gộp cửa sổ, giới hạn candidate và kiểm tra alignment. Mặc định đọc được hiện tại là trước 5 giây/sau 5 giây; yêu cầu mới là trước 5 giây/sau 3 giây.
- `backend/services/evidence_extraction.py` đã có trích clip/frame và manifest bằng chứng.
- `backend/services/vlm_provider.py` đã có adapter HTTP, cấu hình self_hosted, giới hạn frame và prompt trong code.
- `backend/services/processing.py` và `backend/services/vlm.py` có đường phân tích hai bước; hàm lấy mẫu pass 1 hiện đọc được trả 5 mốc.
- Chưa xác minh đường web đang chạy dùng V1/V2, lấy 3 frame hay dùng Gemini. Không sửa đường legacy trước khi truy ra caller thực tế.
- `docker-compose.yml` hiện đọc được có postgres/backend/worker và cấu hình OpenAI. Cần xác minh cách khởi chạy mà người dùng thực sự đang dùng; không thay kiến trúc triển khai dựa trên ghi chú cũ.

### Thông tin cần chốt trước task phụ thuộc

1. Tên/checkpoint, định dạng trọng số và runtime tương thích của Qwen; model phải hỗ trợ hình ảnh/video.
2. CPU/GPU, RAM/VRAM khả dụng để chọn batch và giới hạn suy luận thực tế.
3. Log mẫu, tên cột, đơn vị, timestamp và mốc đồng bộ với video; ngưỡng bất thường phải dựa vào dữ liệu này.
4. Cách chạy FE/BE/API hiện tại và đường dẫn được mount vào môi trường backend.

Không tải hoặc tự chọn model thay người dùng. Có thể làm các task độc lập trước; chưa có model thì chỉ xác minh wiring bằng test, chưa khẳng định chạy Qwen thật.

## 4. Các task thực hiện theo thứ tự

### QL-01 — Xác minh luồng đang chạy

- [ ] Đọc SPEC/ADR/task được liên kết bên dưới và truy endpoint → worker → xử lý log/video → provider.
- [ ] Xác minh cách triển khai thực tế, contract, config và nơi lưu dữ liệu; ghi file/caller cần sửa vào tài liệu này.
- [ ] Ghi nhận các thay đổi Git ngoài phạm vi để bảo toàn; không commit/push nếu chưa được yêu cầu.
- **Nghiệm thu:** xác định được đường active và số frame/call thực tế; danh sách thay đổi không đụng FE hoặc public API.

### QL-02 — Flag từ bất thường trong log

- [ ] Tận dụng `log_normalization.py`, `synchronization.py`, `candidate_detection.py`; xác minh mapping tín hiệu và đơn vị từ log mẫu.
- [ ] Cấu hình rule theo tín hiệu thực có: ngưỡng và/hoặc biến động so với lân cận; không coi mọi giá trị tăng là incident.
- [ ] Lưu flag cùng thời gian, tín hiệu, giá trị và lý do; khử flag lặp cùng đợt bất thường.
- [ ] Kiểm tra spike, log ổn định, NaN/thiếu cột, timestamp không hợp lệ và alignment chưa xác minh.
- **Nghiệm thu:** log fixture bất thường tạo đúng flag; log ổn định không tạo flag sai; không tự coi timestamp log là giây video khi chưa đủ thông tin đồng bộ.

### QL-03 — Cửa sổ 8 giây và frame 4 FPS

- [ ] Đổi cấu hình cửa sổ của đường active sang trước 5 giây/sau 3 giây.
- [ ] Tích hợp mốc lấy mẫu mỗi 0,25 giây với trích xuất/manifest hiện có; ghi timestamp và thứ tự của từng frame.
- [ ] Tránh trích/call lặp; giữ coverage khi nhóm cửa sổ, chia batch nếu đoạn dài vượt giới hạn model.
- [ ] Kiểm tra flag giữa video, gần đầu/cuối, flag trùng/gần nhau và video không giải mã được.
- **Nghiệm thu:** flag `t=10` trong video đủ dài tạo đoạn `[5,13]`, 32 mốc từ `5` đến `12,75`; flag gần biên có đoạn hợp lệ, không vượt duration.

### QL-04 — Prompt ngoài script

- [ ] Tạo `backend/data/promt.txt` với hướng dẫn ban đầu, giữ yêu cầu evidence/unknowns và schema hiện có.
- [ ] Đọc UTF-8 mỗi lần suy luận để thay prompt không cần sửa code hoặc khởi động lại backend.
- [ ] Ghép dữ liệu động gồm log, flag, timestamp/frame và schema; không giữ một prompt phân tích khác hardcode trong script.
- [ ] Báo lỗi rõ nếu file thiếu/rỗng/không đọc được; không âm thầm dùng prompt cũ.
- **Nghiệm thu:** sửa promt.txt làm thay đổi prompt của lần gọi kế tiếp; test xác minh thiếu file/rỗng và ký tự tiếng Việt.

### QL-05 — Qwen local trên luồng hiện có

- [ ] Sau khi có checkpoint, xác minh runtime hỗ trợ model và ảnh; ưu tiên adapter/runtime sẵn có, không thêm server hoặc dependency nếu chưa cần.
- [ ] Đọc model từ `backend/data/model/`, cấu hình backend chỉ dùng local; không fallback VLM external.
- [ ] Tái sử dụng model/runtime giữa các lần gọi; xử lý batch, timeout, model thiếu và hết bộ nhớ với lỗi rõ ràng.
- [ ] Giữ schema kết quả, evidence validation và phản hồi API hiện tại.
- **Nghiệm thu:** test chứng minh không gọi external trong cả đường thành công/lỗi; smoke thực với model người dùng nếu đã có. Không có model thì ghi rõ chưa kiểm chứng suy luận thật.

### QL-06 — Nhật ký outputs.txt chỉ append

- [ ] Append UTF-8 mỗi phản hồi nhận được trước khi parse/validate, kể cả phản hồi không đúng schema.
- [ ] Mỗi entry ghi timestamp, run/candidate ID, flag và cửa sổ, timestamp frame, model/revision, prompt thực gửi và raw output; không nhúng dữ liệu ảnh base64 hoặc secret.
- [ ] Dùng cơ chế đồng bộ ghi phù hợp worker hiện có để entry không xen nhau; không mở file bằng chế độ ghi đè và không tự xoay/xoá lịch sử.
- [ ] Ghi lỗi rõ khi không nhận được phản hồi hoặc append thất bại; không giả lập output hay báo lưu thành công khi chưa ghi được.
- **Nghiệm thu:** hai lần chạy giữ nguyên nội dung cũ, thêm hai entry; test Unicode, output không hợp lệ, concurrent writes và lỗi quyền ghi. File runtime không đưa vào Git.

### QL-07 — Tích hợp, regression và xác minh thực tế

- [ ] Tích hợp các task trên vào worker active; giữ nguyên upload, trạng thái job và contract FE/API.
- [ ] Giữ hành vi upload video không log hiện có; thiếu log/không có flag không được tự kết luận video không incident. Ghi coverage/unknowns theo contract hiện có.
- [ ] Chạy test backend/API liên quan rồi kiểm tra regression theo quy định repo:
  - `python -m ruff check backend/ api/`
  - `python -m pytest tests/ -q`
- [ ] Khi có model và cặp video/log: chạy end-to-end bằng cách triển khai hiện tại, kiểm tra flag → clip → frame → prompt → Qwen → outputs.txt → kết quả API.
- [ ] Ghi thời gian, tài nguyên và số lần gọi đo được; phân biệt test mock, smoke local và chất lượng phân tích incident.
- **Nghiệm thu:** FE/API hoạt động theo contract cũ; log lịch sử không bị mất; không external VLM; có bằng chứng kết quả từng task. Không đánh dấu kiểm thử live hoàn thành nếu chưa chạy.

## 5. Tham chiếu và điểm review

- [Candidate detection](../tools/tasks/RAV-003-candidate-detection.md)
- [Self-hosted VLM](../tools/tasks/RAV-008-self-hosted-vlm.md)
- [Incident workflow](../tools/specs/incident-workflow.md)
- [Analysis V2](../tools/specs/incident-analysis-v2.md)
- [Provider abstraction](../tools/adrs/ADR-004-vlm-provider-abstraction.md)
- [Backend instructions](../backend/AGENTS.md)
- [Governance](../tools/AGENTS.md)

Review tập trung: alignment sai; gộp cửa sổ làm mất coverage 4 FPS; local lỗi dẫn tới fallback external; prompt thay đổi nhưng không được nạp lại; ghi output đồng thời làm mất lịch sử. Các trường hợp này thuộc kiểm thử QL-02, QL-03, QL-04, QL-05 và QL-06.

## 6. Đối chiếu phạm vi và tiến độ — 2026-10-10

Nguồn UI/API được giữ là checkout `develop`, baseline commit `f8eff41`, không phải giao diện đóng sẵn trong image cũ. Không sửa source FE/API hay thêm endpoint.

| Task | Thay đổi thuộc phạm vi | Kiểm chứng / giới hạn |
| --- | --- | --- |
| QL-01 | Truy frontend upload → API V1 → worker V1; giữ worker V2 cho API V2 có sẵn. | FE/API build từ source checkout. Image cũ chỉ cung cấp runtime đã cài, không cung cấp source ứng dụng. |
| QL-02 | Log normalization, alignment, flag ngưỡng/delta/median-MAD; giữ tín hiệu, giá trị và lý do. | Có unit test; chưa hiệu chỉnh ngưỡng trên video thật. CARLA speed_kmh được đổi sang m/s; accel_x chỉ là thành phần trục X. |
| QL-03 | Cửa sổ -5/+3 giây, clamp video, 4 FPS, 32 mốc/8 giây; gộp flag giữ mật độ. | Batch không giảm density; cap extraction 256 frame, vượt cap ghi UNANALYZED. |
| QL-04 | Đọc UTF-8 promt.txt mỗi request, prompt hash và báo lỗi thiếu/rỗng. | Có test thay prompt và Unicode; không fallback prompt hardcode trong luồng local. |
| QL-05 | Qwen2.5-VL-3B GGUF + projector do người dùng cung cấp, llama.cpp loopback local. | Cả worker V1/V2 mặc định local; không fallback external. Đã có bounded native smoke; chưa full-window inference. |
| QL-06 | outputs.txt append trước validation; ghi raw output, prompt và metadata; khóa ghi đa process. | Test concurrent writes/invalid output/write failure; lịch sử hai raw response thật được giữ. |
| QL-07 | Tích hợp vào upload/job hiện có; test backend/API; smoke hai mẫu CARLA. | Phân biệt integration test với chất lượng model. Không có log ở V1 vẫn dùng visual localization có giới hạn theo luồng cũ; V2 giữ yêu cầu scanner/alignment của baseline. |

### Những phần phát sinh đã loại bỏ

- Route login, login redirect và giao diện dashboard của snapshot image cũ: thay bằng **frontend checkout nguyên trạng**, root chuyển tới `/incidents` như trước task.
- API local-session, Cloudflare Access và các module/cấu hình auth được mang sang từ image cũ: thay bằng **API/backend checkout nguyên trạng ngoài các file Qwen**. Cơ chế signed identity V2 có sẵn trước task vẫn giữ; không thêm cơ chế đăng nhập mới.
- Cấu hình text-API discovery, vision-stage riêng, các option lấy 3 frame và pricing từ image cũ: đã gỡ block settings bổ sung chỉ để tương thích image đó.
- Nhánh tự thêm manual/automatic sampled windows trong worker V2 và test cho nhánh đó: đã gỡ. Đây không phải baseline của checkout. Xử lý video-only V1 theo QL-07 vẫn được giữ.
- Các ghi chú khẳng định giữ frontend của image cũ hoặc dùng `/login` làm health check: đã thay bằng cấu hình kiểm tra `/incidents`.

Không xóa dữ liệu, model, outputs.txt hoặc các thay đổi có trước task (bao gồm `.github/workflows/ci.yml`). Không commit/push. Không xóa hoặc thay cơ chế evidence validation, privacy, quyền V2 đã tồn tại trong checkout.

## 7. Cấu hình và kiểm chứng

### File thực hiện task

- `backend/services/candidate_detection.py`, `log_normalization.py`: chuẩn hóa log và tạo flag.
- `backend/services/evidence_extraction.py`: trích clip/frame 4 FPS.
- `backend/services/vlm_provider.py`, `qwen_local.py`, `qwen_processing.py`, `prompt_io.py`: local inference, scope bằng chứng, prompt reload và output append.
- `backend/worker.py`, `backend/worker_v2.py`: tích hợp vào worker có sẵn.
- `backend/qwen_smoke.py`, tests backend/API: kiểm chứng QL-07.

### Cấu hình backend

| Biến | Mặc định / ý nghĩa |
| --- | --- |
| QWEN_MODEL_DIR | `./backend/data/model` |
| QWEN_MODEL_FILE | `Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` |
| QWEN_PROJECTOR_FILE | `mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf` |
| QWEN_SERVER_BIN | `llama-server`, fallback native `backend/data/runtime/llama-server.exe` trên Windows |
| QWEN_ENDPOINT | `http://127.0.0.1:8091/v1/chat/completions`, chỉ loopback |
| QWEN_PROMPT_PATH | `./backend/data/promt.txt` |
| QWEN_OUTPUTS_PATH | `./backend/data/outputs.txt` |
| QWEN_SAMPLING_FPS | 4 |
| QWEN_BATCH_FRAMES | 1, cấu hình 1–32 |
| QWEN_CONTEXT_SIZE | 32768, deployment CPU đặt 16384 để giảm RAM |
| QWEN_TIMEOUT_S | 600 giây, tối đa 3600 |
| QWEN_STARTUP_TIMEOUT_S | 120 giây |
| QWEN_SIGNAL_THRESHOLDS / QWEN_DELTA_THRESHOLDS | JSON mapping tín hiệu và ngưỡng đã chọn theo đơn vị nguồn/canonical |
| QWEN_V1_LOG_OFFSET_S | Trống mặc định; chỉ đặt khi biết đồng bộ log → video, không tự suy từ tên CSV |

### Khởi chạy tại cổng 8089

Việc đổi cổng/cache được người dùng yêu cầu sau kế hoạch Qwen; không mở rộng tính năng sản phẩm:

- `docker-compose.qwen-local.yml` giữ stack một container, cổng host `127.0.0.1:8089`; volume dữ liệu `incidentlens-unified_data` được giữ.
- `deploy/qwen-local/Dockerfile` dùng image `incidentlens:unified-baseline` **chỉ để tái sử dụng binary/runtime**. Source cũ ở backend/API/frontend/deploy bị loại khỏi image mới. FE/API/backend được đóng gói từ checkout; không tái sử dụng route login hoặc bundle FE cũ.
- Build frontend đặt `NEXT_PUBLIC_USE_MOCK_API=false`, API cùng origin `/api/v1` và `/api/v2`; không sửa code giao diện. Gateway phục vụ cả API V1/V2 theo contract có sẵn.
- Model được mount read-only vào `/models`; backend/data mount writable để prompt và outputs giữ trên host. Lock và log runtime nằm cạnh outputs.txt, không ghi vào mount model.
- Database hiện có không downgrade/drop bảng hoặc đổi migration marker vì QL tasks không thay schema. Chỉ database tạo mới mới chạy migrations của checkout. Bảng/lịch sử cũ trong volume được giữ, không đồng nghĩa xuất bản các tính năng ngoài task.
- Qwen chỉ nghe nội bộ `127.0.0.1:8081`, context 16384, CPU 6 thread, runtime batch 512/microbatch 128, image token 1024. Worker trích 4 FPS và chia request 1 frame theo yêu cầu ngày 2026-10-10; ghi chú cải tiến riêng tại `../notes.txt`.
- Backup trước cutover: `backend/data/deployment-backups/before-qwen-8089-20261009-235332.tar.gz`, 270345067 bytes.

```powershell
docker compose -f docker-compose.qwen-local.yml build --no-cache
docker compose -f docker-compose.qwen-local.yml up -d
```

### Bằng chứng và phần chưa kiểm chứng

- Kiểm thử trước bước gỡ phát sinh: 231 test backend/API gốc đã pass; sau bước ghép nhánh video-only không thuộc baseline có 233 pass. Hai case thuộc nhánh phát sinh đã được gỡ cùng feature. Kiểm thử runtime/prompt/journal riêng: 10 passed.
- Hai MP4/CSV CARLA ở `backend/data/vlm` có nhãn auto-generated normal_driving, chưa xác minh bởi người. Log có spike accel lớn ban đầu; MAD warmup 30 dòng chưa bao phủ startup spike.
- Smoke native với offset 0 là **giả định được ghi rõ**, không phải anchor đo từ video. Log tạo merged windows 38 và 37 mốc ở 4 FPS.
- Batch 8 với timeout 120 giây từng chạm timeout trên CPU. Lượt bounded batch 1/timeout 600: một raw response sau khoảng 373,76 giây bị chặn vì window có độ dài 0; một response khác incident_detected=false qua validation sau khoảng 278,62 giây/request. Chỉ một frame được xác nhận qua analysis hợp lệ, không phải full-window hoặc bằng chứng video không incident.
- Hai raw response được giữ trong outputs.txt. SHA256 trước bước gỡ phát sinh: `72082f827556bf93fa80790b1b0460401fee289c562e3918e7920c7b9898f985`.
- Chưa benchmark incident quality/video thật/GPU hoặc hoàn tất 32-frame window qua model thật. Không sửa/coerce output sai thành report hợp lệ.

Trạng thái live/regression sau bước gỡ phát sinh được cập nhật bên dưới khi có kết quả thực tế.

- Regression sau đối chiếu/gỡ phát sinh: **232 passed**, 1 cảnh báo LangGraph, 66,27 giây; Ruff pass. Frontend checkout: typecheck/lint/build pass, route manifest không có login. OpenAPI paths trong image khớp toàn bộ paths của checkout; worker V1/V2 import pass.

- Bản đối chiếu đã triển khai tại `http://localhost:8089`, container **healthy**. `/incidents`, `/incidents/new`, API V1 health/list trả 200; `/login` và endpoint local-session phát sinh trả 404. Browser đã mở root và chuyển đúng tới `/incidents`, sau đó kiểm tra form upload: video bắt buộc, CSV tùy chọn, không có bước đăng nhập.
- Snapshot mới build từ checkout, image `sha256:dedceab5018b562d0da462b838891273f1da09ff0f906dc9ced4f21074b35267`. Source FE/API không có Git diff. DB vẫn giữ marker/lịch sử hiện có, không xóa bảng. outputs.txt giữ nguyên SHA256 đã ghi bên trên.
- Các worker V1/V2 đang chạy với provider Qwen local, 4 FPS, prompt/output trên host. Chỉ kiểm tra readiness/wiring trong lần sửa phạm vi này; không phát sinh generation mới hoặc tuyên bố chất lượng incident đã đạt.
