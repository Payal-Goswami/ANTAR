import pandas as pd

from mde.data.report import build_quality_report
from mde.data.target import build_labelled_set


def test_quality_report_has_required_sections_and_missing_tokens():
    raw = pd.DataFrame(
        {
            "x": list(range(100)),
            "y": ["a" if i % 2 == 0 else "b" for i in range(100)],
            "target": [0 if i < 50 else 1 for i in range(100)],
        }
    )
    labelled = build_labelled_set(raw, "target")
    train = raw.iloc[:3].copy()
    test = raw.iloc[3:].copy()
    report = build_quality_report(
        raw_df=raw,
        labelled_set=labelled,
        train_df=train,
        test_df=test,
        feature_flags={},
        decisions={},
        target_column="target",
        missing_tokens={"features": ["NA"], "target": ["missing"]},
    )

    assert len(report["sections"]) == 6
    assert report["missing_tokens"]["features"] == ["NA"]
    assert report["missing_tokens"]["target"] == ["missing"]
