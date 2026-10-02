# Frontend development

Từ root repository:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
```

Copy `.env.example` trong frontend sang `.env.local` nếu chưa có; giữ secret ngoài Git. `NEXT_PUBLIC_USE_MOCK_API=false` và base `http://localhost:8000/api/v1` để gọi API. Tên NEXT_PUBLIC luôn exposed cho browser, không đặt secret vào đó.

Backend API và worker phải chạy riêng theo [runbook](../../backend/docs/runbook.md). Default mock store phục vụ demo, không chứng minh live VLM hoặc authentication.

Kết quả kiểm tra của lượt audit lưu tại [repo audit](../../tools/docs/implementation-audit.md). Browser test cần video test đã được phép sử dụng, xác minh upload → job polling → evidence seek → edit/409 → submit/reject/approve và keyboard/mobile. Không gửi media nhạy cảm qua worker external chưa privacy.
