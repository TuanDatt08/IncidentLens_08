# Active API routes

Entry point [main.py](../main.py); base `/api/v1`. Namespace version v1 hiện thực contract tài liệu v1.1; app metadata vẫn version `1.0.0`, không suy rằng có `/api/v1.1` hoặc V2.

| Method/path | Module | Behavior |
| --- | --- | --- |
| POST /incidents/upload | [incidents](../incidents.py) | Multipart MP4 + optional CSV, 201 READY |
| GET /incidents | incidents | `{items,total,limit,offset}` |
| GET /incidents/{id} | incidents | Factual record + media/telemetry metadata |
| POST /incidents/{id}/analyze | [jobs](../jobs.py) | 202 queued job_id, không chạy model trong request |
| GET /jobs/{job_id} | jobs | Job status/pass/progress/result_uri/error |
| GET/PATCH /incidents/{id}/report | [reports](../reports.py) | Read hoặc edit DRAFT bằng current version |
| POST /incidents/{id}/report/submit | reports | DRAFT → IN_REVIEW |
| POST /incidents/{id}/report/approve | reports | IN_REVIEW → APPROVED |
| POST /incidents/{id}/report/reject | reports | IN_REVIEW → REJECTED, nonblank reason |
| GET /incidents/{id}/evidence | [evidence](../evidence.py) | `{items}` scoped to incident |
| GET /incidents/{id}/audit | [audit](../audit.py) | `{items}` audit events |
| GET /incidents/{id}/video | [media](../media.py) | FileResponse có Range, local demo raw source |
| GET /incidents/{id}/evidence/{evidence_id}/media | media | Scoped asset, Range và path guard |

Health: `/health` và `/api/v1/health`. Error envelope `{error:{code,message,details}}`. [errors.py](../errors.py) dùng domain ApiError, chuyển validation/HTTP/internal error thành envelope. OpenAPI qua `/docs`; list/evidence/audit còn response dict, chưa typed toàn bộ endpoints.

Review/media production trả 403 qua demo guard; các route còn lại chưa authentication/RBAC đầy đủ. API enum cancelled có nhưng chưa có cancel endpoint. REJECTED terminal ở v1.1; không thêm reopen như tài liệu V2 nếu chưa migration.

Frontend hiện đã tích hợp source v1.1: poll job_id, unwrap items, PATCH version và seek relative+offset. Đối chiếu [frontend integration](../../frontend/docs/api-integration.md); browser/network E2E cần kiểm riêng.
