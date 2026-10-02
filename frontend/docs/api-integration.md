# Frontend ↔ API v1.1

Nguồn public contract: [api/docs/backend-contract-v1.1.md](../../api/docs/backend-contract-v1.1.md). Hiện source đã giải quyết phần lớn bảng migration cũ; không tiếp tục ghi “FE dùng SSE/contract cũ” như hiện trạng.

| Contract | Source frontend đã có |
| --- | --- |
| incident_id + processing_status sau upload | [incident.service.ts](../services/incident.service.ts), [incident types](../types/incident.ts) |
| items envelopes | Incident list và evidence đã xử lý; audit service còn mismatch, xem bên dưới |
| POST analyze trả job_id; polling GET jobs | [analysis.service.ts](../services/analysis.service.ts), [processing-view](../components/incidents/processing-view.tsx) |
| Reload không tạo analysis khi job_id còn sessionStorage | getStoredJobId và pending promise dedup trong analysis service |
| Report PATCH version; 409 current_version | [report.service.ts](../services/report.service.ts), [report-editor](../components/review/report-editor.tsx) |
| Media URL lấy từ IDs, không dùng storage uri | [evidence.service.ts](../services/evidence.service.ts), incident service |
| Seek evidence/video marker | [video-time.ts](../lib/video-time.ts), [review-workspace](../components/review/review-workspace.tsx) |
| Error.code/message/details | [api-client.ts](../lib/api-client.ts) |

Time v1: `videoTime = collision_offset_in_video_s + relativeTime`; guard missing/nonfinite offset, clamp duration. Kết quả không detected được load như successful report, không như failed job. Processing progress hiện suy từ pass1/pass2, chưa stage/coverage V2.

## Giới hạn

SessionStorage chỉ trong phiên tab; tab mới/device khác chưa discover active job, có thể POST analyze và nhận 409. TypeScript casts không runtime-validate payload. Fetch chưa integrated login credential/token handling. Mock mode default nên phải kiểm cả mode API khi release. Chưa resumable multipart upload, multi-candidate list, MASKED gate hoặc V2 adapter. Submit/approve/reject visibility theo report state, chưa principal role.

`audit.service.ts` vẫn khai báo mảng AuditEvent trực tiếp, trong khi API trả `{incident_id, items}`. `types/audit.ts` còn yêu cầu event_id/role/incident_id không có ở event API v1 hiện tại. `AuditSection` chưa được import/render vào `review-workspace.tsx`. Đây là integration gap thật, không đánh dấu audit UI DONE từ việc component tồn tại.

Kiểm v1 bằng API fixture/E2E và browser thật; chỉ typecheck/build không chứng minh endpoint chạy đúng. Khi V2 triển khai, migration theo [RAV-017](../../tools/tasks/RAV-017-frontend-v2-integration.md), giữ v1 regression.
