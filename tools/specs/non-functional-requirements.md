# Non-functional requirements

| ID | SHALL | Task |
| --- | --- | --- |
| NFR-REL-001 | Job idempotent, retry/cancel bounded, lease cũ không publish | RAV-015 |
| NFR-REL-002 | Resume segment/checkpoint sau crash, giữ partial result | RAV-015 |
| NFR-PER-001 | Upload/processing video 3–5 giờ không giữ toàn file trong browser/RAM | RAV-011 |
| NFR-PER-002 | Per-job candidate/frame/call/timeout/disk budget, overflow hiển thị | RAV-003, RAV-015 |
| NFR-SEC-001 | Auth/scope/RBAC và privacy gate fail closed | RAV-005, RAV-014 |
| NFR-OBS-001 | Job stage/progress/coverage, trace ID và sanitized error | RAV-015, RAV-020 |
| NFR-OBS-002 | Usage/cost/latency/retry theo stage | RAV-020 |
| NFR-DAT-001 | Hash/checksum, immutable approved snapshot, evidence vẫn resolve | RAV-009, RAV-013 |
| NFR-AI-001 | Provider/model/prompt/schema/input/config version được lưu | RAV-006, RAV-013 |
| NFR-AI-002 | Đọc report không regenerate; explicit rerun tạo version mới | RAV-013 |

Không dùng latency 30 giây cho workload nhiều giờ. Threshold p95, throughput, retention và budget tiền là quyết định cần đo/ký theo [evaluation](evaluation.md). Mọi claim hiệu năng phải nêu duration, hardware, candidate count và mode. Software acceptance và benchmark release gate tách riêng.
