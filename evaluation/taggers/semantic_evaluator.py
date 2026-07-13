"""
semantic_evaluator.py

Validates the semantic (embedding-based) topic tagger against human annotation.
Uses pre-computed sem_score_* columns from pipeline_predictions.csv.

Steps:
  1. Match each annotator's articles to their sem_scores in pipeline_predictions.csv
  2. Try multiple thresholds to find the best-performing one
  3. Compare semantic predictions vs human labels
  4. Save results alongside keyword pipeline results for side-by-side comparison

Usage:
    python3.11 evaluation/taggers/semantic_evaluator.py

Outputs:
    evaluation/results/semantic_vs_human.csv
    evaluation/results/semantic_vs_human.txt
"""

import os
import sys
import pandas as pd
import numpy as np

ANNOTATOR_FILES = {
    "annotator_1": "evaluation/annotation/annotated/annotator_1.xlsx",
    "annotator_3": "evaluation/annotation/annotated/annotator_3.xlsx",
}

PIPELINE_CSV = "evaluation/results/pipeline_predictions.csv"

# Excel label col → sem_score column
TOPIC_MAP = {
    "Policing/Public Safety":      ("sem_score_policing",              "Policing & Public Safety"),
    "Voter Suppression":           ("sem_score_voter_suppression",     "Voter Suppression"),
    "Book Bans/Anti-DEI":          ("sem_score_book_bans_dei",         "Book Bans & Anti-DEI"),
    "Housing/Displacement":        ("sem_score_housing",               "Housing & Displacement"),
    "Maternal Health":             ("sem_score_maternal_health",       "Maternal Health"),
    "Redlining/Fair Housing":      ("sem_score_redlining",             "Redlining & Fair Housing"),
    "Anti-Black Surveillance":     ("sem_score_surveillance",          "Anti-Black Surveillance"),
    "Reparations":                 ("sem_score_reparations",           "Reparations"),
    "School Funding":              ("sem_score_school_funding",        "School Funding"),
    "Criminal Justice\nReform":    ("sem_score_criminal_justice",      "Criminal Justice Reform"),
    "Environmental Justice":       ("sem_score_environmental_justice", "Environmental Justice"),
    "Economic Equity/Wealth\nGap": ("sem_score_economic_equity",       "Economic Equity & Wealth Gap"),
}

LABEL_COLS  = list(TOPIC_MAP.keys())
THRESHOLDS  = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_annotator(path):
    df = pd.read_excel(path, sheet_name="Annotation").iloc[1:].copy()
    df["ID"] = df["ID"].astype(int)
    for col in LABEL_COLS:
        df[col] = df[col].apply(lambda v: 1 if isinstance(v, str) and "✓" in v else 0)
    return df.set_index("ID")


def compute_metrics(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    n  = tp + fp + fn + tn
    p  = tp / (tp + fp) if (tp + fp) else 0.0
    r  = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    p_o = (tp + tn) / n if n else 0.0
    p_e = ((tp+fp)*(tp+fn) + (tn+fn)*(tn+fp)) / (n*n) if n else 0.0
    k   = (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                precision=round(p,3), recall=round(r,3),
                f1=round(f1,3), kappa=round(k,3),
                human_pos=tp+fn, pipeline_pos=tp+fp)


def format_table(rows, title):
    lines = [title, "=" * max(len(title), 80), ""]
    hdr = f"{'Topic':<32} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Kappa':>7} {'Acc':>6}  TP  FP  FN  TN  H+  P+"
    sep = "-" * len(hdr)
    lines += [hdr, sep]
    macro = dict(precision=0, recall=0, f1=0, kappa=0)
    for r in rows:
        acc = (r['tp']+r['tn']) / (r['tp']+r['fp']+r['fn']+r['tn'])
        lines.append(
            f"{r['topic']:<32} {r['precision']:>6.3f} {r['recall']:>6.3f} {r['f1']:>6.3f} "
            f"{r['kappa']:>7.3f} {acc:>6.3f} "
            f"{r['tp']:>3} {r['fp']:>3} {r['fn']:>3} {r['tn']:>3} "
            f"{r['human_pos']:>3} {r['pipeline_pos']:>3}"
        )
        for k in macro: macro[k] += r[k]
    n = len(rows)
    lines.append(sep)
    lines.append(
        f"{'MACRO AVG':<32} {macro['precision']/n:>6.3f} {macro['recall']/n:>6.3f} "
        f"{macro['f1']/n:>6.3f} {macro['kappa']/n:>7.3f}"
    )
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("[1/4] Loading pipeline predictions (with sem_scores)...")
    pipe      = pd.read_csv(PIPELINE_CSV)
    by_id     = pipe.set_index("article_id")
    by_title  = pipe.set_index("title")

    report_lines = ["SEMANTIC TAGGER vs HUMAN ANNOTATION", ""]
    all_detail   = []
    best_thresholds = {}

    for ann_name, ann_path in ANNOTATOR_FILES.items():
        print(f"\n[2/4] Processing {ann_name}...")
        ann_df = load_annotator(ann_path)

        # Match each annotator row to its sem_scores
        matched_scores = {}   # annotator_id → pipe row
        for aid in ann_df.index:
            title = str(ann_df.at[aid, "Title"]).strip()
            if aid in by_id.index and str(by_id.at[aid, "title"]).strip() == title:
                matched_scores[aid] = by_id.loc[aid]
            elif title in by_title.index:
                matched_scores[aid] = by_title.loc[title]

        matched_ids = list(matched_scores.keys())
        print(f"    Matched {len(matched_ids)} / {len(ann_df)} articles to sem_scores")

        # ── Find best global threshold ────────────────────────────────
        print("    Scanning thresholds...")
        threshold_f1 = {}
        for thresh in THRESHOLDS:
            topic_f1s = []
            for excel_col, (score_col, _) in TOPIC_MAP.items():
                y_true = ann_df[excel_col].reindex(matched_ids).fillna(0).astype(int).values
                y_pred = np.array([
                    1 if matched_scores[aid][score_col] >= thresh else 0
                    for aid in matched_ids
                ])
                m = compute_metrics(y_true, y_pred)
                topic_f1s.append(m["f1"])
            threshold_f1[thresh] = np.mean(topic_f1s)
            print(f"      threshold={thresh:.2f}  macro F1={threshold_f1[thresh]:.3f}")

        best_thresh = max(threshold_f1, key=threshold_f1.get)
        best_thresholds[ann_name] = best_thresh
        print(f"    → Best threshold: {best_thresh}  (macro F1={threshold_f1[best_thresh]:.3f})")

        # ── Compute final metrics at best threshold ───────────────────
        rows = []
        for excel_col, (score_col, topic_name) in TOPIC_MAP.items():
            label  = excel_col.replace("\n", " ")
            y_true = ann_df[excel_col].reindex(matched_ids).fillna(0).astype(int).values
            y_pred = np.array([
                1 if matched_scores[aid][score_col] >= best_thresh else 0
                for aid in matched_ids
            ])
            m = compute_metrics(y_true, y_pred)
            m["topic"] = label
            rows.append(m)

        report_lines.append(
            format_table(rows, f"[{ann_name}] Semantic Tagger vs Human Labels "
                               f"(threshold={best_thresh}, {len(matched_ids)} articles)")
        )
        report_lines.append("")

        # ── Build detail rows ─────────────────────────────────────────
        for aid in matched_ids:
            pipe_row = matched_scores[aid]
            row = {
                "annotator":    ann_name,
                "annotator_id": aid,
                "article_id":   pipe_row.get("article_id", ""),
                "title":        ann_df.at[aid, "Title"],
                "source":       ann_df.at[aid, "Source"],
            }
            for excel_col, (score_col, _) in TOPIC_MAP.items():
                key = excel_col.replace("\n", " ").replace("/", "_").replace(" ", "_").lower()
                row[f"human_{key}"]    = ann_df.at[aid, excel_col]
                row[f"sem_score_{key}"] = pipe_row[score_col]
                row[f"semantic_{key}"] = 1 if pipe_row[score_col] >= best_thresh else 0
            all_detail.append(row)

    # ── Save ──────────────────────────────────────────────────────────
    print("\n[3/4] Saving outputs...")
    detail_df = pd.DataFrame(all_detail)
    detail_df.to_csv("evaluation/results/semantic_vs_human.csv", index=False)
    print("  Saved: evaluation/results/semantic_vs_human.csv")

    report_text = "\n".join(report_lines)
    with open("evaluation/results/semantic_vs_human.txt", "w") as f:
        f.write(report_text)
    print("  Saved: evaluation/results/semantic_vs_human.txt")

    print("\n[4/4] Best thresholds found:")
    for ann, t in best_thresholds.items():
        print(f"  {ann}: {t}")

    print("\n" + report_text)


if __name__ == "__main__":
    main()
