from pathlib import Path

import pandas as pd
from sklearn.datasets import load_breast_cancer


def list_samples() -> list[dict[str, str]]:
    return [{"name": "breast_cancer", "label": "Breast Cancer"}]


def ensure_sample_csv(name: str, directory: str | Path) -> Path:
    if name != "breast_cancer":
        raise ValueError(f"Unknown sample dataset: {name}")

    output = Path(directory) / "breast_cancer.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        dataset = load_breast_cancer(as_frame=True)
        frame = dataset.data.copy()
        frame["diagnosis"] = dataset.target_names[dataset.target]
        frame.to_csv(output, index=False)
    return output
