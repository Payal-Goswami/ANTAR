from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mde.analysis.metrics import model_metrics
from mde.data.diagnostics import detect_feature_flags, resolve_columns
from mde.data.report import build_quality_report
from mde.data.target import build_labelled_set
from mde.data.split import make_split
from mde.samples import ensure_sample_csv
from mde.training.train import encode_labels, fit_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Day 4 core pipeline.")
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
    feature_cols = [col for col in raw.columns if col != args.target and col in resolved["included"] or col not in resolved["excluded"]]
    feature_cols = [col for col in raw.columns if col != args.target]
    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols]
    y_train = labelled.y.loc[record.train_ids]
    y_test = labelled.y.loc[record.test_ids]
    label_order = sorted(labelled.y.unique().tolist())
    y_test_encoded = encode_labels(label_order, y_test)
    results = fit_models(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        numeric_cols=[col for col in feature_cols if raw[col].dtype.kind in "iufc"],
        categorical_cols=[col for col in feature_cols if col not in [col for col in feature_cols if raw[col].dtype.kind in "iufc"]],
        model_keys=["dummy", "logreg", "tree", "rf", "xgb"],
        seed=args.seed,
        n_jobs=1,
    )

    print(f"Labelled rows: {len(labelled.y)}")
    print(f"Train rows: {len(record.train_ids)}")
    print(f"Test rows: {len(record.test_ids)}")
    print(f"Resolved columns: {resolved}")
    print("Quality report sections:")
    for section in quality["sections"]:
        print(f"- {section['id']} ({section['source']})")
    print("\nMetrics:")
    for key in ["dummy", "logreg", "tree", "rf", "xgb"]:
        if key not in results:
            continue
        model_result = results[key]
        if model_result["status"] == "failed":
            print(f"{key}: failed - {model_result['error']}")
            continue
        metrics = model_metrics(y_test_encoded.to_numpy(), model_result["pred"], model_result["proba"], len(label_order))
        print(f"{key}: accuracy={metrics['accuracy']['value']:.4f}")


if __name__ == "__main__":
    main()
