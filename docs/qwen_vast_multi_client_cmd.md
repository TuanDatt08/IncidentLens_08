# Gọi chung Qwen trên Vast.ai từ Windows CMD

## Trạng thái xác minh ngày 15/10/2026

- SSH: `ssh -p 28068 root@58.8.185.95`.
- Runtime: Ollama, lắng nghe `127.0.0.1:11434` trên máy GPU.
- Model: `qwen2.5vl:7b`, Q4_K_M, hỗ trợ completion và vision.
- GPU báo cáo: NVIDIA GeForce RTX 2080 Ti; tổng VRAM 22528 MiB.
- Runner đang chạy với `-np 1`, context 32768.
- Không có dịch vụ lắng nghe cổng 8080 khi kiểm tra.
- Smoke test trực tiếp qua SSH: POST `/api/chat` trả HTTP 200, `done=true`, nội dung `OK`, khoảng 0.36 giây. Đây là test văn bản, chưa chứng minh chất lượng vision hoặc tải đồng thời.

## 1. Chuẩn bị SSH key riêng trên máy khác

Mở Windows CMD:

```cmd
ssh -V
ssh-keygen -t ed25519 -f "%USERPROFILE%\.ssh\vast_qwen" -C "qwen-test-client"
type "%USERPROFILE%\.ssh\vast_qwen.pub"
```

Giữ private key `vast_qwen` trên máy đó. Gửi riêng nội dung public key `vast_qwen.pub` cho chủ instance. Chủ instance cần cấp public key này cho SSH của instance trước khi kết nối; có thể thêm vào `/root/.ssh/authorized_keys` qua phiên SSH đang hoạt động, giữ nguyên các key đã có. Không chia sẻ private key đang dùng trên máy chủ sở hữu.

Lưu ý: key đăng nhập root cấp quyền quản trị instance. Chỉ cấp cho người tin cậy; nếu chỉ muốn quyền gọi API, nên dùng tài khoản/key giới hạn forwarding hoặc API gateway xác thực.

## 2. Mở tunnel trong cửa sổ CMD thứ nhất

```cmd
ssh -i "%USERPROFILE%\.ssh\vast_qwen" -p 28068 -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:18081:127.0.0.1:11434 root@58.8.185.95
```

Lần đầu kết nối, đối chiếu host fingerprint với chủ instance trước khi chấp nhận. Nhập passphrase nếu key có đặt. Lệnh không hiện shell sau đăng nhập là bình thường vì có `-N`. Giữ cửa sổ mở; Ctrl+C đóng tunnel.

`18081` là cổng trên máy Windows. `11434` là cổng Ollama trên GPU. Mỗi máy mở tunnel riêng, có thể dùng cùng cổng local 18081. Không cần thông qua máy Windows của chủ instance.

## 3. Kiểm tra trong cửa sổ CMD thứ hai

```cmd
curl.exe --fail-with-body http://127.0.0.1:18081/api/tags
```

Kết quả phải chứa `qwen2.5vl:7b`.

Gọi inference văn bản; lệnh này dùng cú pháp escape của CMD:

```cmd
curl.exe --fail-with-body --max-time 180 http://127.0.0.1:18081/api/chat -H "Content-Type: application/json" -d "{\"model\":\"qwen2.5vl:7b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: OK\"}],\"stream\":false,\"options\":{\"num_predict\":16}}"
```

Đọc `message.content` và `done`. `stream:false` trả một JSON hoàn chỉnh.

## 4. Cấu hình ứng dụng

- Ollama base URL: `http://127.0.0.1:18081`.
- Ollama chat URL: `http://127.0.0.1:18081/api/chat`.
- Model: `qwen2.5vl:7b`.
- Client OpenAI-compatible dùng base URL `http://127.0.0.1:18081/v1`; cần kiểm tra tương thích riêng với client.

Gọi ảnh qua Ollama: đặt ảnh mã hóa base64 vào trường `messages[].images`, không truyền đường dẫn ảnh Windows cho server GPU.

## 5. Hai máy test cùng lúc

Mỗi máy thực hiện bước 2 và 3. Chỉ dùng một Ollama server/model hiện có. Runner hiện có một slot, nên request có thể chờ nhau. Chưa thay đổi concurrency hoặc restart dịch vụ. Nếu muốn inference song song thực sự, cần đo tải và VRAM trước khi điều chỉnh runtime.

## 6. Lỗi thường gặp

- `Permission denied (publickey)`: public key chưa được cấp hoặc `-i` trỏ sai private key.
- `Address already in use` / không bind được local port: đổi `18081` thành `18082` trong cả SSH và URL curl.
- `Connection refused` ở local: tunnel chưa chạy hoặc đã đóng.
- SSH báo `connect failed: Connection refused`: cổng dịch vụ trên GPU không còn hoạt động; kiểm tra lại Ollama 11434.
- Timeout khi inference: request có thể đang chờ máy khác; kiểm tra tải trước khi tăng timeout.
- IP hoặc SSH port đổi sau khi thay instance: lấy lại thông tin SSH từ Vast.ai.

## Tham khảo

- OpenSSH local forwarding: https://man.openbsd.org/ssh.1
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md

## 7. Quy trình từng bước cho hai người

### A. Người test: tạo key trên máy Windows B

Mở CMD bằng Win+R, gõ `cmd`, Enter. Chạy:

```cmd
ssh -V
if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"
ssh-keygen -t ed25519 -f "%USERPROFILE%\.ssh\vast_qwen" -C "qwen-client-B"
```

Nếu được hỏi passphrase, tự đặt rồi nhập lại. Khi nhập không hiện ký tự là bình thường. Nếu báo file đã tồn tại, không ghi đè key đang dùng; dùng key đó hoặc chọn tên file mới và sửa `-i` tương ứng.

```cmd
type "%USERPROFILE%\.ssh\vast_qwen.pub"
```

Gửi nguyên một dòng bắt đầu `ssh-ed25519` cho chủ instance. Không gửi file `vast_qwen` không có đuôi `.pub`.

### B. Chủ instance: cấp public key qua phiên SSH hiện có

Trên CMD máy A, đăng nhập:

```cmd
ssh -p 28068 root@58.8.185.95
```

Khi prompt chuyển thành Linux trên Vast.ai, chạy từng dòng:

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
cp -p /root/.ssh/authorized_keys /root/.ssh/authorized_keys.before-qwen-client-B
printf '\n' >> /root/.ssh/authorized_keys
cat >> /root/.ssh/authorized_keys
```

Lệnh `cp` áp dụng khi file đã tồn tại, như trường hợp máy A đã đăng nhập bằng key. Nếu backup đã có từ lần trước, chọn tên backup khác để giữ bản cũ.

Sau lệnh `cat`, terminal chờ nhập: dán đúng một dòng public key của máy B, Enter, rồi nhấn Ctrl+D trên dòng trống. Ctrl+D kết thúc nhập, không phải Ctrl+C. Không dán private key. Không dùng `>` thay cho `>>`, vì `>` xóa nội dung key cũ.

Tiếp tục trên Linux:

```bash
chmod 600 /root/.ssh/authorized_keys
ssh-keygen -lf /root/.ssh/authorized_keys
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Lệnh cuối cho fingerprint host ED25519 để máy B đối chiếu khi kết nối lần đầu. Giữ phiên máy A mở cho đến khi máy B đăng nhập thành công. Không cần restart SSH hay Qwen.

### C. Người test: mở tunnel trong CMD số 1

```cmd
ssh -i "%USERPROFILE%\.ssh\vast_qwen" -p 28068 -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:18081:127.0.0.1:11434 root@58.8.185.95
```

Đối chiếu fingerprint nếu được hỏi lần đầu; chỉ chấp nhận khi khớp. Nhập passphrase đã đặt. Sau đó cửa sổ đứng chờ là đúng. Không đóng cửa sổ này.

### D. Người test: gọi model trong CMD số 2

```cmd
curl.exe --fail-with-body http://127.0.0.1:18081/api/tags
```

Phải thấy model `qwen2.5vl:7b`. Sau đó:

```cmd
curl.exe --fail-with-body --max-time 180 http://127.0.0.1:18081/api/chat -H "Content-Type: application/json" -d "{\"model\":\"qwen2.5vl:7b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: OK\"}],\"stream\":false,\"options\":{\"num_predict\":16}}"
```

Kết quả có dạng dưới đây; nội dung thực tế có thể khác:

```json
{"model":"qwen2.5vl:7b","message":{"role":"assistant","content":"OK"},"done":true}
```

### E. Máy A cũng gọi bằng tunnel riêng

Máy A đã có SSH key hợp lệ, mở CMD riêng:

```cmd
ssh -p 28068 -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:18081:127.0.0.1:11434 root@58.8.185.95
```

Nếu máy A dùng key ở đường dẫn tùy chỉnh, thêm `-i "DUONG_DAN_PRIVATE_KEY_MAY_A"`. Sau đó chạy cùng lệnh curl ở CMD khác. Hai máy đều dùng localhost 18081 của chính máy mình; model chỉ chạy trên GPU. Máy A tắt máy không làm ngắt tunnel của máy B, miễn instance và Qwen vẫn chạy.

### F. Lần sử dụng tiếp theo

Không tạo lại key và không thêm public key lại. Chỉ mở tunnel (C), rồi gọi API (D). Dừng dùng bằng Ctrl+C tại cửa sổ tunnel. Chưa kiểm chứng kết nối từ máy B cho đến khi chính máy B chạy thành công.
