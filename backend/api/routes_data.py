from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from mde.data.parsing import load_raw, read_header
from mde.data.prepare import prepare
from mde.data.profile import profile_frame
from mde.data.split import make_split
from mde.data.target import build_labelled_set
from mde.errors import BadRequest, CsvError, NotFound, TooLarge
from mde.samples import ensure_sample_csv, list_samples
from mde.store import FileRunStore
from mde.training.registry import REGISTRY, selectable
from api.schemas import PreflightRequest, SplitRequest


router = APIRouter(prefix="/api")
_CHUNK_SIZE = 1024 * 1024


def _store(request: Request) -> FileRunStore:
    return request.app.state.store


def _filename(value: str | None) -> str:
    if not value:
        return "upload.csv"
    clean = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return clean or "upload.csv"


async def _stream_upload(source: UploadFile, store: FileRunStore, upload_id: str, max_bytes: int) -> tuple[str, int]:
    part_path = store.part_path(upload_id)
    digest = hashlib.sha256()
    total = 0
    try:
        with part_path.open("wb") as output:
            while True:
                chunk = await source.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise TooLarge(
                        "The upload exceeds the configured file-size limit.",
                        {"max_bytes": max_bytes},
                    )
                digest.update(chunk)
                output.write(chunk)
        return digest.hexdigest(), total
    except Exception:
        part_path.unlink(missing_ok=True)
        raise
    finally:
        await source.close()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/models")
def models() -> dict[str, list[dict[str, Any]]]:
    model_list = []
    for key, spec in REGISTRY.items():
        model_list.append(
            {
                "key": key,
                "label": spec.label,
                "baseline": key == "dummy",
                "selectable": key in selectable(),
                "supports_proba": spec.supports_proba,
            }
        )
    return {"models": model_list}


@router.get("/samples")
def samples() -> dict[str, list[dict[str, str]]]:
    return {"samples": list_samples()}


@router.post("/uploads")
async def upload(
    request: Request,
    file: UploadFile | None = File(default=None),
    sample: str | None = Form(default=None),
) -> JSONResponse:
    if (file is None) == (sample is None):
        raise BadRequest("Provide exactly one CSV file or sample name.")

    store = _store(request)
    upload_id = uuid.uuid4().hex
    filename = "breast_cancer.csv"
    final_path = store.upload_path(upload_id)
    part_path = store.part_path(upload_id)
    max_bytes = request.app.state.settings.max_upload_mb * 1024 * 1024

    try:
        if sample is not None:
            if sample not in {item["name"] for item in list_samples()}:
                raise BadRequest("The requested sample dataset is not available.", {"sample": sample})
            sample_path = ensure_sample_csv(sample, store.samples_dir)
            shutil.copyfile(sample_path, part_path)
            size = part_path.stat().st_size
            if size > max_bytes:
                raise TooLarge("The sample exceeds the configured file-size limit.", {"max_bytes": max_bytes})
            digest = hashlib.sha256(part_path.read_bytes()).hexdigest()
        else:
            filename = _filename(file.filename if file else None)
            if Path(filename).suffix.lower() != ".csv":
                raise CsvError("Only CSV files are accepted.", {"filename": filename})
            digest, size = await _stream_upload(file, store, upload_id, max_bytes)

        part_path.replace(final_path)
        header = read_header(final_path, request.app.state.settings.max_cols)
        profile = profile_frame(final_path)
        return JSONResponse(
            {
                "upload_id": upload_id,
                "display_filename": filename,
                "fingerprint": digest,
                "size_bytes": size,
                "n_rows": profile["n_rows"],
                "n_cols": profile["n_cols"],
                "header": header,
                "profile": profile,
            }
        )
    except Exception:
        final_path.unlink(missing_ok=True)
        part_path.unlink(missing_ok=True)
        raise


@router.post("/uploads/{upload_id}/split")
def create_split(upload_id: str, request: Request, body: SplitRequest = Body(...)) -> dict:
    store = _store(request)
    path = store.upload_path(upload_id)
    if not path.is_file():
        raise NotFound("The requested upload was not found.")

    payload = body.model_dump()
    target = payload.get("target")
    target_tokens = payload.get("target_missing_tokens", [])
    seed = payload.get("seed", 42)
    test_size = payload.get("test_size", 0.2)
    if not isinstance(test_size, (int, float)) or not 0.1 <= test_size <= 0.4:
        raise BadRequest("test_size must be between 0.1 and 0.4.", {"test_size": test_size})

    raw = load_raw(path, target=target)
    labelled = build_labelled_set(raw, target, target_tokens)
    record = make_split(
        labelled.y,
        test_size=float(test_size),
        seed=int(seed),
        cap=request.app.state.settings.max_rows,
        params={
            "target": target,
            "target_missing_tokens": list(target_tokens),
            "seed": int(seed),
            "test_size": float(test_size),
        },
    )
    record_payload = record.to_dict()
    record_payload["fingerprint"] = hashlib.sha256(path.read_bytes()).hexdigest()
    record_payload["class_table"] = {
        label: {
            **counts,
            "n_before": int(labelled.class_counts.get(label, counts["n_before"])),
        }
        for label, counts in record_payload["class_table"].items()
    }
    store.save_split(upload_id, record_payload)
    return {
        "split_id": record.split_id,
        "n_labelled": len(labelled.y),
        "dropped_missing_target": labelled.dropped_missing,
        "trimmed_labels": labelled.trimmed,
        "n_train": len(record.train_ids),
        "n_test": len(record.test_ids),
        "class_table": record_payload["class_table"],
        "warnings": [*labelled.warnings, *record.warnings],
    }


@router.post("/uploads/{upload_id}/preflight")
def preflight(upload_id: str, request: Request, body: PreflightRequest = Body(...)) -> dict:
    store = _store(request)
    if not store.upload_path(upload_id).is_file():
        raise NotFound("The requested upload was not found.")
    payload = body.model_dump()
    split_id = payload.get("split_id")
    split = store.load_split(upload_id, split_id)
    result = prepare(
        store.upload_path(upload_id),
        split,
        missing_tokens=payload.get("missing_tokens", []),
        column_decisions=payload.get("column_decisions", {}),
    )
    return {
        "report": result["quality"],
        "flags": result["feature_flags"],
        "undecided": result["undecided"],
        "included": result["included"],
        "excluded": result["excluded"],
        "needs_independence_confirmation": result["needs_independence_confirmation"],
    }
