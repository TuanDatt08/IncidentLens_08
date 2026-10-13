# Chạy IncidentLens local và Qwen GPU

Kiểm tra ngày 13/10/2026, tại `C:\Su\T076\P-076`.

## 1. Chọn cách chạy

- Phát triển local: FE Next.js, BE FastAPI và worker chạy trực tiếp; Ollama chạy riêng.
- Di chuyển/deploy: một gói ứng dụng FE + BE + worker; một gói Ollama + model. Hai gói giao tiếp qua HTTP.
- Máy hiện tại chỉ được Windows liệt kê **Intel UHD Graphics**; `nvidia-smi` không có trong PATH. Chưa xác nhận GPU NVIDIA hoặc khả năng tăng tốc Ollama trên Intel này. Lệnh GPU NVIDIA bên dưới dành cho máy có GPU tương thích, hoặc máy GPU thuê từ xa.

## 2. Chuẩn bị local

Cài Python 3.11, Node.js 22, FFmpeg có cả `ffmpeg` và `ffprobe` trong PATH. Cài Ollama nếu muốn phân tích bằng Qwen ngay trên máy. Chạy PowerShell:

```powershell
Set-Location C:\Su\T076\P-076
python --version
node --version
npm --version
ffmpeg -version
ffprobe -version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Dùng trực tiếp Python trong `.venv`, không cần đổi execution policy hay activate.

## 3. Chạy BE — terminal 1

Không ghi đè `.env` hiện có. Những biến sau ghi đè cấu hình cho terminal này:

```powershell
Set-Location C:\Su\T076\P-076
$env:APP_ENV = 'development'
$env:DATABASE_CLOUD = 'false'
$env:DATABASE_URL = 'sqlite:///./backend/data/incidentlens-ollama.db'
$env:INCIDENT_STORAGE_DIR = './backend/data/incidents'
$env:QWEN_RUNTIME = 'ollama'
$env:QWEN_ENDPOINT = 'http://127.0.0.1:11434/v1/chat/completions'
$env:QWEN_OLLAMA_MODEL = 'qwen2.5vl:7b'
$env:QWEN_REMOTE_OLLAMA = 'false'
$env:QWEN_TIMEOUT_S = '1800'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Chỉ chạy Uvicorn nếu migration thành công. Mở `http://localhost:8000/docs`; kiểm tra `http://localhost:8000/health`. Health chỉ chứng minh API hoạt động, chưa chứng minh Qwen sẵn sàng.

## 4. Chạy FE — terminal 2

```powershell
Set-Location C:\Su\T076\P-076\frontend
npm ci
$env:NEXT_PUBLIC_USE_MOCK_API = 'false'
$env:NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000/api/v1'
$env:NEXT_PUBLIC_API_V2_BASE_URL = 'http://localhost:8000/api/v2'
npm run dev
```

Mở `http://localhost:3000`. Nếu Next.js chọn cổng khác vì 3000 đang bận, cần bổ sung origin đó vào `CORS_ORIGINS` của BE rồi khởi động lại BE.

## 5. Chạy worker — terminal 3

API nhận request nhưng không tự chạy worker. Trong terminal mới, đặt lại **toàn bộ biến ở mục 3**, cùng thư mục gốc, rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m backend.worker_v2
```

Worker này xử lý luồng recording V2. Nếu dùng luồng incident V1, chạy thêm `python -m backend.worker` bằng Python trong cùng `.venv`, cùng các biến môi trường. Không khởi động nhiều worker thừa trên máy ít bộ nhớ.

Các terminal phải dùng chung database và thư mục incidents. Không chuyển sang PostgreSQL mặc định ở riêng một terminal. Dừng tiến trình local bằng Ctrl+C.

## 6. Qwen trên GPU: tải model có đủ không?

Không. Cần **GPU được hỗ trợ + driver + Ollama runtime + model + endpoint đúng**. Ollama chạy inference; Qwen là model do Ollama nạp. Không cần tự cài PyTorch hay CUDA Toolkit đầy đủ cho đường chạy Ollama thông thường.

### A. Ollama trực tiếp trên Windows

1. Cài driver GPU phù hợp và Ollama từ `https://ollama.com/download/windows`.
2. Mở terminal mới. Ollama Windows thường đã chạy nền tại cổng 11434. Chỉ chạy `ollama serve` nếu chưa có server; không chạy thêm server trên cùng cổng.
3. Tải và thử model:

```powershell
ollama --version
ollama pull qwen2.5vl:7b
ollama run qwen2.5vl:7b 'Trả lời một câu tiếng Việt.'
ollama ps
Invoke-RestMethod http://127.0.0.1:11434/api/tags
$body = @{ model = 'qwen2.5vl:7b' } | ConvertTo-Json
(Invoke-RestMethod -Method Post -Uri http://127.0.0.1:11434/api/show -ContentType 'application/json' -Body $body).capabilities
```

`capabilities` phải có `vision`. Xem cột PROCESSOR của `ollama ps` ngay khi model còn được nạp để xác nhận CPU/GPU. Trả lời text thành công chưa chứng minh phân tích ảnh/video đúng; tiếp theo cần thử một recording thật qua ứng dụng và kiểm tra evidence, draft, lỗi worker.

Model `qwen2.5vl:7b` hiện có dung lượng tải khoảng **6.0 GB**, quantization Q4_K_M. Không đồng nhất với file GGUF Q8_0 cũ của repo. Bộ nhớ inference còn chứa vision encoder, KV cache và ảnh; dung lượng tải không phải VRAM cần dùng. Với NVIDIA, 12–16 GB VRAM là mục tiêu thực dụng để thử, không phải bảo đảm cho mọi context/video. GPU 8 GB có thể thiếu bộ nhớ hoặc offload CPU; cần đo bằng input thật. Khởi đầu `QWEN_BATCH_FRAMES=1`, hạn chế context nếu thiếu VRAM, và đánh giá lại độ phủ phân tích.

Nguồn: [Ollama Windows](https://docs.ollama.com/windows), [Qwen2.5-VL 7B](https://ollama.com/library/qwen2.5vl:7b).

### B. Ollama riêng trong Docker trên máy NVIDIA

Windows: cài driver NVIDIA, WSL2, Docker Desktop dùng Linux containers/WSL2; kiểm tra GPU passthrough. Linux: cần driver NVIDIA và NVIDIA Container Toolkit, cấu hình runtime Docker theo tài liệu chính thức.

```powershell
docker run -d --name incidentlens-ollama --gpus all -p 127.0.0.1:11434:11434 -v incidentlens-ollama-models:/root/.ollama -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_MAX_LOADED_MODELS=1 ollama/ollama:0.40.3
docker exec incidentlens-ollama ollama pull qwen2.5vl:7b
docker exec incidentlens-ollama ollama run qwen2.5vl:7b 'Trả lời một câu tiếng Việt.'
docker exec incidentlens-ollama ollama ps
docker logs --tail 80 incidentlens-ollama
```

Tag 0.40.3 lấy từ Dockerfile hiện tại của repo. Các lệnh này là hướng dẫn, chưa được chạy xác nhận trên GPU trong lần kiểm tra này. Không chạy đồng thời Ollama Windows và container với cùng cổng 11434. Volume giữ model khi thay container.

Nguồn: [Ollama Docker](https://docs.ollama.com/docker), [NVIDIA CUDA trên WSL](https://docs.nvidia.com/cuda/wsl-user-guide/).

## 7. Docker đang làm gì trong repo?

`deploy/qwen-local/Dockerfile` build FE Next.js và đóng chung FE, Python BE, worker, FFmpeg, Nginx, Ollama. `docker-compose.qwen-local.yml` chạy gói chung, lưu dữ liệu ở volume `data`, model ở volume `models`, mở web tại `http://localhost:8089`.

```powershell
Set-Location C:\Su\T076\P-076
# Gói chung, không yêu cầu NVIDIA GPU:
docker compose -f docker-compose.qwen-local.yml up -d --build
# Hoặc gói chung có GPU NVIDIA; chọn một cách, không chạy cả hai:
docker compose -f docker-compose.qwen-local.yml -f docker-compose.qwen-gpu.yml up -d --build
```

Lần đầu có thể tải model lâu. Xem `docker compose -f docker-compose.qwen-local.yml logs -f app`. `docker-compose.yml` mặc định còn include cấu hình PostgreSQL cloud; để thử SQLite local, chỉ định file local như trên.

Docker gói môi trường và thư viện, giảm khác biệt giữa máy. Docker không tạo GPU, không mang driver host sang máy mới và không tự mang volume theo image.

## 8. Tách thành hai gói để dễ di chuyển

**Đã có cấu hình hai gói:** `docker-compose.app.yml`, `docker-compose.ai.yml`, `docker-compose.ai-gpu.yml`. Xem [hướng dẫn APP/AI/Neon](docker_app_ai_neon.md). Phần dưới mô tả nguyên tắc tách gói.

```text
Trình duyệt -> Gói APP: Nginx + FE + BE + worker + FFmpeg
                                   |
                                   HTTP
                                   |
                            Gói AI: Ollama
                                   |
                            volume model Qwen
```

- Gói APP không cần CUDA/Ollama. Lưu SQLite, video, evidence và logs trong volume dữ liệu riêng.
- Gói AI dùng image Ollama có quyền GPU và volume model riêng.
- Cùng mạng Compose: BE dùng `QWEN_ENDPOINT=http://ollama:11434/v1/chat/completions`, với `ollama` là tên service. Không dùng localhost để gọi container khác.
- BE trong Docker, Ollama chạy trực tiếp trên Windows: endpoint dùng `http://host.docker.internal:11434/v1/chat/completions`; cần cho Ollama lắng nghe địa chỉ host có thể truy cập, giới hạn bằng firewall.
- Khác máy: dùng địa chỉ riêng/VPN hoặc SSH tunnel, đặt `QWEN_REMOTE_OLLAMA=true` và endpoint tương ứng ở BE/worker. Tránh mở API Ollama trực tiếp ra Internet.
- Máy đích vẫn cần Docker và đủ RAM/disk; máy AI cần GPU/driver/runtime tương thích.

Một “gói” có thể là một image hoặc một thư mục Compose chứa nhiều container. Hai thư mục Compose là đủ để di chuyển độc lập; không cần ép tất cả tiến trình APP vào một container nếu muốn vận hành chúng riêng.

### Những gì phải chuyển

1. Images APP và Ollama: push registry hoặc dùng `docker save` / `docker load`.
2. Compose và cấu hình môi trường riêng của máy đích.
3. Volume dữ liệu ứng dụng: database, video, evidence, logs.
4. Volume model Ollama, hoặc tải lại bằng `ollama pull` trên máy đích.

`docker save` không chứa named volumes. Khi sao lưu SQLite, dừng API và worker ghi dữ liệu trước để có bản sao nhất quán. Không dùng `docker compose down -v` nếu muốn giữ database/model.

## 9. Thứ tự thực hiện nên dùng

1. Chạy FE + BE local bằng SQLite; xác nhận giao diện gọi API thật.
2. Chọn máy GPU phù hợp; chạy Ollama riêng, tải model và xác nhận PROCESSOR/capabilities.
3. Chạy worker, thử recording nhỏ, xem artifacts và trạng thái DRAFT.
4. Sau khi chạy đúng, tách Docker APP/AI để di chuyển độc lập.

Trong lần này đã đối chiếu source/config và tài liệu chính thức; chưa khởi động FE/BE, tải model, benchmark GPU hoặc triển khai hai gói tách rời.
