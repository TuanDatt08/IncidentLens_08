# Worker trên Vast.ai

Luồng V1: Vercel → Render API → Neon (queue/report). Render chuyển tiếp upload,
video, CSV, evidence media và diagnostics qua SSH đến adapter trên Vast.ai.
Worker, FFmpeg, file media và Ollama/Qwen cùng nằm trên Vast.ai. API public,
đăng nhập, quyền truy cập và CSRF vẫn dùng luồng hiện có.

## Các tiến trình

- `incidentlens-gpu-media`: `api.gpu_media:app`, chỉ bind `127.0.0.1:18000`;
  chỉ nhận các route media/upload/diagnostics và vẫn xác thực cookie/CSRF.
- `incidentlens-gpu-worker`: `python -m backend.gpu_worker`, chạy tuần tự;
  kiểm tra model vision và file đầu vào trước khi nhận job V1.
- Ollama có sẵn trên `127.0.0.1:11434`. Không mở inference ra Internet.

File ở `/workspace/incidentlens-media`, log ở `/workspace/incidentlens-logs`
và `/var/log/portal/incidentlens-gpu-*.log`. Code ở `/workspace/incidentlens`.
Virtualenv riêng: `/workspace/incidentlens-venv`.

## Cài trên instance có sẵn

Sao chép code, tạo virtualenv từ requirements hiện có, bảo đảm FFmpeg/ffprobe
và Ollama có model vision. Sao chép `deploy/vast/worker.env.example` thành
`/workspace/incidentlens/worker.env`, điền Neon URL qua secret, chmod 600.
Chạy `bash deploy/vast/install_worker.sh`. Di chuyển media cũ trước khi start worker.

```bash
supervisorctl start incidentlens-gpu-worker
supervisorctl status incidentlens-gpu-media incidentlens-gpu-worker
tail -n 50 /var/log/portal/incidentlens-gpu-worker.log
ollama ps
```

Sau khi xác minh, đặt `autostart=true` trong supervisor config của worker.
Supervisor tự restart tiến trình lỗi; không dùng Docker-in-Docker.

## Render

Dockerfile chạy `python -m deploy.render_start`. Nếu có cấu hình SSH, runner
duy trì tunnel rồi tự reconnect khi ngắt. Các biến secret trên Render:

- `GPU_MEDIA_BASE_URL=http://127.0.0.1:18000`
- `GPU_SSH_TARGET=root@HOST`, `GPU_SSH_PORT=PORT`
- `GPU_SSH_PRIVATE_KEY`: khóa riêng dành riêng cho tunnel, hỗ trợ literal `\n`.
- `GPU_SSH_KNOWN_HOSTS`: host key đã xác minh cho `[HOST]:PORT`.

Khóa public trên Vast dùng `restrict,port-forwarding,permitopen="127.0.0.1:18000",command="/bin/false"`.
Không sao chép khóa quản trị cá nhân vào Render; không tắt kiểm tra host key.
Nếu tunnel/GPU tắt, upload/media trả 503; API danh sách/report/login vẫn chạy.
Render không có worker. Không đặt `GPU_MEDIA_BASE_URL` trong env của GPU.

## Giới hạn và khôi phục

Đây là luồng V1. Worker V2 không được bật tự động.
Stop/start Vast giữ filesystem; recycle/destroy có thể mất toàn bộ media nếu
instance không có volume. Cần sao lưu media trước các thao tác này.
Neon chỉ chứa metadata, không khôi phục được MP4/CSV đã mất.

Rollback routing: bỏ `GPU_MEDIA_BASE_URL` và các biến SSH trên Render, restart;
chỉ dùng khi media đã được chép lại về storage API. Dừng worker bằng
`supervisorctl stop incidentlens-gpu-worker` khi không có job đang chạy;
không hủy job hoặc xóa file để rollback.
