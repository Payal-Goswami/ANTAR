from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from mde.data.diagnostics import detect_feature_flags, resolve_columns
from mde.data.parsing import infer_feature_types, load_raw
from mde.data.report import build_quality_report
from mde.data.target import build_labelled_set


def prepare(
    path: str | Path,
    split_record: dict,
    missing_tokens: Iterable[str] = (),
    column_decisions: dict[str, str] | None = None,
) -> dict:
    params = split_record.get("params", {})
    target = params.get("target")
    if not isinstance(target, str) or not target:
        raise ValueError("The stored split record does not contain a target column.")

    feature_tokens = list(missing_tokens)
    target_tokens = list(params.get("target_missing_tokens", []))
    raw_df = load_raw(path, missing_tokens=feature_tokens, target=target)
    labelled_set = build_labelled_set(raw_df, target, target_tokens)
    feature_raw = raw_df.drop(columns=[target])
    typed_features, typing_report = infer_feature_types(feature_raw)

    train_ids = list(split_record["train_ids"])
    test_ids = list(split_record["test_ids"])
    train_df = typed_features.loc[train_ids].copy()
    test_df = typed_features.loc[test_ids].copy()
    feature_flags = detect_feature_flags(train_df)
    resolved = resolve_columns(
        feature_flags,
        decisions=column_decisions or {},
        target_column=target,
    )
    included = resolved["included"]
    report = build_quality_report(
        raw_df=raw_df,
        labelled_set=labelled_set,
        train_df=train_df,
        test_df=test_df,
        feature_flags=feature_flags,
        decisions=column_decisions or {},
        target_column=target,
        missing_tokens={"features": feature_tokens, "target": target_tokens},
        typing_report=typing_report,
        feature_columns=included,
    )
    needs_confirmation = any(
        info.get("flag") == "datetime_like" and column in included
        for column, info in feature_flags.items()
    )

    return {
        "raw_df": raw_df,
        "typed_df": typed_features,
        "train_df": train_df,
        "test_df": test_df,
        "labelled_set": labelled_set,
        "y_train": labelled_set.y.loc[train_ids].copy(),
        "y_test": labelled_set.y.loc[test_ids].copy(),
        "feature_flags": feature_flags,
        "typing_report": typing_report,
        "included": included,
        "excluded": resolved["excluded"],
        "undecided": resolved["undecided"],
        "quality": report,
        "needs_independence_confirmation": needs_confirmation,
    }
