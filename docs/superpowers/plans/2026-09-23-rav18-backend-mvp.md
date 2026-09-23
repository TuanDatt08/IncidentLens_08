# RAV18 Backend MVP v1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Xây backend cho luồng Upload → Analyze Job → Poll → AnalysisReport/Evidence → Engineer edit → Reviewer approve/reject → Audit theo bản final v1.1.

**Architecture:** Giữ package src/ của repo hiện tại. FastAPI xử lý HTTP và trạng thái; PostgreSQL lưu sáu bảng metadata/report/audit; API và worker riêng dùng chung storage local trong demo. ProcessingService điều phối VLM Pass 1, chuẩn bị clip/keyframes + telemetry window, rồi Pass 2; chỉ kết quả hợp lệ mới được persist.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, FFmpeg/ffprobe, pytest, Docker Compose. Không cần LangGraph cho pipeline hai bước tuyến tính.

**Spec:** [RAV-18 INCIDENTLENS — MVP API + Database Architecture v1.1](https://docs.google.com/document/d/1ZNoL5MpBbeBOGUZ5PlP0ocf1gKA2F56hZqpTALmZaos/edit?tab=t.dy24xd9z1863). Tài liệu ARCHITECTURE.md trong repo là bản cũ; đồng bộ nó sau khi contract v1.1 được phản ánh trong test.

## Global Constraints

- Base URL /api/v1. Public ID duy nhất là incident_id; package_id chỉ là tương thích nội bộ nếu cần.
- Ba nhóm trạng thái độc lập: Incident.processing_status = UPLOADED | READY | PROCESSING | COMPLETED | FAILED; Job.status = queued | running | succeeded | failed | cancelled; AnalysisReport.review_status = DRAFT | IN_REVIEW | APPROVED | REJECTED.
- Upload nhận video MP4 bắt buộc và telemetry CSV tùy chọn; trả 201, incident_id và processing_status READY. Không chạy VLM trong request upload hoặc analyze.
- Telemetry CSV của Đạt dùng sec_from_incident làm timeline chính; sim_time_s và wall_clock_ts phục vụ mapping/chẩn đoán. Không lưu từng row CSV trong DB.
- IncidentRecord là dữ liệu factual từ CARLA/generator hoặc input; AnalysisReport là kết quả VLM + Engineer edit. Không trộn các trường collision/ego vào report.
- Evidence dùng kind, URI tương đối, SHA-256, time_range_s; mốc 0 của time_range_s là va chạm. Report tham chiếu bằng evidence_ids.
- Job trả pass=null khi queued, progress.total có thể null, result_uri chỉ có khi succeeded và error chỉ có khi failed. FE dừng poll khi terminal.
- AI/VLM chỉ phân tích, không duyệt. File nhị phân ở storage; PostgreSQL chỉ chứa metadata, JSONB, trạng thái và audit.
- Bản final chưa chốt PATCH whitelist, reject reason, auth/role trong MVP, retention, cách CARLA gửi IncidentRecord và ETag. Không coi các mục này là đã được phê duyệt.

## Review bản final và thay đổi so với kế hoạch trước

1. Bản final đã chốt incident_id, trạng thái review viết hoa và endpoint GET /incidents, GET /incidents/{id}/audit. Xóa toàn bộ giả định cũ về public package_id, status reviewed chữ thường và API chỉ có 11 route.
2. IncidentDraft v1.0 trước đây được tách thành IncidentRecord và AnalysisReport. Contract validation phải kiểm tra hai schema riêng; PATCH chỉ sửa AnalysisReport, không sửa factual IncidentRecord.
3. Sáu bảng được chốt là incidents, jobs, evidences, analysis_reports, report_versions, audit_events. Migration và tests phải theo đúng quan hệ 1 Incident → N Job/N Evidence/1 Report/N Audit, 1 Report → N Version.
4. CSV canonical được xác định rõ. Cần kiểm thử sec_from_incident, sim_time_s, wall_clock_ts, số hàng, start/end và truy vấn một telemetry window; không dùng tên timestamp cũ làm mặc định.
5. Vẫn thiếu quy tắc chuyển mốc relative sang thời gian chạy của video. Không thể tua đến evidence [-2.5, 1.5] nếu không biết vị trí collision trong MP4. Cần metadata collision_offset_in_video_s hoặc một mapping tương đương từ generator.
6. Bản final không có endpoint lấy video/evidence file dù FE cần xem evidence. Cần FE/BE chọn cơ chế truy cập media có quyền trước khi hoàn thiện màn hình review; đừng trả đường dẫn storage như URL public.
7. Jobs table trong spec chưa có attempt/lease. Worker bền qua restart cần hai cột nội bộ này hoặc cơ chế queue tương đương; đề xuất bổ sung attempt và lease_until vào cùng bảng jobs, không tạo bảng thứ bảy.
8. Spec cho phép incident_detected=false nhưng chưa quy định report/evidence/result_uri khi không phát hiện incident. Freeze nhánh này trước khi viết UI terminal state.
9. Repo hiện vẫn là template chatbot: src/api/routes.py chỉ có /chat, /status; Docker Compose chỉ có backend; requirements chưa bật DB. Frontend có thể ở repo khác nên không đánh giá tiến độ FE từ repo này.

## Contract gate: quyết định cần chốt với FE/BE/VLM/PO

- PATCH whitelist: đề xuất summary, timeline, key_factors, observations, unknowns, incident_type và incident_window nếu Engineer có thể kiểm chứng; cấm sửa evidence_id/hash, system/model metadata và IncidentRecord. FE/PO duyệt danh sách cuối.
- Reject reason: đề xuất bắt buộc, lưu trong audit_events.metadata; PO quyết định.
- Auth/role: nếu demo local chưa có auth, chỉ dùng user giả qua dependency ở môi trường test/development; không đưa API ra internet với cơ chế này. PO/BE chọn identity provider hoặc phương án xác thực thật.
- Generator ingress: CARLA gửi IncidentRecord bằng API push, folder scan hay queue? Chưa chọn nên Task 2 chỉ thiết kế importer interface, không xây cả ba cơ chế.
- Media access: FE cần xem video/clip/frame bằng route có kiểm tra quyền hoặc signed URL thời hạn ngắn. Chọn một cách và xác định contract trước Gate C.
- Relative time: generator hoặc upload metadata phải cung cấp vị trí va chạm trong MP4; sec_from_incident=0 trong CSV chưa tự cho biết frame tương ứng.
- No incident: đề xuất job succeeded, AnalysisReport.incident_detected=false, evidence_ids rỗng, result_uri trỏ report API; cần FE/VLM/PO xác nhận.
- List/audit: bản final chưa ghi query/response. Đề xuất GET /incidents trả danh sách phân trang theo created_at mới nhất; GET /audit trả events theo created_at tăng dần. Chốt field/filter với FE.
- PATCH concurrency: đề xuất report version integer và optimistic check để hai Engineer không ghi đè nhau; bản final đã có report_versions nhưng chưa mô tả request version.
- Retention bulky video và ETag/If-None-Match là quyết định vận hành; ETag có thể làm sau core flow nếu FE polling 2–10 giây hoạt động ổn.

## File map

| File | Trách nhiệm |
| --- | --- |
| src/main.py, src/config.py | Cấu hình app, đăng ký router, DB/storage/worker settings |
| src/api/health.py, incidents.py, jobs.py, reports.py, evidence.py, audit.py | 13 endpoint trong spec v1.1; router không chứa FFmpeg/VLM |
| src/models/contracts.py | Pydantic: IncidentRecord, AnalysisReport, Evidence, Job, lỗi, request/response |
| src/models/tables.py, src/db.py, alembic/versions/* | Sáu bảng, index, session và migration |
| src/services/storage.py, video.py, telemetry.py | Lưu file, ffprobe/extract, parse/filter CSV |
| src/services/incidents.py, jobs.py, processing.py, evidence.py, reports.py, audit.py | Nghiệp vụ, chuyển trạng thái và persist |
| src/services/vlm.py, src/worker.py | Adapter Pass 1/2 và worker lấy job PostgreSQL |
| tests/test_api/*, tests/test_services/*, tests/test_worker.py, tests/test_e2e.py | Contract, route, telemetry, persistence, retry, review, end-to-end |
| requirements.txt, docker-compose.yml, .env.example | API + worker + PostgreSQL + shared storage demo |

---

### Task 1: Contract v1.1 và kiểm tra khác biệt

**Files:** Create src/models/contracts.py, src/api/health.py, tests/test_api/test_contracts.py, docs/backend-contract-v1.1.md; modify src/main.py, ARCHITECTURE.md, docs/architecture_diagram.md.

**Interfaces:** Pydantic models IncidentRecordV1, AnalysisReportV1, EvidenceV1, LocalizationResult, AnalysisResult, JobResponse, ErrorResponse. IncidentRecordV1 chấp nhận field mới trong source/collision/ego/quality; scenario là chuỗi mở, template là rear_end | pedestrian.

- [ ] Viết test GET /api/v1/health và ba nhóm status riêng, public incident_id, IncidentRecord/AnalysisReport không lẫn field, unknown field của IncidentRecord không gây lỗi và JobResponse chấp nhận progress.total=null. Giữ GET /health hiện tại làm alias trong giai đoạn chuyển tiếp.

      assert IncidentRecordV1.model_validate(record).scenario == "jaywalk_occluded"
      assert AnalysisReportV1.model_validate(report).review_status == "DRAFT"
      assert JobResponse.model_validate(queued_job).progress.total is None

- [ ] Chạy python -m pytest tests/test_api/test_contracts.py -q, xác nhận lỗi vì model chưa tồn tại.
- [ ] Implement Pydantic models với validator URI tương đối, SHA-256 lowercase 64 hex, evidence time_start <= time_end; không tự ép thời gian âm thành 0.
- [ ] Chạy lại test, xem OpenAPI của các route mới; ghi ví dụ request/response đúng v1.1 trong docs/backend-contract-v1.1.md.
- [ ] Đồng bộ ARCHITECTURE.md và diagram: sửa endpoint, 3 trạng thái, 6 bảng, storage local/demo, dữ liệu IncidentRecord vs AnalysisReport.

### Task 2: PostgreSQL và sáu bảng

**Files:** Create src/db.py, src/models/tables.py, alembic.ini, alembic/env.py, alembic/versions/20260923_rav18_initial.py, tests/test_db.py; modify requirements.txt, src/config.py, docker-compose.yml, .env.example.

**Interfaces:** SQLAlchemy tables incidents, jobs, evidences, analysis_reports, report_versions, audit_events; FK và unique constraints đúng spec. Internal jobs fields attempt, lease_until để recovery. Partial unique index ngăn hai job queued/running cho cùng incident.

- [ ] Viết test migration tạo đúng sáu bảng, FK/unique/index và JSONB; test hai job active cùng incident bị từ chối.

      session.add_all([make_job(incident, "queued"), make_job(incident, "queued")])
      with pytest.raises(IntegrityError):
          session.commit()

- [ ] Chạy test để thấy thiếu migration.
- [ ] Bật SQLAlchemy 2, Alembic và PostgreSQL driver; tạo migration có upgrade/downgrade, không dùng create_all trong startup.
- [ ] Thêm postgres và worker vào Compose; cùng mount storage local, nhưng API/worker chạy hai process. Không đưa MP4/CSV vào DB.
- [ ] Chạy migration trên DB sạch, test rollback migration trên DB test, rồi python -m pytest tests/test_db.py -q.

### Task 3: Upload, IncidentRecord và GET/list

**Files:** Create src/api/incidents.py, src/services/storage.py, src/services/video.py, src/services/incidents.py, tests/test_api/test_incidents.py; modify src/main.py.

**Interfaces:** POST /api/v1/incidents/upload nhận video MP4 và log CSV optional, trả 201 incident_id/READY/sync_offset=null/frame_count=0/video_metadata. GET /api/v1/incidents/{incident_id} trả metadata + factual IncidentRecord nếu có. GET /api/v1/incidents trả danh sách cho dashboard.

- [ ] Test upload MP4 hợp lệ tạo Incident READY; file lỗi/quá cỡ/không phải MP4 bị từ chối; GET/list trả incident_id và không trả absolute path.

      response = await client.post("/api/v1/incidents/upload", files={"video": ("clip.mp4", valid_mp4, "video/mp4")})
      assert response.status_code == 201
      assert response.json()["processing_status"] == "READY"
      assert response.json()["incident_id"].startswith("INC-")

- [ ] Chạy test để xác nhận route chưa có.
- [ ] Stream file vào storage theo incidents/{incident_id}/source, kiểm tra kích thước, container bằng ffprobe, đọc duration/fps/width/height; lưu URI tương đối trong incidents.
- [ ] Tạo importer interface nhận factual IncidentRecord từ generator khi đường ingress được chốt; upload thủ công vẫn hợp lệ khi scenario/template/source chưa có.
- [ ] Test GET/list với incident có và không có IncidentRecord; phân trang theo contract đã chốt; xác nhận upload không tự chạy VLM.

### Task 4: TelemetryService theo CSV canonical

**Files:** Create src/services/telemetry.py, tests/test_services/test_telemetry.py; modify src/api/incidents.py, src/services/incidents.py.

**Interfaces:** parse_telemetry(csv_path) trả row_count, time_column="sec_from_incident", time_reference="incident_relative", start_s, end_s. select_window(csv_path, start_s, end_s) trả rows trong khoảng tương đối. sim_time_s và wall_clock_ts được giữ cho diagnostic/mapping.

- [ ] Test CSV mẫu có sec_from_incident=-5..5, sim_time_s, wall_clock_ts; metadata đúng; select_window(-1,1) chỉ trả rows đúng khoảng.

      metadata = parse_telemetry(csv_path)
      assert metadata.time_column == "sec_from_incident"
      assert metadata.time_reference == "incident_relative"
      assert all(-1 <= row.sec_from_incident <= 1 for row in select_window(csv_path, -1, 1))

- [ ] Chạy test để thấy service chưa có.
- [ ] Parse CSV theo header canonical; từ chối thiếu sec_from_incident, giá trị thời gian không hữu hạn hoặc không tăng; không nạp toàn bộ CSV vào PostgreSQL.
- [ ] Ghi telemetry_metadata JSONB trong incident; upload không có CSV trả metadata=null.
- [ ] Chạy tests telemetry và API upload cho trường hợp có/không có CSV.

### Task 5: Analyze Job và polling

**Files:** Create src/api/jobs.py, src/services/jobs.py, src/worker.py, tests/test_api/test_jobs.py, tests/test_worker.py; modify src/api/incidents.py.

**Interfaces:** POST /api/v1/incidents/{incident_id}/analyze trả 202 job_id ngay; GET /api/v1/jobs/{job_id} trả status/pass/progress/updated_at/result_uri/error. claim_job() dùng PostgreSQL FOR UPDATE SKIP LOCKED, lease và giới hạn retry.

- [ ] Test analyze READY trả queued, analyze lặp khi active trả 409, missing job trả 404, pass=null lúc queued, progress.total=null hợp lệ.

      response = await client.post(f"/api/v1/incidents/{incident_id}/analyze")
      assert response.status_code == 202
      assert response.json()["status"] == "queued"
      assert (await client.post(f"/api/v1/incidents/{incident_id}/analyze")).status_code == 409

- [ ] Chạy test đỏ.
- [ ] Tạo job DB trong request, không gọi VLM; worker claim/update heartbeat và progress, phục hồi job có lease hết hạn hoặc đánh failed sau giới hạn retry.
- [ ] Test hai worker không claim cùng job; restart worker giữ job và không tạo kết quả trùng; terminal state ngừng thay đổi.
- [ ] Chạy tests job/worker; đo GET /jobs đáp ứng polling 2–10 giây mà không cần SSE. ETag làm riêng nếu nhóm chốt.

### Task 6: ProcessingService và VLM Pass 1/2

**Files:** Create src/services/processing.py, src/services/vlm.py, tests/test_services/test_processing.py; modify src/worker.py.

**Interfaces:** pass1(video, metadata) -> LocalizationResult; prepare_pass2(window, video, CSV) -> clips/keyframes/telemetry rows; pass2(prepared) -> AnalysisResult. VLM adapter inject được fake trong tests.

- [ ] Test Pass 1 trả candidate_start/critical_time/candidate_end/evidence_timestamps theo incident-relative timeline; Pass 2 nhận đúng clip và telemetry window; no-incident không gọi Pass 2.

      fake = FakeVLM(localization=LocalizationResult(incident_detected=False))
      result = await process_incident(incident, vlm=fake)
      assert result.incident_detected is False
      assert fake.pass2_calls == 0

- [ ] Chạy test đỏ.
- [ ] Implement FFmpeg extraction theo cửa sổ Pass 1; select_window dùng sec_from_incident; validate structured output của Pass 2 gồm summary/timeline/key_factors/observations/unknowns/evidence/model_metadata.
- [ ] Kiểm tra candidate_start <= critical_time <= candidate_end; time_range_s evidence nằm trong timeline và video sau khi đã có mapping collision offset.
- [ ] Test provider timeout, malformed JSON, evidence yếu: job failed với VLM_FAILED hoặc INSUFFICIENT_EVIDENCE; không tạo report nửa chừng.

### Task 7: Persist AnalysisReport/Evidence và API đọc

**Files:** Create src/api/reports.py, src/api/evidence.py, src/services/evidence.py, src/services/reports.py, tests/test_api/test_results.py; modify src/worker.py.

**Interfaces:** GET /api/v1/incidents/{incident_id}/report trả AnalysisReport với review_status DRAFT và evidence_ids; GET /evidence trả Evidence[] với time_range_s. Job.result_uri khi succeeded trỏ API resource đã chốt, không trỏ file hệ điều hành.

- [ ] Test report trước khi analyze trả 404; succeeded có report DRAFT và evidence_ids tham chiếu Evidence tồn tại; IncidentRecord vẫn nguyên.

      report = (await client.get(f"/api/v1/incidents/{incident_id}/report")).json()
      evidences = (await client.get(f"/api/v1/incidents/{incident_id}/evidence")).json()
      assert report["review_status"] == "DRAFT"
      assert set(report["evidence_ids"]) <= {item["evidence_id"] for item in evidences["items"]}

- [ ] Chạy test đỏ.
- [ ] Persist report, evidences, incident PROCESSING→COMPLETED và job succeeded trong một transaction; chỉ dùng URI tương đối.
- [ ] Test một evidence invalid gây rollback toàn bộ report/evidence/job success; failed job có error nhưng không có report giả.
- [ ] Chạy tests result API và kiểm tra FE render được report/evidence không cần IncidentRecord chứa nội dung VLM.

### Task 8: Report edit, version, review và audit

**Files:** Create src/api/audit.py, src/services/audit.py, tests/test_api/test_review.py, tests/test_api/test_audit.py; modify src/api/reports.py, src/services/reports.py, src/models/contracts.py.

**Interfaces:** PATCH /report chỉ nhận whitelist đã chốt và version; submit DRAFT→IN_REVIEW; approve IN_REVIEW→APPROVED; reject IN_REVIEW→REJECTED. Mỗi edit tạo report_versions snapshot; mỗi hành động quan trọng tạo audit_events. GET /api/v1/incidents/{incident_id}/audit đọc sự kiện.

- [ ] Test Engineer edit tạo version mới và REPORT_EDITED event; stale version trả 409; không PATCH IncidentRecord/evidence hash/model metadata.

      response = await engineer.patch(report_url, json={"version": 1, "summary": "Checked against telemetry"})
      assert response.status_code == 200
      assert (await engineer.patch(report_url, json={"version": 1, "summary": "Old edit"})).status_code == 409

- [ ] Chạy test đỏ.
- [ ] Implement state machine đúng DRAFT→IN_REVIEW→APPROVED/REJECTED; reject không tự quay về DRAFT. Quy tắc sửa REJECTED phải được chốt trước khi cài.
- [ ] Ghi report version và audit event trong cùng transaction với edit/transition; actor/reason theo quyết định auth và reject reason.
- [ ] Test Engineer không approve, Reviewer không edit nếu auth/role thuộc MVP; nếu deferred, ghi rõ demo chỉ chạy local và không giả vờ có phân quyền.
- [ ] Test GET /audit có INCIDENT_CREATED, ANALYSIS_STARTED/COMPLETED, REPORT_EDITED/SUBMITTED/APPROVED/REJECTED theo thứ tự.

### Task 9: Media access, error contract và E2E

**Files:** Create src/api/errors.py, tests/test_api/test_errors.py, tests/test_e2e.py, docs/backend-runbook.md; modify src/main.py, docker-compose.yml. Nếu FE/BE chọn streaming route, create src/api/media.py; nếu chọn signed URL, modify src/api/incidents.py.

**Interfaces:** Lỗi trả {error:{code,message,details}}; không lộ stack trace, credential, raw VLM output hoặc absolute storage path. FE lấy được video/evidence bằng cơ chế có quyền đã được chốt.

- [ ] Test error codes INVALID_VIDEO, VIDEO_TOO_LARGE, INVALID_LOG, INCIDENT_NOT_FOUND, INCIDENT_NOT_READY, ANALYSIS_ALREADY_RUNNING, JOB_NOT_FOUND, VLM_FAILED, INSUFFICIENT_EVIDENCE, INVALID_REPORT_STATE, PERMISSION_DENIED, INTERNAL_ERROR.
- [ ] Test E2E với fake VLM: upload → READY → analyze → queued/running/succeeded → report/evidence → edit/version → submit → approve hoặc reject → audit.

      assert job["status"] == "succeeded"
      assert report["review_status"] == "DRAFT"
      assert reviewed_report["review_status"] == "APPROVED"
      assert any(event["action"] == "REPORT_APPROVED" for event in audit["items"])

- [ ] Chạy python -m pytest tests -q; chạy Alembic trên DB sạch; chạy docker compose up --build với API, worker, PostgreSQL và fake VLM.
- [ ] Chạy thêm clip có CSV canonical, clip không CSV, video lỗi và job bị restart; xác nhận evidence timestamp, rollback và retry.
- [ ] Thay test template /chat, /status bằng test contract RAV18; bỏ đăng ký route chatbot mẫu sau khi các route v1.1 đã qua E2E. Giữ code mẫu ngoài đường chạy ứng dụng cho tới khi nhóm quyết định dọn.
- [ ] Bàn giao OpenAPI, ví dụ payload, biến môi trường, hướng dẫn chạy và các điểm chưa chốt cho FE/AI-Data. Đánh giá VLM thật bằng bộ clip có quyền sử dụng, báo cáo rõ độ đúng evidence, latency và chi phí.

## Gates và stop condition

- **Gate A — Contract:** Task 1 và các quyết định ảnh hưởng API: PATCH, no-incident, list/audit response, timeline mapping. FE/BE/VLM dùng cùng v1.1.
- **Gate B — Persistence + ingestion:** Tasks 2–4. Video/CSV lưu storage, sáu bảng/migration chạy, dashboard list/get đọc từ PostgreSQL.
- **Gate C — Vertical slice:** Tasks 5–7. Upload → Analyze → Poll → fake VLM hai pass → AnalysisReport/Evidence persist và FE đọc được.
- **Gate D — Review + demo:** Tasks 8–9. Version, audit, submit/approve/reject, media access và các test lỗi/restart hoạt động.

**Phân công gợi ý:** BE làm DB/API/worker/review; AI/Data sở hữu schema LocalizationResult/AnalysisResult và mẫu output có unknowns; FE kiểm tra OpenAPI/list/poll/report/audit ở từng gate; người phụ trách CARLA chốt cách nạp IncidentRecord và time mapping. Dừng mở rộng sau khi Gate D đạt, chỉ xử lý lỗi phát hiện bởi clip thử nghiệm và điều kiện demo.

**Phạm vi chưa triển khai trong plan:** camera trực tiếp, batch, analytics, RAG/vector DB, API clip/frame riêng, retention automation và ETag nếu chưa được nhóm xác nhận.
