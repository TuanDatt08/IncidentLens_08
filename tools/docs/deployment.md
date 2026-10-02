# Deployment and release gates

## Current local topology

Compose postgres:16-alpine + backend + worker, bind DB/API localhost và shared backend/data volume. Frontend không nằm trong compose. APP_ENV production chặn media/review tới auth thật; local compose không phải production security baseline.

## Target preparation

1. Owner chọn storage theo ADR-006: region/capacity/retention, signed parts/resume, storage/access/egress cost, backup/restore.
2. Identity issuer/claims/session và server RBAC/scope; TLS/secrets manager, private raw storage và public masked boundary.
3. Worker FFmpeg + privacy detector có resource/timeout/disk cap, lease/checkpoint metrics; API và inference tách tài nguyên.
4. External profile: privacy PASSED, sanitized telemetry, data policy/egress approval, quota/rate/budget. Self-host profile: internal endpoint/model revision/GPU memory/concurrency benchmark và network containment.
5. Migration V2 giữ v1 reads; health/readiness, rollback app/schema compatible, snapshot/evidence backup restore drill.
6. Release khi auth/large upload/privacy/evidence/retry/CI/benchmark thresholds đều có measured evidence. Chưa có threshold/hardware/dataset thì chưa production-ready.

Không có manifest production được tạo trong lần này; không chốt cloud/GPU/provider. Rollback không xóa snapshots; restore DB và storage phải cùng provenance/hash. Trước destructive restore phải xác nhận target/environment.
