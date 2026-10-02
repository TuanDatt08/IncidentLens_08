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
# Recording V2 operations — 2026-10-03

Implementation/limits: [V2 operating guide](../../backend/docs/v2-implementation.md), [task evidence](task-execution-2026-10-03.md). Production release remains blocked by the listed identity/storage/privacy/PG/expert-data/provider gates.

Local failure drills are automated: worker crash after one report → resume retains that report; expired lease denies publication; cancellation stops the next sparse frame; missing scanner persists pending discovery; corrupt/oversize/expired upload fails; transport retry is bounded; privacy failure prevents network and RAW playback. Public error output contains codes, not exception text, raw telemetry or credentials. Job polling provides stage, coverage, budgets, partial reports and per-candidate usage/provenance.

SQLite restore drill: `python -m pytest tests/backend/test_db.py -q` seeds V1 evidence/snapshot, upgrades through V2, uses sqlite backup API and compares restored snapshot bytes. This does not verify production PostgreSQL backup. Before production, run pg_dump/restore against an isolated database plus readback of approved versions, evidence hashes and referenced private objects; record RPO/RTO with the deployment owner.

Retention policy is **DRAFT**, not activated: proposed dev incomplete uploads 24h, orphan attempt outputs after lease expiry plus 24h grace, completed raw media only after owner-approved retention and verification that no immutable snapshot references it. Approved versions/evidence must not be removed by orphan cleanup. Production owner must sign actual retention/region/legal constraints and a deletion/restore drill; no cleanup process is enabled by this change.

CI now configures full ruff/Python tests, FFmpeg preflight, FE typecheck/lint/build and Node client checks. Local execution is recorded separately; remote CI/merge has not run.
