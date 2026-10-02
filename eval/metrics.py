"""Metrics with visible denominators, missing costs and overflow candidates."""

from __future__ import annotations

import math

COST_COMPONENTS = {"inference", "gpu", "preprocess", "storage", "retry", "review"}


def number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def ratio(numerator: int, denominator: int) -> dict:
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (numerator, denominator)) or numerator > denominator:
        raise ValueError("metric counts must be nonnegative integers with numerator <= denominator")
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}


def cost_per_accepted(costs: dict[str, float | None], accepted: int) -> float | None:
    if isinstance(accepted, bool) or not isinstance(accepted, int) or accepted < 0 or set(costs) != COST_COMPONENTS:
        raise ValueError("all cost components and nonnegative accepted count required")
    if any(value is not None and not number(value) for value in costs.values()):
        raise ValueError("costs must be finite nonnegative amounts or NOT_MEASURED/null")
    if not accepted or any(value is None for value in costs.values()):
        return None
    return sum(costs.values()) / accepted


def percentile(values: list[float], percent: float) -> float | None:
    if not number(percent) or percent > 100 or any(not number(value) for value in values):
        raise ValueError("percentile requires finite nonnegative samples and percentage <= 100")
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent / 100
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def candidate_recall(candidates: list[dict], ground_truth: list[tuple[float, float]], *, min_iou: float) -> dict:
    if not number(min_iou) or not 0 < min_iou <= 1:
        raise ValueError("IoU threshold must be declared in (0, 1]")
    proposed = [(item["start_s"], item["end_s"]) for item in candidates]
    if any(not number(start) or not number(end) or start >= end for start, end in [*proposed, *ground_truth]):
        raise ValueError("candidate/GT windows must be finite ordered video seconds")
    edges = []
    for start, end in ground_truth:
        neighbors = []
        for index, (left, right) in enumerate(proposed):
            intersection = max(0.0, min(end, right) - max(start, left))
            union = end - start + right - left - intersection
            if intersection / union >= min_iou:
                neighbors.append(index)
        edges.append(neighbors)
    matched: dict[int, int] = {}
    def augment(gt_index: int, seen: set[int]) -> bool:
        for candidate_index in edges[gt_index]:
            if candidate_index in seen:
                continue
            seen.add(candidate_index)
            if candidate_index not in matched or augment(matched[candidate_index], seen):
                matched[candidate_index] = gt_index
                return True
        return False
    for index in range(len(ground_truth)):
        augment(index, set())
    return ratio(len(matched), len(ground_truth))
