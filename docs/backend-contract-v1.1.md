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

Trong 13 route của v1.1, backend hiện phục vụ health, upload, list/detail incident, analyze, poll job, đọc report/evidence và audit. Bốn route `PATCH /incidents/{incident_id}/report`, `POST /report/submit`, `POST /report/approve`, `POST /report/reject` còn chờ chốt quy tắc chỉnh sửa, actor/role và reject reason. Nhánh `incident_detected=false` hiện kết thúc job với `INSUFFICIENT_EVIDENCE` cho đến khi xác nhận trạng thái terminal chính thức.

## Khác biệt với frontend ở `origin/frontend` (`ba1f099`)

| FE hiện tại | Cần đổi ở FE |
| --- | --- |
| `package_id`, `status` sau upload | `incident_id`, `processing_status`; `frontend/services/incident.service.ts`, `frontend/types/incident.ts`, `frontend/components/incidents/upload-form.tsx` |
| `listIncidents`, `getEvidence`, `getIncidentAudit` nhận mảng trực tiếp | Unwrap `{items, ...}` ở `frontend/services/incident.service.ts`, `evidence.service.ts`, `audit.service.ts`; đây là envelope backend tạm dùng cho phân trang |
| SSE `/incidents/{id}/progress` và bỏ `job_id` | Poll `GET /jobs/{job_id}` và lưu `job_id` để reload không POST analyze lần nữa; `frontend/services/analysis.service.ts`, `frontend/components/incidents/processing-view.tsx` |
| `VALIDATING`, `EXTRACTING`, `SYNCHRONIZING`, `PASS_1`, `PASS_2` nằm trong `ProcessingStatus` của Incident | Đọc `processing_status` của Incident riêng với job `status`, `pass`, `progress`; chuyển job sang nhãn UI trong `frontend/types/incident.ts`, `frontend/types/processing.ts`, `processing-view.tsx` |
| Một `IncidentDraft` có `summary_text`, `start_sec` và `confidence` | Tách factual `IncidentRecord` khỏi `AnalysisReport`; dùng `summary`, `incident_window`, `review_status`; `frontend/types/incident.ts`, `frontend/services/report.service.ts`, các component review |
| Evidence `timestamp_sec` và `video_url` trực tiếp | Dùng `time_range_s`, URI tương đối và cơ chế media được chốt; cộng `video_metadata.collision_offset_in_video_s` khi seek MP4; `frontend/types/evidence.ts`, `frontend/components/review/evidence-section.tsx`, `video-player.tsx` |
| Lỗi `detail/message` | Đọc `error.code/message/details`; `frontend/lib/api-client.ts` |
| Mock là mặc định | Đặt `NEXT_PUBLIC_USE_MOCK_API=false` và base URL thật trong `frontend/.env.local` khi tích hợp |

## NEED_CONFIRMATION

Final v1.1 chưa chốt PATCH whitelist, reject reason bắt buộc hay không, auth/role Engineer và Reviewer, retention video bulky, cách CARLA nạp `IncidentRecord`, và ETag cho polling. Để FE xem/tua evidence còn cần chọn media route hay signed URL và cung cấp vị trí va chạm trong MP4 để đổi thời gian tương đối sang video seek time. Response list/audit, cách xử lý `incident_detected=false`, và quy tắc edit report đã REJECTED cũng cần chốt trước khi coi là contract ổn định.
