from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score

from mde.analysis.stats import stat


def _safe_roc_auc(y_true, proba, n_classes):
    if proba is None:
        return stat(None, "unavailable")
    if n_classes == 2:
        proba_values = np.asarray(proba)
        if proba_values.ndim == 1:
            y_score = proba_values
        else:
            y_score = proba_values[:, 1]
        try:
            return stat(float(roc_auc_score(y_true, y_score)), reason=None)
        except Exception:
            return stat(None, "unavailable")
    try:
        return stat(float(roc_auc_score(y_true, proba, multi_class="ovr", average="macro", labels=list(range(n_classes)))), reason=None)
    except Exception:
        return stat(None, "unavailable")


def model_metrics(y_true, pred, proba, n_classes):
    y_true = np.asarray(y_true)
    pred = np.asarray(pred)
    accuracy = float(accuracy_score(y_true, pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        pred,
        labels=list(range(n_classes)),
        zero_division=0,
        average=None,
    )
    per_class = []
    for idx in range(n_classes):
        precision_value = float(precision[idx])
        recall_value = float(recall[idx])
        f1_value = float(f1[idx])
        per_class.append(
            {
                "class_index": idx,
                "precision": precision_value,
                "recall": recall_value,
                "f1": f1_value,
                "support": int(support[idx]),
                "precision_undefined": bool(np.isnan(precision_value)) or (int(support[idx]) == 0 and precision_value == 0.0),
            }
        )
    matrix = confusion_matrix(y_true, pred, labels=list(range(n_classes)))
    macro_precision = float(np.mean(precision)) if len(precision) else 0.0
    macro_recall = float(np.mean(recall)) if len(recall) else 0.0
    macro_f1 = float(np.mean(f1)) if len(f1) else 0.0
    auc = _safe_roc_auc(y_true, proba, n_classes)
    return {
        "accuracy": stat(accuracy),
        "macro_precision": stat(macro_precision),
        "macro_recall": stat(macro_recall),
        "macro_f1": stat(macro_f1),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "roc_auc": auc,
    }
