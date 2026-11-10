import pandas as pd

from mde.training.registry import REGISTRY
from mde.training.train import encode_labels, fit_models


def test_label_encoding_and_model_fit_result_keys():
    y = pd.Series(["b", "a", "b", "a"])
    encoded = encode_labels(["a", "b"], y)
    assert encoded.tolist() == [1, 0, 1, 0]

    X_train = pd.DataFrame({"num": [0.0, 1.0, 2.0, 3.0], "cat": ["u", "v", "u", "v"]})
    X_test = pd.DataFrame({"num": [0.5, 2.5], "cat": ["u", "v"]})
    y_train = pd.Series(["a", "b", "a", "b"])
    results = fit_models(X_train, y_train, X_test, ["num"], ["cat"], ["dummy", "logreg"], seed=7, n_jobs=1)
    assert set(results) == {"dummy", "logreg"}
    assert results["dummy"]["status"] == "done"


def test_failed_model_is_recorded_without_stopping_others(monkeypatch):
    X_train = pd.DataFrame({"x": [0, 1, 2, 3]})
    X_test = pd.DataFrame({"x": [0.5, 1.5]})
    y_train = pd.Series([0, 1, 0, 1])
    original_spec = REGISTRY["tree"]

    def broken_factory(seed=None, n_jobs=None):
        raise ValueError("boom")

    monkeypatch.setitem(REGISTRY, "tree", original_spec.__class__(
        key="tree",
        label="Decision Tree",
        factory=broken_factory,
        needs_scaling=False,
        supports_proba=True,
        supports_sample_weight=True,
        seedable=True,
    ))
    results = fit_models(X_train, y_train, X_test, ["x"], [], ["dummy", "tree"], seed=7, n_jobs=1)
    assert results["tree"]["status"] == "failed"
    assert results["dummy"]["status"] == "done"
    monkeypatch.setitem(REGISTRY, "tree", original_spec)
