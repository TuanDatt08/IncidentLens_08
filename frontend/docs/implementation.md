# Frontend implementation và gaps

Next.js App Router: `/incidents`, `/incidents/new`, `/incidents/[id]/processing`, `/incidents/[id]`. `services/` chọn mock/API; `types/` model v1; `lib/` config/client/time; `components/` upload/progress/review/video/evidence/audit.

Đã có loading/error, queued/running/failure/cancelled display, fetch report/evidence, no-incident successful result, DRAFT editor/version conflict, submit/approve/reject confirmations, read-only approved/rejected, responsive utility classes và evidence seek. Audit component/service có nhưng chưa tích hợp đúng shape/render. [API integration](api-integration.md) mô tả source cụ thể.

## Chưa đạt SPEC V2

Auth và role-aware workflow; reopen REJECTED; preserve structured claims/evidence khi edit; multipart/resume/checksum; multi-candidate/UNANALYZED/coverage; masked media gate; v2 types/client; browser E2E, responsive và keyboard verification.

`report-editor.tsx` serialize object thành JSON text rồi save lại string list khi sửa. Điều này có thể làm mất structured claim; V2 cần editor có typed fields/evidence, không dùng tuyến text này để chứng minh evidence fidelity.

## UI observations từ source

Theo tiêu chí Impeccable, chưa chấm điểm visual/contrast/performance vì chưa browser/screenshot test. Các vấn đề source thấy được:

- [workflow-actions](../components/review/workflow-actions.tsx): modal có role/dialog và aria-modal, chưa focus trap/restore/Escape/accessible dialog title wiring.
- [video-player](../components/review/video-player.tsx): overlay play button chỉ icon chưa accessible name; custom controls cần kiểm keyboard/focus/video loading-error.
- Icon close control có h-8/w-8; kiểm touch target thực tế trên mobile trong RAV-017.
- Không đánh dấu responsive/a11y “đạt” chỉ vì có `sm:` classes/aria attributes; contrast/focus/tab order/reduced motion cần browser verification.

Các acceptance cụ thể bổ sung vào [RAV-017](../../tools/tasks/RAV-017-frontend-v2-integration.md); chưa sửa giao diện trong lượt tổ chức tài liệu này.
