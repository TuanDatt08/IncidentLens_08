# IncidentLens runbook

## Preflight

Xác định environment/DB/storage, app version/schema, ffmpeg/ffprobe, capacity và policy. Không in secrets. API health chỉ liveness, không chứng minh worker/inference/storage ready. Kiểm DB queue, worker heartbeat, media read và provider profile.

## Job chậm hoặc dừng

Tra job_id/stage/attempt/lease; xem queue wait khác processing time. Kiểm disk/memory, FFmpeg, telemetry mapping, privacy status, provider quota/timeout. Không resubmit analyze liên tục hoặc publish bằng attempt đã hết lease. Resume từ checkpoint theo RAV-015; hiện pipeline legacy chưa checkpoint dài.

## Privacy failure

Chặn external egress và frontend media; giữ restricted raw và error sanitized. Kiểm detector/region masking trên fixture, thực hiện review vùng che. Chỉ retry sau gate PASSED; không bypass để hoàn tất job.

## Invalid output/evidence

Không publish/approve. Kiểm schema version, time basis, registry/hash/source/scope. Log mâu thuẫn thành unknown; retry tối đa budget, không loop tự do. Engineer sửa vẫn qua validator.

## Review conflict

409 stale → đọc version mới, trình bày thay đổi, không ghi đè. 401/403 kiểm identity/role/scope; không bật demo actor ở production. Reject reason và reopened snapshot phải audit.

## Recovery/release

Giữ snapshot cũ và partial result; retry cùng idempotency key. Backup/restore kiểm DB và evidence hash cùng phiên bản. Đối chiếu [release gates](deployment.md); ghi incident/action/actor/time và limitations. Hiện chưa có đo quality/latency/cost; không dùng fake DEMO report làm báo cáo thật.

Chi tiết local worker/database/fake smoke: [Backend runbook](../../backend/docs/runbook.md). HTTP routes: [API docs](../../api/docs/routes.md); client integration: [Frontend docs](../../frontend/docs/api-integration.md).
