from pathlib import Path

from mde.data.profile import profile_frame
from mde.samples import ensure_sample_csv


def test_breast_cancer_sample_is_a_text_target_csv(tmp_path):
    sample_path = ensure_sample_csv("breast_cancer", tmp_path)
    profile = profile_frame(sample_path)

    assert profile["n_rows"] == 569
    assert profile["n_cols"] == 31
    by_name = {column["name"]: column for column in profile["columns"]}
    assert by_name["diagnosis"]["kind"] == "categorical"
    assert sum(column["kind"] == "numeric" for column in profile["columns"]) == 30
    assert Path(sample_path).exists()
