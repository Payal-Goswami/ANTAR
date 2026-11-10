import pandas as pd

from mde.training.pipeline import build_pipeline
from mde.training.registry import REGISTRY, selectable


def test_registry_has_expected_keys_and_seedable_factories():
    assert list(REGISTRY) == ["dummy", "logreg", "tree", "rf", "xgb"]
    assert selectable() == ["logreg", "tree", "rf", "xgb"]
    for key in ["logreg", "tree", "rf", "xgb"]:
        model = REGISTRY[key].factory(seed=7, n_jobs=1)
        assert model.random_state == 7
    assert REGISTRY["logreg"].needs_scaling is True
    assert REGISTRY["tree"].needs_scaling is False
    assert REGISTRY["rf"].needs_scaling is False
    assert REGISTRY["xgb"].needs_scaling is False


def test_pipeline_fits_on_numeric_and_categorical_data():
    X = pd.DataFrame({
        "num": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "cat": ["a", "b", "a", "b", "a", "b"],
        "missing": [None, "a", None, "b", "a", "b"],
    })
    y = pd.Series([0, 1, 0, 1, 0, 1])
    pipeline = build_pipeline(REGISTRY["logreg"], ["num"], ["cat", "missing"], seed=7, n_jobs=1)
    pipeline.fit(X, y)
    preds = pipeline.predict(X)
    assert len(preds) == len(X)

    all_numeric = pd.DataFrame({"n1": [1.0, 2.0, 3.0, 4.0], "n2": [4.0, 5.0, 6.0, 7.0]})
    pipeline2 = build_pipeline(REGISTRY["tree"], ["n1", "n2"], [], seed=7, n_jobs=1)
    pipeline2.fit(all_numeric, pd.Series([0, 1, 0, 1]))
    assert len(pipeline2.predict(all_numeric)) == 4

    all_categ = pd.DataFrame({"c1": ["x", "y", "x", "y"], "c2": ["m", "n", "m", "n"]})
    pipeline3 = build_pipeline(REGISTRY["rf"], [], ["c1", "c2"], seed=7, n_jobs=1)
    pipeline3.fit(all_categ, pd.Series([0, 1, 0, 1]))
    assert len(pipeline3.predict(all_categ)) == 4
