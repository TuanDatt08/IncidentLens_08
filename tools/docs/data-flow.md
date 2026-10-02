# Data flow and provenance

1. Upload session lưu filename/size/hash/scope; parts được checksum, complete idempotent mới tạo recording READY.
2. Worker ffprobe lấy duration/fps; normalize telemetry theo time/unit/source; alignment lưu offset/drift/anchors/quality.
3. Deterministic candidate detector xuất candidate ID/window/reason/config hash; fallback segment sparse → dense có coverage/checkpoint.
4. Extract evidence trong video_seconds, hash asset, giữ frame order và log rows liên quan. Legacy v1 seek = collision-relative seconds + collision_offset; V2 seek = video_seconds.
5. Restricted raw → MASKED artifact + privacy PASSED; allowlisted telemetry. Chặn frontend/external khi chưa đạt. Self-host raw chỉ internal policy.
6. Adapter nhận AnalysisContext versioned, sinh AnalysisV2 DRAFT. Validate schema/time/source/cross-recording references/claim evidence. Unknown và contradiction không bị biến thành fact.
7. Transaction lưu snapshot/provenance/usage/evidence mapping. Engineer edit tạo version, Reviewer transition tạo snapshot/audit; approved immutable.
8. Read chỉ snapshot; rerun/migration explicit sinh version mới. Retention không làm approved evidence mất khả năng truy vết âm thầm.

Cache key phải có masked asset/input hash + log/time mapping + sampling/normalization/privacy config + prompt/schema/model revision. Không chia cache khác scope người dùng. Cache hit vẫn chạy policy/scope/version validation, không tái dùng APPROVED status.
