import json
import math

import numpy as np
import pytest
from scipy.stats import binomtest

from mde.analysis.stats import holm, kappa, mcnemar_exact, wilson


def test_mcnemar_exact_matches_scipy_and_handles_zero_discordant_pairs():
    rng = np.random.default_rng(0)
    for _ in range(300):
        b = int(rng.integers(1, 100))
        c = int(rng.integers(1, 100))
        expected = binomtest(min(b, c), b + c, p=0.5, alternative="two-sided").pvalue
        actual = mcnemar_exact(b, c)["p"]["value"]
        assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)

    assert mcnemar_exact(3, 3)["p"]["value"] == pytest.approx(1.0)
    assert mcnemar_exact(0, 0)["flag"] == "no_discordant_pairs"
    assert mcnemar_exact(0, 0)["p"]["value"] == 1.0


def test_holm_matches_expected_values_and_is_monotone():
    adjusted = holm([0.01, 0.04, 0.03, 0.2])
    assert adjusted == pytest.approx([0.04, 0.09, 0.09, 0.2])
    raw = [0.01, 0.04, 0.03, 0.2]
    assert all(adj >= raw[idx] for idx, adj in enumerate(adjusted))
    assert all(adj <= 1.0 for adj in adjusted)


def test_wilson_matches_textbook_formula_and_handles_zero_n():
    checks = [(0, 10), (3, 40), (14, 40), (35, 100), (10, 10)]
    for k, n in checks:
        result = wilson(k, n)
        expected = binomtest(k, n, p=0.5).proportion_ci(confidence_level=0.95, method="wilson")
        assert result["low"]["value"] == pytest.approx(expected.low, rel=1e-9, abs=1e-9)
        assert result["high"]["value"] == pytest.approx(expected.high, rel=1e-9, abs=1e-9)

    result = wilson(0, 0)
    assert result["low"]["value"] is None
    assert result["high"]["value"] is None
    assert result["low"]["reason"] == "n_is_zero"


def test_kappa_contract():
    assert kappa([0, 0, 0], [0, 0, 0])["value"] is None
    assert kappa([0, 1, 0], [0, 1, 0])["value"] == pytest.approx(1.0)
    assert kappa([0, 0, 0], [1, 1, 1])["value"] == pytest.approx(0.0)

    json.dumps({"kappa": kappa([0, 1], [0, 1])}, allow_nan=False)
