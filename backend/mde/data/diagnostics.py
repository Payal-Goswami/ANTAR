from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

import pandas as pd

from mde.errors import BadRequest

_DATETIME_PATTERNS = (
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?$"),
    re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$"),
)


def _is_all_missing(series: pd.Series) -> bool:
    return series.dropna().empty


def _consecutive_numbers(values: pd.Series) -> bool:
    if values.empty:
        return False
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return False
    unique = sorted(numeric.astype(float).unique().tolist())
    if not unique:
        return False
    expected = list(range(int(unique[0]), int(unique[-1]) + 1))
    return unique == expected


def _datetime_like_ratio(series: pd.Series) -> float:
    text = series.dropna().astype(str).str.strip()
    if text.empty:
        return 0.0
    matches = text.map(
        lambda value: any(pattern.fullmatch(value) for pattern in _DATETIME_PATTERNS)
    )
    return float(matches.mean())


def _looks_datetime_like(series: pd.Series) -> tuple[bool, float]:
    if pd.api.types.is_numeric_dtype(series):
        return False, 0.0
    ratio = _datetime_like_ratio(series)
    return ratio >= 0.9, ratio


def _looks_long_text(series: pd.Series) -> bool:
    non_missing = series.dropna().astype(str).str.strip()
    if non_missing.empty:
        return False
    mean_length = float(non_missing.map(len).mean())
    return mean_length > 50.0


def _looks_id_like(series: pd.Series) -> tuple[bool, str, float, bool]:
    non_missing = series.dropna()
    if non_missing.empty:
        return False, "unknown", 0.0, False

    if pd.api.types.is_string_dtype(series) or non_missing.map(lambda value: isinstance(value, str)).all():
        text = non_missing.astype(str).str.strip()
        is_id_string = text.map(
            lambda value: bool(
                re.fullmatch(r"[0-9a-fA-F]+(?:[-_][0-9a-fA-F]+)+", value)
                or re.fullmatch(r"[0-9a-fA-F]{8,}", value)
                or re.fullmatch(r"\d+", value)
            )
        )
        if is_id_string.all():
            unique_ratio = float(non_missing.nunique(dropna=True) / len(non_missing))
            if unique_ratio >= 0.95:
                return True, "string", unique_ratio, False
        return False, "string", 0.0, False

    numeric = pd.to_numeric(non_missing, errors="coerce")
    if numeric.notna().all() and (numeric % 1 == 0).all():
        unique_ratio = float(numeric.nunique(dropna=True) / len(numeric))
        if unique_ratio >= 0.95:
            consecutive = _consecutive_numbers(non_missing)
            return True, "whole_number", unique_ratio, consecutive
    return False, "whole_number", 0.0, False


def detect_feature_flags(train_df: pd.DataFrame, target_column: str | None = None) -> dict[str, dict]:
    flags: dict[str, dict] = {}
    for column_name in train_df.columns:
        if target_column is not None and column_name == target_column:
            continue
        series = train_df[column_name]
        entry: dict[str, object] = {
            "flag": None,
            "default_decision": "include",
            "reason": "",
            "details": {},
        }

        if _is_all_missing(series):
            entry["flag"] = "all_missing"
            entry["default_decision"] = "exclude"
            entry["reason"] = "column is entirely missing in the train partition"
            entry["details"] = {"n_missing": int(series.isna().sum())}
        else:
            datetime_like, datetime_ratio = _looks_datetime_like(series)
            if datetime_like:
                entry["flag"] = "datetime_like"
                entry["default_decision"] = "exclude"
                entry["reason"] = "at least 90% of non-missing values match datetime patterns"
                entry["details"] = {"ratio": datetime_ratio}
            elif _looks_long_text(series):
                entry["flag"] = "long_text"
                entry["default_decision"] = "exclude"
                entry["reason"] = "mean text length exceeds 50 characters"
            else:
                is_id, id_kind, unique_ratio, consecutive = _looks_id_like(series)
                if is_id:
                    entry["flag"] = "id_like"
                    entry["default_decision"] = "exclude" if id_kind == "string" else "undecided"
                    entry["reason"] = "column looks like a unique identifier"
                    entry["details"] = {
                        "kind": id_kind,
                        "unique_ratio": unique_ratio,
                        "consecutive": consecutive,
                    }

        flags[column_name] = entry
    return flags


def resolve_columns(
    feature_flags: dict[str, dict],
    decisions: dict[str, str] | None = None,
    target_column: str | None = None,
) -> dict[str, list[str]]:
    if target_column is not None and target_column in (decisions or {}):
        raise BadRequest(
            "The target column cannot be included in feature decisions.",
            {"target_column": target_column, "decision": decisions[target_column]},
        )

    normalized = decisions or {}
    included: list[str] = []
    excluded: list[str] = []
    undecided: list[str] = []

    for column_name, info in feature_flags.items():
        if column_name == target_column:
            continue
        flag = info.get("flag")
        decision = str(normalized.get(column_name, info.get("default_decision", "include"))).strip().lower()
        if flag == "all_missing":
            final = "exclude"
        elif decision in {"include", "exclude"}:
            final = decision
        elif decision == "undecided":
            final = "undecided"
        else:
            if info.get("default_decision") == "undecided":
                final = "undecided"
            else:
                final = info.get("default_decision", "include")

        if flag == "all_missing":
            final = "exclude"

        if final == "include":
            included.append(column_name)
        elif final == "exclude":
            excluded.append(column_name)
        else:
            undecided.append(column_name)

    return {"included": included, "excluded": excluded, "undecided": undecided}


def duplicate_report(
    train_df: pd.DataFrame,
    target_series: pd.Series,
    test_df: pd.DataFrame | None = None,
    test_target_series: pd.Series | None = None,
    feature_columns: Iterable[str] | None = None,
) -> dict:
    columns = list(feature_columns) if feature_columns is not None else list(train_df.columns)
    train_pairs = train_df[columns].copy()
    repeats: dict[tuple, list[int]] = defaultdict(list)

    for row_id, row in train_pairs.iterrows():
        key = tuple("__MISSING__" if pd.isna(value) else value for value in row.tolist())
        repeats[key].append(int(row_id))

    repeated_groups = {key: rows for key, rows in repeats.items() if len(rows) > 1}
    repeated_rows = sum(len(rows) for rows in repeated_groups.values())
    conflicting_groups = 0
    conflicting_rows = []
    agreement_total = 0
    if repeated_groups:
        for key, rows in repeated_groups.items():
            labels = target_series.loc[rows].tolist()
            unique_labels = set(labels)
            if len(unique_labels) > 1:
                conflicting_groups += 1
                conflicting_rows.extend(rows)
            agreement_total += max(labels.count(label) for label in unique_labels)

    report = {
        "repeated_rows": repeated_rows,
        "repeated_row_share": (repeated_rows / len(train_df)) if len(train_df) else 0.0,
        "conflicting_groups": conflicting_groups,
        "conflicting_group_rows": conflicting_rows,
        "agreement_ceiling": (
            (agreement_total / repeated_rows) if repeated_rows else "not_applicable"
        ),
    }

    if test_df is not None and test_target_series is not None:
        test_groups: dict[tuple, list] = defaultdict(list)
        for row_id, row in train_pairs.iterrows():
            key = tuple("__MISSING__" if pd.isna(value) else value for value in row.tolist())
            test_groups[key].append({"row_id": int(row_id), "label": target_series.loc[row_id]})

        matched = 0
        consistent = 0
        conflicting = 0
        for row_id, row in test_df[columns].iterrows():
            key = tuple("__MISSING__" if pd.isna(value) else value for value in row.tolist())
            if key not in test_groups:
                continue
            matched += 1
            train_labels = {item["label"] for item in test_groups[key]}
            label = test_target_series.loc[row_id]
            if len(train_labels) == 1 and next(iter(train_labels)) == label:
                consistent += 1
            else:
                conflicting += 1

        report["test_rows_matched"] = matched
        report["test_rows_consistent"] = consistent
        report["test_rows_conflicting"] = conflicting
        report["test_rows_matched_share"] = (matched / len(test_df)) if len(test_df) else 0.0
        report["test_rows_consistent_share"] = (consistent / len(test_df)) if len(test_df) else 0.0
        report["test_rows_conflicting_share"] = (conflicting / len(test_df)) if len(test_df) else 0.0

    return report


def build_feature_flags(train_df: pd.DataFrame, target_column: str | None = None) -> dict[str, dict]:
    return detect_feature_flags(train_df, target_column)


def summarize_duplicate_report(
    train_df: pd.DataFrame,
    target_series: pd.Series,
    test_df: pd.DataFrame | None = None,
    test_target_series: pd.Series | None = None,
    feature_columns: Iterable[str] | None = None,
) -> dict:
    return duplicate_report(
        train_df=train_df,
        target_series=target_series,
        test_df=test_df,
        test_target_series=test_target_series,
        feature_columns=feature_columns,
    )
