import pandas as pd

from mde.training.pipeline import build_pipeline
from mde.training.registry import REGISTRY


def test_no_leakage_in_numeric_imputer_statistics():
    X_train = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    X_test = pd.DataFrame({"x": [1000.0, 2000.0]})
    y_train = pd.Series([0, 1, 0, 1, 0])
    pipeline = build_pipeline(REGISTRY["logreg"], ["x"], [], seed=7, n_jobs=1)
    pipeline.fit(X_train, y_train)
    imputer = pipeline.named_steps["prep"].transformers_[0][1].named_steps["imputer"]
    assert imputer.statistics_[0] == 3.0
    assert pipeline.predict(X_test).shape[0] == 2


def test_unseen_category_in_test_does_not_crash_prediction():
    X_train = pd.DataFrame({"cat": ["a", "b", "a", "b"]})
    X_test = pd.DataFrame({"cat": ["c", "a"]})
    y_train = pd.Series([0, 1, 0, 1])
    pipeline = build_pipeline(REGISTRY["tree"], [], ["cat"], seed=7, n_jobs=1)
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    assert len(preds) == 2
