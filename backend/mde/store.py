from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from mde.errors import NotFound


_VALID_ID = re.compile(r"^[0-9a-f]{32}$")


class FileRunStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir).resolve()
        self.uploads_dir = self.data_dir / "uploads"
        self.splits_root = self.data_dir / "splits"
        self.runs_dir = self.data_dir / "runs"
        self.samples_dir = self.data_dir / "samples"
        for directory in (self.uploads_dir, self.splits_root, self.runs_dir, self.samples_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def valid_id(value: str) -> str:
        if not isinstance(value, str) or not _VALID_ID.fullmatch(value):
            raise NotFound("The requested resource was not found.")
        return value

    @classmethod
    def _json_bytes(cls, payload: object) -> bytes:
        return json.dumps(payload, allow_nan=False, ensure_ascii=False, indent=2).encode("utf-8")

    @classmethod
    def write_json(cls, path: str | Path, payload: object) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".part")
        temporary.write_bytes(cls._json_bytes(payload))
        temporary.replace(destination)

    @classmethod
    def read_json(cls, path: str | Path) -> dict:
        last_error = None
        for attempt in range(3):
            try:
                with Path(path).open("r", encoding="utf-8") as file:
                    return json.load(file)
            except (OSError, json.JSONDecodeError) as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.01)
        raise NotFound("The requested resource was not found.") from last_error

    def upload_path(self, upload_id: str) -> Path:
        upload_id = self.valid_id(upload_id)
        return self.uploads_dir / f"{upload_id}.csv"

    def upload_metadata_path(self, upload_id: str) -> Path:
        upload_id = self.valid_id(upload_id)
        return self.uploads_dir / f"{upload_id}.json"

    def save_upload_metadata(self, upload_id: str, metadata: dict) -> None:
        self.write_json(self.upload_metadata_path(upload_id), metadata)

    def load_upload_metadata(self, upload_id: str) -> dict:
        path = self.upload_metadata_path(upload_id)
        if not path.is_file():
            raise NotFound("The requested upload was not found.")
        return self.read_json(path)

    def part_path(self, upload_id: str) -> Path:
        upload_id = self.valid_id(upload_id)
        return self.uploads_dir / f"{upload_id}.part"

    def splits_dir(self, upload_id: str) -> Path:
        upload_id = self.valid_id(upload_id)
        return self.splits_root / upload_id

    def save_split(self, upload_id: str, record: dict) -> None:
        upload_id = self.valid_id(upload_id)
        split_id = self.valid_id(record.get("split_id"))
        self.write_json(self.splits_dir(upload_id) / f"{split_id}.json", record)

    def load_split(self, upload_id: str, split_id: str) -> dict:
        upload_id = self.valid_id(upload_id)
        split_id = self.valid_id(split_id)
        path = self.splits_dir(upload_id) / f"{split_id}.json"
        if not path.is_file():
            raise NotFound("The requested split was not found.")
        return self.read_json(path)

    def delete_upload(self, upload_id: str) -> None:
        upload_id = self.valid_id(upload_id)
        self.upload_path(upload_id).unlink(missing_ok=True)
        self.upload_metadata_path(upload_id).unlink(missing_ok=True)
        shutil.rmtree(self.splits_dir(upload_id), ignore_errors=True)

    def run_dir(self, run_id: str) -> Path:
        run_id = self.valid_id(run_id)
        return self.runs_dir / run_id

    def create_run(self, run_id: str) -> Path:
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def run_json_path(self, run_id: str, name: str) -> Path:
        if Path(name).name != name or not name.endswith(".json"):
            raise ValueError("Run metadata filenames must be simple JSON filenames.")
        return self.run_dir(run_id) / name

    def read_run_json(self, run_id: str, name: str) -> dict:
        return self.read_json(self.run_json_path(run_id, name))

    def write_run_json(self, run_id: str, name: str, payload: object) -> None:
        self.write_json(self.run_json_path(run_id, name), payload)

    def update_status(self, run_id: str, patch: dict) -> dict:
        try:
            status = self.read_run_json(run_id, "status.json")
        except NotFound:
            status = {}
        status.update(patch)
        self.write_run_json(run_id, "status.json", status)
        return status

    def write_parquet(self, run_id: str, name: str, frame: pd.DataFrame) -> None:
        if Path(name).name != name or not name.endswith(".parquet"):
            raise ValueError("Run data filenames must be simple Parquet filenames.")
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        destination = run_dir / name
        temporary = run_dir / f"{name}.part"
        frame.to_parquet(temporary, index=False)
        temporary.replace(destination)

    def read_parquet(self, run_id: str, name: str) -> pd.DataFrame:
        if Path(name).name != name or not name.endswith(".parquet"):
            raise ValueError("Run data filenames must be simple Parquet filenames.")
        path = self.run_dir(run_id) / name
        if not path.is_file():
            raise NotFound("The requested run data was not found.")
        return pd.read_parquet(path)

    def list_runs(self) -> list[dict]:
        runs = []
        for run_dir in self.runs_dir.iterdir():
            if not run_dir.is_dir() or not _VALID_ID.fullmatch(run_dir.name):
                continue
            try:
                config = self.read_run_json(run_dir.name, "config.json")
                status = self.read_run_json(run_dir.name, "status.json")
            except NotFound:
                continue
            runs.append({"run_id": run_dir.name, "config": config, "status": status})
        return sorted(
            runs,
            key=lambda item: item["config"].get("created_at", ""),
            reverse=True,
        )

    def delete_run(self, run_id: str) -> None:
        shutil.rmtree(self.run_dir(run_id), ignore_errors=False)

    def apply_retention(self, keep: int, active_run_id: str | None = None) -> list[str]:
        removed = []
        retained = 0
        for run in self.list_runs():
            run_id = run["run_id"]
            state = run["status"].get("state")
            if state == "running" or run_id == active_run_id:
                continue
            retained += 1
            if retained > keep:
                self.delete_run(run_id)
                removed.append(run_id)
        return removed

    def recover(self, settings) -> None:
        for run in self.list_runs():
            run_id = run["run_id"]
            status = run["status"]
            config = run["config"]
            if status.get("state") == "running":
                self.update_status(
                    run_id,
                    {
                        "state": "interrupted",
                        "stage": "interrupted",
                        "error": "The server stopped before this run completed.",
                    },
                )
            upload_id = config.get("upload_id")
            if upload_id:
                self.delete_upload(upload_id)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.upload_ttl_hours)
        for upload_path in self.uploads_dir.glob("*.csv"):
            modified = datetime.fromtimestamp(upload_path.stat().st_mtime, timezone.utc)
            if modified < cutoff and _VALID_ID.fullmatch(upload_path.stem):
                self.delete_upload(upload_path.stem)

        for part_path in self.data_dir.rglob("*.part"):
            if part_path.is_file():
                part_path.unlink()
