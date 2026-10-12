# Triển khai P-076: domain cố định, VPS, Neon và Vast.ai GPU

## Cấu trúc được triển khai trong repository

Frontend và backend/worker ở VPS chạy 24/7. PostgreSQL dùng Neon đã tạo.
Vast.ai chỉ chạy Ollama với `qwen2.5vl:7b`, bật/tắt thủ công khi có nhu cầu.
Frontend giữ nguyên giao diện. Bản đầu đặt frontend cùng VPS và truy cập qua một domain HTTPS.
Có thể tách hosting frontend sau; cần build lại API URL và cấu hình CORS khi tách domain.

```text
Browser -> domain HTTPS -> Caddy -> Next.js / FastAPI trên VPS
                                      |
                                      +-> Neon: incident/job/report/evidence/audit
                                      +-> /data/incidents: MP4/CSV/frame/clip/output
                                      +-> Worker: trigger O(n), trích frame, prompt
                                                 |
                                        SSH tunnel xác thực
                                                 |
                                        Vast.ai Ollama Qwen 7B
```

Model nhận ảnh mã hóa base64 và prompt qua API OpenAI-compatible hiện có.
Không cần đưa MP4, CSV hoặc credential Neon lên Vast.ai. Worker và FFmpeg vẫn ở VPS.
Đường truyền từ VPS tới máy GPU đi qua SSH; không mở cổng Ollama công khai.
Đây cũng là cách kết nối Ollama được mô tả trong [hướng dẫn Vast.ai](https://vast.ai/article/build-agent-on-vast-ai-less-than-100-lines-python).

## Những file mới

| File | Chức năng |
|---|---|
| `docker-compose.vps-vast.yml` | App production, SSH tunnel và HTTPS gateway |
| `.env.vps.example` | Các biến cần cấu hình, không chứa secret thật |
| `deploy/vast/tunnel.Dockerfile` | OpenSSH client, chuyển port trong network namespace app |
| `deploy/vast/Caddyfile` | Domain HTTPS và đăng nhập chung cho nhóm demo |

Image app tái sử dụng Dockerfile hiện có để giảm thay đổi. Có binary Ollama trong image,
nhưng remote mode không khởi động Ollama, không tải model và không đợi GPU để bật web.
VPS không cần GPU hoặc volume model.

## Khi GPU offline

1. Web vẫn mở được, người dùng vẫn upload và xem report/video cũ.
2. Incident/job mới được ghi vào Neon; MP4/log lưu trên VPS.
3. Worker kiểm tra model vision qua SSH tunnel **trước khi claim queue**.
4. Nếu GPU/model chưa sẵn sàng, job giữ `queued`, không tiêu attempt và không tạo report giả.
5. Khi GPU bật, model và tunnel hoạt động trở lại, worker tự xử lý theo lần polling tiếp theo.

`WORKER_POLL_S=30` mặc định. Thời gian đợi thực tế gồm khởi động instance, tải/nạp model,
kết nối SSH và chu kỳ polling; không cam kết sẵn sàng trong 30 giây.
Log worker ghi chuyển trạng thái `Remote GPU unavailable` / `Remote GPU ready`.
Frontend dùng trạng thái queue hiện có; chưa bổ sung nhãn mới “chờ GPU” trên giao diện.

Nếu tắt GPU **giữa inference**, luồng lỗi/timeout hiện có vẫn đánh dấu job failed.
Chưa có tự động requeue/resume an toàn cho mọi nhánh. Đợi job kết thúc trước khi stop instance.
Nếu lỗi, engineer kiểm tra raw attempt/output rồi tạo lại analysis qua ứng dụng.

## Chuẩn bị VPS và domain

### Cấu hình VPS đề xuất

| Thành phần | Demo ít người | Đề xuất khởi đầu |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk persistent | 60 GB SSD | 80–100 GB SSD/NVMe |
| Hệ điều hành | Ubuntu Server 24.04 LTS x86_64 | Ubuntu Server 24.04 LTS x86_64 |
| GPU | Không cần trên VPS | Qwen chạy riêng trên Vast.ai |

Đây là ước tính capacity khởi đầu, chưa benchmark concurrency trên VPS thật.
VPS chạy Next.js, API, worker, FFmpeg/trích frame, Nginx/Caddy và SSH tunnel.
RAM 8 GB có khoảng trống cho build frontend, xử lý file và cache, không phải RAM chạy Qwen.
Image app hiện khoảng 4,01 GB; disk còn chứa image/cache build, input video, clip/frame/output và backup.
Chừa ít nhất 20 GB trống để cập nhật image và xử lý file; theo dõi usage thay vì suy số video từ dung lượng MP4 gốc.
Chọn gói có public IPv4, quyền sudo/root, Docker được phép chạy, disk không bị mất khi reboot,
băng thông đủ cho upload/download video và outbound SSH tới Vast.ai.
Singapore là vị trí thuận tiện để thử với người dùng Việt Nam và Neon đang ở ap-southeast-1;
phải đo độ trễ tới GPU thực tế, không xem vị trí này là bảo đảm nhanh nhất.
Docker hỗ trợ Ubuntu 24.04 LTS, xem [hướng dẫn chính thức](https://docs.docker.com/engine/install/ubuntu/).

Cần VPS Linux với Docker Compose, disk persistent và DNS domain trỏ đến public IP VPS.
Chỉ mở port 80/443 cho web và port SSH quản trị theo chính sách của bạn.
Neon credentials chỉ nằm ở secret trên VPS. Đổi mật khẩu đã xuất hiện trong chat trước deployment.
Model key, SSH private key và file `.env.vps` không được đưa lên Git.

```bash
cp .env.vps.example .env.vps
chmod 600 .env.vps
mkdir -p deploy/vast/ssh
chmod 700 deploy/vast/ssh
```

Điền domain, Neon URL, địa chỉ SSH/port/user từ instance Vast.ai.
SSH private key đã đăng ký public key với Vast.ai đặt tại `deploy/vast/ssh/id_ed25519` (chmod 600).
Pin host key được xác minh vào `deploy/vast/ssh/known_hosts`. Có thể dùng `ssh-keyscan` để thu thập
nhưng phải so fingerprint với thông tin đáng tin cậy trước khi sử dụng; không tắt StrictHostKeyChecking.

Gateway demo dùng HTTP Basic Authentication qua HTTPS. Tạo bcrypt hash tương tác:

```bash
docker run --rm -it caddy:2 caddy hash-password
```

Đặt username/hash vào `.env.vps`; hash giữ trong dấu nháy đơn để bảo toàn ký tự `$`.
Caddy yêu cầu password đã hash, theo [tài liệu basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth).
Đây là tài khoản gateway chung cho nhóm demo tin cậy, **chưa phải users/RBAC của ứng dụng**.
Không chia tài khoản này cho người cần quyền chỉ xem nếu họ không được phép sửa/duyệt report.
Muốn người dùng và kỹ sư có quyền riêng cần thêm identity production, bảng users hoặc provider identity,
và kiểm tra quyền ở các route V1. Project chưa có bảng users production như trong sơ đồ.

## Chuẩn bị Vast.ai

Chọn template chính thức có Ollama và SSH. Vast.ai chạy instance container;
không giả định có thể chạy Docker-in-Docker trong instance.
Người dùng tự thuê/chọn instance và ngân sách; cấu hình này không tự gọi API thuê GPU.

Trên instance, kiểm tra Ollama, GPU bằng công cụ của template. Giữ Ollama loopback:

```bash
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_CONTEXT_LENGTH=32768
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_NO_CLOUD=1
# Nếu template chưa chạy Ollama, chạy ollama serve qua startup script của template.
ollama pull qwen2.5vl:7b
curl --fail http://127.0.0.1:11434/api/show \
  -H 'Content-Type: application/json' -d '{"model":"qwen2.5vl:7b"}'
```

Response phải có capability `vision`. Sau một request ảnh thật, kiểm tra `ollama ps`
để xác nhận model đang sử dụng GPU; `nvidia-smi` thấy GPU chưa đủ để chứng minh inference dùng GPU.
Sau khi start lại instance, kiểm tra endpoint SSH và host key: nếu địa chỉ/port thay đổi,
cập nhật `.env.vps` và recreate tunnel. Không tự chấp nhận host key mới.

Stop giữ disk/model nhưng vẫn có phí storage; destroy có thể mất dữ liệu.
Xem [Vast.ai FAQ](https://console.vast.ai/faq/). Không xem GPU stop là chi phí bằng 0.

## Chuyển dữ liệu file cũ

Neon đã có dữ liệu SQL, không import SQLite cũ lại vào mỗi deployment.
Chép nội dung `backend/data/incidents` tới `/data/incidents` của app trên VPS,
giữ tên thư mục và quyền user 10001. Có thể dùng `docker cp` rồi chỉnh owner volume
hoặc restore từ archive có manifest/hash. Backup trước khi chép đè.

Với worker trên VPS và GPU chỉ inference, volume persistent trên VPS là đủ.
Object Storage là bước tùy chọn khi cần backup/scale API/worker sang nhiều máy.
Không đặt file nghiệp vụ dài hạn chỉ trên disk Vast.ai.

## Build và khởi động

```bash
docker compose --env-file .env.vps -f docker-compose.vps-vast.yml config --quiet
docker compose --env-file .env.vps -f docker-compose.vps-vast.yml up -d --build --force-recreate
docker compose --env-file .env.vps -f docker-compose.vps-vast.yml ps
docker compose --env-file .env.vps -f docker-compose.vps-vast.yml logs --tail 100 gpu-tunnel
```

`config --quiet` tránh in connection string. Tránh gửi toàn bộ Docker inspect/config output vào chat.
App startup tự nâng schema Alembic và sử dụng Neon. Website có thể bật khi GPU đang offline.
Khi recreate app, recreate tunnel cùng lần để tunnel dùng network namespace của container app mới.
Healthcheck web/database không phụ thuộc GPU để không gây restart website khi GPU stop.
Tình trạng model xem ở `/data/logs/runtime/worker.stderr.log` trong container.
Compose gốc local không đổi cách hoạt động.

## Dữ liệu và chi phí vận hành

Queue/report/evidence metadata ở Neon, file trên VPS, model cache trên Vast.ai.
Polling worker/healthcheck vẫn truy vấn Neon khi có tunnel/model readiness hoặc healthcheck SQL;
30/60 giây không có nghĩa database sẽ scale to zero. Dịch vụ 24/7 cần dự trù compute cloud.
Thêm quotas/rate limits theo người dùng trước khi mở cho công chúng; hiện có giới hạn kích thước file.
Backup SQL và file theo lịch, giới hạn thời gian lưu raw outputs và giám sát dung lượng.

## Kiểm chứng và việc còn thiếu

Đã kiểm chứng local: 268 test pass; Ruff backend/API/deploy pass; app và tunnel image build;
cấu hình Compose và Caddy validate thành công. Container remote-mode khởi động khi không có GPU:
frontend HTTP 200, healthcheck pass, chỉ có API/frontend/worker/gateway; job thử giữ queued, attempt=0.
Container/volume thử đã được dọn; bằng chứng ở `logs/vps-vast/verification.json`.
Kiểm thử remote mode với GPU không tồn tại chỉ chứng minh xử lý downtime, không chứng minh model quality.
Chưa thuê Vast.ai hoặc có VPS/domain thật, chưa có kết quả ảnh/video thật qua SSH tới GPU.
Chưa tự động bật/tắt GPU theo queue, chưa triển khai users/RBAC production.

Trước public deployment phải kiểm tra:

- GPU offline: login/web/upload hoạt động, job vẫn queued và attempt không tăng.
- GPU online: SSH xác thực, model vision đúng, request ảnh thật thành công.
- Video/log thật: đúng prompt, raw input/output, evidence và DRAFT trên Neon.
- Review: version/audit giữ nguyên hợp đồng, quyền kỹ sư được kiểm tra khi RBAC triển khai.
- Restart app/tunnel và stop/start GPU: dữ liệu file không mất, queue không bị claim nhầm.
- Truy cập HTTPS từ máy khác; không public Ollama hoặc database credentials.
