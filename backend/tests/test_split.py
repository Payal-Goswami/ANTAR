import pandas as pd
import pytest

from mde.data.split import make_split
from mde.errors import SplitError


def test_make_split_on_rare_class_invalidates_small_test_set():
    y = pd.Series(["A"] * 90 + ["B"] * 5 + ["C"] * 5, index=range(100))
    with pytest.raises(SplitError):
        make_split(y, 0.1, 0, 1000, {"target": "target", "seed": 0, "test_size": 0.1})


def test_make_split_succeeds_and_round_trips():
    y = pd.Series(["A"] * 80 + ["B"] * 10 + ["C"] * 10, index=range(100))
    record = make_split(y, 0.2, 42, 1000, {"target": "target"})
    assert len(record.train_ids) + len(record.test_ids) == 100
    assert set(record.train_ids).isdisjoint(record.test_ids)
    assert set(record.train_ids) | set(record.test_ids) == set(y.index)
    assert record.params["target"] == "target"
    payload = record.to_dict()
    restored = type(record).from_dict(payload)
    assert restored.train_ids == record.train_ids
    assert restored.test_ids == record.test_ids


def test_make_split_fails_when_unsubsampled_minority_class_is_too_small():
    y = pd.Series(["A"] * 90092 + ["B"] * 9000 + ["C"] * 900 + ["D"] * 5 + ["E"] * 3, index=range(100000))
    with pytest.raises(SplitError):
        make_split(y, 0.2, 0, 100000, {"target": "target"})
