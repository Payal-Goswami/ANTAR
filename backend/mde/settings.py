from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("./data")
    max_upload_mb: int = 20
    max_cols: int = 50
    max_rows: int = 20_000
    keep_runs: int = 20
    upload_ttl_hours: int = 24
    n_jobs: int = 1


def get_settings() -> Settings:
    return Settings(
        data_dir=Path(os.getenv("MDE_DATA_DIR", "./data")),
        max_upload_mb=int(os.getenv("MDE_MAX_UPLOAD_MB", "20")),
        max_cols=int(os.getenv("MDE_MAX_COLS", "50")),
        max_rows=int(os.getenv("MDE_MAX_ROWS", "20000")),
        keep_runs=int(os.getenv("MDE_KEEP_RUNS", "20")),
        upload_ttl_hours=int(os.getenv("MDE_UPLOAD_TTL_HOURS", "24")),
        n_jobs=int(os.getenv("MDE_N_JOBS", "1")),
    )
