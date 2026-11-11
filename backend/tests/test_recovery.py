from datetime import datetime, timedelta, timezone
import uuid

from mde.settings import Settings
from mde.store import FileRunStore


def _create_run(store, run_id, state, created_at, upload_id=None):
    store.create_run(run_id)
    store.write_run_json(
        run_id,
        "config.json",
        {
            "run_id": run_id,
            "created_at": created_at,
            "upload_id": upload_id,
        },
    )
    store.write_run_json(
        run_id,
        "status.json",
        {"run_id": run_id, "state": state, "stage": "training"},
    )


def test_recovery_interrupts_runs_and_removes_uploads_splits_ttl_and_parts(tmp_path):
    store = FileRunStore(tmp_path)
    upload_id = uuid.uuid4().hex
    split_id = uuid.uuid4().hex
    store.upload_path(upload_id).write_text("feature,target\n1,a\n", encoding="utf-8")
    store.save_split(upload_id, {"split_id": split_id, "params": {}, "train_ids": [], "test_ids": []})
    run_id = uuid.uuid4().hex
    _create_run(store, run_id, "running", datetime.now(timezone.utc).isoformat(), upload_id)

    expired_id = uuid.uuid4().hex
    expired_upload = store.upload_path(expired_id)
    expired_upload.write_text("feature,target\n1,a\n", encoding="utf-8")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
    import os

    os.utime(expired_upload, (old_time, old_time))
    stale_split_id = uuid.uuid4().hex
    store.save_split(expired_id, {
        "split_id": stale_split_id,
        "params": {},
        "train_ids": [],
        "test_ids": [],
    })
    leftover = store.uploads_dir / "leftover.part"
    leftover.write_text("partial", encoding="utf-8")

    store.recover(Settings(data_dir=tmp_path, upload_ttl_hours=24))

    assert store.read_run_json(run_id, "status.json")["state"] == "interrupted"
    assert not store.upload_path(upload_id).exists()
    assert not store.splits_dir(upload_id).exists()
    assert not expired_upload.exists()
    assert not store.splits_dir(expired_id).exists()
    assert not leftover.exists()


def test_retention_keeps_newest_completed_and_never_deletes_running_or_active(tmp_path):
    store = FileRunStore(tmp_path)
    for index in range(21):
        run_id = f"{index + 1:032x}"
        _create_run(
            store,
            run_id,
            "completed",
            f"2026-01-{index + 1:02d}T00:00:00+00:00",
        )
    running_id = f"{22:032x}"
    _create_run(store, running_id, "running", "2026-02-01T00:00:00+00:00")
    active_id = f"{23:032x}"
    _create_run(store, active_id, "completed", "2026-02-02T00:00:00+00:00")

    removed = store.apply_retention(20, active_run_id=active_id)
    remaining = {item["run_id"] for item in store.list_runs()}
    assert len(removed) == 1
    assert len(remaining) == 22
    assert running_id in remaining
    assert active_id in remaining
    assert f"{21:032x}" in remaining
    assert f"{1:032x}" not in remaining
