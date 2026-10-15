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

Temporal context: bật `QWEN_TEMPORAL_CONTEXT=true`, `QWEN_BATCH_FRAMES=6`,
`QWEN_TWO_STAGE=false`. Worker bổ sung mẫu 8 FPS quanh đỉnh ±1 giây, gồm đúng
critical timestamp; tổng extraction vẫn không vượt 256 frame. Các batch chồng
lấn 2 frame và có thêm lượt kết luận cuối với overview trước/đỉnh/sau và các
quan sát sơ bộ. Evidence citation của lượt cuối chỉ dùng ảnh/telemetry gửi trong
lượt đó. Kết luận sơ bộ không được OR thành incident cuối cùng.

Consistency check chạy trên toàn cửa sổ candidate. Kết quả âm tính có mâu thuẫn
telemetry chuyển `REVIEW_REQUIRED_TELEMETRY_CONFLICT`; lượt kết luận thiếu/hỏng
chuyển `REVIEW_REQUIRED_INCOMPLETE_CANDIDATE`. Các trạng thái này không tự ép
`incident_detected=true`. Raw response vẫn được lưu; summary chỉ tổng hợp ngắn.
Route review-context cũng đi qua tunnel để đọc được telemetry và artifacts trên GPU.

Bộ lọc phanh mạnh tùy chọn: `QWEN_TRIGGER_DECELERATION=22`,
`QWEN_BRAKING_CONFIRMATION_S=0.08`, `QWEN_FLAG_ONLY=true`. Candidate cần
phanh ≥ 0,8 đồng thời acceleration ≤ −22 trong ít nhất 0,08 giây;
khoảng cách giữa mẫu không quá 0,125 giây. Flag sensor va chạm vẫn được giữ.
Raw trigger không bị xóa; trường `selection` cho biết nhóm được chọn hoặc loại.
Mặc định confirmation=0 giữ hành vi cũ. Đây là hiệu chỉnh cho recording đã cung cấp,
chưa có đánh giá recall trên nhiều video; acceleration phải dùng cùng đơn vị với CSV.
Giữ clip có ngữ cảnh trước/sau trigger; không dùng mốc thời gian hardcode.

Đây là luồng V1. Worker V2 không được bật tự động.
Stop/start Vast giữ filesystem; recycle/destroy có thể mất toàn bộ media nếu
instance không có volume. Cần sao lưu media trước các thao tác này.
Neon chỉ chứa metadata, không khôi phục được MP4/CSV đã mất.

Rollback routing: bỏ `GPU_MEDIA_BASE_URL` và các biến SSH trên Render, restart;
chỉ dùng khi media đã được chép lại về storage API. Dừng worker bằng
`supervisorctl stop incidentlens-gpu-worker` khi không có job đang chạy;
không hủy job hoặc xóa file để rollback.

## Kiểm chứng triển khai ngày 2026-10-15

- Suite chạy với `DATABASE_CLOUD=false`: 406 passed, 4 skipped; Ruff đạt.
- Supervisor chạy cả media adapter và worker trên host `19fa9d3b29ef`.
- Request ảnh thật tới Qwen trả 200; `ollama ps`: `qwen2.5vl:7b`, 100% GPU.
- Upload fixture qua Vercel → Render → SSH tạo `INC-A64CF2D6F122` trên GPU;
  SHA-256 của file nhận trùng file gốc.
- Diagnostics từ website đọc được `worker_host` và lịch sử pipeline trên GPU.
- `JOB-924E0D244846` đã được worker xử lý, dừng `INSUFFICIENT_EVIDENCE`
  vì thiếu đồng bộ thời gian CSV/video; không tự đoán offset.
- 17 video cũ đã trả `MEDIA_NOT_FOUND` trên Render trước khi chuyển. MP4/CSV
  của `INC-8870DFE54AE1` được di chuyển với SHA-256 giữ nguyên.
- Instance hiện không có host volume (`workspace_is_volume=false`): cần backup
  trước recycle/destroy. Kiểm tra trên không phải đánh giá chất lượng phát hiện incident.
