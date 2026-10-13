# Đối chiếu Docker với tài liệu mục 12.1–12.3

Kiểm tra ngày 13/10/2026 tại `C:\Su\T076\P-076`. Nguồn yêu cầu là văn bản người dùng đính kèm về Docker, multi-stage và Compose. Đây là kiểm tra hiện trạng, không thay cấu hình triển khai.

## Kết luận

Đã container hóa và chạy local hai gói APP/AI, dùng Neon PostgreSQL. Chưa hoàn tất vòng đời registry → server → production hoặc pipeline CI/CD trong sơ đồ. Gói AI đã có runtime Ollama nhưng volume model mới chưa chứa Qwen.

| Tiêu chí | Trạng thái | Bằng chứng / phần thiếu |
| --- | --- | --- |
| Dockerfile và build image | Đạt local | Image `incidentlens:app` tồn tại, container chạy |
| Tách APP / AI | Đạt | Hai Compose riêng; APP chứa FE/API/worker/gateway, AI chứa Ollama |
| Tag phiên bản | Một phần | Ollama pin `0.40.3`; APP dùng tag `app`, chưa có release version/commit tag |
| Push registry, pull trên server | Chưa xác nhận | Không có build/push/deploy step trong workflow hiện tại |
| Secrets truyền lúc runtime | Đạt cho cấu hình đang dùng | Neon URL từ `.env`; `/app/.env` không tồn tại trong APP; `.env` và FE `.env.local` không được Git track |
| Multi-stage | Đạt cấu trúc | Stage Node build FE, stage Python nhận standalone FE; Python dependencies vẫn được cài trực tiếp trong runtime stage |
| Layer caching | Đạt | Copy requirements trước pip install; copy package/lock trước npm ci |
| Loại build/dev tools khỏi runtime | Một phần | Không mang toàn bộ Node builder; APP vẫn chứa pytest, Ruff do requirements chung |
| Image nhỏ gọn | Cần phân biệt số đo | Image inspect báo 338,444,171 bytes cho dữ liệu image nén; Docker image ls/system df báo khoảng 1.36 GB gồm storage nén và giải nén của containerd. Không dùng 323 MiB để mô tả dung lượng trên disk |
| Non-root | APP đạt | APP chạy `appuser`; AI dùng user mặc định image upstream, chưa harden non-root riêng |
| Healthcheck | APP đạt | Container healthy; script kiểm tra DB, FE/API và PID; AI chưa khai báo healthcheck riêng |
| `.dockerignore` | Đạt cơ bản | Loại Git, `.env`, node_modules, `.next`, logs, tests và dữ liệu backend khỏi build context |
| Compose network | Đạt cùng host | Shared network `incidentlens-ai`; APP dùng loopback proxy Nginx tới service `ollama` |
| Database PostgreSQL | Đạt | `DATABASE_CLOUD=true`; Neon SELECT 1 thành công trong APP |
| Named volumes | Đạt cấu hình | `incidentlens-app_data`, `incidentlens-ai_models`; chưa thử phục hồi backup lên máy khác |
| Startup dependency | Có cơ chế phù hợp | AI tạo network trước; APP migration trước startup; worker chờ model vision sẵn sàng, không bắt APP phải chờ AI healthy |
| CPU/RAM limits | Chưa có | Container APP/AI đều có Memory=0 và NanoCPUs=0, tức không đặt giới hạn container |
| Restart policy | Đạt cấu hình | `unless-stopped`; chưa thử mô phỏng crash để kiểm chứng recovery |
| GitHub Actions main/develop | Có cấu hình | Ruff, pytest, frontend typecheck/lint/build; runner `self-hosted`, chưa kiểm tra trạng thái runner/run trên GitHub |
| Test coverage | Chưa có trong workflow | Không có lệnh `--cov` hoặc báo cáo coverage |
| Docker build + container healthcheck trong CI | Chưa có | Workflow chưa build/smoke-test gói APP/AI mới; tests deployment mới cần Docker CLI |
| Staging/production | Chưa có bằng chứng triển khai | Local APP vẫn `APP_ENV=development`, cổng bind 127.0.0.1 |
| Qwen GPU | Chưa đạt live | AI tags rỗng; chưa tải model, chưa xác nhận GPU passthrough/inference |

## Những điểm không cần sao chép nguyên mẫu

- Neon thay thế PostgreSQL container, đúng lựa chọn người dùng; không cần thêm DB local để giống YAML mẫu.
- Redis/vector store là ví dụ cho ứng dụng có nhu cầu tương ứng, không phải điều kiện bắt buộc của Docker. Không thêm khi pipeline hiện tại không sử dụng.
- Bind mount source/hot reload là tùy chọn development; production image hiện tại cần rebuild khi đổi code.
- Hai gói Compose độc lập yêu cầu chỉ định `-f` và khởi động AI/network trước APP. `docker compose up` mặc định vẫn dùng cấu hình gói cũ.

## Sửa cách hiểu trong tài liệu nguồn

`HEALTHCHECK` đánh dấu healthy/unhealthy. Docker Compose thông thường không tự restart chỉ vì container unhealthy; restart policy xử lý khi tiến trình container thoát hoặc Docker khởi động lại. Supervisor APP hiện thoát nếu child process chết, nhưng thất bại healthcheck riêng không tự làm nó thoát. [Docker restart policies](https://docs.docker.com/engine/containers/start-containers-automatically/).

Multi-stage cho phép chọn artifacts chuyển giữa stages; không đảm bảo một mức giảm dung lượng cố định hoặc tự loại dependencies development. [Docker multi-stage](https://docs.docker.com/build/building/multi-stage/).

## Thứ tự hoàn thiện đề xuất

1. Tải Qwen vào volume AI và kiểm chứng inference trên máy GPU phù hợp.
2. Pin dependencies/release tags; tách dependencies development khỏi image APP nếu muốn tối ưu production.
3. Thêm AI healthcheck và giới hạn tài nguyên sau khi đo workload thật.
4. Bổ sung CI coverage, Docker APP build và smoke-test FE/API/database; provisioning Docker/FFmpeg cho self-hosted runner.
5. Push registry, deploy staging, kiểm tra volumes/media/backup rồi mới xác nhận production.

Hướng dẫn chạy hiện tại: [APP/AI/Neon](docker_app_ai_neon.md). Không suy readiness GPU hoặc production từ việc API healthy.

## Vì sao APP chiếm khoảng 1.35 GB?

Image SHA `ba3a2f1b758a66d07fecb12e036362d762d350cd8d2e57c3b9fe8c77963cf85f` đã được kiểm tra trực tiếp bằng image inspect, history, system df và du trong container.

APP còn chứa worker, FFmpeg, Nginx và runtime Node/Python, không chỉ source FE/BE. Layer history báo xấp xỉ:

| Thành phần | Layer size |
| --- | ---: |
| FFmpeg, Nginx, thư viện hệ thống cài bằng apt | 464 MB |
| Python virtual environment/dependencies | 260 MB |
| Node binary | 125 MB |
| Debian/Python base layers | 142 MB |
| FE standalone và static | 26 MB |
| Backend/API source và deployment scripts | Khoảng 1.5 MB |

Tổng layers giải nén khoảng 1.02 GB. Docker containerd còn lưu bản nén khoảng 338 MB, nên storage báo khoảng 1.36 GB. Đây không phải RAM đang dùng, không gồm model Qwen hay volume video. Docker build cache toàn hệ thống còn là mục riêng, hiện khoảng 16.91 GB; không cộng cache đó vào kích thước gói APP.

Số du là dung lượng file trong filesystem và không nhất thiết bằng kích thước layer history. Các điểm có thể tối ưu sau: tách requirements production/dev, loại dependency AI scaffold không được active flow dùng sau khi trace imports, dùng FFmpeg runtime phù hợp và kiểm chứng codec, strip binary nếu đã kiểm chứng. Chỉ thêm Python builder stage không tự loại libraries runtime hoặc giảm một mức cố định.

Nguồn giải thích cơ chế storage: [Docker containerd image store](https://docs.docker.com/engine/storage/containerd/).
