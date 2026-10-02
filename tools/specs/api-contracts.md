# API boundaries

V1.1 ở [contract hiện có](../../api/docs/backend-contract-v1.1.md), base `/api/v1`. Giữ nguyên enum, error envelope và collision-relative seconds. Không nhét V2 vào response v1.

V2 namespace `/api/v2`, đích thiết kế chưa có route runtime. RAV-016 phải xuất OpenAPI và fixture request/response trước khi FE migration. Một recording có nhiều candidate/report; dùng recording_id, candidate_id, report_id rõ ràng, không thay nghĩa incident_id v1.

| Proposed V2 operation | Contract behavior |
| --- | --- |
| POST /uploads | Tạo session: filename, bytes, media_type, sha256; trả upload_id, expires_at, part_size, các URL có hạn |
| GET /uploads/{upload_id} | Trả parts đã xác minh để resume |
| POST /uploads/{upload_id}/complete | Part list/checksum; replay trả cùng recording, không tạo trùng |
| POST /recordings/{recording_id}/analyze | Idempotency-Key; 202 job_id; provider profile phải được policy cho phép |
| GET /jobs/{job_id} | status, stage, progress, coverage, budget, error/result refs |
| GET /recordings/{recording_id}/candidates | items, cursor, reason, window, analysis_state |
| GET /reports/{report_id} | Analysis V2 + envelope version/evidence links |
| PATCH /reports/{report_id} | expected_version; allowlisted fields; 409 stale |
| POST /reports/{report_id}/{submit,approve,reject,reopen} | expected_version, reject reason; RBAC và snapshot transaction |
| GET /recordings/{recording_id}/evidence/{evidence_id}/media | Authorized masked asset; Range/streaming |

Error envelope `{error:{code,message,details}}`; 401 unauthenticated, 403 unauthorized/privacy blocked, 404 scope-safe not found, 409 stale/conflicting state, 413 too large, 422 invalid schema/time/evidence, 429 budget/rate, 503 retryable dependency. Không lộ raw path/secret. List dùng `{items,next_cursor}`; time V2 là video_seconds.

API layer kiểm tra domain validator ở cả generation, edit và approval. Khả năng APPROVED không thuộc provider output. Deprecation v1 cần thông báo và regression sau khi FE đã migrate; chưa ấn định ngày xóa.
