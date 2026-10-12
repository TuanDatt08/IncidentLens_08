# Những phần cần bổ sung để deploy P-076 lên Internet

Đánh giá từ checkout hiện tại ngày 12/10/2026. Đây là hướng triển khai, chưa phải kết quả kiểm chứng trên server public.

## Phương án ít thay đổi nhất

Dùng một server chạy Docker với ổ đĩa persistent. Frontend, API, worker và Ollama cùng server;
PostgreSQL dùng Neon đã cấu hình. Một reverse proxy phía trước cấp HTTPS và chuyển request vào cổng 8089 trên localhost.
Giữ một worker/model consumer ban đầu để giới hạn bộ nhớ và tránh nhiều job inference chạy đồng thời.

```text
Người dùng trên Internet
        |
    Domain + HTTPS
        |
    Reverse proxy
        |
    Docker app :8089 (localhost)
        |-- Frontend
        |-- FastAPI ------------ Neon PostgreSQL
        |-- Worker ------------- Ollama Qwen 7B
        |-- /data/incidents ---- ổ đĩa persistent
        `-- /models ------------ ổ đĩa persistent
```

Nhiều người dùng có thể truy cập một server và xem cùng file qua backend;
không cần mỗi người dùng có model hoặc bản sao video. Server xử lý inference thay họ.

## Đã có trong repository

- Docker đóng gói frontend, FastAPI, worker, Ollama và Nginx.
- Volume `data` và `models` để giữ file/model qua lần tạo lại container trên cùng host.
- Docker build frontend với API cùng origin: `/api/v1`, `/api/v2`; mock API tắt.
- PostgreSQL cloud override, Alembic migrations và công cụ import SQLite.
- Backend native đã kết nối Neon; dữ liệu cũ đã được import.
- Queue persistent, lease/heartbeat, report DRAFT, evidence và audit.

## Cần bổ sung trước khi mở public

### 1. Server chạy Qwen

Chọn server hỗ trợ Docker và đủ RAM/VRAM cho model qwen2.5vl:7b đang dùng.
GPU NVIDIA là lựa chọn cần đánh giá nếu muốn thời gian phân tích thực dụng; CPU chạy được nhưng phép thử một ảnh tại máy phát triển mất khoảng 283 giây.
Con số này không phải thời gian xử lý mọi video. Đo trên chính server với video/log thật trước khi công bố tốc độ.
GPU override hiện có nhưng chưa được kiểm chứng trên máy có NVIDIA.
Không chọn mô hình hosting chỉ chạy frontend hoặc filesystem tạm thời cho toàn bộ stack hiện tại.

### 2. Domain và HTTPS

Cổng Docker hiện bind `127.0.0.1:8089`: chỉ host truy cập trực tiếp.
Đặt reverse proxy HTTPS trên host, chuyển domain tới cổng này. Có thể giữ bind localhost để không mở trực tiếp ứng dụng ra ngoài.
Proxy phía ngoài phải hỗ trợ dung lượng upload và timeout tương thích với Nginx phía trong.
Định nghĩa giới hạn upload phù hợp thay vì mặc định cho mọi người upload 2 GB.
Chỉ mở cổng public của proxy; Ollama và PostgreSQL credentials không được công khai.

### 3. Cấu hình production

Tạo cấu hình deployment riêng, không chứa secret trong Git:

- `APP_ENV=production`.
- `DATABASE_CLOUD=true` và `DATABASE_URL` lấy từ secret của server hoặc cloud override.
- `CORS_ORIGINS` đặt domain thực tế; nếu dùng một domain thì frontend gọi API cùng origin.
- `P076_DATABASE_URL` chỉ tồn tại trong `.env`/secret server, không đưa vào frontend hoặc image.
- Giữ các biến Qwen phù hợp tài nguyên server, bắt đầu parallel=1.

Build frontend native riêng phải đặt `NEXT_PUBLIC_USE_MOCK_API=false` và API URL đúng **trước khi build**.
Image Docker hiện đã đặt đường dẫn API tương đối, không cần trỏ browser người dùng tới localhost:8000.
Cloud override có sẵn nhưng compose gốc vẫn dùng SQLite; phải ghép đúng file khi deploy.

### 4. Chuyển file cũ và giữ file mới

Neon hiện chỉ lưu metadata/report và đường dẫn file. Source code/image không mang theo file ở `backend/data/incidents`.
Chép nội dung thư mục này vào `/data/incidents` trong volume của server, giữ nguyên cây thư mục và tên incident.
Kiểm tra hash hoặc manifest sau khi chép và quyền đọc/ghi của user trong container (UID 10001).
Không cần tải trọng số GGUF cũ lên Neon; Docker dùng cache model Ollama trong volume `/models`.
Server có thể tải model lần đầu hoặc nhận cache đúng định dạng Ollama.

Với một server, ổ đĩa persistent là đủ. Nếu tách API và worker hoặc chạy nhiều replica,
cần storage chung/Object Storage và chỉnh backend đọc/ghi file, phục vụ media, tải file vào scratch để FFmpeg/Qwen xử lý.
Chỉ tạo bucket hoặc chép file vào bucket chưa thay thế các chỗ dùng `Path` trong backend.

### 5. Đăng nhập và quyền truy cập

Các route V1 hiện đọc/upload/analyze/edit/approve/reject report chưa gắn kiểm tra identity ở API.
Trước khi mở cho mọi người, cần xác thực ở gateway hoặc API và quyền phù hợp cho xem/upload/review.
Nếu chỉ demo nhóm nhỏ, gateway có đăng nhập có thể là bước ban đầu đơn giản.
Nếu người dùng và kỹ sư cần quyền khác nhau, cần kiểm tra role phía backend; gateway chung không thay thế phân quyền review.
Giữ quy tắc Qwen chỉ tạo DRAFT, kỹ sư mới duyệt. Không tin role/identity do frontend tự khai báo.

### 6. Hạn mức và vận hành

- Giới hạn tốc độ upload/analyze và số job chờ để tránh một người chiếm hết Qwen/ổ đĩa.
- Backup Neon theo chính sách project và backup file/model volume riêng. Kiểm tra phục hồi.
- Theo dõi disk, lỗi job, worker heartbeat, model readiness và thời gian/token.
- Worker hiện polling 2 giây, healthcheck Docker hiện SELECT 1 mỗi 15 giây.
  Những truy vấn này có thể giữ Neon hoạt động liên tục. Cần tính ngân sách compute,
  điều chỉnh lịch kiểm tra/polling hoặc chọn gói phù hợp cho dịch vụ chạy 24/7.
- Đổi credential đã xuất hiện trong chat bằng dashboard Neon; cập nhật secret và restart service.

## Kiểm tra bắt buộc trước khi bàn giao

1. Truy cập domain HTTPS từ máy khác, không dùng localhost của máy phát triển.
2. Người chưa đăng nhập không được upload/analyze/review hoặc xem dữ liệu bị giới hạn.
3. Xem được report và video cũ sau khi chuyển file.
4. Upload video/log mới; thấy incident/job thật xuất hiện trên Neon.
5. Worker gọi Qwen thật; kiểm tra prompt, raw request/output, evidence và report DRAFT.
6. Kỹ sư review; version và audit được lưu đúng.
7. Restart container/server; file, model và dữ liệu còn nguyên, worker/API hoạt động trở lại.
8. Hai người dùng cùng lúc: queue/lease hoạt động, không xử lý cùng job hai lần hoặc vượt tài nguyên.

Chưa có kết quả chạy thử public hoặc GPU server trong checkout này.
Kết nối Neon thành công không đủ để xác nhận toàn bộ deployment đã sẵn sàng.
