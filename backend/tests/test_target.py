import pandas as pd
import pytest

from mde.data.target import build_labelled_set
from mde.errors import TargetError


def test_build_labelled_set_validates_target_and_class_rules():
    df = pd.DataFrame({"target": ["a"] * 20 + ["b"] * 20 + ["c"] * 20 + ["d"] * 20 + ["e"] * 20})
    labelled = build_labelled_set(df, "target")
    assert len(labelled.y) == 100
    assert labelled.dropped_missing == 0
    assert labelled.trimmed == 0

    with pytest.raises(TargetError):
        build_labelled_set(pd.DataFrame({"target": ["a"] * 10}), "target")

    with pytest.raises(TargetError):
        build_labelled_set(pd.DataFrame({"target": ["a", "a", "b", "b", "c", "c", "d", "d", "e", "e", "f", "f", "g", "g", "h", "h", "i", "i", "j", "j", "k", "k", "l", "l", "m", "m", "n", "n", "o", "o", "p", "p", "q", "q", "r", "r", "s", "s", "t", "t"]}), "target")

    with pytest.raises(TargetError):
        build_labelled_set(pd.DataFrame({"target": ["a", "NA", "b", "b", "c", "c", "d", "d", "e", "e"]}), "target", tokens=["NA"])

    df_na = pd.DataFrame({"target": ["NA"] * 2 + ["benign"] * 50 + ["malignant"] * 50})
    labelled_na = build_labelled_set(df_na, "target", tokens=["NA"])
    assert "NA" not in labelled_na.class_counts
    assert labelled_na.class_counts["benign"] == 50


def test_build_labelled_set_warns_on_small_or_imbalanced_classes():
    df = pd.DataFrame({"target": ["a"] * 8 + ["b"] * 2 + ["c"] * 90})
    labelled = build_labelled_set(df, "target")
    assert any("fewer than 10 rows" in warning for warning in labelled.warnings)
    assert any("minority class" in warning for warning in labelled.warnings)
