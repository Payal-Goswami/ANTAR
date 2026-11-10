from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from mde.data.parsing import clean_target
from mde.errors import TargetError


@dataclass
class LabelledSet:
    y: pd.Series
    dropped_missing: int
    trimmed: int
    class_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)


def build_labelled_set(
    df_raw: pd.DataFrame, target: str, tokens: Iterable[str] | None = None
) -> LabelledSet:
    if target not in df_raw.columns:
        raise TargetError(f"Target column '{target}' is not present.", {"target": target})

    token_list = list(tokens or [])
    series = df_raw[target].copy()
    cleaned, report = clean_target(series, token_list)
    missing_mask = cleaned.isna()
    dropped_missing = int(missing_mask.sum())
    kept = df_raw.loc[~missing_mask].copy()
    kept.loc[~missing_mask, target] = cleaned.loc[~missing_mask].to_numpy()

    if kept.empty:
        raise TargetError("The labelled set is empty after dropping missing targets.", {"target": target})

    y = kept[target].astype(str).copy()
    y.index = kept.index
    class_counts = y.value_counts(dropna=False).to_dict()
    unique_classes = list(class_counts)

    if not (2 <= len(class_counts) <= 10):
        raise TargetError(
            "The target must contain between 2 and 10 classes.",
            {"class_count": len(class_counts), "classes": unique_classes},
        )

    if any(count < 2 for count in class_counts.values()):
        offenders = {label: count for label, count in class_counts.items() if count < 2}
        raise TargetError(
            "Every class must have at least 2 rows.",
            {"offending_classes": offenders},
        )

    if len(y) < 100:
        raise TargetError(
            "The labelled set must contain at least 100 rows.",
            {"n_rows": len(y), "class_counts": class_counts},
        )

    warnings: list[str] = []
    if any(count < 10 for count in class_counts.values()):
        warnings.append("Some classes have fewer than 10 rows.")
    if len(y) < 500:
        warnings.append("The labelled set has fewer than 500 rows.")
    minority = min(class_counts.values()) / len(y)
    if minority < 0.05:
        warnings.append("The minority class is below 5% of the labelled set.")

    return LabelledSet(
        y=y,
        dropped_missing=dropped_missing,
        trimmed=report["trimmed_count"],
        class_counts={str(key): int(value) for key, value in class_counts.items()},
        warnings=warnings,
    )
