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


def test_numeric_slice_table_sorts_low_to_high_and_rounds_labels():
    feature = pd.Series([5.432198, 1.123456, 4.321987, 2.234567, 3.345678])
    y = np.array([0, 0, 0, 0, 0])
    predictions = np.array([0, 0, 0, 0, 0])

    rows = slice_table(feature, "numeric", y, predictions, predictions)
    labels = [row["label"] for row in rows]
    lower_bounds = [float(label[1:].split(",")[0]) for label in labels]
    decimal_places = [
        len(endpoint.split(".")[-1])
        for label in labels
        for endpoint in label[1:-1].split(", ")
    ]

    assert lower_bounds == sorted(lower_bounds)
    assert all(3 <= places <= 4 for places in decimal_places)


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


def test_categorical_slice_masks_stay_aligned_when_values_are_missing():
    feature = pd.Series(["a", None, "b", "a", None, "b"])
    y = np.array([0, 0, 1, 0, 1, 1])
    pa = np.array([0, 1, 1, 0, 0, 1])
    pb = np.array([1, 1, 0, 0, 1, 1])
    rows = slice_table(feature, "categorical", y, pa, pb)
    assert sum(row["n"] for row in rows) == len(feature)
    by_label = {row["label"]: row for row in rows}
    assert by_label["missing"]["n"] == 2
    assert by_label["a"]["n"] == 2
    assert by_label["b"]["n"] == 2
