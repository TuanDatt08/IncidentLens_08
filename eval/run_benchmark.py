"""Aggregate signed expert measurements; never invent measurements or call a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from eval.manifest import load_manifest
from eval.metrics import COST_COMPONENTS, cost_per_accepted, number, percentile, ratio


def compare(manifest_path: Path, measurements_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    if not manifest.release_ready:
        raise ValueError("benchmark BLOCKED: " + ", ".join(manifest.blockers()))
    measurements = json.loads(measurements_path.read_text(encoding="utf-8"))
    required_ids = {case.case_id for case in manifest.cases if case.split == "test"}
    profiles: dict[str, list[dict]] = {}
    expected_hashes = {case.case_id: case.video_sha256 for case in manifest.cases}
    budgets = set()
    for row in measurements:
        if row["case_id"] not in required_ids or row["input_sha256"] != expected_hashes[row["case_id"]] or not row.get("expert_review_ref") or not row.get("pricing_source") or not row.get("provenance"):
            raise ValueError("measurements must match locked test cases and signed expert/pricing provenance")
        if not isinstance(row["accepted"], bool) or not number(row["latency_s"]):
            raise ValueError("acceptance must be human-labelled and latency finite")
        budgets.add(row["budget_hash"])
        profiles.setdefault(row["provider"], []).append(row)
    if len(profiles) < 2 or len(budgets) != 1:
        raise ValueError("comparison requires multiple providers with the same declared budget")
    results = {}
    for provider, rows in profiles.items():
        if len(rows) != len(required_ids) or {row["case_id"] for row in rows} != required_ids:
            raise ValueError("each provider must cover every locked case once")
        accepted = sum(row["accepted"] for row in rows)
        costs = {}
        for component in COST_COMPONENTS:
            values = [row["cost_usd"].get(component) for row in rows]
            if any(value is not None and not number(value) for value in values):
                raise ValueError("cost components must be finite or NOT_MEASURED/null")
            costs[component] = None if any(value is None for value in values) else sum(values)
        correctness = [row["evidence_correctness"] for row in rows]
        for item in correctness:
            ratio(item["numerator"], item["denominator"])
        results[provider] = {"case_count": len(rows), "engineer_acceptance": ratio(accepted, len(rows)), "evidence_correctness": ratio(sum(item["numerator"] for item in correctness), sum(item["denominator"] for item in correctness)), "latency_p50_s": percentile([row["latency_s"] for row in rows], 50), "latency_p95_s": percentile([row["latency_s"] for row in rows], 95), "cost_components_usd": costs, "cost_per_accepted_usd": cost_per_accepted(costs, accepted)}
    return {"status": "MEASURED", "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "measurements_sha256": hashlib.sha256(measurements_path.read_bytes()).hexdigest(), "budget_hash": next(iter(budgets)), "providers": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("eval/datasets/manifest.json"))
    parser.add_argument("--measurements", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    if args.measurements is None:
        result = {"status": "READY" if manifest.release_ready else "BLOCKED", "actual_case_count": len(manifest.cases), "target_case_count": manifest.target_cases, "blockers": manifest.blockers(), "quality": "NOT_MEASURED", "gpu_throughput": "NOT_MEASURED"}
    else:
        result = compare(args.manifest, args.measurements)
    rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
