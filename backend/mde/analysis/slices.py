from __future__ import annotations

import numpy as np
import pandas as pd

from mde.analysis.stats import wilson


def _slice_metrics(feature_values, y_true, pa, pb):
    mask = feature_values.notna()
    y = np.asarray(y_true)[mask.to_numpy()]
    pred_a = np.asarray(pa)[mask.to_numpy()]
    pred_b = np.asarray(pb)[mask.to_numpy()]
    n = len(y)
    if n == 0:
        return None
    only_a = int(np.sum((pred_a == y) & (pred_b != y)))
    only_b = int(np.sum((pred_b == y) & (pred_a != y)))
    disagreements = int(np.sum(pred_a != pred_b))
    acc_a = float(np.mean(pred_a == y)) if n else 0.0
    acc_b = float(np.mean(pred_b == y)) if n else 0.0
    ci = wilson(disagreements, n)
    return {
        "n": int(n),
        "acc_a": acc_a,
        "acc_b": acc_b,
        "b": only_a,
        "c": only_b,
        "disagreements": disagreements,
        "disagreement_rate": float(disagreements / n) if n else 0.0,
        "wilson_low": ci["low"]["value"],
        "wilson_high": ci["high"]["value"],
    }


def slice_table(feature, kind, y, pa, pb):
    feature = pd.Series(feature)
    y = np.asarray(y)
    pa = np.asarray(pa)
    pb = np.asarray(pb)
    rows = []

    missing_mask = feature.isna()
    if missing_mask.any():
        missing_values = missing_mask.to_numpy()
        missing_y = y[missing_values]
        missing_pa = pa[missing_values]
        missing_pb = pb[missing_values]
        rows.append({
            "label": "missing",
            "n": int(len(missing_y)),
            "acc_a": float(np.mean(missing_pa == missing_y)),
            "acc_b": float(np.mean(missing_pb == missing_y)),
            "b": int(np.sum((missing_pa == missing_y) & (missing_pb != missing_y))),
            "c": int(np.sum((missing_pb == missing_y) & (missing_pa != missing_y))),
            "disagreements": int(np.sum(missing_pa != missing_pb)),
            "disagreement_rate": float(np.mean(missing_pa != missing_pb)),
            "wilson_low": wilson(int(np.sum(missing_pa != missing_pb)), len(missing_y))["low"]["value"],
            "wilson_high": wilson(int(np.sum(missing_pa != missing_pb)), len(missing_y))["high"]["value"],
            "low_support": bool(len(missing_y) < 30 or np.sum(missing_pa != missing_pb) < 5),
        })

    valid = feature[~missing_mask]
    if valid.empty:
        return rows

    if kind == "numeric":
        bins = pd.qcut(valid, q=5, duplicates="drop", precision=4)
        if bins.nunique() <= 1:
            bins = pd.Series(["all"] * len(valid), index=valid.index)
            intervals = ["all"]
        else:
            intervals = bins.cat.categories
        for interval in intervals:
            group_mask = bins == interval
            group = valid[group_mask]
            group_index = group.index
            ids = feature.index.isin(group_index)
            metrics = _slice_metrics(pd.Series(np.where(ids, feature, np.nan), index=feature.index), y, pa, pb)
            row = {
                "label": str(interval),
                "n": int(np.sum(ids)),
                "acc_a": metrics["acc_a"],
                "acc_b": metrics["acc_b"],
                "b": metrics["b"],
                "c": metrics["c"],
                "disagreements": metrics["disagreements"],
                "disagreement_rate": metrics["disagreement_rate"],
                "wilson_low": metrics["wilson_low"],
                "wilson_high": metrics["wilson_high"],
                "low_support": bool(metrics["n"] < 30 or metrics["disagreements"] < 5),
            }
            rows.append(row)
        return rows

    counts = valid.value_counts(dropna=False)
    top = counts.head(8).index.tolist()
    other_total = int(counts.iloc[8:].sum()) if len(counts) > 8 else 0
    labels = []
    if top:
        labels.extend(top)
    if other_total:
        labels.append("Other")
    if not labels:
        return rows
    for label in labels:
        if label == "Other":
            mask = feature.isin(counts.index[8:]) if len(counts) > 8 else pd.Series(False, index=feature.index)
        else:
            mask = feature == label
        mask = mask.fillna(False)
        idx = np.asarray(mask.to_numpy())
        n = int(np.sum(idx))
        if n == 0:
            continue
        row = {
            "label": str(label),
            "n": n,
            "acc_a": float(np.mean(pa[idx] == y[idx])) if n else 0.0,
            "acc_b": float(np.mean(pb[idx] == y[idx])) if n else 0.0,
            "b": int(np.sum((pa[idx] == y[idx]) & (pb[idx] != y[idx]))),
            "c": int(np.sum((pb[idx] == y[idx]) & (pa[idx] != y[idx]))),
            "disagreements": int(np.sum(pa[idx] != pb[idx])) if n else 0,
            "disagreement_rate": float(np.mean(pa[idx] != pb[idx])) if n else 0.0,
            "wilson_low": wilson(int(np.sum(pa[idx] != pb[idx])), n)["low"]["value"],
            "wilson_high": wilson(int(np.sum(pa[idx] != pb[idx])), n)["high"]["value"],
            "low_support": bool(n < 30 or int(np.sum(pa[idx] != pb[idx])) < 5),
        }
        rows.append(row)
    return rows
