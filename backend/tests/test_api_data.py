from __future__ import annotations

import csv
import hashlib
import io
import json

import pytest

from conftest import assert_error_shape


def upload_sample(client):
    response = client.post("/api/uploads", data={"sample": "breast_cancer"})
    assert response.status_code == 200
    return response.json()


def upload_csv(client, content: bytes, filename: str = "fixture.csv"):
    return client.post(
        "/api/uploads",
        files={"file": (filename, content, "text/csv")},
    )


def csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def test_health_models_samples_and_sample_upload(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert assert_error_shape(client.get("/api/missing"), 404)["code"] == "not_found"
    models = client.get("/api/models").json()["models"]
    assert len(models) == 5
    assert sum(model["baseline"] for model in models) == 1
    assert client.get("/api/samples").json()["samples"][0]["name"] == "breast_cancer"

    uploaded = upload_sample(client)
    stored = client.app.state.store.upload_path(uploaded["upload_id"])
    assert uploaded["fingerprint"] == hashlib.sha256(stored.read_bytes()).hexdigest()
    assert uploaded["n_rows"] == 569
    assert uploaded["n_cols"] == 31


def test_upload_rejects_duplicate_header_and_cleans_files(client):
    response = upload_csv(client, b"name,name\n1,2\n")
    body = assert_error_shape(response, 400)
    assert body["code"] == "bad_csv"
    assert body["details"]["duplicate_names"] == ["name"]
    assert list(client.app.state.store.uploads_dir.iterdir()) == []


def test_upload_size_limit_removes_partial_file(client):
    client.app.state.settings = client.app.state.settings.__class__(
        data_dir=client.app.state.settings.data_dir,
        max_upload_mb=0,
    )
    response = upload_csv(client, b"x\n1\n")
    body = assert_error_shape(response, 413)
    assert body["code"] == "too_large"
    assert list(client.app.state.store.uploads_dir.iterdir()) == []


def test_upload_rejects_too_many_columns(client):
    headers = [f"c{index}" for index in range(51)]
    response = upload_csv(client, csv_bytes(headers, [["1"] * len(headers)]))
    body = assert_error_shape(response, 422)
    assert body["code"] == "too_many_columns"
    assert list(client.app.state.store.uploads_dir.iterdir()) == []


def test_upload_requires_csv_file_and_valid_id(client):
    response = upload_csv(client, b"x\n1\n", filename="fixture.txt")
    assert_error_shape(response, 400)
    invalid_id = client.post("/api/uploads/not-a-uuid/split", json={"target": "x"})
    assert assert_error_shape(invalid_id, 404)["code"] == "not_found"


def test_split_valid_target_invalid_rare_class_and_bad_test_size(client):
    uploaded = upload_sample(client)
    split = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "diagnosis", "seed": 42, "test_size": 0.2},
    )
    assert split.status_code == 200
    assert split.json()["split_id"]
    assert split.json()["n_train"] + split.json()["n_test"] == split.json()["n_labelled"]

    invalid_target = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "unknown"},
    )
    assert assert_error_shape(invalid_target, 422)["code"] == "target_invalid"

    rare_csv = csv_bytes(
        ["feature", "target"],
        [[str(index), label] for label, count in (("a", 90), ("b", 5), ("c", 5)) for index in range(count)],
    )
    rare_upload = upload_csv(client, rare_csv).json()
    rare = client.post(
        f"/api/uploads/{rare_upload['upload_id']}/split",
        json={"target": "target", "test_size": 0.1},
    )
    assert assert_error_shape(rare, 422)["code"] == "split_invalid"
    assert "b" in rare.json()["details"]["undersized_classes"]

    bad_size = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "diagnosis", "test_size": 0.5},
    )
    assert assert_error_shape(bad_size, 400)["code"] == "bad_request"


def test_preflight_returns_undecided_columns_then_applies_decision(client):
    rows = [[str(index), "yes" if index % 2 else "no"] for index in range(1, 201)]
    uploaded = upload_csv(client, csv_bytes(["row_number", "target"], rows)).json()
    split = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "target", "seed": 7, "test_size": 0.2},
    ).json()

    missing = client.post(
        f"/api/uploads/{uploaded['upload_id']}/preflight",
        json={"split_id": "a" * 32},
    )
    assert assert_error_shape(missing, 404)["code"] == "not_found"

    preflight = client.post(
        f"/api/uploads/{uploaded['upload_id']}/preflight",
        json={"split_id": split["split_id"]},
    )
    assert preflight.status_code == 200
    assert "row_number" in preflight.json()["undecided"]

    resolved = client.post(
        f"/api/uploads/{uploaded['upload_id']}/preflight",
        json={
            "split_id": split["split_id"],
            "column_decisions": {"row_number": "exclude"},
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["undecided"] == []
    assert "row_number" in resolved.json()["excluded"]
    duplicate_section = next(
        section for section in resolved.json()["report"]["sections"] if section["id"] == "duplicates"
    )
    assert duplicate_section["items"][0]["data"]["agreement_ceiling"] == "not_applicable"
    json.dumps(resolved.json(), allow_nan=False)


def test_extra_request_fields_and_non_csv_content_errors_are_shaped(client):
    uploaded = upload_sample(client)
    invalid = client.post(
        f"/api/uploads/{uploaded['upload_id']}/split",
        json={"target": "diagnosis", "extra": True},
    )
    assert assert_error_shape(invalid, 422)["code"] == "bad_request"
