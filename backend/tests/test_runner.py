from __future__ import annotations

import json
import time
import uuid
from dataclasses import replace

import numpy as np
import pandas as pd

from mde.runner import ThreadJobRunner, _json_value, run_experiment
from mde.settings import Settings
from mde.store import FileRunStore
from mde.training.registry import REGISTRY


def test_json_value_converts_non_finite_model_parameters_to_null():
    payload = _json_value(
        {
            "unset": float("nan"),
            "numpy_infinity": np.float64(np.inf),
            "nested": [float("-inf")],
        }
    )

    assert payload == {
        "unset": None,
        "numpy_infinity": None,
        "nested": [None],
    }
    json.dumps(payload, allow_nan=False)


def _prepare_run(tmp_path, models):
    store = FileRunStore(tmp_path)
    upload_id = uuid.uuid4().hex
    run_id = uuid.uuid4().hex
    frame = pd.DataFrame(
        {
            "value": list(range(1, 201)),
            "category": ["a" if index % 2 else "b" for index in range(200)],
            "target": ["positive" if index % 2 else "negative" for index in range(200)],
        },
        index=pd.RangeIndex(1, 201),
    )
    upload_path = store.upload_path(upload_id)
    frame.to_csv(upload_path, index=False)
    from mde.data.split import make_split

    labels = frame["target"].astype(str)
    record = make_split(
        labels,
        test_size=0.2,
        seed=7,
        cap=20_000,
        params={
            "target": "target",
            "target_missing_tokens": [],
            "seed": 7,
            "test_size": 0.2,
        },
    ).to_dict()
    record["fingerprint"] = "test-fingerprint"
    store.save_split(upload_id, record)
    store.save_upload_metadata(
        upload_id,
        {"upload_id": upload_id, "display_filename": "fixture.csv", "fingerprint": "test-fingerprint"},
    )
    store.create_run(run_id)
    store.write_run_json(
        run_id,
        "config.json",
        {
            "run_id": run_id,
            "upload_id": upload_id,
            "split_id": record["split_id"],
            "created_at": "2026-01-01T00:00:00+00:00",
        },
    )
    store.write_run_json(
        run_id,
        "status.json",
        {"run_id": run_id, "state": "running", "stage": "queued", "models": {}},
    )
    request = {
        "upload_id": upload_id,
        "split_id": record["split_id"],
        "missing_tokens": [],
        "models": models,
        "class_weight": False,
        "independence_confirmed": False,
        "column_decisions": {"value": "include"},
    }
    return store, Settings(data_dir=tmp_path), run_id, request, upload_id, record["test_ids"]


def test_runner_releases_lock_after_thread_finishes():
    runner = ThreadJobRunner()
    assert runner.acquire()
    runner.start(lambda: time.sleep(0.01), ())
    deadline = time.monotonic() + 2
    while runner._lock.locked() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not runner._lock.locked()
    assert runner.acquire()
    runner.release()


def test_run_experiment_writes_metrics_pairs_and_row_id_aligned_parquet(tmp_path):
    store, settings, run_id, request, upload_id, expected_test_ids = _prepare_run(
        tmp_path, ["logreg", "tree", "rf"]
    )
    run_experiment(store, settings, run_id, request)
    status = store.read_run_json(run_id, "status.json")
    assert status["state"] == "completed"
    assert len(store.read_run_json(run_id, "metrics.json")) == 4
    assert len(store.read_run_json(run_id, "comparisons.json")) == 3
    predictions = store.read_parquet(run_id, "predictions.parquet")
    features = store.read_parquet(run_id, "test_features.parquet")
    assert predictions["row_id"].tolist() == expected_test_ids
    assert features["row_id"].tolist() == expected_test_ids
    assert "row_id" in features.columns
    assert "value" in features.columns
    assert "category" in features.columns
    config = store.read_run_json(run_id, "config.json")
    assert config["split_id"] == request["split_id"]
    assert config["class_names"] == ["negative", "positive"]
    assert not store.upload_path(upload_id).exists()


def test_insufficient_successful_nonbaseline_models_fails_run(tmp_path, monkeypatch):
    store, settings, run_id, request, _, _ = _prepare_run(tmp_path, ["logreg", "tree"])
    original = REGISTRY["tree"]
    monkeypatch.setitem(
        REGISTRY,
        "tree",
        replace(original, factory=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("factory failed"))),
    )
    run_experiment(store, settings, run_id, request)
    status = store.read_run_json(run_id, "status.json")
    assert status["state"] == "failed"
    assert "At least two selected non-baseline models" in status["error"]
    assert status["models"]["tree"]["status"] == "failed"
    assert status["models"]["tree"]["error"] == "factory failed"


def test_one_model_factory_failure_is_isolated_when_two_models_succeed(tmp_path, monkeypatch):
    store, settings, run_id, request, _, _ = _prepare_run(
        tmp_path, ["logreg", "tree", "rf"]
    )
    original = REGISTRY["tree"]
    monkeypatch.setitem(
        REGISTRY,
        "tree",
        replace(original, factory=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("factory failed"))),
    )
    run_experiment(store, settings, run_id, request)
    status = store.read_run_json(run_id, "status.json")
    assert status["state"] == "completed"
    assert status["models"]["tree"]["status"] == "failed"
    assert status["models"]["tree"]["error"] == "factory failed"
    assert status["models"]["logreg"]["status"] == "done"
    assert status["models"]["rf"]["status"] == "done"
