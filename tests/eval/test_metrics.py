import importlib

import pytest


def test_cost_includes_all_components_and_zero_accepted_is_undefined():
    module = importlib.import_module("eval.metrics")
    costs = {"inference": 1.0, "gpu": 2.0, "preprocess": 3.0, "storage": 4.0, "retry": 5.0, "review": 6.0}
    assert module.cost_per_accepted(costs, 3) == 7
    assert module.cost_per_accepted(costs, 0) is None
    assert module.cost_per_accepted({**costs, "review": None}, 3) is None


def test_latency_percentiles_and_invalid_samples():
    module = importlib.import_module("eval.metrics")
    assert module.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3
    assert module.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) == pytest.approx(4.8)
    assert module.percentile([], 95) is None
    with pytest.raises(ValueError):
        module.percentile([float("nan")], 95)


def test_candidate_recall_includes_overflow_and_matches_one_to_one():
    module = importlib.import_module("eval.metrics")
    candidates = [{"start_s": 0.0, "end_s": 10.0, "analysis_state": "UNANALYZED"}]
    assert module.candidate_recall(candidates, [(0.0, 10.0)], min_iou=0.5) == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert module.candidate_recall(candidates, [(0.0, 5.0), (5.0, 10.0)], min_iou=0.5)["numerator"] == 1
