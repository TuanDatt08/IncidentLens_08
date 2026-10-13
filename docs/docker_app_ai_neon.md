# Hai gói Docker: APP, AI và Neon

APP: image `incidentlens:app`, chứa FE, API, worker V1/V2 tuần tự, Nginx và FFmpeg. AI: image `ollama/ollama:0.40.3`, chạy Ollama và nạp Qwen từ volume. Database dùng Neon qua `P076_DATABASE_URL` trong `.env`; không copy `.env` vào image.

## Chạy trên cùng máy

PowerShell tại `C:\Su\T076\P-076`:

```powershell
# Máy NVIDIA: dùng GPU override.
docker compose -f docker-compose.ai.yml -f docker-compose.ai-gpu.yml up -d
# Máy không có NVIDIA: dùng lệnh này thay cho lệnh trên.
docker compose -f docker-compose.ai.yml up -d

# Tải model một lần; cần Internet và disk trống.
docker compose -f docker-compose.ai.yml exec ollama ollama pull qwen2.5vl:7b

# Khởi động APP, đọc Neon URL từ .env.
docker compose -f docker-compose.app.yml up -d --build
```

Chọn một lệnh khởi động AI phù hợp. Máy hiện tại được Windows liệt kê Intel UHD Graphics; GPU NVIDIA chưa được xác nhận. AI tạo mạng `incidentlens-ai`; APP tham gia mạng đó. APP chạy migrations Neon trước khi khởi động API. Không chạy nhiều APP đồng thời khi migration đang diễn ra.

Mở `http://localhost:8089`. API dùng cùng origin `/api/v1`, `/api/v2`, không cần thay cấu hình FE. Trước khi chạy, dừng gói cũ nếu đang chiếm 8089; dừng Ollama native nếu đang chiếm 11434. Không xóa volumes cũ.

```powershell
docker compose -f docker-compose.app.yml ps
docker compose -f docker-compose.ai.yml ps
docker compose -f docker-compose.app.yml logs --tail 80 app
docker compose -f docker-compose.app.yml exec app tail -n 80 /data/logs/runtime/worker.stderr.log
docker compose -f docker-compose.ai.yml exec ollama ollama ps
```

APP vẫn hoạt động khi AI chưa có model/offline; worker không claim job cho đến khi endpoint/model vision sẵn sàng. Health APP kiểm tra database, API, FE và tiến trình, không chứng minh model chạy GPU hoặc chất lượng phân tích.

## Biến cấu hình

- `P076_DATABASE_URL`: URL PostgreSQL Neon hiện có; cloud mode bắt buộc SSL và tự thêm `sslmode=require` nếu thiếu.
- `QWEN_ENDPOINT` được Compose cố định ở loopback APP. Nginx nội bộ chuyển tiếp tới `http://ollama:11434`; DNS Docker được resolve mỗi request để APP vẫn khởi động khi AI chưa chạy.
- `P076_PORT`: cổng APP, mặc định 8089.
- `P076_OLLAMA_PORT`: cổng Ollama trên host, mặc định 11434; đổi cổng này không đổi port 11434 giữa containers.
- Model cố định `qwen2.5vl:7b` theo contract phân tích video hiện tại.
- `WORKER_POLL_S`: mặc định 30 giây, giảm polling khi GPU chưa sẵn sàng.

Compose APP cố ý dùng `P076_DATABASE_URL`, giống cấu hình PostgreSQL cloud của repo; không dùng `DATABASE_URL` local trong `.env`. Chỉ các biến được liệt kê trong Compose được truyền vào container.

## Dữ liệu và di chuyển

Neon chứa tables/metadata/jobs/reports. Video, evidence, logs và identity secret nằm trong volume `incidentlens-app_data`. Model nằm trong `incidentlens-ai_models`. Hai gói không tự sao chép dữ liệu từ volumes của gói cũ.

Chuyển images bằng registry hoặc:

```powershell
docker save -o incidentlens-images.tar incidentlens:app ollama/ollama:0.40.3
# Trên máy đích:
docker load -i incidentlens-images.tar
```

Chuyển Compose, `.env` qua kênh riêng, sao lưu volume APP sau khi dừng APP; model có thể tải lại. `docker save` không chứa volumes. Giữ identity secret khi di chuyển nếu cần duy trì chữ ký hiện tại. Không dùng `down -v` để dừng dịch vụ.

## AI ở máy GPU khác

Chạy gói AI trên máy GPU. Tạo mạng external ở máy APP bằng `docker network create incidentlens-ai` nếu chưa có. Dùng một SSH tunnel container trên mạng này với alias `ollama`, lắng nghe cổng 11434 và forward tới Ollama loopback máy GPU; hoặc sửa upstream `http://ollama:11434` trong `deploy/app/nginx.conf` thành IP riêng/VPN của AI rồi build lại APP. Port AI mặc định chỉ bind loopback; cần tunnel hoặc cấu hình bind IP riêng cùng firewall để kết nối từ xa, không mở Ollama ra Internet. Hai Compose hiện tại đã cấu hình sẵn cho cùng Docker host; trường hợp khác máy cần bổ sung kết nối riêng như trên.

Gói cũ `docker-compose.qwen-local.yml` vẫn có thể dùng riêng. Không chạy gói cũ và mới trên cùng cổng hoặc cùng queue Neon trong thời gian chuyển đổi.

## Kết quả kiểm tra ngày 13/10/2026

- Build image APP thành công, gồm typecheck, lint và build Next.js.
- 9 tests deployment pass; Ruff backend/API và test mới pass.
- Bộ test toàn repo: 267 pass, 3 test migration SQLite thất bại do đọc `DATABASE_CLOUD=true` từ `.env` Neon. Chạy lại `tests/backend/test_db.py` với `DATABASE_CLOUD=false`: cả 3 pass. Có warning deprecation LangGraph và warning dependency từ môi trường Python host; không thay dependency trong tác vụ đóng gói.
- Container APP healthy, FE `/incidents` và API `/api/v1/health` HTTP 200.
- Neon `SELECT 1` thành công cả trên host và trong APP; Alembic version `20261003_jobs`.
- APP có 4 tiến trình được supervisor quản lý: API, FE, worker, gateway; không có Ollama cục bộ.
- Ollama riêng trả `/api/tags` qua proxy APP; volume AI mới chưa chứa model. Worker ghi `Remote GPU unavailable; jobs remain queued`.
- Chưa tải weights vào volume AI mới, chưa thử inference GPU/recording thật. Chạy lệnh `ollama pull` ở trên trên máy AI phù hợp trước khi phân tích.
