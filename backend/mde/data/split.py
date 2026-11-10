from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

import pandas as pd
from sklearn.model_selection import train_test_split

from mde.data.subsample import subsample_ids
from mde.errors import SplitError


@dataclass
class SplitRecord:
    split_id: str
    params: dict
    train_ids: list[int]
    test_ids: list[int]
    class_table: dict[str, dict[str, int]]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "split_id": self.split_id,
            "params": self.params,
            "train_ids": self.train_ids,
            "test_ids": self.test_ids,
            "class_table": self.class_table,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SplitRecord":
        return cls(
            split_id=payload["split_id"],
            params=payload["params"],
            train_ids=list(payload["train_ids"]),
            test_ids=list(payload["test_ids"]),
            class_table=payload["class_table"],
            warnings=list(payload.get("warnings", [])),
        )


def make_split(
    y: pd.Series,
    test_size: float,
    seed: int,
    cap: int,
    params: dict,
) -> SplitRecord:
    y = y.copy()
    if len(y) > cap:
        selected_ids = subsample_ids(y, cap, test_size, seed)
        y = y.loc[selected_ids]
    else:
        selected_ids = sorted(y.index.tolist())

    class_counts = y.value_counts().to_dict()
    if len(class_counts) < 2:
        raise SplitError("The target must contain at least 2 classes.", {"class_counts": class_counts})
    min_required = math.ceil(1 / test_size)
    undersized = {str(label): int(count) for label, count in class_counts.items() if count < min_required}
    if undersized:
        raise SplitError(
            "At least one class is too small for the requested test size.",
            {"undersized_classes": undersized, "minimum_per_class": min_required},
        )

    try:
        train_ids, test_ids = train_test_split(
            sorted(y.index.tolist()),
            test_size=test_size,
            random_state=seed,
            stratify=y.reindex(sorted(y.index.tolist())),
        )
    except ValueError as exc:
        raise SplitError(
            "The split could not be formed with the requested test size.",
            {"test_size": test_size, "class_counts": class_counts, "error": str(exc)},
        ) from exc

    train_ids = sorted(train_ids)
    test_ids = sorted(test_ids)
    n_classes = len(class_counts)
    warnings: list[str] = []
    offending: dict[str, dict[str, int]] = {}
    class_table: dict[str, dict[str, int]] = {}

    for label in sorted(class_counts):
        n_before = int(class_counts[label])
        n_train = int((y.loc[train_ids] == label).sum())
        n_test = int((y.loc[test_ids] == label).sum())
        class_table[str(label)] = {
            "n_before": n_before,
            "n_after": n_before,
            "n_train": n_train,
            "n_test": n_test,
        }

        if n_train == 0 or n_test == 0:
            offending[str(label)] = {"n_rows": n_before, "n_train": n_train, "n_test": n_test}
        if n_test < 5:
            warnings.append(f"Class {label} has fewer than 5 test rows.")

    if offending:
        raise SplitError(
            "Each class must be present in both train and test partitions.",
            {"offending_classes": offending, "hint": "increase the test size or exclude this class explicitly"},
        )

    if len(train_ids) < n_classes or len(test_ids) < n_classes:
        raise AssertionError("Train and test partitions violate the minimum class count assertions.")

    return SplitRecord(
        split_id=uuid.uuid4().hex,
        params=params,
        train_ids=train_ids,
        test_ids=test_ids,
        class_table=class_table,
        warnings=warnings,
    )
