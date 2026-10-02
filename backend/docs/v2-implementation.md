# Recording analysis V2 — implementation and operating limits

Ngày kiểm tra: 2026-10-03. [Task ledger](../../tools/docs/task-execution-2026-10-03.md) ghi trạng thái acceptance. V1.1 vẫn giữ namespace, schema, relative time và rejected-terminal behavior.

## Luồng xử lý

1. Signed identity fixture → Engineer upload theo part, checksum và scope → RecordingV2.
2. `python -m backend.worker_v2` claim job trong DB; chuẩn hóa CSV và affine alignment với anchors.
3. Rules đề cử nhiều cửa sổ hoặc sparse scan qua adapter nội bộ được review. Không có adapter scan thì fail rõ, lưu coverage còn chưa scan.
4. FFmpeg trích clip/frame theo video_seconds, lưu thứ tự, hash, manifest; evidence nằm riêng theo job/attempt.
5. Privacy adapter dùng `VideoService` có guard và output_root của attempt. External inference chỉ nhận frame MASKED/PASSED và telemetry allowlist. Clip RAW không được playback.
6. Provider cùng contract/schema → shared evidence validator → report, snapshot và checkpoint trong một transaction.
7. Engineer sửa/submit; Reviewer khác subject approve/reject. Reopen từ REJECTED tạo version mới. APPROVED không sửa. Mỗi mutation có expected_version, stale trả 409.

## Contract và cấu hình

- [OpenAPI V2](../../api/docs/openapi-v2.json); export bằng `python -m api.export_v2_contract`. Snapshot test phát hiện drift.
- [HTTP contract](../../api/docs/backend-contract-v2.md); FE routes `/recordings`, `/recordings/[id]`, `/reports/[id]`.
- Migration: `alembic upgrade head`. Ba revision additive tạo các bảng V2, không rewrite bảng V1. Test seed V1 evidence/snapshot → upgrade → kiểm nội dung giữ nguyên.
- `V2_IDENTITY_SECRET` chỉ lấy từ environment/secret store; không ghi giá trị vào repo. LOCAL/TEST signed fixture có issuer/audience/expiry và scope. Production auth luôn 503 cho tới khi có IdP adapter được review.
- Provider chọn qua `V2_PROVIDER_ENDPOINT`, `V2_PROVIDER_MODEL`, `V2_PROVIDER_REVISION`. External cần HTTPS host allowlist và `V2_EXTERNAL_EGRESS_APPROVED`; đây là gate kỹ thuật, không phải bằng chứng approval. API key lấy từ environment hiện có, không ghi vào provenance.
- Upload prototype lưu filesystem private, part tối đa 16 MiB, expiry 24 giờ; production storage luôn 503 trước khi chọn/review adapter theo ADR-006.
- UI dùng HttpOnly fixture cookie hoặc API Bearer. Cookie mutation yêu cầu application header và CORS origin hợp lệ. Role/scope quyết định ở server.

## Resume, budget và cancellation

Lease 120 giây; heartbeat nền, attempt/version fence trước publish. Max attempts/calls/disk/wall/scan hữu hạn, calls được reserve trước provider. Checkpoint của candidate đã publish không được thay; checkpoint discovery `scan_pending=true` có thể được thay bằng kết quả hoàn tất dưới lease mới.

Artifact namespace tách theo attempt, giữ evidence cũ cho report đã publish. Dung lượng tính cả các attempt của job. Trước mỗi output FFmpeg, manifest và telemetry, guard kiểm lease/wall và tính lại dung lượng còn lại. FFmpeg `-fs` hạn chế file; output chạm cap bị loại bỏ và không được publish. `-fs` có thể vượt theo packet trong lúc ghi; production cần filesystem/container quota cho hard disk isolation giữa process, và cleanup attempt hết lease. Không tuyên bố OS quota đã được chứng minh.

Cancellation hợp tác giữa các bước, scan frame và mỗi 1.000 CSV rows. FFmpeg hiện timeout 180 giây; provider timeout/retry hữu hạn. Không hủy tức thời subprocess đang chạy, nhưng attempt mất lease không publish. Partial results giữ nguyên; chỉ failed job còn attempt được resume; browser reload đọc DB và không tự reanalyze.

## Bằng chứng và giới hạn

- Real FFmpeg fixtures: seek/time tolerance 100 ms, clip/order/hash, masking vùng synthetic và upload MP4 hoàn chỉnh. Mask synthetic không đo recall detector mặt/biển số.
- 64 MiB synthetic upload qua 8 part, chunk 64 KiB; tracemalloc peak dưới 8 MiB. Đây là Python allocation, không RSS/browser memory hoặc proof media 5 giờ đầy đủ.
- Candidate detection fixture có duration 18.000 giây; sparse samples vượt 5 frame, coverage/UNANALYZED rõ. Không có full 5-hour live inference benchmark.
- Real API + production Next.js E2E: upload, reload/recover/cancel, typed edit, seek, dialog Escape/focus, Engineer/Reviewer approval, audit, 401 và desktop/mobile. Node checks giữ typed fields và 401/403/409/upload expiry copy.
- Worker crash/resume, stale lease, pending scan resume, cancellation, shared validation, invalid privacy/provider/storage đều có tests. PostgreSQL multiworker chưa chạy: Docker daemon không khả dụng tại lượt kiểm tra.
- VLM transport tests dùng mock network, không phải live API hoặc GPU quality/throughput. Usage/cost không đo ghi null/NOT_MEASURED; retry cost không suy từ attempt cuối.
- Expert manifest thực có **0 case**, mục tiêu 50–100. `python -m eval.run_benchmark` trả BLOCKED. Không dùng synthetic test labels làm expert dataset.

## Release gate

Chưa release production. Cần IdP review, ADR-006 storage/region/retention approval, production detector + full-motion masking/independent validator, PostgreSQL concurrent worker smoke, licensed expert dataset và disagreement resolution, locked split/threshold sign-off, API egress policy và hardware profile, live provider comparison, OS quotas và operational restore/retention drill.

## Kiểm tra

```text
python -m ruff check .
python -m pytest tests -q -p pytest_asyncio.plugin
npm --prefix frontend run typecheck
npm --prefix frontend run lint
node tests/frontend/report-editor-check.mjs
node tests/frontend/v2-client-check.mjs
npm --prefix frontend run build
python tests/frontend/v2-workflow.py
```

Browser harness cần Playwright development tool và Chrome, dùng port 8000/3016 nếu còn trống, tạo DB/media/cookie synthetic trong temp và chỉ dừng process do harness khởi tạo. Không sử dụng tài khoản hay dữ liệu riêng của người dùng. CI thêm FE checks và media tool preflight; remote CI vẫn pending tới khi có run thực.
