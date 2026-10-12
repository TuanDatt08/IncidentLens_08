# Chạy P-076 bằng Docker và Qwen 7B local

## Kiến trúc

Profile `docker-compose.qwen-local.yml` đóng gói frontend, API, một worker phục vụ tuần tự cả V1/V2, Ollama và nginx trong một container. Ollama chỉ nghe tại `127.0.0.1:11434` bên trong container. Model là **qwen2.5vl:7b**, có vision. Backend giữ nguyên hai nhánh: MP4 + log tìm trigger rồi trích clip/frame; MP4 đơn chạy Stage A/B. Kết quả hợp lệ được lưu DRAFT để kỹ sư review.

SQLite, input, evidence, output và log nằm trong volume `incidentlens-qwen-local_data`. Model Ollama nằm trong volume `incidentlens-qwen-local_models`. Không dùng GGUF trong `backend/data/model`, không cần image nền riêng và không chép database/log/secret của máy phát triển vào image. Frontend giữ nguyên giao diện.

## Máy nhận cần gì?

Cài Docker Engine hoặc Docker Desktop chạy Linux containers. Cần mạng ở lần build và tải model đầu tiên. Dành đủ RAM cho Qwen 7B, context và ảnh; RAM 16 GB trở lên là điểm khởi đầu thực tế, nhưng tốc độ còn phụ thuộc CPU/GPU, ảnh và context. Dành khoảng 25 GB dung lượng trống cho image, cache build, model và dữ liệu, nhiều hơn nếu lưu nhiều video. Không cần Python, Node hoặc Ollama trên host.

CPU chạy được nhưng suy luận có thể chậm. GPU NVIDIA cần driver và runtime phù hợp; Docker Desktop Windows cần WSL2. Xem [Docker GPU](https://docs.docker.com/desktop/features/gpu/) và [Ollama Docker](https://docs.ollama.com/docker).

## Build và chạy

Tại thư mục chứa compose, `docker compose up -d --build` dùng profile Ollama mặc định. Lệnh tường minh tương đương:

```powershell
docker compose -f docker-compose.qwen-local.yml up -d --build
docker compose -f docker-compose.qwen-local.yml logs -f --tail 50
docker compose -f docker-compose.qwen-local.yml ps
```

Mở http://127.0.0.1:8089/incidents. Lần đầu startup tự tải model nếu chưa có; chưa nhận job cho đến khi model và database sẵn sàng. Dòng `IncidentLens ready` và trạng thái `healthy` xác nhận các dịch vụ sẵn sàng, không phải đánh giá chất lượng phân tích.

GPU NVIDIA:

```powershell
docker compose -f docker-compose.qwen-local.yml -f docker-compose.qwen-gpu.yml up -d --build
```

Kiểm tra khả năng vision:

```powershell
docker compose -f docker-compose.qwen-local.yml exec app ollama show qwen2.5vl:7b
docker compose -f docker-compose.qwen-local.yml exec app ollama ps
```

## Cấu hình máy mạnh hơn

Tạo `.env` cạnh compose hoặc đặt biến môi trường PowerShell. Ví dụ:

```dotenv
P076_PORT=8089
QWEN_BATCH_FRAMES=1
QWEN_SAMPLING_FPS=4
QWEN_TIMEOUT_S=600
OLLAMA_CONTEXT_LENGTH=32768
OLLAMA_NUM_PARALLEL=1
OLLAMA_KEEP_ALIVE=5m
OLLAMA_AUTO_PULL=true
```

Tăng `QWEN_BATCH_FRAMES` lên 2 hoặc 4 sau khi đo RAM/VRAM và kiểm tra chất lượng. Tăng số ảnh làm tăng chi phí xử lý. `OLLAMA_NUM_PARALLEL` cho phép Ollama xử lý nhiều request độc lập đồng thời, cần thêm bộ nhớ; worker hiện tại vẫn chạy tuần tự các job nhằm tránh hai hàng đợi cùng tranh model. Thay biến này không biến worker thành nhiều consumer. `QWEN_SAMPLING_FPS` tác động lấy frame ở luồng log, không thay toàn bộ chiến lược Stage A/B. Context lớn hơn cũng cần thêm bộ nhớ. Chạy lại `up -d` để áp dụng biến, không cần rebuild khi chỉ đổi env.

Không truyền `.env` cá nhân vào image. Compose chỉ truyền các biến được liệt kê. Không tự đặt offset CSV chung cho mọi video: CSV phải có căn cứ đồng bộ với MP4.

## Input, output, database, log

Trong container:

- `/data/incidentlens.db`: database riêng của bản Docker.
- `/data/incidents/<incident_id>/`: MP4, CSV và artifact của pipeline.
- `/data/incidents/<incident_id>/output/`: các request, phản hồi, tiến độ và draft của luồng V1 Ollama.
- `/data/logs/runtime/`: stdout/stderr của Ollama, API, frontend, worker, nginx, migration và tải model.
- `/data/logs/qwen/outputs.txt`: journal provider dùng đường dẫn mặc định.
- `/models`: cache model Ollama.

Prompt video Stage A/B: `/app/backend/data/promt.txt`. Prompt luồng log: `/app/backend/prompts/ollama_incident.txt`. Sửa source rồi build lại để đóng gói prompt mới. Backend gọi `http://127.0.0.1:11434/v1/chat/completions`; API/model không mở port host riêng. Browser gọi `/api/v1` hoặc `/api/v2` qua nginx cùng origin.

Xem log và lấy dữ liệu ra host:

```powershell
docker compose -f docker-compose.qwen-local.yml exec app tail -n 80 /data/logs/runtime/worker.stderr.log
docker compose -f docker-compose.qwen-local.yml cp app:/data/logs ./logs/docker-export
```

Sao lưu nhất quán SQLite bằng cách dừng app trước khi copy database và incident artifacts. `docker compose down` giữ volume; **không thêm `-v` nếu cần giữ dữ liệu/model**. Runtime Docker là database mới; không tự migrate các incident ở database native của host.

## Gửi sang máy khác

Gửi source đã commit cùng Dockerfile, compose, requirements, frontend và prompt, bỏ `.env` cá nhân, `.ai-log`, cache, runtime native, model GGUF và dữ liệu khách hàng. Máy nhận chạy lệnh build trên; model Ollama tải riêng vào volume.

Nếu không muốn build lại, xuất image:

```powershell
docker save -o incidentlens-qwen-ollama-7b.tar incidentlens:qwen-ollama-7b
# Máy nhận:
docker load -i incidentlens-qwen-ollama-7b.tar
docker compose -f docker-compose.qwen-local.yml up -d --no-build
```

Image tar **không chứa model volume**. Máy nhận cần mạng để tải model hoặc chuyển model volume riêng. Không gửi database/log chứa thông tin riêng nếu chỉ bàn giao ứng dụng. Gói offline cần cả model cache và image; chỉ chép folder source không đủ để chạy offline.

## Chẩn đoán lỗi

- Tải model lỗi: xem `model-pull.stderr.log`; kiểm tra mạng và dung lượng.
- Model không hỗ trợ vision: startup dừng trước khi chạy worker.
- Migration lỗi: xem `migration.stderr.log`; không xóa database để che lỗi.
- API/model timeout: xem worker log và các request/output của incident.
- CSV chưa đồng bộ: kiểm tra log offset/anchor, không ép CSV vào MP4 không có căn cứ.
- Thiếu RAM/VRAM: giảm batch/context, giữ parallel=1; kiểm tra Docker Desktop memory và `ollama ps`.

Mỗi máy nhận vẫn cần kiểm tra một request ảnh thật và một video/log hợp lệ. Healthcheck không thay thế kiểm tra đầu ra DRAFT và evidence.

## Kiểm chứng tại máy phát triển (2026-10-12)

- Image `incidentlens:qwen-ollama-7b` build thành công từ image public; frontend typecheck, lint và build đều pass.
- Ruff pass; 263 test repo pass; 5 test triển khai chạy trong image cũng pass.
- Container healthy; form upload và API health HTTP 200.
- Gọi `/v1/chat/completions` trong container với một frame thật tại giây 5 của `nearmiss_20261011_133619_sudden_obstacle.mp4`, response_format JSON schema: HTTP 200, JSON đúng cấu trúc, 283.183 giây trên CPU; 1066 prompt token, 101 output token, tổng 1167. Đây là phép thử một ảnh, không phải phân tích đầy đủ video hay benchmark độ chính xác.
- Context 32768, Ollama qwen2.5vl:7b; Docker Engine có khoảng 7.6 GiB RAM. Model hiển thị 100% CPU. GPU override chưa được chạy trên máy này.
- Restart thành công; database giữ nguyên SHA256, schema `20261003_jobs`, model vẫn có khả năng vision; app trở lại healthy.
- Bằng chứng local: `logs/docker-smoke/verification.json`, `vision-response.json`; các file này được ignore và không đưa vào image.
- Chưa chạy lại toàn bộ video qua Docker, chưa kiểm chứng trên máy nhận hoặc GPU. Lần kiểm chứng này dùng cache model native được chép vào volume; đường tải model lần đầu còn phụ thuộc mạng máy nhận.
