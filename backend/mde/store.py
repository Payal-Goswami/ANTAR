from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

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
        try:
            with Path(path).open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise NotFound("The requested resource was not found.") from error

    def upload_path(self, upload_id: str) -> Path:
        upload_id = self.valid_id(upload_id)
        return self.uploads_dir / f"{upload_id}.csv"

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
        shutil.rmtree(self.splits_dir(upload_id), ignore_errors=True)
