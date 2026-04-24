"""
validation/evaluate.py — Manual Validation Evaluator

Reads the completed validation_sample.csv (with human labels filled in)
and computes per-topic and overall precision, recall, and F1 score
comparing the pipeline's predictions against human annotations.

Also outputs:
  - validation/validation_metrics.json   (for the paper / supplementary data)
  - validation/confusion_matrix.csv      (per-topic TP/FP/TN/FN counts)

Usage:
    python3.11 -m validation.evaluate
    # or
    python3.11 validation/evaluate.py [--input validation/validation_sample.csv]
                                       [--output-dir validation/]
"""

import argparse
import json
import os
import warnings
import pandas as pd
from analysis.topics import TOPICS

warnings.filterwarnings("ignore")

TOPIC_IDS   = [t["id"]   for t in TOPICS]
TOPIC_NAMES = {t["id"]:  t["name"] for t in TOPICS}


def _prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    return round(precision, 3), round(recall, 3), round(f1, 3)


def evaluate(
    input_path:  str = "validation/validation_sample.csv",
    output_dir:  str = "validation/",
) -> dict:
    print(f"\n[evaluate] Loading {input_path} ...")
    df = pd.read_csv(input_path)

    # Check all label columns exist
    missing = [f"label_{tid}" for tid in TOPIC_IDS if f"label_{tid}" not in df.columns]
    if missing:
        raise ValueError(f"Missing label columns: {missing}")

    # Drop rows where ALL label columns are blank (not yet annotated)
    label_cols = [f"label_{tid}" for tid in TOPIC_IDS]
    df = df.dropna(subset=label_cols, how="all")
    print(f"[evaluate] {len(df)} annotated articles found")

    results      = {}
    confusion    = []
    macro_p = macro_r = macro_f1 = 0.0
    topics_evaluated = 0

    print(f"\n  {'Topic':<35} {'P':>6} {'R':>6} {'F1':>6}  {'TP':>4} {'FP':>4} {'TN':>4} {'FN':>4}")
    print(f"  {'─'*35} {'─'*6} {'─'*6} {'─'*6}  {'─'*4} {'─'*4} {'─'*4} {'─'*4}")

    for tid in TOPIC_IDS:
        col = f"label_{tid}"

        # Use only rows where this column has a value
        sub = df[df[col].notna()].copy()
        sub[col] = sub[col].astype(int)

        # Pipeline prediction: 1 if topic_id appears in pipeline's topic_ids
        sub["pred"] = sub["pipeline_topics"].apply(
            lambda t: 1 if isinstance(t, str) and TOPIC_NAMES[tid] in t else 0
        )

        human = sub[col]
        pred  = sub["pred"]

        tp = int(((pred == 1) & (human == 1)).sum())
        fp = int(((pred == 1) & (human == 0)).sum())
        tn = int(((pred == 0) & (human == 0)).sum())
        fn = int(((pred == 0) & (human == 1)).sum())

        p, r, f1 = _prf(tp, fp, fn)

        results[tid] = {
            "topic_name": TOPIC_NAMES[tid],
            "precision":  p,
            "recall":     r,
            "f1":         f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "n_annotated": len(sub),
        }
        confusion.append({
            "topic_id":   tid,
            "topic_name": TOPIC_NAMES[tid],
            "precision":  p,
            "recall":     r,
            "f1":         f1,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        })

        print(f"  {TOPIC_NAMES[tid]:<35} {p:>6.3f} {r:>6.3f} {f1:>6.3f}  {tp:>4} {fp:>4} {tn:>4} {fn:>4}")

        if (tp + fp + fn) > 0:   # skip topics with zero support
            macro_p  += p
            macro_r  += r
            macro_f1 += f1
            topics_evaluated += 1

    # ── Macro averages ────────────────────────────────────────────────
    if topics_evaluated > 0:
        macro_p  = round(macro_p  / topics_evaluated, 3)
        macro_r  = round(macro_r  / topics_evaluated, 3)
        macro_f1 = round(macro_f1 / topics_evaluated, 3)

    print(f"\n  {'─'*35} {'─'*6} {'─'*6} {'─'*6}")
    print(f"  {'Macro Average':<35} {macro_p:>6.3f} {macro_r:>6.3f} {macro_f1:>6.3f}")

    # ── Overall agreement rate ────────────────────────────────────────
    # Percentage of (article, topic) pairs where pipeline == human
    all_human = []
    all_pred  = []
    for tid in TOPIC_IDS:
        col = f"label_{tid}"
        sub = df[df[col].notna()].copy()
        sub[col] = sub[col].astype(int)
        sub["pred"] = sub["pipeline_topics"].apply(
            lambda t: 1 if isinstance(t, str) and TOPIC_NAMES[tid] in t else 0
        )
        all_human.extend(sub[col].tolist())
        all_pred.extend(sub["pred"].tolist())

    agreement = round(
        sum(h == p for h, p in zip(all_human, all_pred)) / len(all_human) * 100, 1
    ) if all_human else 0.0
    print(f"\n  Overall agreement rate: {agreement}%  ({len(df)} articles × {len(TOPIC_IDS)} topics)")

    # ── Save outputs ──────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)

    metrics = {
        "n_articles":         len(df),
        "n_topics":           len(TOPIC_IDS),
        "macro_precision":    macro_p,
        "macro_recall":       macro_r,
        "macro_f1":           macro_f1,
        "overall_agreement":  agreement,
        "per_topic":          results,
    }
    metrics_path = os.path.join(output_dir, "validation_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[evaluate] ✓ Metrics saved    → {metrics_path}")

    confusion_path = os.path.join(output_dir, "confusion_matrix.csv")
    pd.DataFrame(confusion).to_csv(confusion_path, index=False)
    print(f"[evaluate] ✓ Confusion matrix → {confusion_path}")
    print()

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate manual validation labels")
    parser.add_argument("--input",      default="validation/validation_sample.csv")
    parser.add_argument("--output-dir", default="validation/")
    args = parser.parse_args()

    evaluate(input_path=args.input, output_dir=args.output_dir)
