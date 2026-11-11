from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Body, Query, Request, status

from api.schemas import RunRequest
from mde.analysis.pairs import disagreement_rows
from mde.analysis.slices import slice_table
from mde.data.prepare import prepare
from mde.errors import BadRequest, Busy, ConfirmationRequired, DecisionRequired, NotFound
from mde.runner import run_experiment
from mde.store import FileRunStore
from mde.training.registry import selectable


router = APIRouter(prefix="/api/runs")


def _store(request: Request) -> FileRunStore:
    return request.app.state.store


def _require_run(store: FileRunStore, run_id: str) -> tuple[dict, dict]:
    run_dir = store.run_dir(run_id)
    if not run_dir.is_dir():
        raise NotFound("The requested run was not found.")
    return (
        store.read_run_json(run_id, "config.json"),
        store.read_run_json(run_id, "status.json"),
    )


def _validate_pair(status: dict, a: str, b: str) -> None:
    if a == b:
        raise BadRequest("Choose two different models.", {"a": a, "b": b})
    model_states = status.get("models", {})
    for key in (a, b):
        if model_states.get(key, {}).get("status") != "done":
            raise BadRequest(
                "Both models must have completed successfully.",
                {"model": key},
            )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def start_run(request: Request, body: RunRequest = Body(...)) -> dict:
    runner = request.app.state.runner
    if not runner.acquire():
        raise Busy("A run is already in progress.")

    run_id = uuid.uuid4().hex
    created = False
    thread_started = False
    try:
        store = _store(request)
        store.valid_id(body.upload_id)
        store.valid_id(body.split_id)
        upload_path = store.upload_path(body.upload_id)
        if not upload_path.is_file():
            raise NotFound("The requested upload was not found.")
        split = store.load_split(body.upload_id, body.split_id)
        metadata = store.load_upload_metadata(body.upload_id)

        payload = body.model_dump()
        prepared = prepare(
            upload_path,
            split,
            missing_tokens=payload["missing_tokens"],
            column_decisions=payload["column_decisions"],
        )
        if prepared["undecided"]:
            raise DecisionRequired(
                "Some feature columns still need an include or exclude decision.",
                {"columns": prepared["undecided"]},
            )
        if prepared["needs_independence_confirmation"] and not body.independence_confirmed:
            raise ConfirmationRequired(
                "Confirm that rows are independent before using a datetime-like feature.",
                {"columns": [
                    name for name, flag in prepared["feature_flags"].items()
                    if flag.get("flag") == "datetime_like" and name in prepared["included"]
                ]},
            )
        if not prepared["included"]:
            raise BadRequest("At least one feature column must be included.")
        if body.class_weight:
            raise BadRequest("Class weighting is not available in this version.", {"class_weight": True})
        if not 2 <= len(body.models) <= 4 or len(set(body.models)) != len(body.models):
            raise BadRequest(
                "Select between 2 and 4 distinct models.",
                {"models": body.models},
            )
        unknown = [key for key in body.models if key not in selectable()]
        if unknown:
            raise BadRequest("One or more selected models are unavailable.", {"models": unknown})

        created_at = datetime.now(timezone.utc).isoformat()
        store.create_run(run_id)
        created = True
        config = {
            **payload,
            "run_id": run_id,
            "target": split["params"]["target"],
            "seed": split["params"]["seed"],
            "test_size": split["params"]["test_size"],
            "upload_id": body.upload_id,
            "split_id": body.split_id,
            "fingerprint": split.get("fingerprint", metadata["fingerprint"]),
            "display_filename": metadata["display_filename"],
            "created_at": created_at,
            "class_names": sorted(prepared["labelled_set"].y.unique().tolist()),
            "included_columns": prepared["included"],
            "excluded_columns": prepared["excluded"],
            "feature_columns": [
                {"name": name, "kind": prepared["typing_report"][name]["kind"]}
                for name in prepared["included"]
            ],
            "library_versions": {},
            "n_jobs": request.app.state.settings.n_jobs,
        }
        store.write_run_json(run_id, "config.json", config)
        store.write_run_json(
            run_id,
            "status.json",
            {
                "run_id": run_id,
                "state": "running",
                "stage": "queued",
                "models": {
                    key: {"status": "queued"} for key in ["dummy", *body.models]
                },
                "error": None,
                "created_at": created_at,
            },
        )
        request_payload = body.model_dump()
        runner.start(
            run_experiment,
            (store, request.app.state.settings, run_id, request_payload),
        )
        thread_started = True
        return {"run_id": run_id, "state": "running"}
    except Exception:
        if created and not thread_started:
            try:
                _store(request).delete_run(run_id)
            except FileNotFoundError:
                pass
        if not thread_started:
            runner.release()
        raise


@router.get("")
def list_runs(request: Request) -> dict:
    runs = []
    for item in _store(request).list_runs():
        config = item["config"]
        status = item["status"]
        runs.append(
            {
                "run_id": item["run_id"],
                "display_filename": config.get("display_filename"),
                "created_at": config.get("created_at"),
                "state": status.get("state"),
                "stage": status.get("stage"),
                "models": status.get("models", {}),
            }
        )
    return {"runs": runs}


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    store = _store(request)
    config, status = _require_run(store, run_id)
    quality_path = store.run_dir(run_id) / "quality.json"
    quality = store.read_json(quality_path) if quality_path.is_file() else None
    return {
        "run_id": run_id,
        "state": status.get("state"),
        "stage": status.get("stage"),
        "models": status.get("models", {}),
        "error": status.get("error"),
        "config": config,
        "quality": quality,
    }


@router.get("/{run_id}/summary")
def get_summary(run_id: str, request: Request) -> dict:
    store = _store(request)
    config, _ = _require_run(store, run_id)
    metrics = store.read_run_json(run_id, "metrics.json")
    return {
        "metrics": metrics,
        "class_names": config["class_names"],
        "feature_columns": config["feature_columns"],
    }


@router.get("/{run_id}/pairs")
def get_pairs(run_id: str, request: Request) -> dict:
    store = _store(request)
    _require_run(store, run_id)
    return {"pairs": store.read_run_json(run_id, "comparisons.json")}


@router.get("/{run_id}/disagreements")
def get_disagreements(
    run_id: str,
    request: Request,
    a: str,
    b: str,
    bucket: str = "all",
    true_class: str | None = Query(default=None, alias="class"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    store = _store(request)
    config, status = _require_run(store, run_id)
    _validate_pair(status, a, b)
    if bucket not in {"all", "only_a", "only_b", "both_wrong_diff"}:
        raise BadRequest("Unknown disagreement bucket.", {"bucket": bucket})
    class_names = config["class_names"]
    if true_class is None:
        class_index = None
    else:
        try:
            class_index = class_names.index(true_class)
        except ValueError as error:
            raise BadRequest("Unknown true class.", {"class": true_class}) from error

    predictions = store.read_parquet(run_id, "predictions.parquet")
    features = store.read_parquet(run_id, "test_features.parquet")
    proba_columns = config.get("probability_columns", {})
    proba = {}
    for key in (a, b):
        columns = proba_columns.get(key, [])
        proba[key] = predictions[columns].to_numpy() if columns else None
    result = disagreement_rows(
        features,
        predictions["y_true"].to_numpy(),
        {
            a: predictions[f"pred_{a}"].to_numpy(),
            b: predictions[f"pred_{b}"].to_numpy(),
        },
        proba,
        class_names,
        a,
        b,
        bucket=bucket,
        true_class=class_index,
        page=page,
        page_size=page_size,
    )
    for row in result["rows"]:
        row["y_true"] = class_names[row["y_true"]]
        row["pred_a"] = class_names[row["pred_a"]]
        row["pred_b"] = class_names[row["pred_b"]]
    return result


@router.get("/{run_id}/slices")
def get_slices(
    run_id: str,
    request: Request,
    a: str,
    b: str,
    feature: str,
) -> dict:
    store = _store(request)
    config, status = _require_run(store, run_id)
    _validate_pair(status, a, b)
    feature_columns = {
        item["name"]: item["kind"] for item in config.get("feature_columns", [])
    }
    if feature not in feature_columns:
        raise BadRequest("The feature is not included in this run.", {"feature": feature})
    predictions = store.read_parquet(run_id, "predictions.parquet")
    features = store.read_parquet(run_id, "test_features.parquet")
    result = slice_table(
        features[feature],
        feature_columns[feature],
        predictions["y_true"].to_numpy(),
        predictions[f"pred_{a}"].to_numpy(),
        predictions[f"pred_{b}"].to_numpy(),
    )
    return {"feature": feature, "slices": result}


@router.delete("/{run_id}")
def delete_run(run_id: str, request: Request) -> dict[str, bool]:
    store = _store(request)
    _, status = _require_run(store, run_id)
    if status.get("state") == "running":
        raise Busy("A running run cannot be deleted.")
    store.delete_run(run_id)
    return {"deleted": True}
