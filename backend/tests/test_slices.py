import json

import numpy as np
import pandas as pd
import pytest

from mde.analysis.slices import slice_table


def test_numeric_slice_table_handles_repeated_values_and_missing():
    feature = pd.Series([1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, np.nan, np.nan])
    y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0])
    pa = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0])
    pb = np.array([0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1])
    rows = slice_table(feature, "numeric", y, pa, pb)
    assert len(rows) < 5
    labels = {row["label"] for row in rows}
    assert "missing" in labels

    for row in rows:
        assert row["low_support"] in (True, False)

    json.dumps({"rows": rows}, allow_nan=False)


def test_categorical_slice_table_uses_top_values_and_other_bucket():
    values = [f"v{i}" for i in range(12)] * 3
    feature = pd.Series(values)
    y = np.array([0] * len(feature))
    pa = np.array([0] * len(feature))
    pb = np.array([1 if i % 2 == 0 else 0 for i in range(len(feature))])
    rows = slice_table(feature, "categorical", y, pa, pb)
    non_missing = [row for row in rows if row["label"] != "missing"]
    assert len(non_missing) == 9
    assert any(row["label"] == "Other" for row in non_missing)
