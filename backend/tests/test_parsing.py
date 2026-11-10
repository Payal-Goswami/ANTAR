import hashlib
from pathlib import Path

import pandas as pd
import pytest

from mde.data.parsing import (
    clean_target,
    infer_feature_types,
    load_raw,
    read_header,
    sha256_file,
)
from mde.errors import CsvError, TooManyColumns


def fixture(name: str) -> str:
    return str(Path(__file__).parent / "fixtures" / name)


def test_header_rejects_duplicate_and_empty_names():
    with pytest.raises(CsvError) as duplicate:
        read_header(fixture("header_dupe.csv"), max_cols=5)
    assert duplicate.value.details["duplicate_names"] == ["id"]

    with pytest.raises(CsvError) as empty:
        read_header(fixture("header_empty.csv"), max_cols=5)
    assert empty.value.details["empty_positions"] == [2]


def test_header_rejects_too_many_columns_and_empty_file(tmp_path):
    wide = tmp_path / "wide.csv"
    wide.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(TooManyColumns):
        read_header(wide, max_cols=2)

    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(CsvError):
        read_header(empty, max_cols=5)

    undecodable = tmp_path / "undecodable.csv"
    undecodable.write_bytes(b"\xff")
    with pytest.raises(CsvError):
        read_header(undecodable, max_cols=5)


def test_header_reads_utf8_bom(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_text("\ufeffname,value\nx,1\n", encoding="utf-8")
    assert read_header(path, max_cols=5) == ["name", "value"]


def test_missing_tokens_only_apply_to_features():
    frame = load_raw(fixture("na_class.csv"), missing_tokens=["NA", "N/A"], target="target")
    assert frame.loc[1, "target"] == "NA"
    assert pd.isna(frame.loc[1, "feature"])
    assert pd.isna(frame.loc[2, "feature"])
    assert frame.loc[3, "feature"] == "NULL"

    default_frame = load_raw(fixture("na_class.csv"))
    assert default_frame["target"].tolist() == ["NA", "benign", "malignant"]
    assert default_frame["feature"].tolist() == ["NA", "N/A", "NULL"]


def test_whitespace_is_missing_and_padded_number_parses(tmp_path):
    path = tmp_path / "values.csv"
    path.write_text("number,blank\n 5 ,   \n", encoding="utf-8")
    frame = load_raw(path)
    typed, report = infer_feature_types(frame)
    assert typed.loc[1, "number"] == 5
    assert pd.isna(typed.loc[1, "blank"])
    assert report["number"]["kind"] == "numeric"


def test_mixed_numeric_column_reports_offending_values_and_suggestion():
    frame = load_raw(fixture("mixed_type.csv"))
    typed, report = infer_feature_types(frame)
    assert report["amount"]["kind"] == "categorical"
    assert report["amount"]["offending"] == ["bad"]
    assert report["amount"]["suggest_tokens"] is True
    assert typed.loc[10, "amount"] == "bad"


def test_text_nan_is_categorical_and_infinity_becomes_missing():
    nan_frame = pd.DataFrame({"value": ["1", "nan"]})
    typed_nan, report_nan = infer_feature_types(nan_frame)
    assert report_nan["value"]["kind"] == "categorical"
    assert typed_nan["value"].tolist() == ["1", "nan"]

    inf_frame = load_raw(fixture("inf.csv"))
    typed_inf, report_inf = infer_feature_types(inf_frame)
    assert report_inf["value"]["kind"] == "numeric"
    assert report_inf["value"]["inf_converted"] == 2
    assert typed_inf["value"].tolist()[0] == 1
    assert typed_inf["value"].isna().tolist() == [False, True, True]


def test_clean_target_trims_without_normalizing_case_and_respects_tokens():
    raw = load_raw(fixture("target_spaces.csv"))["target"]
    cleaned, report = clean_target(raw, tokens=[])
    assert cleaned.tolist() == ["yes", "Yes", "yes"]
    assert report == {"trimmed_count": 1, "missing_count": 0}

    labels = pd.Series(["NA", " yes ", "", "Yes"])
    cleaned, report = clean_target(labels, tokens=["NA"])
    assert cleaned.iloc[0] is pd.NA
    assert cleaned.iloc[1] == "yes"
    assert pd.isna(cleaned.iloc[2])
    assert cleaned.iloc[3] == "Yes"
    assert report == {"trimmed_count": 1, "missing_count": 2}


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "bytes.csv"
    path.write_bytes(b"header\nvalue\n")
    assert sha256_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
