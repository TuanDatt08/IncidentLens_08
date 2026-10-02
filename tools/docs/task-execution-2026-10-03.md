# Task execution — 2026-10-03

User authorizes all implementation choices and local commits; no repeated approval. Canonical SPEC/ADR/tasks remain the design and acceptance authority. Execute inline with Superpowers and Ponytail; group commits by behavior, not task ID. Preserve API v1.1.

## Order and checks

1. Verify existing schema/log work; normalization → alignment → candidates → ordered evidence.
2. Shared evidence validator → provider/privacy contracts → bounded adapters.
3. Upload/auth/versioned API/review/checkpoints → frontend.
4. Evaluation/observability; publish measured evidence and remaining external prerequisites.

For each task: read linked documents, add negative acceptance tests before new behavior, run targeted checks, update only evidenced checklist entries. Final gates: `python -m ruff check .`, full pytest, frontend checks when touched, staged secret scan; guide render/link checks only when `docs/guide/**` changes.

## Ledger

- Baseline: develop, two existing untracked normalization files preserved. Ruff clean; pytest 131 passed (16.58s). SQLite/fake tests do not establish PostgreSQL, live provider, privacy quality or expert benchmark results.
- Ruling: existing task briefs/specs supply the design; execute approved work without creating duplicate design documents or asking again. Commit format follows the user's latest instruction, overriding per-task commit examples.
- Ruling: ROS2 adapter may explicitly reject unsupported bags, as RAV-002 acceptance allows. No new ROS dependency.

## Current completion

20 tasks đã kiểm và cập nhật AC có bằng chứng: **12 DONE (local AC), 7 PARTIAL, 1 BLOCKED**. DONE local AC không là production delivery/remote CI/merge. Checklist RED cho từng AC chỉ tick khi có record; không tạo bằng chứng RED hồi tố.

| Tasks | Local outcome | Remaining gate |
| --- | --- | --- |
| 001–004, 006, 008–010, 012–013, 016–017 | Schema/log/align/discovery/ordered evidence, providers, validation, versioned review/API/UI verified | Some downstream production identity/storage dependencies still gated; remote CI/merge pending |
| 005 | Synthetic-region masking, privacy failure/telemetry/RAW media guard | Annotated real detector quality and full-motion masking/validator |
| 007 | Mock transport, explicit egress policy, schema/evidence/usage gate | Approved live API smoke and privacy prerequisite |
| 011 | Local resumable streaming upload, MP4 integrity, browser expiry recovery, bounded synthetic memory workload | Reviewed production storage/retention/region; full long-media deployment workload |
| 014 | Signed LOCAL/TEST fixture, expiry/roles/scope/cookie-CSRF, no self-review | Reviewed production IdP adapter |
| 015 | Durable checkpoints/leases, replay, calls/wall/output bounds, cancellation | PostgreSQL multiworker smoke; OS quotas for production hard isolation |
| 018 | Manifest/protocol/GT schema, leakage/license/signoff validators; actual count 0 | Licensed expert cases, independent annotations/resolution, locked split/signed thresholds |
| 019 | Metrics/comparison runner and synthetic unit tests | BLOCKED: actual dataset/signoff/API policy/GPU hardware; quality/cost/throughput NOT_MEASURED |
| 020 | Stage/coverage/budget/usage, sanitized errors, local failure fixtures and SQLite restore, expanded CI config | Production restore/retention drill and remote CI |

Implementation/limits: [V2 operating guide](../../backend/docs/v2-implementation.md), [HTTP contract](../../api/docs/backend-contract-v2.md), [evaluation protocol](../../eval/protocol.md). Backlog/sprint checkboxes updated to local AC only; P0 external gates keep sprints incomplete.

## Review and verification

One independent code review found no Critical and four Important worker issues plus one upload UX issue. Resolved in one pass: attempt-specific artifact namespace, fenced replacement of pending discovery, remaining output budget recomputed for every artifact/metadata write, cooperative lease/wall/cancel guards during discovery, expired upload reset/retry. Regression tests cover the scenarios. FFmpeg `-fs` may transiently overshoot a packet; this is documented, not claimed as an OS quota.

RED observed during current fixes: pending discovery coverage remained 0, output guard constructor absent, worker stage remained DETECTION during provider call. Each regression went GREEN after implementation. Existing baseline schema RED record retained.

Media: real FFmpeg synthetic red/blue seek and clip tolerance100ms; masking synthetic FACE/PLATE region test; real MP4 upload/replay. Memory: streamed total64MiB, 8MiB parts,64KiB chunks, tracemalloc peak<8MiB; does not measure RSS/browser/full5h inference. Candidate test duration18.000s is coverage simulation.

Real browser/API E2E passed: upload→job recovery after reload→cancel; typed edit→seek absolute2.5s to relative1.5s→native dialog Escape/focus restore→different Reviewer approval→audit→401. Next production build, Chrome, disposable SQLite/media/signed cookie. Batched screenshots1440px desktop/390px mobile visually inspected; no horizontal overflow. Temp artifacts: `C:/Users/Lenovo/AppData/Local/Temp/p076-v2-e2e-1yhg1y6u`. These are synthetic evidence, not real detector/model accuracy. Impeccable context loaded; one final mechanical detector call detected Next project and suggested URL scan; browser inspection supplied the actual visual check.

SQLite HEAD upgrade preserves seeded V1 evidence/hash/snapshot; native SQLite backup/restore readback passed. Two concurrent edits produce one version2 and one409, exactly two snapshots. Docker daemon unavailable; PostgreSQL smoke not performed.

Final gate commands/results are recorded below after the final run. No `docs/guide/**` changes, so Technical Book rendering/link gate is N/A. Added/changed implementation docs have local relative links checked. CI config is reviewable, but remote CI is pending; no push/merge/release performed.

Final-suite timing finding: V1 heartbeat fixture used a 150ms lease and a 350ms real sleep; one full run reclaimed during Windows scheduling (209 passed/1 failed), while isolated test passed. Test now controls job datetime and waits for actual background heartbeats before advancing 100ms steps beyond the original lease. Worker production behavior is unchanged. Targeted four V1 worker tests passed; final whole-suite result follows.

### Final results

- `python -m ruff check .`: All checks passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q -p pytest_asyncio.plugin -p no:cacheprovider`: **210 passed**, 60.29s. Two environment dependency/deprecation warnings; no failed/skipped tests. Disable unrelated installed plugins, explicitly enable the required async plugin.
- FE typecheck: passed; lint: no warnings/errors; production build: passed (9 routes).
- Node typed-editor and V2 client checks: passed.
- Real API/browser workflow harness: passed; desktop/mobile inspected as above.
- `python -m eval.run_benchmark`: BLOCKED, actual0/target50, quality/GPU NOT_MEASURED; correct gate result, no fabricated benchmark.
- Staged secret-pattern/direct-literal scan: no findings; `.env.example` not modified. Staged diff whitespace check passed; changed Markdown local links resolve. `docs/guide/**` not modified; render/guide-link condition N/A.
- Remote CI/merge/release not performed. Commit grouped by final behavior rather than individual task.
