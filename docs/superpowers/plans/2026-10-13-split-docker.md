# Tách Docker APP / AI

Thiết kế đã được người dùng chọn: APP chứa FE, API, worker; AI chứa Ollama và model Qwen. PostgreSQL dùng Neon từ `.env`; media/artifacts vẫn dùng volume APP. Giữ nguyên UI và gói Docker cũ.

1. Thêm kiểm tra image APP không phụ thuộc Ollama và Compose dùng Neon, network chung, volume riêng.
2. Tái sử dụng supervisor, healthcheck, worker và Nginx hiện có; build APP trên Python thay vì Ollama.
3. Thêm Compose APP, AI và GPU override; model được tải bằng lệnh riêng.
4. Kiểm tra pytest, Compose render không lộ secret, build APP; thử Neon chỉ nếu có URL cấu hình.
5. Viết lệnh vận hành, di chuyển và báo rõ những phần chưa chạy được.
