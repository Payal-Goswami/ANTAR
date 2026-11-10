from __future__ import annotations

import math

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score


def stat(value, reason=None):
    if value is None:
        return {"value": None, "reason": reason}
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return {"value": None, "reason": reason or "invalid_value"}
    if not math.isfinite(numeric):
        return {"value": None, "reason": reason or "non_finite_value"}
    return {"value": numeric, "reason": reason}


def mcnemar_exact(b, c):
    total = int(b) + int(c)
    if total == 0:
        return {"p": stat(1.0), "flag": "no_discordant_pairs"}
    p_value = float(binomtest(min(int(b), int(c)), total, p=0.5, alternative="two-sided").pvalue)
    return {"p": stat(p_value), "flag": None}


def holm(pvalues):
    values = [float(value) for value in pvalues]
    if not values:
        return []
    order = sorted(range(len(values)), key=lambda idx: values[idx])
    m = len(values)
    adjusted = [0.0] * m
    running = 0.0
    for rank, original_index in enumerate(order):
        raw = values[original_index]
        candidate = max(running, (m - rank) * raw)
        adjusted_value = min(1.0, candidate)
        running = adjusted_value
        adjusted[original_index] = adjusted_value
    return adjusted


def wilson(k, n):
    if n == 0:
        return {"low": stat(None, "n_is_zero"), "high": stat(None, "n_is_zero")}
    ci = binomtest(int(k), int(n), p=0.5, alternative="two-sided").proportion_ci(
        confidence_level=0.95,
        method="wilson",
    )
    return {"low": stat(float(ci.low)), "high": stat(float(ci.high))}


def kappa(pred_a, pred_b):
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    if pred_a.size == 0 or pred_b.size == 0:
        return stat(None, "both_models_predict_one_class")
    unique_a = np.unique(pred_a)
    unique_b = np.unique(pred_b)
    if unique_a.size == 1 and unique_b.size == 1 and np.all(pred_a == pred_b):
        return stat(None, "both_models_predict_one_class")
    score = float(cohen_kappa_score(pred_a, pred_b))
    if not math.isfinite(score):
        return stat(None, "both_models_predict_one_class")
    return stat(score)
