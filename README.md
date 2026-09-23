# IncidentLens

IncidentLens là ứng dụng phân tích sự cố giao thông bằng video và telemetry. Frontend Next.js gọi backend FastAPI để upload incident, theo dõi job phân tích, xem report/evidence và hỗ trợ quy trình Engineer chỉnh sửa, Reviewer duyệt.

Backend API tuân theo [contract v1.1](docs/backend-contract-v1.1.md). Các trạng thái job được lấy qua polling; media video và evidence được phục vụ bằng các endpoint của backend.

## Backend gồm những gì?

| Thành phần | Vai trò |
| --- | --- |
| `frontend/` | Ứng dụng Next.js cho upload, theo dõi job và review report/evidence. |
| `src/main.py`, `src/api/` | FastAPI, Swagger, các route upload, incident, job, report, evidence, audit và media. |
| `src/services/incident_ingestion.py`, `video.py`, `telemetry.py`, `storage.py` | Kiểm tra MP4 bằng FFprobe, nhận CSV có `sec_from_incident`, lưu file và metadata. |
| `src/worker.py`, `src/services/jobs.py`, `processing.py`, `vlm.py` | Worker lấy job từ PostgreSQL; Pass 1 định vị sự cố, Pass 2 phân tích clip, frame và telemetry. Worker thường gọi OpenAI. |
| `src/services/reports.py`, `review.py`, `media.py` | Lưu report/evidence, edit có version, submit/approve/reject, phục vụ video và ảnh qua API. |
| `src/demo_fake_worker.py` | Chạy **một job được chọn** với VLM giả để thử luồng mà không cần API key. Chỉ dùng cho demo local. |
| `src/models/contracts.py`, `tables.py`, `alembic/` | Schema API, sáu bảng nghiệp vụ PostgreSQL và migration. |
| `tests/`, `tests/postgres_smoke.py` | Test API/service với fake VLM; smoke test riêng dùng PostgreSQL và FFmpeg thật. |

Sáu bảng nghiệp vụ là `incidents`, `jobs`, `analysis_reports`, `evidences`, `report_versions`, `audit_events`. MP4, ảnh và CSV được lưu trong `data/incidents/`; database chỉ giữ metadata và đường dẫn nội bộ. Docker dùng volume PostgreSQL để giữ dữ liệu sau khi container dừng.

Luồng API: **upload → `incident_id` → analyze → `job_id` → poll job → report/evidence → edit/review**. Ba nhóm trạng thái độc lập:

- Incident: `UPLOADED`, `READY`, `PROCESSING`, `COMPLETED`, `FAILED`.
- Job: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
- Report review: `DRAFT`, `IN_REVIEW`, `APPROVED`, `REJECTED`.

`sec_from_incident`, `incident_window` và `Evidence.time_range_s` tính bằng giây tương đối với va chạm; giá trị âm là trước va chạm. Khi tua video gốc, cộng thêm `video_metadata.collision_offset_in_video_s`. `Evidence.uri` là đường dẫn lưu trữ, **không phải URL phát media**; dùng các media route ở Swagger.

## Yêu cầu

- Docker Desktop và Docker Compose.
- Node.js 20 trở lên để chạy frontend.
- Python 3.11 trở lên nếu chạy backend hoặc test ngoài Docker.

## Khởi động backend

Yêu cầu Docker Desktop đang chạy. Trong thư mục gốc repo:

```powershell
docker compose up -d --build backend
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Compose khởi động PostgreSQL, chạy Alembic migration và API. Health trả `status: ok`. Mở Swagger tại <http://127.0.0.1:8000/docs>. PostgreSQL của demo ở `127.0.0.1:5432`, database/user `rav18`. Lệnh trên chưa khởi động worker OpenAI; phù hợp để thử fake report bên dưới.

## Khởi động frontend

Trong terminal khác, từ thư mục gốc repo:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
Set-Location frontend
npm ci
npm run dev
```

Frontend mặc định gọi API tại `http://localhost:8000/api/v1` và dùng backend thật. Mở <http://localhost:3000>. Để đổi URL API, sửa `NEXT_PUBLIC_API_BASE_URL` trong `frontend/.env.local`.

Các trang chính:

- `/incidents` — danh sách incidents.
- `/incidents/new` — upload video và CSV telemetry tùy chọn.
- `/incidents/{incident_id}/processing` — trạng thái job và tiến độ phân tích.
- `/incidents/{incident_id}` — video, timeline, evidence, report và review workflow.

## Thử luồng phân tích với DemoVLM

Các lệnh sau dùng **PowerShell** và không cần `OPENAI_API_KEY`. Đứng ở thư mục gốc repo. Dừng worker thường trước khi tạo job để nó không lấy job dành cho demo:

```powershell
docker compose stop worker
```

**1. Chuẩn bị MP4 và CSV.** Có thể dùng file của bạn, hoặc tạo mẫu 4 giây bằng FFmpeg trong image backend:

```powershell
docker compose run --rm --no-deps backend ffmpeg -loglevel error -f lavfi -i testsrc2=size=160x120:rate=10 -t 4 -c:v libx264 -pix_fmt yuv420p -y /app/data/demo.mp4
@'
sec_from_incident,sim_time_s
-0.5,1.5
0,2
0.5,2.5
'@ | Set-Content -Encoding utf8 data/demo-log.csv
```

CSV phải có cột `sec_from_incident` dạng số và tăng nghiêm ngặt. Log là tùy chọn; MP4 là bắt buộc. Hai file mẫu nằm trong `data/`, thư mục được Git bỏ qua.

**2. Upload và tạo job.** Dùng `curl.exe` vì `curl` trong Windows PowerShell có thể là alias khác:

```powershell
$upload = curl.exe -sS -F 'video=@data/demo.mp4;type=video/mp4' -F 'log=@data/demo-log.csv;type=text/csv' http://127.0.0.1:8000/api/v1/incidents/upload | ConvertFrom-Json
$upload
$job = Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/incidents/$($upload.incident_id)/analyze"
$job
```

Upload tạo incident và trả `incident_id`, `processing_status: READY`. Analyze trả HTTP 202 với `job_id` và `status: queued`. Mỗi lần thử cần upload một incident mới; report đã hoàn tất không được analyze lại.

**3. Chạy fake VLM cho đúng job vừa tạo.** Lệnh này dùng worker/persistence hiện có và chỉ thay adapter VLM trong lần chạy đó:

```powershell
docker compose run --rm --no-deps backend python -m src.demo_fake_worker "$($job.job_id)"
$jobResult = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/jobs/$($job.job_id)"
$jobResult
$report = Invoke-RestMethod "http://127.0.0.1:8000$($jobResult.result_uri)"
$report
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/incidents/$($upload.incident_id)/evidence"
```

Kết quả mong đợi: job `succeeded`, report `review_status: DRAFT`, `version: 1`, summary bắt đầu bằng `DEMO`, và evidence có clip, frame, telemetry. Fake VLM **giả định va chạm ở giữa MP4** để kiểm tra pipeline; nó không kết luận gì về nội dung video. Có thể mở `GET /api/v1/incidents/{incident_id}/video` hoặc `GET /api/v1/incidents/{incident_id}/evidence/{evidence_id}/media` trong trình duyệt. Trong Swagger, có thể thử tiếp PATCH report với `version`, rồi submit và approve/reject.

## Kiểm thử

Test thường dùng SQLite tạm và fake VLM, không gọi OpenAI hoặc sửa database `rav18`. Khi chạy trong Compose, phải xóa `DATABASE_URL` của service để migration test dùng SQLite riêng:

```powershell
docker compose run --rm --no-deps -e DATABASE_URL= backend pytest -q tests/
```

Kết quả đã kiểm tra: **56 passed**. Smoke test với PostgreSQL và FFmpeg thật dùng database `rav18_e2e` tách biệt; xem [backend runbook](docs/backend-runbook.md) để tạo, migrate, chạy test và dọn database này.

Kiểm tra frontend và tạo production build:

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run build
```

Muốn dùng VLM thật, đặt `OPENAI_API_KEY` trong môi trường rồi chạy `docker compose up -d --build` để khởi động cả `worker`. Xem log bằng `docker compose logs -f backend worker`. Dừng API/worker mà vẫn giữ PostgreSQL và dữ liệu bằng `docker compose stop backend worker`.

## Tài liệu và giới hạn hiện tại

- [Contract API v1.1](docs/backend-contract-v1.1.md)
- [Runbook backend](docs/backend-runbook.md)
- [Kiến trúc](ARCHITECTURE.md)
- [Worklog](WORKLOG.md)
- [README template ban đầu](README_boilerplate.md) và [technical guidebook](docs/guide/) của khóa học

DemoVLM tạo report giả để kiểm tra pipeline; kết quả này không phải phân tích thực tế video. Các route ghi report và truy cập media hiện giới hạn ở môi trường demo/local; chúng trả `403` trong `APP_ENV=production` khi chưa có xác thực và phân quyền. Những trường contract còn cần xác nhận được ghi trong tài liệu contract.
