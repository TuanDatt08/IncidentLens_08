# Frontend role

- Đọc [governance](../tools/AGENTS.md), task/SPEC/ADR và [API integration](docs/api-integration.md).
- Next.js routes/components, TypeScript types/services, state/UI helpers và role-specific docs ở đây.
- Giữ Impeccable + Ponytail khi sửa UI; kiểm responsive, keyboard, loading/empty/error/conflict, privacy và interaction. Không dùng UI role visibility thay server RBAC.
- Default mock mode; tắt mock để kiểm tích hợp thật. Không tuyên bố mock walkthrough là API/browser E2E.
- Time v1 là collision-relative + offset; time V2 là video_seconds, không silently reinterpret.
- Canonical requirements/tasks giữ trong `../tools`; không copy public contract vào types comments như một nguồn chuẩn mới.
- `npm run typecheck`, `npm run lint`, `npm run build`; browser E2E chỉ ghi verified sau khi chạy thật.
