from __future__ import annotations

import json
import threading
import time

import pandas as pd

from conftest import assert_error_shape


def _sample_and_split(client):
    uploaded_response = client.post("/api/uploads", data={"sample": "breast_cancer"})
    assert uploaded_response.status_code == 200
    uploaded = uploaded_response.json()
    split_response = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "diagnosis", "seed": 42, "test_size": 0.2},
    )
    assert split_response.status_code == 200
    return uploaded, split_response.json()


def _start(client, uploaded, split, models=None):
    return client.post(
        "/api/runs",
        json={
            "upload_id": uploaded["upload_id"],
            "split_id": split["split_id"],
            "missing_tokens": [],
            "column_decisions": {},
            "models": models or ["logreg", "tree", "rf"],
            "class_weight": False,
            "independence_confirmed": False,
        },
    )


def _wait_for_run(client, run_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200, (
            response.text,
            [
                (path, list(path.iterdir()) if path.is_dir() else [])
                for path in client.app.state.store.runs_dir.iterdir()
            ],
        )
        payload = response.json()
        json.dumps(payload, allow_nan=False)
        if payload["state"] in {"completed", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("Run did not reach a terminal state.")


def test_run_integration_summary_pairs_disagreements_and_slices(client):
    uploaded, split = _sample_and_split(client)
    expected_ids = set(
        client.app.state.store.load_split(uploaded["upload_id"], split["split_id"])["test_ids"]
    )
    response = _start(client, uploaded, split)
    assert response.status_code == 202
    run_id = response.json()["run_id"]

    finished = _wait_for_run(client, run_id)
    assert finished["state"] == "completed", finished.get("error")
    assert finished["config"]["split_id"] == split["split_id"]

    summary_response = client.get(f"/api/runs/{run_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    json.dumps(summary, allow_nan=False)
    assert len(summary["metrics"]) == 4
    assert "dummy" in summary["metrics"]
    assert summary["class_names"] == ["benign", "malignant"]
    numeric_features = [item["name"] for item in summary["feature_columns"] if item["kind"] == "numeric"]
    assert numeric_features

    pairs_response = client.get(f"/api/runs/{run_id}/pairs")
    pairs = pairs_response.json()["pairs"]
    json.dumps(pairs_response.json(), allow_nan=False)
    assert len(pairs) == 3
    assert all(pair["p_holm"] >= pair["p_raw"] for pair in pairs)

    first_pair = pairs[0]
    disagreements_response = client.get(
        f"/api/runs/{run_id}/disagreements",
        params={"a": first_pair["model_a"], "b": first_pair["model_b"], "page": 1, "page_size": 10},
    )
    assert disagreements_response.status_code == 200
    disagreements = disagreements_response.json()
    json.dumps(disagreements, allow_nan=False)
    assert disagreements["page"] == 1
    assert disagreements["page_size"] == 10
    assert len(disagreements["rows"]) <= 10
    assert all(row["row_id"] in expected_ids for row in disagreements["rows"])

    slices_response = client.get(
        f"/api/runs/{run_id}/slices",
        params={
            "a": first_pair["model_a"],
            "b": first_pair["model_b"],
            "feature": numeric_features[0],
        },
    )
    assert slices_response.status_code == 200
    slices = slices_response.json()
    json.dumps(slices, allow_nan=False)
    assert len(slices["slices"]) <= 5

    assert client.get("/api/runs").status_code == 200
    assert client.delete(f"/api/runs/{run_id}").json() == {"deleted": True}
    assert_error_shape(client.get(f"/api/runs/{run_id}"), 404)


def test_busy_lock_rejects_second_start_and_release_allows_next(client):
    uploaded, split = _sample_and_split(client)
    runner = client.app.state.runner
    assert runner.acquire()
    busy = _start(client, uploaded, split, models=["logreg", "tree"])
    assert assert_error_shape(busy, 409)["code"] == "busy"
    runner.release()

    started = _start(client, uploaded, split, models=["logreg", "tree"])
    assert started.status_code == 202
    assert _wait_for_run(client, started.json()["run_id"])["state"] == "completed"


def test_start_rejects_extra_split_parameters_and_releases_lock(client):
    uploaded, split = _sample_and_split(client)
    body = {
        "upload_id": uploaded["upload_id"],
        "split_id": split["split_id"],
        "models": ["logreg", "tree"],
        "seed": 1,
        "test_size": 0.3,
        "target": "diagnosis",
    }
    response = client.post("/api/runs", json=body)
    assert assert_error_shape(response, 422)["code"] == "bad_request"
    assert client.app.state.runner.acquire()
    client.app.state.runner.release()


def test_decision_required_failure_does_not_leave_runner_locked(client):
    rows = [[str(index), "yes" if index % 2 else "no"] for index in range(1, 201)]
    raw = pd.DataFrame(rows, columns=["row_number", "target"]).to_csv(index=False).encode()
    uploaded_response = client.post(
        "/api/uploads",
        files={"file": ("rows.csv", raw, "text/csv")},
    )
    uploaded = uploaded_response.json()
    split = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "target", "test_size": 0.2},
    ).json()
    failed = _start(client, uploaded, split, models=["logreg", "tree"])
    assert assert_error_shape(failed, 422)["code"] == "decision_required"
    assert client.app.state.runner.acquire()
    client.app.state.runner.release()


def test_training_exception_marks_failed_cleans_upload_and_releases_lock(client, monkeypatch):
    import mde.runner

    uploaded, split = _sample_and_split(client)

    def fail_fit_models(**_kwargs):
        raise RuntimeError("controlled training failure")

    monkeypatch.setattr(mde.runner, "fit_models", fail_fit_models)
    response = _start(client, uploaded, split, models=["logreg", "tree"])
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    finished = _wait_for_run(client, run_id)
    assert finished["state"] == "failed"
    assert "controlled training failure" in finished["error"]
    assert finished["models"]["logreg"]["status"] == "failed"
    assert not client.app.state.store.upload_path(uploaded["upload_id"]).exists()
    assert client.app.state.runner.acquire()
    client.app.state.runner.release()


def test_running_run_cannot_be_deleted(client, monkeypatch):
    import api.routes_runs

    uploaded, split = _sample_and_split(client)
    entered = threading.Event()
    finish = threading.Event()

    def wait_for_finish(store, settings, run_id, request):
        entered.set()
        assert finish.wait(timeout=10)
        store.update_status(run_id, {"state": "completed", "stage": "completed"})

    monkeypatch.setattr(api.routes_runs, "run_experiment", wait_for_finish)
    response = _start(client, uploaded, split, models=["logreg", "tree"])
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    assert entered.wait(timeout=5)

    deletion = client.delete(f"/api/runs/{run_id}")
    assert assert_error_shape(deletion, 409)["code"] == "busy"
    finish.set()
    assert _wait_for_run(client, run_id)["state"] == "completed"


def test_run_errors_are_consistent_and_models_validate(client):
    uploaded, split = _sample_and_split(client)
    invalid_count = _start(client, uploaded, split, models=["logreg"])
    assert assert_error_shape(invalid_count, 400)["code"] == "bad_request"

    duplicate = _start(client, uploaded, split, models=["logreg", "logreg"])
    assert assert_error_shape(duplicate, 400)["code"] == "bad_request"

    bad_pair = client.get("/api/runs/not-a-uuid/pairs")
    assert assert_error_shape(bad_pair, 404)["code"] == "not_found"


def test_multiclass_disagreement_filter_returns_both_wrong_different_labels(client):
    store = client.app.state.store
    run_id = "a" * 32
    store.create_run(run_id)
    store.write_run_json(
        run_id,
        "config.json",
        {
            "run_id": run_id,
            "class_names": ["zero", "one", "two"],
            "feature_columns": [{"name": "feature", "kind": "numeric"}],
            "probability_columns": {},
        },
    )
    store.write_run_json(
        run_id,
        "status.json",
        {
            "state": "completed",
            "models": {
                "logreg": {"status": "done"},
                "rf": {"status": "done"},
            },
        },
    )
    store.write_parquet(
        run_id,
        "predictions.parquet",
        pd.DataFrame(
            {
                "y_true": [0, 1, 2],
                "pred_logreg": [1, 1, 0],
                "pred_rf": [2, 1, 0],
            }
        ),
    )
    store.write_parquet(
        run_id,
        "test_features.parquet",
        pd.DataFrame({"row_id": [10, 20, 30], "feature": [1.0, 2.0, 3.0]}),
    )

    response = client.get(
        f"/api/runs/{run_id}/disagreements",
        params={
            "a": "logreg",
            "b": "rf",
            "bucket": "both_wrong_diff",
            "page": 1,
            "page_size": 25,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["rows"] == [
        {
            "row_id": 10,
            "features": {"feature": 1.0},
            "y_true": "zero",
            "pred_a": "one",
            "pred_b": "two",
            "prob_a": None,
            "prob_b": None,
            "bucket": "both_wrong_diff",
        }
    ]
