from pathlib import Path

from mde.data.parsing import infer_feature_types, load_raw, read_header


def profile_frame(path: str | Path) -> dict:
    header = read_header(path, max_cols=2**31 - 1)
    raw = load_raw(path)
    typed, typing_report = infer_feature_types(raw)
    columns = [
        {
            "name": name,
            "kind": typing_report[name]["kind"],
            "missing_pct": round(float(typed[name].isna().mean() * 100), 2)
            if len(typed)
            else 0.0,
        }
        for name in header
    ]
    return {"n_rows": len(raw), "n_cols": len(header), "columns": columns}
