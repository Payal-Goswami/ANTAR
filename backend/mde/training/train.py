from __future__ import annotations

import time
from typing import Callable

import pandas as pd

from mde.training.pipeline import build_pipeline
from mde.training.registry import REGISTRY


def encode_labels(class_names_sorted: list[str], y_text: pd.Series) -> pd.Series:
    mapping = {label: index for index, label in enumerate(class_names_sorted)}
    encoded = y_text.map(mapping)
    return encoded.astype(int)


def fit_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
    model_keys: list[str],
    seed: int,
    n_jobs: int,
    on_progress: Callable[[str, str], None] | None = None,
) -> dict[str, dict]:
    ordered_keys = ["dummy", "logreg", "tree", "rf", "xgb"]
    allowed = set(model_keys or ordered_keys)
    results: dict[str, dict] = {}
    class_names_sorted = sorted(y_train.unique().tolist())
    encoded_train = encode_labels(class_names_sorted, y_train)

    for key in ordered_keys:
        if key not in allowed:
            continue
        if key not in REGISTRY:
            continue

        spec = REGISTRY[key]
        if on_progress is not None:
            on_progress(key, "running")

        try:
            pipeline = build_pipeline(spec, numeric_cols, categorical_cols, seed=seed, n_jobs=n_jobs)
            start = time.perf_counter()
            pipeline.fit(X_train, encoded_train)
            fit_seconds = time.perf_counter() - start
            preds = pipeline.predict(X_test)
            proba = pipeline.predict_proba(X_test) if spec.supports_proba else None
            clf = pipeline.named_steps["clf"]
            assert list(clf.classes_) == list(range(len(class_names_sorted)))
            results[key] = {
                "status": "done",
                "fit_seconds": fit_seconds,
                "pred": preds,
                "proba": proba,
                "model": pipeline,
            }
        except Exception as exc:
            results[key] = {
                "status": "failed",
                "error": str(exc),
                "model": None,
            }

        if on_progress is not None:
            on_progress(key, results[key]["status"])

    return results
