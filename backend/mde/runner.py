from __future__ import annotations

import importlib.metadata
import threading
from datetime import datetime, timezone
from typing import Callable

import numpy as np
import pandas as pd

from mde.analysis.metrics import model_metrics
from mde.analysis.pairs import all_pairs
from mde.data.prepare import prepare
from mde.errors import DecisionRequired, ConfirmationRequired
from mde.store import FileRunStore
from mde.training.train import encode_labels, fit_models


def _json_value(value):
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _versions() -> dict[str, str]:
    versions = {}
    for package in ("numpy", "pandas", "scikit-learn", "scipy", "xgboost", "pyarrow"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _model_params(results: dict) -> dict:
    params = {}
    for key, result in results.items():
        pipeline = result.get("model")
        if pipeline is not None:
            params[key] = _json_value(pipeline.named_steps["clf"].get_params(deep=True))
    return params


def run_experiment(
    store: FileRunStore,
    settings,
    run_id: str,
    request: dict,
) -> None:
    upload_id = request["upload_id"]
    try:
        split = store.load_split(upload_id, request["split_id"])
        store.update_status(run_id, {"state": "running", "stage": "preparing"})
        prepared = prepare(
            store.upload_path(upload_id),
            split,
            missing_tokens=request["missing_tokens"],
            column_decisions=request["column_decisions"],
        )
        if prepared["undecided"]:
            raise DecisionRequired(
                "Some feature columns still need an include or exclude decision.",
                {"columns": prepared["undecided"]},
            )
        if prepared["needs_independence_confirmation"] and not request["independence_confirmed"]:
            raise ConfirmationRequired(
                "Confirm that rows are independent before using a datetime-like feature.",
                {"columns": [
                    name for name, flag in prepared["feature_flags"].items()
                    if flag.get("flag") == "datetime_like" and name in prepared["included"]
                ]},
            )

        included = prepared["included"]
        kinds = prepared["typing_report"]
        numeric_cols = [name for name in included if kinds[name]["kind"] == "numeric"]
        categorical_cols = [name for name in included if kinds[name]["kind"] != "numeric"]
        class_names = sorted(prepared["labelled_set"].y.unique().tolist())
        y_test = encode_labels(class_names, prepared["y_test"])
        X_train = prepared["train_df"][included]
        X_test = prepared["test_df"][included]
        selected_models = ["dummy", *request["models"]]

        def on_progress(model_key: str, state: str) -> None:
            status = store.read_run_json(run_id, "status.json")
            model_states = status.setdefault("models", {})
            model_states[model_key] = {"status": state}
            store.update_status(run_id, {"models": model_states, "stage": "training"})

        initial_status = store.read_run_json(run_id, "status.json")
        initial_status["stage"] = "training"
        initial_status["models"] = {
            key: {"status": "queued"} for key in selected_models
        }
        store.write_run_json(run_id, "status.json", initial_status)
        results = fit_models(
            X_train=X_train,
            y_train=prepared["y_train"],
            X_test=X_test,
            numeric_cols=numeric_cols,
            categorical_cols=categorical_cols,
            model_keys=selected_models,
            seed=int(split["params"]["seed"]),
            n_jobs=settings.n_jobs,
            on_progress=on_progress,
        )
        observed_status = {
            key: {
                "status": result["status"],
                **(
                    {"fit_seconds": float(result["fit_seconds"])}
                    if "fit_seconds" in result
                    else {}
                ),
                **(
                    {"error": str(result["error"])}
                    if result.get("error")
                    else {}
                ),
            }
            for key, result in results.items()
        }
        store.update_status(run_id, {"models": observed_status, "stage": "training"})
        successful_non_baseline = [
            key for key in request["models"]
            if results.get(key, {}).get("status") == "done"
        ]
        if len(successful_non_baseline) < 2:
            failures = {
                key: results.get(key, {}).get("error", "model did not complete")
                for key in request["models"]
                if results.get(key, {}).get("status") != "done"
            }
            raise RuntimeError(
                "At least two selected non-baseline models must train successfully."
                + (f" Failures: {failures}" if failures else "")
            )

        store.update_status(run_id, {"stage": "analysing"})
        metrics = {}
        predictions = pd.DataFrame(
            {
                "row_id": [int(row_id) for row_id in split["test_ids"]],
                "y_true": y_test.to_numpy(dtype=int),
            }
        )
        probability_columns = {}
        status_models = {}
        for key in selected_models:
            model_result = results.get(key)
            if not model_result:
                status_models[key] = {"status": "failed", "error": "Model was not run."}
                continue
            if model_result["status"] == "failed":
                status_models[key] = {
                    "status": "failed",
                    "error": str(model_result.get("error", "Model training failed.")),
                }
                continue

            pred = np.asarray(model_result["pred"], dtype=int)
            proba = model_result.get("proba")
            metrics[key] = {
                "status": "done",
                "fit_seconds": float(model_result["fit_seconds"]),
                **model_metrics(y_test.to_numpy(dtype=int), pred, proba, len(class_names)),
            }
            status_models[key] = {
                "status": "done",
                "fit_seconds": float(model_result["fit_seconds"]),
            }
            predictions[f"pred_{key}"] = pred
            if proba is not None:
                proba_array = np.asarray(proba)
                if proba_array.ndim == 1:
                    proba_array = np.column_stack((1.0 - proba_array, proba_array))
                for class_index in range(proba_array.shape[1]):
                    column = f"proba_{key}_{class_index}"
                    predictions[column] = proba_array[:, class_index]
                    probability_columns.setdefault(key, []).append(column)

        comparable_predictions = {
            key: results[key]
            for key in successful_non_baseline
        }
        comparisons = all_pairs(y_test.to_numpy(dtype=int), comparable_predictions)

        store.write_run_json(run_id, "quality.json", prepared["quality"])
        store.write_run_json(run_id, "metrics.json", _json_value(metrics))
        store.write_run_json(run_id, "comparisons.json", comparisons)
        store.write_parquet(run_id, "predictions.parquet", predictions)
        test_features = prepared["test_df"][included].copy()
        test_features.insert(0, "row_id", [int(row_id) for row_id in split["test_ids"]])
        store.write_parquet(run_id, "test_features.parquet", test_features)

        config = store.read_run_json(run_id, "config.json")
        config.update(
            {
                "class_names": class_names,
                "feature_columns": [
                    {"name": name, "kind": kinds[name]["kind"]}
                    for name in included
                ],
                "included_columns": included,
                "excluded_columns": prepared["excluded"],
                "model_parameters": _model_params(results),
                "library_versions": _versions(),
                "n_jobs": settings.n_jobs,
                "probability_columns": probability_columns,
            }
        )
        store.write_run_json(run_id, "config.json", config)
        store.update_status(
            run_id,
            {
                "state": "completed",
                "stage": "completed",
                "models": status_models,
                "error": None,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as error:
        failed_status = store.read_run_json(run_id, "status.json")
        model_states = failed_status.get("models", {})
        for key, model_status in model_states.items():
            if model_status.get("status") in {"queued", "running"}:
                model_states[key] = {"status": "failed", "error": str(error)}
        store.update_status(
            run_id,
            {
                "state": "failed",
                "stage": "failed",
                "error": str(error),
                "models": model_states,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    finally:
        try:
            store.delete_upload(upload_id)
            store.apply_retention(settings.keep_runs, active_run_id=run_id)
        except Exception as cleanup_error:
            status = store.read_run_json(run_id, "status.json")
            state = "failed" if status.get("state") != "failed" else status["state"]
            store.update_status(
                run_id,
                {
                    "state": state,
                    "stage": "failed" if state == "failed" else status.get("stage"),
                    "error": (
                        f"{status.get('error')}; cleanup failed: {cleanup_error}"
                        if status.get("error")
                        else f"Run cleanup failed: {cleanup_error}"
                    ),
                },
            )


class ThreadJobRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        if self._lock.locked():
            self._lock.release()

    def start(self, fn: Callable, args: tuple) -> threading.Thread:
        def run() -> None:
            try:
                fn(*args)
            finally:
                self.release()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
