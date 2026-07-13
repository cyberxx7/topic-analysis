"""
keyword_tagger.py

End-to-end comparison:
  1. Load articles from human-annotated Excel sheets
  2. Enrich with body text from pipeline_predictions.csv
  3. Run keyword-based topic pipeline on those articles
  4. Compare pipeline output vs human labels per annotator

NOTE: The two annotators labeled completely different sets of articles.
      Matching is done by title for annotator_3 (IDs differ from pipeline).

Usage:
    python3.11 evaluation/taggers/keyword_tagger.py

Outputs:
    evaluation/results/pipeline_vs_human.csv    — per-article results
    evaluation/results/pipeline_vs_human.txt    — metrics report
"""

import json
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.topic_matcher import match_topics

# ── Config ─────────────────────────────────────────────────────────────────────

ANNOTATOR_FILES = {
    "annotator_1": "evaluation/annotation/annotated/annotator_1.xlsx",
    "annotator_3": "evaluation/annotation/annotated/annotator_3.xlsx",
}

PIPELINE_PREDICTIONS = "evaluation/results/pipeline_predictions.csv"

# Excel label column → pipeline topic name
TOPIC_MAP = {
    "Policing/Public Safety":      "Policing & Public Safety",
    "Voter Suppression":           "Voter Suppression",
    "Book Bans/Anti-DEI":          "Book Bans & Anti-DEI",
    "Housing/Displacement":        "Housing & Displacement",
    "Maternal Health":             "Maternal Health",
    "Redlining/Fair Housing":      "Redlining & Fair Housing",
    "Anti-Black Surveillance":     "Anti-Black Surveillance",
    "Reparations":                 "Reparations",
    "School Funding":              "School Funding",
    "Criminal Justice\nReform":    "Criminal Justice Reform",
    "Environmental Justice":       "Environmental Justice",
    "Economic Equity/Wealth\nGap": "Economic Equity & Wealth Gap",
}

LABEL_COLS = list(TOPIC_MAP.keys())


# ── Load & prepare ─────────────────────────────────────────────────────────────

def load_annotator(path):
    df = pd.read_excel(path, sheet_name="Annotation")
    df = df.iloc[1:].copy()  # drop repeated-header row
    df["ID"] = df["ID"].astype(int)
    for col in LABEL_COLS:
        df[col] = df[col].apply(lambda v: 1 if isinstance(v, str) and "✓" in v else 0)
    return df.set_index("ID")


def build_article_df(ann_df, pipe_by_id, pipe_by_title):
    """
    Build article DataFrame for one annotator.
    Matches to pipeline by article_id first (annotator_1),
    falls back to title match (annotator_3).
    """
    articles = []
    id_map = {}  # annotator row ID → pipeline article_id

    for aid in ann_df.index:
        title = str(ann_df.at[aid, "Title"]).strip()

        if aid in pipe_by_id.index:
            pipe_row = pipe_by_id.loc[aid]
            pipe_id  = aid
        elif title in pipe_by_title.index:
            pipe_row = pipe_by_title.loc[title]
            pipe_id  = pipe_row["article_id"]
        else:
            continue

        id_map[aid] = pipe_id
        articles.append({
            "annotator_id": aid,
            "article_id":   pipe_id,
            "title":        title,
            "description":  ann_df.at[aid, "Description"],
            "source":       ann_df.at[aid, "Source"],
            "date":         ann_df.at[aid, "Date"],
            "link":         ann_df.at[aid, "Link"],
            "body":         pipe_row.get("body", ""),
        })

    return pd.DataFrame(articles).set_index("annotator_id"), id_map


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_pred, name=""):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    n  = tp + fp + fn + tn

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy  = (tp + tn) / n if n else 0.0

    p_o = (tp + tn) / n if n else 0.0
    p_e = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n * n) if n else 0.0
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0

    return dict(
        topic=name, tp=tp, fp=fp, fn=fn, tn=tn,
        precision=round(precision, 3), recall=round(recall, 3),
        f1=round(f1, 3), accuracy=round(accuracy, 3), kappa=round(kappa, 3),
        human_pos=tp + fn, pipeline_pos=tp + fp,
    )


def format_table(rows, title):
    lines = [title, "=" * max(len(title), 80), ""]
    hdr = f"{'Topic':<32} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Kappa':>7} {'Acc':>6}  TP  FP  FN  TN  H+  P+"
    sep = "-" * len(hdr)
    lines += [hdr, sep]
    macro = dict(precision=0, recall=0, f1=0, kappa=0)
    for r in rows:
        lines.append(
            f"{r['topic']:<32} {r['precision']:>6.3f} {r['recall']:>6.3f} {r['f1']:>6.3f} "
            f"{r['kappa']:>7.3f} {r['accuracy']:>6.3f} "
            f"{r['tp']:>3} {r['fp']:>3} {r['fn']:>3} {r['tn']:>3} "
            f"{r['human_pos']:>3} {r['pipeline_pos']:>3}"
        )
        for k in macro:
            macro[k] += r[k]
    n = len(rows)
    lines.append(sep)
    lines.append(
        f"{'MACRO AVG':<32} {macro['precision']/n:>6.3f} {macro['recall']/n:>6.3f} "
        f"{macro['f1']/n:>6.3f} {macro['kappa']/n:>7.3f}"
    )
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("[1/4] Loading pipeline predictions...")
    pipe_csv   = pd.read_csv(PIPELINE_PREDICTIONS)
    pipe_by_id    = pipe_csv.set_index("article_id")
    pipe_by_title = pipe_csv.set_index("title")

    print("[2/4] Loading annotator Excel sheets...")
    all_detail_rows = []
    report_lines = ["PIPELINE vs HUMAN ANNOTATION — KEYWORD MATCHER", ""]

    annotator_results = {}

    for ann_name, ann_path in ANNOTATOR_FILES.items():
        ann_df = load_annotator(ann_path)
        articles, id_map = build_article_df(ann_df, pipe_by_id, pipe_by_title)
        print(f"      {ann_name}: {len(articles)} articles matched to pipeline")

        # Run pipeline on this annotator's articles
        tagged = match_topics(articles.reset_index())
        tagged = tagged.set_index("annotator_id")
        tagged_count = (tagged["topics"].str.strip() != "").sum()
        print(f"        Pipeline tagged: {tagged_count} / {len(articles)}")

        # Compute metrics
        rows = []
        for excel_col, pipe_topic in TOPIC_MAP.items():
            label = excel_col.replace("\n", " ")
            y_true = ann_df[excel_col].reindex(articles.index).fillna(0).astype(int).values
            y_pred = tagged["topics"].reindex(articles.index).fillna("").apply(
                lambda s: 1 if pipe_topic in s else 0
            ).values
            rows.append(compute_metrics(y_true, y_pred, name=label))

        annotator_results[ann_name] = rows
        report_lines.append(format_table(rows, f"[{ann_name}] Pipeline vs Human Labels ({len(articles)} articles)"))
        report_lines.append("")

        # Per-article detail
        for aid in articles.index:
            row = {
                "annotator":     ann_name,
                "annotator_id":  aid,
                "article_id":    id_map.get(aid, ""),
                "title":         articles.at[aid, "title"],
                "source":        articles.at[aid, "source"],
                "pipeline_topics": tagged.at[aid, "topics"],
                "pipeline_phrases": tagged.at[aid, "matched_phrases"],
            }
            for excel_col, pipe_topic in TOPIC_MAP.items():
                short = excel_col.replace("\n", " ").replace("/", "_").replace(" ", "_").lower()
                row[f"human_{short}"]    = ann_df.at[aid, excel_col]
                row[f"pipeline_{short}"] = 1 if pipe_topic in str(tagged.at[aid, "topics"]) else 0
            all_detail_rows.append(row)

    # Save outputs
    print("\n[3/4] Saving outputs...")
    detail_df = pd.DataFrame(all_detail_rows)
    detail_df.to_csv("evaluation/results/pipeline_vs_human.csv", index=False)
    print("  Saved: evaluation/results/pipeline_vs_human.csv")

    report_text = "\n".join(report_lines)
    with open("evaluation/results/pipeline_vs_human.txt", "w") as f:
        f.write(report_text)
    print("  Saved: evaluation/results/pipeline_vs_human.txt")

    print("\n[4/4] Results:\n")
    print(report_text)


if __name__ == "__main__":
    main()
