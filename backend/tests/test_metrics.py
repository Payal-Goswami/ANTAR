import math

from mde.analysis.metrics import model_metrics
from mde.analysis.stats import stat


def test_model_metrics_match_expected_values():
    result = model_metrics([0, 0, 1, 1], [0, 1, 1, 1], [[0.8, 0.2], [0.4, 0.6], [0.3, 0.7], [0.1, 0.9]], 2)
    assert result["accuracy"]["value"] == 0.75
    assert round(result["macro_precision"]["value"], 4) == 0.8333
    assert round(result["macro_recall"]["value"], 4) == 0.75
    assert round(result["macro_f1"]["value"], 4) == 0.7333

    assert result["per_class"][1]["precision_undefined"] is False


def test_unseen_class_marks_precision_as_undefined_and_auc_handles_nulls():
    result = model_metrics([0, 0, 0], [0, 0, 0], [[0.9, 0.1], [0.8, 0.2], [0.7, 0.3]], 2)
    assert result["per_class"][1]["precision_undefined"] is True
    assert result["per_class"][1]["precision"] == 0.0

    perfect = model_metrics([0, 1, 0, 1], [0, 1, 0, 1], [[0.99, 0.01], [0.02, 0.98], [0.95, 0.05], [0.03, 0.97]], 2)
    assert perfect["roc_auc"]["value"] == 1.0

    missing = model_metrics([0, 1], [0, 1], None, 2)
    assert missing["roc_auc"]["value"] is None
    assert missing["roc_auc"]["reason"] == "unavailable"

    nan_stat = stat(float("nan"))
    assert nan_stat["value"] is None
