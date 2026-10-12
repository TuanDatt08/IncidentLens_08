# File dữ liệu và log khi chạy local

## Vì sao backend/data có log và script tạm?

Các lượt probe, benchmark, sửa kết quả và khởi động dịch vụ trước đây dùng lệnh
ad hoc, redirect stdout/stderr vào backend/data. Tên phiên như frontend-v3b làm
phát sinh nhiều file cùng chức năng. Chúng không phải dữ liệu đầu vào của detector.
Cleanup xoá script thử nghiệm và artifacts test riêng; giữ regression suite trong
tests vì suite dùng để kiểm tra code thực tế.

## Vị trí hiện hành

| Đường dẫn | Nội dung |
|---|---|
| backend/data/incidents/ | Upload, metadata, clip/frame evidence, request/response, draft theo incident |
| backend/data/incidentlens-ollama.db | Database SQLite hiện hành |
| backend/data/model/ và backend/data/runtime/ | Model và runtime portable cần thiết |
| backend/data/promt.txt | Prompt Stage A/B có thể chỉnh sửa |
| logs/runtime/ | stdout/stderr và PID của API, worker, frontend, Ollama; llama-server log/lock |
| logs/qwen/outputs.txt | Journal Qwen toàn cục, giữ lịch sử append-only |
| .ai-log/ | Log AI gửi Phoenix, không commit lên GitHub |

outputs.txt trong từng incident là output phân tích và được giữ cùng evidence.
Không coi MP4/CSV đã upload, report, model hay database là cache.

## Khởi động

Sau cài dependency, model, migration database và build frontend, từ root chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

Hoặc chạy riêng: `powershell -ExecutionPolicy Bypass -File .\start-local.ps1 -Services api`.
Launcher dùng tên log cố định trong logs/runtime, ghi PID, bỏ qua cổng đã có dịch vụ
và không tạo thêm worker nếu PID worker đã ghi còn sống. Khi dịch vụ được chạy từ
terminal khác, launcher sẽ dùng dịch vụ đó; muốn đổi redirect của dịch vụ cũ cần
dừng đúng process rồi chạy lại launcher. Thay đổi env cần restart API/worker.

Runtime llama-server dùng RUNTIME_LOG_DIR (mặc định ./logs/runtime); journal toàn
cục dùng QWEN_OUTPUTS_PATH (mặc định ./logs/qwen/outputs.txt). Launcher local Windows
luôn gom log các dịch vụ vào logs/runtime trong repo. Không redirect log mới vào
backend/data hoặc tạo script probe/sửa database trong đó.

Các backup cũ cần giữ được chuyển ra folder P-076-local-backups cạnh repo, không
đóng gói chung khi bàn giao ứng dụng. logs/ và .ai-log/ đã được Git ignore.
