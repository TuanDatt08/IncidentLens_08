# Analysis schema V2

Runtime: [analysis_v2.py](../models/analysis_v2.py). Dùng `AIIncidentAnalysisV2` cho provider output (review_status bắt buộc DRAFT), `IncidentAnalysisV2` cho snapshot sau human review. Model validation không cấp quyền submit/approve; RBAC vẫn kiểm ở service boundary.

```python
from backend.models.analysis_v2 import AIIncidentAnalysisV2

draft = AIIncidentAnalysisV2.model_validate(
    provider_payload,
    context={"video_duration_s": trusted_video_metadata["duration"]},
)
```

Model strict/finite, object đóng mọi cấp, không nhận enum lạ hoặc string/bool làm timestamp. JSON numeric integers vẫn hợp lệ. Claim OBSERVED/SUPPORTED_INFERENCE cần evidence IDs; UNKNOWN/HYPOTHESIS không ép bịa evidence. Incident có window positive và timeline nằm trong window; không incident thì UNKNOWN event, null window, empty claims. No-incident không được APPROVED như báo cáo nguyên nhân sự cố.

Context duration là metadata được pipeline cung cấp, không nằm trong payload AI. Không truyền context chỉ kiểm cấu trúc/time/window tương đối; pipeline phải truyền duration trước publish theo RAV-009. Schema không resolve ID/hash/source, kiểm privacy hoặc suy đúng nguyên nhân; đó là validator domain và human review.

Machine-readable artifacts: [business](../models/json_schema/incident-analysis-v2.json), [AI output](../models/json_schema/ai-incident-analysis-v2.json). Sinh bằng `Model.model_json_schema()`; regression kiểm hai files không drift. JSON Schema encode shape/enums/minimum/required; cross-field rules và duration context được Pydantic validators kiểm sau decoding.

V1 models/API vẫn dùng [contracts.py](../models/contracts.py), không thêm V2 field vào v1. Provider migration và API routes có task riêng. Tests: [test_analysis_v2.py](../../tests/backend/test_services/test_analysis_v2.py). Canonical behavior: [SPEC](../../tools/specs/incident-analysis-v2.md).
