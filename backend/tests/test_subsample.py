import pandas as pd

from mde.data.subsample import allocate, subsample_ids


def test_allocate_matches_expected_cap_fixture():
    counts = {"A": 90000, "B": 9000, "C": 900, "D": 5, "E": 3}
    result = allocate(counts, 20000, 0.2)
    assert result == {"A": 18004, "B": 1804, "C": 184, "D": 5, "E": 3}


def test_allocate_keeps_rows_when_total_is_under_cap():
    counts = {"A": 100, "B": 50}
    assert allocate(counts, 300, 0.2) == counts


def test_subsample_ids_is_deterministic_per_seed_and_preserves_minimum_class_sizes():
    y = pd.Series(["A"] * 10 + ["B"] * 10 + ["C"] * 10 + ["D"] * 5, index=range(35))
    ids_a = subsample_ids(y, 20, 0.2, 42)
    ids_b = subsample_ids(y, 20, 0.2, 42)
    ids_c = subsample_ids(y, 20, 0.2, 7)
    assert ids_a == ids_b
    assert ids_a != ids_c
    assert len(ids_a) == 20
    assert len(set(ids_a)) == 20
