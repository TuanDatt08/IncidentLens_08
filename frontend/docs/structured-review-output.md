# Structured prompt output and full-width review

Reviewed the public demo report at https://p-136.vercel.app/review/adasto_0080 for its conditions, chronology, key factors and evidence organization. Its US DOT labels and per-field approval controls were not imported into this application's contract.

`backend/data/promt.txt` retains strict Stage A/B v3 JSON fields. Stage B now requests concise Vietnamese narrative, distinguishing observed facts, supported cause, hypotheses, response/outcome and unavailable information. Numeric log metrics and taxonomy labels cannot be fabricated. Existing reports are not automatically rewritten; the new prompt applies on subsequent analysis.

The review-context API exposes the validated Stage B analyses plus the primary confirmed analysis, retaining the full original bundle and original-video timestamps. The UI presents conditions, chronology with seek controls, factors/causes, outcomes, evidence and data quality. These are read-only model suggestions; the existing versioned engineer draft remains editable separately.

Workspace navigation is now entirely in the sticky top header. Desktop pins the video/telemetry column below it; narrow screens keep the compact source player above a separately scrolling report region. Color tokens stay unchanged. Surface hover and section-entry motion use the landing's violet accents and respect reduced motion.

Verification: nine targeted prompt/review-context backend tests and Ruff passed; frontend typecheck/lint/build and video/draft regression tests passed. Browser QA used isolated `QA-STRUCTURED`, explicitly marked synthetic test data, not real Qwen inference. At desktop page scroll ~1259px header stayed at 0 and video at 88px; mobile report scroll ~1688px preserved video position and had no horizontal overflow.

Live Qwen output quality has not been measured. PostgreSQL and production deployment were not exercised for this UI change.
