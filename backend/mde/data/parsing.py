import csv
import hashlib
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from mde.errors import CsvError, TooManyColumns


def read_header(path: str | Path, max_cols: int) -> list[str]:
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
            header = next(csv.reader(file), None)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise CsvError("The CSV header could not be read.") from error

    if header is None:
        raise CsvError("The CSV file is empty.")
    if not header:
        raise CsvError("The CSV file has no header row.")

    trimmed = [name.strip() for name in header]
    empty_positions = [index for index, name in enumerate(trimmed, start=1) if not name]
    duplicate_names = sorted(
        name for name, count in Counter(trimmed).items() if name and count > 1
    )
    if empty_positions or duplicate_names:
        raise CsvError(
            "The CSV header contains empty or duplicate column names.",
            {"empty_positions": empty_positions, "duplicate_names": duplicate_names},
        )
    if len(header) > max_cols:
        raise TooManyColumns(
            f"The CSV has {len(header)} columns; the maximum is {max_cols}.",
            {"n_cols": len(header), "max_cols": max_cols},
        )
    return header


def load_raw(
    path: str | Path,
    missing_tokens: Iterable[str] = (),
    target: str | None = None,
) -> pd.DataFrame:
    try:
        frame = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            na_values=[""],
            encoding="utf-8-sig",
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError, OSError) as error:
        raise CsvError("The CSV data could not be parsed.") from error

    frame = frame.replace(r"^\s*$", pd.NA, regex=True)
    tokens = set(missing_tokens)
    if tokens:
        for column in frame.columns:
            if column == target:
                continue
            matches = frame[column].map(
                lambda value: isinstance(value, str) and value.strip() in tokens
            )
            frame.loc[matches, column] = pd.NA

    frame.index = pd.RangeIndex(1, len(frame) + 1, name="row_id")
    return frame


def infer_feature_types(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict]]:
    typed = df.copy()
    report: dict[str, dict] = {}

    for column in df.columns:
        values = df[column]
        non_missing = values.dropna()
        if non_missing.empty:
            typed[column] = pd.Series(pd.NA, index=df.index, dtype="object")
            report[column] = {
                "kind": "empty",
                "inf_converted": 0,
                "offending": [],
                "suggest_tokens": False,
            }
            continue

        parsed = pd.to_numeric(non_missing, errors="coerce")
        infinite = np.isinf(parsed.to_numpy(dtype=float, na_value=np.nan))
        inf_count = int(infinite.sum())
        numeric_count = int(parsed.notna().sum())
        is_numeric = numeric_count == len(non_missing)

        if is_numeric:
            converted = pd.to_numeric(values, errors="coerce")
            converted = converted.replace([np.inf, -np.inf], np.nan)
            typed[column] = converted
            kind = "numeric"
            offending: list[str] = []
            suggest_tokens = False
        else:
            converted_values = values.copy()
            if inf_count:
                infinite_indexes = parsed.index[infinite]
                converted_values.loc[infinite_indexes] = pd.NA
            typed[column] = converted_values
            kind = "categorical"
            if numeric_count:
                non_numeric = non_missing.loc[parsed.isna()]
                offending = non_numeric.value_counts().head(5).index.tolist()
            else:
                offending = []
            suggest_tokens = bool(
                offending and numeric_count / len(non_missing) >= 0.9
            )

        report[column] = {
            "kind": kind,
            "inf_converted": inf_count,
            "offending": offending,
            "suggest_tokens": suggest_tokens,
        }

    return typed, report


def clean_target(
    series: pd.Series, tokens: Iterable[str]
) -> tuple[pd.Series, dict[str, int]]:
    token_set = set(tokens)
    cleaned: list[object] = []
    trimmed_count = 0

    for value in series:
        if pd.isna(value):
            cleaned.append(pd.NA)
            continue
        text = str(value)
        trimmed = text.strip()
        if trimmed != text and trimmed:
            trimmed_count += 1
        cleaned.append(pd.NA if not trimmed or trimmed in token_set else trimmed)

    result = pd.Series(cleaned, index=series.index, name=series.name, dtype="object")
    return result, {
        "trimmed_count": trimmed_count,
        "missing_count": int(result.isna().sum()),
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
