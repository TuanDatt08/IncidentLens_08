# Docker Ollama Qwen 7B

Đã được người dùng yêu cầu triển khai. Giữ frontend và backend pipeline hiện hành.

1. Dockerfile tự build từ image Ollama public đã kiểm tra tag, build frontend standalone;
   cài Python/FFmpeg/nginx, không dùng incidentlens:unified-baseline.
2. Supervisor chạy một Ollama loopback, API, frontend, V1/V2 workers và gateway;
   migration SQLite lúc startup, kiểm tra model vision trước khi nhận job.
3. Compose tự tạo volume model và data/log; port 8089; override NVIDIA GPU riêng.
4. Dockerignore loại env/key, AI log, dữ liệu local, cache và node_modules khỏi image;
   include riêng prompt được chỉnh sửa.
5. Kiểm tra Compose, build mới, readiness, model vision, request ảnh thật và restart;
   ghi rõ giới hạn nếu Docker Engine hoặc tài nguyên máy chặn kiểm thử.

Kết quả: build thành công, 263 test pass, 5 deployment test trong image pass; health + request ảnh thật + restart persistence pass. Chi tiết tại docs/docker_qwen7b.md.
