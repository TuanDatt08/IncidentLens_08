# IncidentAnalysisV2 — canonical business schema

Schema version `2.0`; object đóng (`additionalProperties=false`) ở mọi cấp, không coercion enum/timestamp, số phải hữu hạn. Runtime [IncidentAnalysisV2/AIIncidentAnalysisV2](../../backend/models/analysis_v2.py) và [implementation guide](../../backend/docs/analysis-schema-v2.md) đã có qua RAV-001; provider/API migration vẫn là task riêng.

| Field bắt buộc | Type/rule |
| --- | --- |
| schema_version | literal 2.0 |
| incident_detected | boolean |
| event_type | DISENGAGEMENT, HARD_BRAKING, COLLISION, CONTROL_ANOMALY, OTHER, UNKNOWN |
| time_basis | literal video_seconds |
| window | null khi chưa phát hiện; nếu có: start_s ≤ critical_s ≤ end_s, 0 ≤ start_s < end_s ≤ duration |
| summary | string không trống |
| timeline | array các observation có time_s, observation, evidence_ids, source, certainty |
| factors | array có category, label, claim_status, evidence_ids |
| unknowns | array string, ghi thiếu nguồn/mâu thuẫn/coverage |
| review_status | DRAFT, IN_REVIEW, APPROVED, REJECTED; output AI chỉ DRAFT |

`source`: VIDEO, TELEMETRY, FUSED. `certainty` và `claim_status`: OBSERVED, SUPPORTED_INFERENCE, HYPOTHESIS, UNKNOWN. `category`: EXTERNAL_CONDITION, VEHICLE_OR_SYSTEM, HUMAN_INTERACTION, UNKNOWN. Factor có căn cứ lấy timestamp từ evidence tham chiếu; timeline có time_s nằm trong window.

OBSERVED/SUPPORTED_INFERENCE yêu cầu evidence_ids không rỗng và resolve trong cùng incident/candidate, đúng time range và source. HYPOTHESIS/UNKNOWN có thể không có evidence, không được trình bày như fact. Internal cause không có log phù hợp phải UNKNOWN hoặc HYPOTHESIS; validator kiểm tra policy và Engineer review ý nghĩa. ID hợp lệ không bảo đảm claim đúng.

Không phát hiện: incident_detected=false, event_type=UNKNOWN, window=null, timeline=[], factors=[], summary mô tả phạm vi đã kiểm tra, unknowns nêu coverage. Không approve một kết quả này như báo cáo nguyên nhân sự cố.

```json
{"schema_version":"2.0","incident_detected":true,"event_type":"DISENGAGEMENT","time_basis":"video_seconds","window":{"start_s":3582.4,"critical_s":3591.2,"end_s":3605.0},"summary":"Xe chuyển sang điều khiển thủ công sau khi xe phía trước giảm tốc.","timeline":[{"time_s":3588.1,"observation":"Xe phía trước giảm tốc","evidence_ids":["EVD-001"],"source":"VIDEO","certainty":"OBSERVED"}],"factors":[{"category":"VEHICLE_OR_SYSTEM","label":"Nguyên nhân nội tại của disengagement","claim_status":"UNKNOWN","evidence_ids":[]}],"unknowns":["Không có log bộ điều khiển tại mốc chuyển chế độ."],"review_status":"DRAFT"}
```

Envelope lưu riêng recording_id, candidate_id, report_id, version, provider, model/revision, prompt_version, schema_version, input hashes, sampling/normalization config, privacy result, usage/cost/latency, created_at và actor. Không bắt model sinh metadata vận hành. Evidence registry lưu immutable asset hash, time range, source, media type, privacy state; raw URI không public.

Prompt chuẩn: chỉ phân tích frame/telemetry cung cấp, theo thứ tự thời gian; trả schema V2; dẫn timestamp/ID/source; tách OBSERVED, SUPPORTED_INFERENCE, HYPOTHESIS, UNKNOWN; không suy lỗi nội tại từ video; mâu thuẫn ghi unknowns; không approve. Temperature=0 không bảo đảm tái lập byte; đọc report phải dùng snapshot.
