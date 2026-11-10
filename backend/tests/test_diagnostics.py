import pandas as pd
import pytest

from mde.data.diagnostics import detect_feature_flags, duplicate_report, resolve_columns
from mde.errors import BadRequest
from mde.samples import ensure_sample_csv


def test_feature_flags_match_id_and_datetime_requirements():
    train = pd.DataFrame(
        {
            "row_id": list(range(1, 301)),
            "uuid_text": [f"{i:08x}-{i:04x}-abcd" for i in range(300)],
            "income": list(range(300)),
            "age": [18 + (i % 72) for i in range(300)],
            "float_col": [float(i) / 3.0 for i in range(300)],
            "id_float": [float(i) for i in range(1, 301)],
            "date_col": ["2020-01-05", "12/31/2020"] * 150,
            "name": ["Alice", "Bob"] * 150,
        }
    )
    flags = detect_feature_flags(train)
    assert flags["row_id"]["flag"] == "id_like"
    assert flags["row_id"]["default_decision"] == "undecided"
    assert flags["row_id"]["details"]["consecutive"] is True

    assert flags["uuid_text"]["flag"] == "id_like"
    assert flags["uuid_text"]["default_decision"] == "exclude"

    assert flags["income"]["flag"] == "id_like"
    assert flags["income"]["default_decision"] == "undecided"

    assert flags["age"]["flag"] is None
    assert flags["float_col"]["flag"] is None
    assert flags["id_float"]["flag"] == "id_like"
    assert flags["date_col"]["flag"] == "datetime_like"
    assert flags["name"]["flag"] is None


def test_breast_cancer_sample_has_no_flags():
    path = ensure_sample_csv("breast_cancer", "data/samples")
    train = pd.read_csv(path)
    flags = detect_feature_flags(train)
    assert all(info["flag"] is None for info in flags.values())


def test_duplicate_report_matches_expected_train_and_test_counts():
    train = pd.DataFrame(
        {
            "x": [1, 1, 1, 1, 2, 2, None, None, 9, 10],
            "c": ["u", "u", "u", "u", "v", "v", None, None, "q", "y"],
        },
        index=[101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
    )
    target = pd.Series([0, 0, 1, 1, 1, 1, 0, 0, 0, 1], index=train.index)
    test = pd.DataFrame(
        {
            "x": [1, 2, None, 9],
            "c": ["u", "v", None, "z"],
        },
        index=[201, 202, 203, 204],
    )
    test_target = pd.Series([0, 1, 0, 0], index=test.index)

    report = duplicate_report(train, target, test, test_target)
    assert report["repeated_rows"] == 8
    assert report["conflicting_groups"] == 1
    assert report["agreement_ceiling"] == pytest.approx(0.75)
    assert report["test_rows_matched"] == 3
    assert report["test_rows_consistent"] == 2
    assert report["test_rows_conflicting"] == 1


def test_resolve_columns_rejects_target_and_keeps_all_missing_excluded():
    flags = {
        "id_col": {"flag": "id_like", "default_decision": "undecided"},
        "all_missing": {"flag": "all_missing", "default_decision": "exclude"},
    }
    resolved = resolve_columns(flags, decisions={"id_col": "include", "all_missing": "include"})
    assert resolved["included"] == ["id_col"]
    assert resolved["excluded"] == ["all_missing"]
    assert resolved["undecided"] == []

    with pytest.raises(BadRequest):
        resolve_columns(flags, decisions={"id_col": "exclude", "target": "exclude"}, target_column="target")


def test_datetime_like_columns_are_detected_but_not_numeric_ones():
    df = pd.DataFrame(
        {
            "date_col": ["2020-01-05", "12/31/2020", "01/02/2021"],
            "month_names": ["Jan", "March", "February"],
            "numbers": [1.1, 2.2, 3.3],
        }
    )
    flags = detect_feature_flags(df)
    assert flags["date_col"]["flag"] == "datetime_like"
    assert flags["month_names"]["flag"] is None
    assert flags["numbers"]["flag"] is None
