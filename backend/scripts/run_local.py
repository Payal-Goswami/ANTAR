from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mde.data.diagnostics import detect_feature_flags, resolve_columns
from mde.data.report import build_quality_report
from mde.data.target import build_labelled_set
from mde.data.split import make_split
from mde.samples import ensure_sample_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Day 3 core pipeline.")
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--target", type=str, default="diagnosis")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--cap", type=int, default=20_000)
    parser.add_argument("--tokens", nargs="*", default=[])
    args = parser.parse_args()

    if args.csv:
        path = Path(args.csv)
    else:
        path = ensure_sample_csv("breast_cancer", Path("data") / "samples")

    raw = __import__("pandas").read_csv(path)
    labelled = build_labelled_set(raw, args.target, args.tokens)
    record = make_split(
        labelled.y,
        test_size=args.test_size,
        seed=args.seed,
        cap=args.cap,
        params={
            "target": args.target,
            "target_missing_tokens": args.tokens,
            "seed": args.seed,
            "test_size": args.test_size,
        },
    )
    train_df = raw.loc[record.train_ids].copy()
    test_df = raw.loc[record.test_ids].copy()
    feature_flags = detect_feature_flags(train_df, target_column=args.target)
    decisions = {name: info.get("default_decision", "include") for name, info in feature_flags.items() if info.get("flag")}
    resolved = resolve_columns(feature_flags, decisions=decisions, target_column=args.target)
    quality = build_quality_report(
        raw_df=raw,
        labelled_set=labelled,
        train_df=train_df,
        test_df=test_df,
        feature_flags=feature_flags,
        decisions=decisions,
        target_column=args.target,
        missing_tokens={"features": [], "target": args.tokens},
    )

    print(f"Labelled rows: {len(labelled.y)}")
    print(f"Train rows: {len(record.train_ids)}")
    print(f"Test rows: {len(record.test_ids)}")
    print(f"Resolved columns: {resolved}")
    print("Quality report sections:")
    for section in quality["sections"]:
        print(f"- {section['id']} ({section['source']})")


if __name__ == "__main__":
    main()
