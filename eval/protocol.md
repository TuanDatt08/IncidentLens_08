# Expert benchmark protocol

Canonical requirements: [evaluation SPEC](../tools/specs/evaluation.md), [RAV-018](../tools/tasks/RAV-018-expert-benchmark.md), [RAV-019](../tools/tasks/RAV-019-provider-cost-comparison.md).

## Current evidence

Actual licensed expert cases: **0**. Target: **50–100**. [Manifest](datasets/manifest.json) is an empty draft, not synthetic benchmark evidence. Software fixtures only test contracts and metric arithmetic. GPU throughput, provider quality and accepted-incident cost: **NOT_MEASURED**. Production comparison/release remain blocked.

## Collect and label

Keep media in restricted storage; manifest contains references, SHA-256 and licence/consent references, never raw media or identifiable telemetry. Two independent expert pseudonyms annotate event/window, factor/category/claim status, expected evidence source/time and unknowns. Resolve disagreements with a third reviewer and record a signed resolution reference, including agreement when labels match. A normal-driving case can have empty ground truth.

Split by recording, scenario group and source hash. The validator rejects leakage across calibration/test. Freeze a version/hash and test-lock timestamp before tuning. Calibration changes require a new manifest version; do not tune on test labels.

## Sign before measurement

IoU 0.5 and time tolerance 100 ms in the draft are proposed protocol parameters, **not signed release thresholds**. Owner and Reviewer must sign the thresholds reference, quality/privacy limits, latency/cost limits, budget and date before a real experiment. Also record hardware profile and approved API/egress policy. The runner blocks absent prerequisites; it cannot authenticate a signature reference itself.

## Run comparable experiments

Use identical locked cases, input hashes and budget for V1 frame baseline, external V2, self-hosted V2, plus rule/sparse ablations. Record model/revision, prompt/schema/config/input hashes, sampling/normalization/privacy settings, retry, tokens, GPU utilization, stage and queue latency. Count UNANALYZED windows in candidate recall; absence in sparse samples is not negative ground truth.

Human reviewers label evidence correctness and acceptance using the agreed rubric. Report numerator/denominator, factor precision/recall by category and completeness; never substitute LLM-only judgement for experts. Labeling and metric collection are separate from the aggregation CLI.

Costs include inference, GPU, preprocess, storage, retry and human review. Every price needs currency, date and source. Use zero only when the component was measured as zero; null means NOT_MEASURED. Zero accepted reports makes cost per accepted report undefined. Latency uses linear-interpolated p50/p95 with sample count; archive raw measurement provenance to permit uncertainty analysis.

```powershell
python -m eval.run_benchmark
python -m eval.run_benchmark --manifest eval/datasets/manifest.json --measurements <restricted-measurements.json> --output <comparison.json>
```

The first command reports blockers. The second aggregates expert-reviewed measurements only after the manifest is ready; no network inference is initiated. Input reports must include every locked case once per provider, identical budget hash, accepted boolean, latency, cost components, evidence counts, signed expert review, pricing and model provenance. Do not publish private inputs. Threshold enforcement, expert factor/completeness scores and confidence intervals must be reviewed before a release claim.
