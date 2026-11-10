from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from mde.analysis.stats import holm, kappa, mcnemar_exact, stat


def buckets(y, pa, pb):
    y = np.asarray(y)
    pa = np.asarray(pa)
    pb = np.asarray(pb)
    both_right = int(np.sum((pa == y) & (pb == y)))
    both_wrong = int(np.sum((pa != y) & (pb != y)))
    only_a = int(np.sum((pa == y) & (pb != y)))
    only_b = int(np.sum((pb == y) & (pa != y)))
    both_wrong_diff = int(np.sum((pa != y) & (pb != y) & (pa != pb)))
    return {
        "both_right": both_right,
        "both_wrong": both_wrong,
        "both_wrong_diff": both_wrong_diff,
        "only_a": only_a,
        "only_b": only_b,
    }


def pair_stats(y, pa, pb, n_classes):
    y = np.asarray(y)
    pa = np.asarray(pa)
    pb = np.asarray(pb)
    counts = buckets(y, pa, pb)
    b = int(counts["only_a"])
    c = int(counts["only_b"])
    disagreement_count = int(np.sum(pa != pb))
    n = len(y)
    disagreement_rate = float(disagreement_count / n) if n else 0.0
    acc_a = float(np.mean(pa == y)) if n else 0.0
    acc_b = float(np.mean(pb == y)) if n else 0.0
    kapp = kappa(pa, pb)
    raw = kapp["value"] if isinstance(kapp, dict) else kapp
    per_true_class = {}
    for class_index in range(int(n_classes)):
        class_mask = y == class_index
        rows = int(np.sum(class_mask))
        if rows == 0:
            per_true_class[class_index] = {"rows": 0, "disagreements": 0, "rate": None}
            continue
        disagreements = int(np.sum(class_mask & (pa != pb)))
        rate = float(disagreements / rows) if rows else None
        per_true_class[class_index] = {"rows": rows, "disagreements": disagreements, "rate": rate}
    stats = mcnemar_exact(b, c)
    result = {
        "buckets": counts,
        "b": b,
        "c": c,
        "disagreement_count": disagreement_count,
        "disagreement_rate": disagreement_rate,
        "per_true_class": per_true_class,
        "kappa": raw,
        "kappa_stat": kapp,
        "accuracy_a": acc_a,
        "accuracy_b": acc_b,
        "accuracy_diff": float(acc_a - acc_b),
        "accuracy_a_stat": stat(acc_a),
        "accuracy_b_stat": stat(acc_b),
        "accuracy_diff_stat": stat(acc_a - acc_b),
        "mcnemar": stats,
    }
    return result


def all_pairs(y, preds):
    model_keys = [key for key in preds if preds.get(key, {}).get("status") == "done" and key != "dummy"]
    entries = []
    raw_p_values = []
    for left, right in combinations(model_keys, 2):
        left_pred = np.asarray(preds[left]["pred"])
        right_pred = np.asarray(preds[right]["pred"])
        stats = pair_stats(y, left_pred, right_pred, len(np.unique(y)))
        entry = {
            "model_a": left,
            "model_b": right,
            "buckets": stats["buckets"],
            "b": stats["b"],
            "c": stats["c"],
            "disagreement_count": stats["disagreement_count"],
            "disagreement_rate": stats["disagreement_rate"],
            "per_true_class": stats["per_true_class"],
            "kappa": stats["kappa"],
            "accuracy_a": stats["accuracy_a"],
            "accuracy_b": stats["accuracy_b"],
            "accuracy_diff": stats["accuracy_diff"],
            "mcnemar": stats["mcnemar"],
        }
        raw_p_values.append(stats["mcnemar"]["p"]["value"])
        entries.append(entry)
    adjusted = holm(raw_p_values)
    for entry, adj in zip(entries, adjusted):
        entry["p_raw"] = entry["mcnemar"]["p"]["value"]
        entry["p_holm"] = float(adj)
    return entries


def _prob_for_prediction(proba_values, prediction, row_index, class_names=None):
    if proba_values is None:
        return None
    array = np.asarray(proba_values)
    if array.ndim == 1:
        return float(array[row_index]) if len(array) > row_index else None
    if array.ndim == 2 and array.shape[1] > 0:
        if prediction is None:
            return None
        try:
            prediction_index = int(prediction)
        except (TypeError, ValueError):
            if class_names is not None:
                prediction_index = list(class_names).index(prediction)
            else:
                return None
        if prediction_index < 0 or prediction_index >= array.shape[1]:
            return None
        return float(array[row_index, prediction_index])
    return None


def disagreement_rows(features, y_true, preds, proba, class_names, a, b, bucket="all", true_class=None, page=1, page_size=25):
    if page < 1:
        raise ValueError("page must be at least 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")
    frame = features.copy()
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    y_values = np.asarray(y_true)
    pred_a = np.asarray(preds[a])
    pred_b = np.asarray(preds[b])
    rows = []
    for row_index in range(len(frame)):
        first = int(pred_a[row_index])
        second = int(pred_b[row_index])
        if first == second:
            continue
        actual = int(y_values[row_index])
        if first == actual and second != actual:
            row_bucket = "only_a"
        elif second == actual and first != actual:
            row_bucket = "only_b"
        elif first != actual and second != actual:
            row_bucket = "both_wrong_diff"
        else:
            continue
        if bucket != "all" and row_bucket != bucket:
            continue
        if true_class is not None and actual != true_class:
            continue
        feature_values = {}
        for col_name, value in frame.iloc[row_index].items():
            feature_values[col_name] = None if pd.isna(value) else value
        rows.append(
            {
                "row_id": int(row_index),
                "features": feature_values,
                "y_true": int(actual),
                "pred_a": int(first),
                "pred_b": int(second),
                "prob_a": _prob_for_prediction(proba.get(a), first, row_index, class_names),
                "prob_b": _prob_for_prediction(proba.get(b), second, row_index, class_names),
                "bucket": row_bucket,
            }
        )
    rows.sort(key=lambda item: item["row_id"])
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "rows": rows[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
