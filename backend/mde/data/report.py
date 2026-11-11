from __future__ import annotations

from typing import Iterable

import pandas as pd

from mde.data.diagnostics import duplicate_report, detect_feature_flags, resolve_columns


def build_quality_report(
    raw_df: pd.DataFrame,
    labelled_set: object,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_flags: dict[str, dict] | None = None,
    decisions: dict[str, str] | None = None,
    target_column: str | None = None,
    missing_tokens: dict[str, Iterable[str]] | None = None,
    typing_report: dict[str, dict] | None = None,
    feature_columns: Iterable[str] | None = None,
) -> dict:
    if feature_flags is None:
        feature_flags = detect_feature_flags(train_df, target_column)
    resolved = resolve_columns(feature_flags, decisions=decisions or {}, target_column=target_column)
    duplicates = duplicate_report(
        train_df=train_df,
        target_series=labelled_set.y.loc[train_df.index],
        test_df=test_df,
        test_target_series=labelled_set.y.loc[test_df.index],
        feature_columns=feature_columns,
    )

    sections = [
        {
            "id": "file",
            "source": "whole file",
            "items": [
                {
                    "kind": "info",
                    "message": "Whole-file profile",
                    "data": {"n_rows": len(raw_df), "n_cols": len(raw_df.columns)},
                }
            ],
        },
        {
            "id": "labelled_set",
            "source": "labelled set",
            "items": [
                {
                    "kind": "info",
                    "message": "Labelled set summary",
                    "data": {
                        "n_rows": len(labelled_set.y),
                        "dropped_missing": labelled_set.dropped_missing,
                        "trimmed": labelled_set.trimmed,
                        "class_counts": labelled_set.class_counts,
                    },
                }
            ],
        },
        {
            "id": "feature_typing",
            "source": "whole file",
            "items": [
                {
                    "kind": "info",
                    "message": "Feature typing flags",
                    "data": typing_report if typing_report is not None else feature_flags,
                }
            ],
        },
        {
            "id": "train_flags",
            "source": "train partition",
            "items": [
                {
                    "kind": "info",
                    "message": "Columns requiring a decision",
                    "data": {
                        "flagged": {name: info for name, info in feature_flags.items() if info.get("flag")},
                        "resolved": resolved,
                    },
                }
            ],
        },
        {
            "id": "duplicates",
            "source": "train partition",
            "items": [
                {
                    "kind": "info",
                    "message": "Repeated-vector summary",
                    "data": {
                        "repeated_rows": duplicates["repeated_rows"],
                        "repeated_row_share": duplicates["repeated_row_share"],
                        "conflicting_groups": duplicates["conflicting_groups"],
                        "agreement_ceiling": duplicates["agreement_ceiling"],
                    },
                }
            ],
        },
        {
            "id": "test_vs_train",
            "source": "test versus train",
            "items": [
                {
                    "kind": "info",
                    "message": "Test rows matched to the train feature vectors",
                    "data": {
                        "matched": duplicates.get("test_rows_matched", 0),
                        "consistent": duplicates.get("test_rows_consistent", 0),
                        "conflicting": duplicates.get("test_rows_conflicting", 0),
                    },
                }
            ],
        },
    ]

    warnings = []
    for name, info in feature_flags.items():
        if info.get("flag"):
            warnings.append(f"{name}: {info['reason']}")

    tokens = missing_tokens or {"features": [], "target": []}
    return {
        "sections": sections,
        "warnings": warnings,
        "missing_tokens": {
            "features": list(tokens.get("features", [])),
            "target": list(tokens.get("target", [])),
        },
    }
