"""
hybrid_tagger.py — Hybrid Topic Tagger Evaluation

Combines the keyword pipeline and semantic tagger into three hybrid strategies
and evaluates all methods against human annotation:

  1. Keyword Pipeline          — seed-phrase matching (baseline)
  2. Semantic Tagger           — sentence embedding cosine similarity (baseline)
  3. Hybrid OR (Union)         — tag if keyword OR semantic fires
  4. Hybrid AND (Intersect)    — tag only if keyword AND semantic agree
  5. Hybrid Soft Boost         — keyword always kept; semantic added only when its
                                 raw score >= a per-topic threshold tuned on the
                                 SAME annotator set (in-sample upper bound —
                                 optimistic due to tuning leak)
  6. Hybrid Soft Boost (CV)    — same mechanism, but thresholds are tuned on the
                                 OTHER annotator's set (cross-annotator
                                 validation — the honest, leak-free estimate)

Outputs:
  evaluation/results/hybrid_vs_human.txt  — human-readable report
  evaluation/results/hybrid_vs_human.csv  — per-topic metrics for report generation

Usage:
    python3.11 evaluation/taggers/hybrid_tagger.py
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Topic registry ─────────────────────────────────────────────────────────────

TOPIC_KEYS = [
    "policing_public_safety",
    "voter_suppression",
    "book_bans_anti-dei",
    "housing_displacement",
    "maternal_health",
    "redlining_fair_housing",
    "anti-black_surveillance",
    "reparations",
    "school_funding",
    "criminal_justice_reform",
    "environmental_justice",
    "economic_equity_wealth_gap",
]

TOPIC_LABELS = {
    "policing_public_safety":     "Policing/Public Safety",
    "voter_suppression":          "Voter Suppression",
    "book_bans_anti-dei":         "Book Bans/Anti-DEI",
    "housing_displacement":       "Housing/Displacement",
    "maternal_health":            "Maternal Health",
    "redlining_fair_housing":     "Redlining/Fair Housing",
    "anti-black_surveillance":    "Anti-Black Surveillance",
    "reparations":                "Reparations",
    "school_funding":             "School Funding",
    "criminal_justice_reform":    "Criminal Justice Reform",
    "environmental_justice":      "Environmental Justice",
    "economic_equity_wealth_gap": "Economic Equity/Wealth Gap",
}

ANNOTATORS = ["annotator_1", "annotator_3"]
OTHER = {"annotator_1": "annotator_3", "annotator_3": "annotator_1"}

# ── Metrics ────────────────────────────────────────────────────────────────────

def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    n  = tp + fp + fn + tn
    p  = tp / (tp + fp) if (tp + fp) else 0.0
    r  = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    p_o = (tp + tn) / n if n else 0.0
    p_e = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n * n) if n else 0.0
    k   = (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0
    return dict(prec=p, rec=r, f1=f1, kappa=k,
                tp=tp, fp=fp, fn=fn, tn=tn,
                human_pos=tp + fn, pred_pos=tp + fp)


def topic_metrics(df: pd.DataFrame, pred_prefix: str) -> pd.DataFrame:
    rows = []
    for key in TOPIC_KEYS:
        hcol = f"human_{key}"
        pcol = f"{pred_prefix}_{key}"
        if hcol not in df.columns or pcol not in df.columns:
            rows.append({"topic": TOPIC_LABELS[key], **{k: 0.0 for k in
                         ["prec","rec","f1","kappa","tp","fp","fn","tn",
                          "human_pos","pred_pos"]}})
            continue
        m = metrics(df[hcol].fillna(0).astype(int).values,
                    df[pcol].fillna(0).astype(int).values)
        rows.append({"topic": TOPIC_LABELS[key], **m})
    return pd.DataFrame(rows)


# ── Hybrid strategies ──────────────────────────────────────────────────────────

def apply_or(df: pd.DataFrame) -> pd.DataFrame:
    """Union: tag if keyword OR semantic fires."""
    df = df.copy()
    for key in TOPIC_KEYS:
        df[f"hybrid_or_{key}"] = (
            (df[f"pipeline_{key}"].fillna(0).astype(int) == 1) |
            (df[f"semantic_{key}"].fillna(0).astype(int) == 1)
        ).astype(int)
    return df


def apply_and(df: pd.DataFrame) -> pd.DataFrame:
    """Intersection: tag only if keyword AND semantic both fire."""
    df = df.copy()
    for key in TOPIC_KEYS:
        df[f"hybrid_and_{key}"] = (
            (df[f"pipeline_{key}"].fillna(0).astype(int) == 1) &
            (df[f"semantic_{key}"].fillna(0).astype(int) == 1)
        ).astype(int)
    return df


def find_best_soft_threshold(df: pd.DataFrame) -> dict[str, float]:
    """
    Grid-search the per-topic semantic score threshold that maximises F1
    for the soft-boost hybrid on THIS dataframe's articles.

    For each topic: tag if pipeline fires OR sem_score >= t.
    Sweep t in [0.05, 0.45] at 0.01 steps.
    """
    best_thresholds: dict[str, float] = {}
    sweep = np.arange(0.05, 0.46, 0.01)

    for key in TOPIC_KEYS:
        hcol    = f"human_{key}"
        pcol    = f"pipeline_{key}"
        scol    = f"sem_score_{key}"
        if hcol not in df.columns or scol not in df.columns:
            best_thresholds[key] = 0.30
            continue

        y_true = df[hcol].fillna(0).astype(int).values
        kw_bin = df[pcol].fillna(0).astype(int).values
        scores = df[scol].fillna(0).astype(float).values

        best_f1, best_t = -1.0, 0.30
        for t in sweep:
            y_pred = ((kw_bin == 1) | (scores >= t)).astype(int)
            m = metrics(y_true, y_pred)
            if m["f1"] > best_f1:
                best_f1, best_t = m["f1"], round(float(t), 2)

        best_thresholds[key] = best_t

    return best_thresholds


def apply_soft_boost(df: pd.DataFrame, thresholds: dict[str, float],
                     col: str = "hybrid_soft") -> pd.DataFrame:
    """
    Soft boost: keyword always kept; semantic contributes only when its raw
    score >= the per-topic threshold. `col` names the output column prefix
    ("hybrid_soft" for in-sample thresholds, "hybrid_soft_cv" for thresholds
    tuned on the other annotator's set).
    """
    df = df.copy()
    for key in TOPIC_KEYS:
        t      = thresholds.get(key, 0.30)
        kw_bin = df[f"pipeline_{key}"].fillna(0).astype(int)
        scores = df[f"sem_score_{key}"].fillna(0).astype(float)
        df[f"{col}_{key}"] = (
            (kw_bin == 1) | (scores >= t)
        ).astype(int)
    return df


# ── Pretty-print report ────────────────────────────────────────────────────────

METHOD_META = [
    ("pipeline",       "Keyword Pipeline"),
    ("semantic",       "Semantic Tagger"),
    ("hybrid_or",      "Hybrid OR (Union)"),
    ("hybrid_and",     "Hybrid AND (Intersect)"),
    ("hybrid_soft",    "Hybrid Soft Boost"),
    ("hybrid_soft_cv", "Hybrid Soft Boost (CV)"),
]

def print_method_table(results: dict[str, pd.DataFrame], annotator: str,
                       file=None) -> None:
    def w(*args, **kwargs):
        if file:
            print(*args, **kwargs, file=file)
        else:
            print(*args, **kwargs)

    width = 33 + 24 * len(METHOD_META)
    w(f"\n[{annotator}] All Methods — 200 articles")
    w("=" * width)
    w(f"{'Topic':<33}", end="")
    for _, label in METHOD_META:
        w(f"  {label[:20]:<20}  ", end="")
    w()
    w(f"{'':33}", end="")
    for _ in METHOD_META:
        w(f"  {'F1':>5} {'K':>5} {'P':>5} {'R':>5}", end="")
    w()
    w("-" * width)

    for key in TOPIC_KEYS:
        label = TOPIC_LABELS[key]
        w(f"{label:<33}", end="")
        for prefix, _ in METHOD_META:
            df = results[prefix]
            row = df[df["topic"] == label]
            if row.empty:
                w(f"  {'—':>5} {'—':>5} {'—':>5} {'—':>5}", end="")
            else:
                f1 = row["f1"].values[0]
                k  = row["kappa"].values[0]
                p  = row["prec"].values[0]
                r  = row["rec"].values[0]
                w(f"  {f1:>5.3f} {k:>5.3f} {p:>5.3f} {r:>5.3f}", end="")
        w()

    w("-" * width)
    w(f"{'MACRO AVG':<33}", end="")
    for prefix, _ in METHOD_META:
        df = results[prefix]
        w(f"  {df['f1'].mean():>5.3f} {df['kappa'].mean():>5.3f} "
          f"{df['prec'].mean():>5.3f} {df['rec'].mean():>5.3f}", end="")
    w()


def print_soft_thresholds(thresholds: dict[str, float], title: str,
                          file=None) -> None:
    def w(*args, **kwargs):
        if file:
            print(*args, **kwargs, file=file)
        else:
            print(*args, **kwargs)

    w(f"\n{title}")
    w("-" * 55)
    for key, t in thresholds.items():
        w(f"  {TOPIC_LABELS[key]:<35}  t = {t:.2f}")


# ── Main ───────────────────────────────────────────────────────────────────────

def run(
    kw_path:  str = "evaluation/results/pipeline_vs_human.csv",
    sem_path: str = "evaluation/results/semantic_vs_human.csv",
    out_txt:  str = "evaluation/results/hybrid_vs_human.txt",
    out_csv:  str = "evaluation/results/hybrid_vs_human.csv",
) -> None:

    print("[hybrid] Loading annotation data...")
    kw_raw  = pd.read_csv(kw_path)
    sem_raw = pd.read_csv(sem_path)

    all_results: list[dict] = []
    all_output_rows: list[pd.DataFrame] = []
    report_lines: list[str] = []

    def log(msg=""):
        print(msg)
        report_lines.append(msg)

    log("=" * 120)
    log("HYBRID TAGGER EVALUATION — ALL METHODS vs HUMAN ANNOTATION")
    log("=" * 120)
    log()
    log("Methods compared:")
    for i, (_, label) in enumerate(METHOD_META, 1):
        log(f"  {i}. {label}")
    log()
    log("Soft Boost thresholds are tuned per topic by grid search (0.05–0.45).")
    log("  'Hybrid Soft Boost'      tunes on the SAME annotator set it is scored on (in-sample upper bound).")
    log("  'Hybrid Soft Boost (CV)' tunes on the OTHER annotator's set (cross-annotator validation — leak-free).")
    log()
    log("Columns reported per method:  F1  Kappa  Precision  Recall")
    log()

    # ── Phase 1: build merged frame per annotator, tune thresholds ────
    merged_by_ann: dict[str, pd.DataFrame] = {}
    thresholds_by_ann: dict[str, dict[str, float]] = {}

    sem_cols = (
        [f"semantic_{k}" for k in TOPIC_KEYS] +
        [f"sem_score_{k}" for k in TOPIC_KEYS]
    )

    for ann in ANNOTATORS:
        kw_ann  = kw_raw[kw_raw["annotator"] == ann].reset_index(drop=True)
        sem_ann = sem_raw[sem_raw["annotator"] == ann].reset_index(drop=True)

        merged = kw_ann.copy()
        for col in sem_cols:
            if col in sem_ann.columns:
                merged[col] = sem_ann[col].values

        merged = apply_or(merged)
        merged = apply_and(merged)
        merged_by_ann[ann] = merged
        thresholds_by_ann[ann] = find_best_soft_threshold(merged)

    # ── Phase 2: apply soft boost (in-sample + cross-validated) ───────
    import io
    for ann in ANNOTATORS:
        merged = merged_by_ann[ann]
        merged = apply_soft_boost(merged, thresholds_by_ann[ann],
                                  col="hybrid_soft")
        merged = apply_soft_boost(merged, thresholds_by_ann[OTHER[ann]],
                                  col="hybrid_soft_cv")
        merged_by_ann[ann] = merged

        # Compute metrics for all methods
        results: dict[str, pd.DataFrame] = {}
        for prefix, _ in METHOD_META:
            results[prefix] = topic_metrics(merged, prefix)

        # Log thresholds
        buf = io.StringIO()
        print_soft_thresholds(
            thresholds_by_ann[ann],
            f"[{ann}] In-sample thresholds (tuned and scored on {ann} — upper bound)",
            file=buf)
        print_soft_thresholds(
            thresholds_by_ann[OTHER[ann]],
            f"[{ann}] Cross-validated thresholds (tuned on {OTHER[ann]}, scored on {ann})",
            file=buf)
        log(buf.getvalue().strip())
        log()

        # Log comparison table
        buf2 = io.StringIO()
        print_method_table(results, ann, file=buf2)
        log(buf2.getvalue().strip())
        log()

        # Collect rows for CSV
        for prefix, label in METHOD_META:
            for _, row in results[prefix].iterrows():
                all_results.append({
                    "annotator": ann,
                    "method":    label,
                    "topic":     row["topic"],
                    "f1":        round(row["f1"], 4),
                    "kappa":     round(row["kappa"], 4),
                    "precision": round(row["prec"], 4),
                    "recall":    round(row["rec"], 4),
                    "tp":        int(row["tp"]),
                    "fp":        int(row["fp"]),
                    "fn":        int(row["fn"]),
                    "tn":        int(row["tn"]),
                })

        all_output_rows.append(merged)

    # ── Summary ───────────────────────────────────────────────────────
    log("=" * 120)
    log("SUMMARY — Macro-Averaged Scores (both annotator sets pooled)")
    log("-" * 60)
    log(f"  {'Method':<30}  {'Macro F1':>9}  {'Macro Kappa':>12}")
    log("-" * 60)
    results_df = pd.DataFrame(all_results)
    for _, label in METHOD_META:
        subset = results_df[results_df["method"] == label]
        log(f"  {label:<30}  {subset['f1'].mean():>9.4f}  {subset['kappa'].mean():>12.4f}")
    log("=" * 120)
    log()
    log("The 'Hybrid Soft Boost (CV)' row is the honest, leak-free estimate to report.")
    log("The gap between it and the in-sample 'Hybrid Soft Boost' row quantifies the tuning optimism.")

    # ── Save ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(out_txt), exist_ok=True)
    with open(out_txt, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\n[hybrid] ✓ Report saved → {out_txt}")

    results_df.to_csv(out_csv, index=False)
    print(f"[hybrid] ✓ Results CSV saved → {out_csv}")

    combined = pd.concat(all_output_rows, ignore_index=True)
    preds_path = out_csv.replace(".csv", "_predictions.csv")
    combined.to_csv(preds_path, index=False)
    print(f"[hybrid] ✓ Per-article predictions saved → {preds_path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Hybrid tagger evaluation")
    p.add_argument("--kw-path",  default="evaluation/results/pipeline_vs_human.csv")
    p.add_argument("--sem-path", default="evaluation/results/semantic_vs_human.csv")
    p.add_argument("--out-txt",  default="evaluation/results/hybrid_vs_human.txt")
    p.add_argument("--out-csv",  default="evaluation/results/hybrid_vs_human.csv")
    a = p.parse_args()
    run(kw_path=a.kw_path, sem_path=a.sem_path,
        out_txt=a.out_txt, out_csv=a.out_csv)
