import json

import numpy as np
import pandas as pd
import pytest

from mde.analysis.pairs import all_pairs, disagreement_rows, pair_stats


def test_binary_pair_stats_match_expected_values():
    y = np.array([0, 0, 1, 1, 0, 1])
    pa = np.array([0, 1, 1, 0, 0, 1])
    pb = np.array([0, 0, 1, 1, 1, 1])
    result = pair_stats(y, pa, pb, n_classes=2)
    assert result["buckets"]["both_right"] == 3
    assert result["b"] == 1
    assert result["c"] == 2
    assert result["buckets"]["both_wrong"] == 0
    assert result["disagreement_count"] == 3
    assert result["mcnemar"]["p"]["value"] == pytest.approx(1.0)


def test_multiclass_pair_stats_and_disagreement_rows_include_both_wrong_diff():
    y = np.array([0, 1, 2, 0])
    pa = np.array([1, 1, 0, 0])
    pb = np.array([2, 1, 0, 0])
    result = pair_stats(y, pa, pb, n_classes=3)
    assert result["buckets"]["both_wrong_diff"] == 1
    assert result["disagreement_count"] == 1

    features = pd.DataFrame({"x": [10, 20, 30, 40], "category": ["a", "b", "c", "d"]})
    proba = {
        "a": np.array([[0.1, 0.8, 0.1], [0.2, 0.7, 0.1], [0.7, 0.2, 0.1], [0.8, 0.1, 0.1]]),
        "b": np.array([[0.1, 0.1, 0.8], [0.2, 0.7, 0.1], [0.7, 0.2, 0.1], [0.8, 0.1, 0.1]]),
    }
    rows = disagreement_rows(features, y, {"a": pa, "b": pb}, proba, ["zero", "one", "two"], "a", "b")
    assert rows["total"] == 1
    assert rows["rows"][0]["bucket"] == "both_wrong_diff"
    json.dumps(rows, allow_nan=False)


def test_all_pairs_ignores_dummy_and_holms_are_monotone():
    y = np.array([0, 1, 0, 1, 0, 1])
    preds = {
        "dummy": {"status": "done", "pred": np.array([0, 0, 0, 0, 0, 0])},
        "a": {"status": "done", "pred": np.array([0, 1, 0, 1, 0, 1])},
        "b": {"status": "done", "pred": np.array([0, 0, 0, 1, 0, 1])},
        "c": {"status": "done", "pred": np.array([1, 1, 1, 0, 1, 1])},
    }
    pairs = all_pairs(y, preds)
    assert len(pairs) == 3
    assert all(item["model_a"] != "dummy" and item["model_b"] != "dummy" for item in pairs)
    assert all(item["p_holm"] >= item["p_raw"] for item in pairs)
    assert all("kappa_stat" in item for item in pairs)

    json.dumps({"pairs": pairs}, allow_nan=False)
