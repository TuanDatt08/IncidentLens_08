# PostgreSQL cloud cho P-076

## Trạng thái đã kiểm chứng ngày 12/10/2026

Backend native tại cổng 8000 dùng Neon PostgreSQL 18.6 qua TLS 1.3.
Đã chuyển 6 incident, 12 job, 33 evidence, 2 report, 4 report version và 34 audit event.
Import chạy trong transaction, từ chối job đang chạy và không ghi đè bản review khác nội dung.
Import lại đã được kiểm tra: không tạo record trùng.
Kết quả migration nằm trong `logs/postgresql/migration.json` (không commit).

## Cấu hình native

Trong `.env` (không đưa lên Git), đặt:

```dotenv
DATABASE_CLOUD=true
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require&channel_binding=require
P076_DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require&channel_binding=require
```

Backend chuẩn hóa URL sang driver psycopg2 và thêm connect timeout 10 giây.
Giữ nguyên các tham số SSL/channel binding và mật khẩu đã URL encode.
Khởi động lại API và worker sau khi đổi URL; frontend vẫn dùng API hiện tại.
Không gửi mật khẩu qua chat hoặc đưa vào source code.

## Schema và chuyển dữ liệu

```powershell
python -m alembic upgrade head
python -m backend.migrate_to_postgres --source backend/data/incidentlens-ollama.db
python -m backend.migrate_to_postgres --source backend/data/incidentlens-ollama.db --apply --output logs/postgresql/migration.json
```

Dừng API/worker đang ghi vào database nguồn trước khi chuyển.
CLI tạo snapshot SQLite nhất quán; mặc định chỉ kiểm tra, `--apply` mới ghi dữ liệu.
Giữ backup nguồn bên ngoài repository. Không import lại nếu đã sửa report trên cloud;
script sẽ từ chối khi phát hiện khác biệt để bảo vệ nội dung review.

## Docker

Docker mặc định dùng PostgreSQL cloud từ `P076_DATABASE_URL` trong `.env`:

```powershell
docker compose up -d --build
```

Supervisor nâng cấp schema trước khi chạy API/worker. Healthcheck có truy vấn database.
Không khởi động worker trên nhiều máy nếu mỗi máy chưa có đủ file của incident mà worker có thể claim.

## File video và log

PostgreSQL lưu metadata, job, evidence, report, review và audit.
MP4, CSV, frame, clip, raw model request/output vẫn ở `backend/data/incidents` với native,
hoặc `/data/incidents` trong volume Docker. Chưa tích hợp Object Storage.
Máy khác kết nối SQL sẽ thấy metadata nhưng cần storage chung hoặc bản sao file để xem video và xử lý job.
Model Qwen và Ollama tiếp tục chạy local, không được tải vào PostgreSQL.

## Xem dữ liệu trên website Neon

1. Mở https://console.neon.tech, chọn project **P076**.
2. Chọn branch **production**, database **neondb**.
3. Trong **Postgres database → Tables**, chọn schema **public**.
4. Chọn bảng bên trái để xem dữ liệu. Bấm **Refresh rows** để lấy dữ liệu mới nhất.

| Bảng | Nội dung | Số record sau migration |
|---|---|---:|
| `incidents` | ID incident, trạng thái, đường dẫn video/log, metadata | 6 |
| `jobs` | Trạng thái xử lý, tiến độ, lỗi, lease worker | 12 |
| `evidences` | Evidence, đường dẫn frame/clip, thời gian và hash | 33 |
| `analysis_reports` | Nội dung phân tích và trạng thái review | 2 |
| `report_versions` | Lịch sử phiên bản report | 4 |
| `audit_events` | Lịch sử thao tác | 34 |

Các bảng có hậu tố `_v2` đang trống vì dữ liệu được chuyển thuộc luồng V1.
Bảng `alembic_version` ghi phiên bản schema, không phải incident.
Trạng thái FAILED trong dữ liệu cũ được giữ nguyên; migration không chạy lại Qwen hoặc sửa kết quả cũ.

### SQL Editor

Chọn **Postgres database → SQL Editor**, thay toàn bộ SQL mẫu bằng truy vấn dưới đây, rồi bấm **Run**.
Đây là truy vấn chỉ đọc, không sửa dữ liệu:

```sql
SELECT 'incidents' AS table_name, count(*) AS records FROM public.incidents
UNION ALL SELECT 'jobs', count(*) FROM public.jobs
UNION ALL SELECT 'evidences', count(*) FROM public.evidences
UNION ALL SELECT 'analysis_reports', count(*) FROM public.analysis_reports
UNION ALL SELECT 'report_versions', count(*) FROM public.report_versions
UNION ALL SELECT 'audit_events', count(*) FROM public.audit_events;
```

Xem incident và report:

```sql
SELECT incident_id, processing_status, video_uri, telemetry_uri, created_at
FROM public.incidents ORDER BY created_at DESC;

SELECT * FROM public.analysis_reports;
```

### Dữ liệu mới được gửi lên như thế nào?

Với frontend native http://127.0.0.1:3000, upload video/log gửi đến backend native đã cấu hình Neon.
Backend ghi incident và job vào Neon. Worker chạy Qwen local; sau khi phân tích hợp lệ,
backend ghi evidence, report DRAFT, version và audit vào Neon trong transaction.
Không cần bấm upload hoặc import thủ công trên dashboard mỗi lần.
Refresh bảng để xem record mới. Kỹ sư review qua ứng dụng để giữ đúng quy tắc version/audit.
Docker cổng 8089 dùng PostgreSQL cloud khi chạy compose mặc định. Chạy riêng `docker-compose.qwen-local.yml` vẫn dùng SQLite.

Neon Tables chỉ hiển thị `video_uri`/`telemetry_uri` như đường dẫn, không phải file đã upload lên cloud.
Menu **Object storage** là nơi lưu file riêng; chỉ tạo bucket chưa làm backend tự đồng bộ file.
Cần tích hợp storage vào backend trước khi có thể chia sẻ video/frame giữa các máy.

## Hạn mức Neon free

Worker hiện polling mỗi 2 giây. Nếu để chạy liên tục, database có thể không ngủ và tiêu hết compute miễn phí.
Dừng worker khi không dùng; thay đổi polling chỉ được áp dụng khi có yêu cầu về thời gian chờ job.
Không dùng truy vấn keep-alive liên tục để giữ Neon thức.

## Kiểm tra

```sql
SHOW server_version;
SELECT count(*) FROM incidents;
SELECT count(*) FROM analysis_reports;
```

Với Neon pooler, `pg_stat_ssl` phản ánh kết nối pooler tới server; kiểm tra TLS client bằng
`connection.info.ssl_in_use` của psycopg2.
