from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    factory: Callable[..., object]
    needs_scaling: bool = False
    supports_proba: bool = True
    supports_sample_weight: bool = True
    seedable: bool = False


def _make_dummy(seed: int | None = None, n_jobs: int | None = None):
    return DummyClassifier(strategy="most_frequent")


def _make_logreg(seed: int | None = None, n_jobs: int | None = None):
    return LogisticRegression(max_iter=1000, random_state=seed)


def _make_tree(seed: int | None = None, n_jobs: int | None = None):
    return DecisionTreeClassifier(random_state=seed)


def _make_rf(seed: int | None = None, n_jobs: int | None = None):
    return RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=n_jobs)


def _make_xgb(seed: int | None = None, n_jobs: int | None = None):
    return XGBClassifier(tree_method="hist", random_state=seed, n_jobs=n_jobs)


REGISTRY: dict[str, ModelSpec] = {
    "dummy": ModelSpec("dummy", "Dummy", _make_dummy, needs_scaling=False, supports_proba=True, supports_sample_weight=False, seedable=False),
    "logreg": ModelSpec("logreg", "Logistic Regression", _make_logreg, needs_scaling=True, supports_proba=True, supports_sample_weight=True, seedable=True),
    "tree": ModelSpec("tree", "Decision Tree", _make_tree, needs_scaling=False, supports_proba=True, supports_sample_weight=True, seedable=True),
    "rf": ModelSpec("rf", "Random Forest", _make_rf, needs_scaling=False, supports_proba=True, supports_sample_weight=True, seedable=True),
    "xgb": ModelSpec("xgb", "XGBoost", _make_xgb, needs_scaling=False, supports_proba=True, supports_sample_weight=True, seedable=True),
}


def selectable() -> list[str]:
    return [key for key in REGISTRY if key != "dummy"]
