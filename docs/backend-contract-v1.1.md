# RAV18 backend contract v1.1

Nguồn chuẩn: [MVP API + Database Architecture v1.1](https://docs.google.com/document/d/1ZNoL5MpBbeBOGUZ5PlP0ocf1gKA2F56hZqpTALmZaos/edit?tab=t.dy24xd9z1863). Phần v1.0 được nối ở cuối Google Doc là lịch sử, không phải contract hiện hành.

## Public API

Base URL: `/api/v1`. Public ID duy nhất là `incident_id`. Upload nhận `video` MP4 bắt buộc và `log` CSV tùy chọn. Upload trả 201 và `processing_status: "READY"`; analyze trả 202 cùng `job_id`; FE poll `GET /jobs/{job_id}` cho tới `succeeded`, `failed` hoặc `cancelled`.

Ba nhóm trạng thái độc lập:

- Incident: `UPLOADED | READY | PROCESSING | COMPLETED | FAILED`.
- Job: `queued | running | succeeded | failed | cancelled`.
- AnalysisReport: `DRAFT | IN_REVIEW | APPROVED | REJECTED`.

`IncidentRecord` chứa dữ liệu factual của generator. `AnalysisReport` chứa kết quả VLM và chỉnh sửa của Engineer; không sao chép `collision`/`ego` vào report. `Evidence.time_range_s` và `incident_window` là giây tương đối so với va chạm, có thể âm. `Evidence.uri` là đường dẫn tương đối trong storage, không phải URL public.

Lỗi trả `{ "error": { "code": "...", "message": "...", "details": null } }`. Job có `pass: null` khi queued; `progress.total` có thể null. Chỉ job succeeded có `result_uri`, chỉ job failed có `error`.

Backend phục vụ đủ 13 route của v1.1. Theo quyết định MVP ngày 2026-09-23, `PATCH /incidents/{incident_id}/report` nhận `version` và chỉ sửa `summary`, `timeline`, `key_factors`, `observations`, `unknowns`. Edit tạo snapshot `report_versions` mới; version cũ trả 409. Submit chuyển `DRAFT → IN_REVIEW`; approve/reject chỉ nhận `IN_REVIEW`; reject bắt buộc `reason` không rỗng và lưu reason trong audit. `REJECTED` giữ nguyên trạng thái và chưa cho edit lại trong MVP. Response của ba action là `{incident_id,status,version,rejection_reason}`.

Khi Pass 1 không phát hiện incident, job vẫn `succeeded` với `pass=1`, Incident `COMPLETED`, AnalysisReport `incident_detected=false`, `incident_window=null`, `evidence_ids=[]`, `review_status=DRAFT`; `GET /evidence` trả `items=[]`. FE phải xem đây là một kết quả hoàn tất, không phải lỗi VLM.

Hai media route bổ sung cho demo local: `GET /incidents/{incident_id}/video` và `GET /incidents/{incident_id}/evidence/{evidence_id}/media`. Chúng kiểm tra incident/evidence thuộc nhau và URI nằm trong storage của incident; FileResponse hỗ trợ HTTP Range để tua video. Vì identity provider chưa chốt, media và mọi thao tác ghi review trả `PERMISSION_DENIED` (403) khi `APP_ENV=production`. Trong `development`/`test`, actor audit là `demo-engineer` hoặc `demo-reviewer` và chưa phân quyền người dùng thật.

## Khác biệt với frontend ở `origin/frontend` (`ba1f099`)

| FE hiện tại | Cần đổi ở FE |
| --- | --- |
| `package_id`, `status` sau upload | `incident_id`, `processing_status`; `frontend/services/incident.service.ts`, `frontend/types/incident.ts`, `frontend/components/incidents/upload-form.tsx` |
| `listIncidents`, `getEvidence`, `getIncidentAudit` nhận mảng trực tiếp | Unwrap `{items, ...}` ở `frontend/services/incident.service.ts`, `evidence.service.ts`, `audit.service.ts`; đây là envelope backend tạm dùng cho phân trang |
| SSE `/incidents/{id}/progress` và bỏ `job_id` | Poll `GET /jobs/{job_id}` và lưu `job_id` để reload không POST analyze lần nữa; `frontend/services/analysis.service.ts`, `frontend/components/incidents/processing-view.tsx` |
| `VALIDATING`, `EXTRACTING`, `SYNCHRONIZING`, `PASS_1`, `PASS_2` nằm trong `ProcessingStatus` của Incident | Đọc `processing_status` của Incident riêng với job `status`, `pass`, `progress`; chuyển job sang nhãn UI trong `frontend/types/incident.ts`, `frontend/types/processing.ts`, `processing-view.tsx` |
| Một `IncidentDraft` có `summary_text`, `start_sec` và `confidence` | Tách factual `IncidentRecord` khỏi `AnalysisReport`; dùng `summary`, `incident_window`, `review_status`; `frontend/types/incident.ts`, `frontend/services/report.service.ts`, các component review |
| Evidence `timestamp_sec` và `video_url` trực tiếp | Dùng `time_range_s`; gọi media route bằng `incident_id`/`evidence_id`, không dùng `uri` làm URL; cộng `video_metadata.collision_offset_in_video_s` khi seek MP4; `frontend/types/evidence.ts`, `frontend/components/review/evidence-section.tsx`, `video-player.tsx` |
| FE chưa tạo URL media từ ID | Thêm helper trong `frontend/services/incident.service.ts` cho `/incidents/{id}/video` và `frontend/services/evidence.service.ts` cho `/incidents/{id}/evidence/{evidence_id}/media`; truyền URL vào `video-player.tsx`/`evidence-section.tsx` để phát media và tua bằng Range |
| PATCH đang gửi `summary_text` và không gửi `version` | Gửi `{version, summary, timeline?, key_factors?, observations?, unknowns?}`; lấy `version` từ GET report và xử lý 409; `frontend/types/report.ts`, `frontend/services/report.service.ts`, `frontend/components/review/report-editor.tsx` |
| Màn hình processing coi mọi job `succeeded` là đã thấy incident | Sau khi poll thành công, đọc report và hiển thị trường hợp `incident_detected=false` với evidence rỗng; `frontend/components/incidents/processing-view.tsx`, `frontend/components/review/review-workspace.tsx` |
| Lỗi `detail/message` | Đọc `error.code/message/details`; `frontend/lib/api-client.ts` |
| Mock là mặc định | Đặt `NEXT_PUBLIC_USE_MOCK_API=false` và base URL thật trong `frontend/.env.local` khi tích hợp |

## NEED_CONFIRMATION

Final v1.1 vẫn chưa chốt auth/role Engineer và Reviewer, retention video bulky, cách CARLA nạp `IncidentRecord`, và ETag cho polling. Trước production cần identity provider và phân quyền thật cho media/review; hiện route 403 trong production. Response list/audit vẫn là envelope backend tạm dùng; nhóm FE cần chốt filter/pagination. Nguồn chính xác cho `collision_offset_in_video_s` từ generator cần chốt để Pass 1 không phải suy ra từ frame. Quy tắc mở lại report `REJECTED` chưa được duyệt; MVP coi trạng thái này là terminal.
