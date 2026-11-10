from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from mde.training.registry import ModelSpec


def build_pipeline(
    spec: ModelSpec,
    numeric_cols: list[str],
    categorical_cols: list[str],
    seed: int,
    n_jobs: int,
) -> Pipeline:
    transformers: list[tuple[str, object, list[str]]] = []

    if numeric_cols:
        numeric_steps = [
            ("imputer", SimpleImputer(strategy="median")),
        ]
        if spec.needs_scaling:
            numeric_steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(numeric_steps), numeric_cols))

    if categorical_cols:
        transformers.append(
            (
                "categorical",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=20)),
                ]),
                categorical_cols,
            )
        )

    prep = ColumnTransformer(transformers=transformers, remainder="drop")
    estimator = spec.factory(seed=seed, n_jobs=n_jobs)
    return Pipeline([("prep", prep), ("clf", estimator)])
