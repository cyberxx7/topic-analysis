"""
supervised_tagger.py — Supervised Topic Classifier (logistic regression)

Trains one logistic regression per topic on sentence embeddings of the
human-annotated articles, and evaluates with the same leak-free
cross-annotator protocol as the Soft Boost (CV) hybrid:

  train on Annotator 1's 200 articles → test on Annotator 3's 200 articles
  train on Annotator 3's 200 articles → test on Annotator 1's 200 articles

Features per article/topic:
  - sentence embedding of title + description + body (all-MiniLM-L6-v2, 384-d)
  - the keyword pipeline's binary prediction for that topic
  - the semantic tagger's raw cosine score for that topic

Topics with fewer than 2 positive training examples fall back to the keyword
pipeline prediction (logged in the report).

Usage:
    python3.11 evaluation/taggers/supervised_tagger.py

Outputs:
    evaluation/results/supervised_vs_human.txt
    evaluation/results/supervised_vs_human.csv
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sklearn.linear_model import LogisticRegression
from sentence_transformers import SentenceTransformer

ANNOTATOR_FILES = {
    "annotator_1": "evaluation/annotation/annotated/annotator_1.xlsx",
    "annotator_3": "evaluation/annotation/annotated/annotator_3.xlsx",
}
PIPELINE_CSV = "evaluation/results/pipeline_predictions.csv"
OUT_TXT = "evaluation/results/supervised_vs_human.txt"
OUT_CSV = "evaluation/results/supervised_vs_human.csv"

# Excel label column → (pipeline topic name, sem_score column)
TOPIC_MAP = {
    "Policing/Public Safety":      ("Policing & Public Safety",      "sem_score_policing"),
    "Voter Suppression":           ("Voter Suppression",             "sem_score_voter_suppression"),
    "Book Bans/Anti-DEI":          ("Book Bans & Anti-DEI",          "sem_score_book_bans_dei"),
    "Housing/Displacement":        ("Housing & Displacement",        "sem_score_housing"),
    "Maternal Health":             ("Maternal Health",               "sem_score_maternal_health"),
    "Redlining/Fair Housing":      ("Redlining & Fair Housing",      "sem_score_redlining"),
    "Anti-Black Surveillance":     ("Anti-Black Surveillance",       "sem_score_surveillance"),
    "Reparations":                 ("Reparations",                   "sem_score_reparations"),
    "School Funding":              ("School Funding",                "sem_score_school_funding"),
    "Criminal Justice\nReform":    ("Criminal Justice Reform",       "sem_score_criminal_justice"),
    "Environmental Justice":       ("Environmental Justice",         "sem_score_environmental_justice"),
    "Economic Equity/Wealth\nGap": ("Economic Equity & Wealth Gap",  "sem_score_economic_equity"),
}
LABEL_COLS = list(TOPIC_MAP.keys())


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
                precision=p, recall=r, f1=f1, kappa=k,
                human_pos=tp + fn, pred_pos=tp + fp)


def load_annotator_matched(ann_path: str, pipe: pd.DataFrame) -> pd.DataFrame:
    """Load one annotator's labels and attach the matching pipeline row
    (description, body, sem_scores, pipeline topics) by ID then title."""
    df = pd.read_excel(ann_path, sheet_name="Annotation").iloc[1:].copy()
    df["ID"] = df["ID"].astype(int)
    for col in LABEL_COLS:
        df[col] = df[col].apply(lambda v: 1 if isinstance(v, str) and "✓" in v else 0)

    by_id    = pipe.set_index("article_id")
    by_title = pipe.set_index("title")

    rows = []
    for _, r in df.iterrows():
        aid   = r["ID"]
        title = str(r["Title"]).strip()
        if aid in by_id.index and str(by_id.at[aid, "title"]).strip() == title:
            pr = by_id.loc[aid]
        elif title in by_title.index:
            pr = by_title.loc[title]
            if isinstance(pr, pd.DataFrame):
                pr = pr.iloc[0]
        else:
            continue
        row = {"title": title,
               "text": f"{title}. {str(pr.get('description','') or '')}. "
                       f"{str(pr.get('body','') or '')[:3000]}",
               "pipeline_topics": str(pr.get("pipeline_topics", "") or "")}
        for col, (pipe_topic, score_col) in TOPIC_MAP.items():
            row[f"human_{col}"] = r[col]
            row[f"kw_{col}"]    = 1 if pipe_topic in row["pipeline_topics"] else 0
            row[f"sem_{col}"]   = float(pr.get(score_col, 0.0) or 0.0)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    print("[supervised] Loading data...")
    pipe = pd.read_csv(PIPELINE_CSV)
    sets = {ann: load_annotator_matched(path, pipe)
            for ann, path in ANNOTATOR_FILES.items()}
    for ann, df in sets.items():
        print(f"  {ann}: {len(df)} articles matched")

    print("[supervised] Encoding articles (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = {ann: model.encode(df["text"].tolist(), batch_size=32,
                             show_progress_bar=False)
           for ann, df in sets.items()}

    report = ["SUPERVISED CLASSIFIER (LOGISTIC REGRESSION) vs HUMAN ANNOTATION",
              "",
              "Protocol: cross-annotator validation — train on one annotator's 200",
              "articles, test on the other's. Identical to Hybrid Soft Boost (CV).",
              "Features: sentence embedding + keyword binary + semantic score.",
              ""]
    out_rows = []
    directions = [("annotator_1", "annotator_3"), ("annotator_3", "annotator_1")]

    for train_ann, test_ann in directions:
        tr, te   = sets[train_ann], sets[test_ann]
        Xtr_emb  = emb[train_ann]
        Xte_emb  = emb[test_ann]

        header = (f"[test on {test_ann}] trained on {train_ann} "
                  f"({len(tr)} train / {len(te)} test articles)")
        report.append(header)
        report.append("=" * 100)
        hdr = (f"{'Topic':<32} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Kappa':>7} "
               f"  TP  FP  FN  TN  H+  P+  note")
        report.append(hdr)
        report.append("-" * 100)

        macro = {"precision": [], "recall": [], "f1": [], "kappa": []}
        for col in LABEL_COLS:
            label   = col.replace("\n", " ")
            y_train = tr[f"human_{col}"].values.astype(int)
            y_test  = te[f"human_{col}"].values.astype(int)

            Xtr = np.hstack([Xtr_emb,
                             tr[[f"kw_{col}", f"sem_{col}"]].values])
            Xte = np.hstack([Xte_emb,
                             te[[f"kw_{col}", f"sem_{col}"]].values])

            note = ""
            if y_train.sum() < 2:
                y_pred = te[f"kw_{col}"].values.astype(int)
                note = "fallback: keyword (too few train positives)"
            else:
                clf = LogisticRegression(class_weight="balanced",
                                         max_iter=2000, C=1.0)
                clf.fit(Xtr, y_train)
                y_pred = clf.predict(Xte)

            m = compute_metrics(y_test, y_pred)
            for k in macro:
                macro[k].append(m[k])
            report.append(
                f"{label:<32} {m['precision']:>6.3f} {m['recall']:>6.3f} "
                f"{m['f1']:>6.3f} {m['kappa']:>7.3f} "
                f"{m['tp']:>4} {m['fp']:>3} {m['fn']:>3} {m['tn']:>3} "
                f"{m['human_pos']:>3} {m['pred_pos']:>3}  {note}")
            out_rows.append({
                "annotator": test_ann, "method": "Supervised (CV)",
                "topic": label,
                "f1": round(m["f1"], 4), "kappa": round(m["kappa"], 4),
                "precision": round(m["precision"], 4),
                "recall": round(m["recall"], 4),
                "tp": m["tp"], "fp": m["fp"], "fn": m["fn"], "tn": m["tn"],
            })

        report.append("-" * 100)
        report.append(
            f"{'MACRO AVG':<32} {np.mean(macro['precision']):>6.3f} "
            f"{np.mean(macro['recall']):>6.3f} {np.mean(macro['f1']):>6.3f} "
            f"{np.mean(macro['kappa']):>7.3f}")
        report.append("")

    # Pooled summary + comparison against earlier methods
    res = pd.DataFrame(out_rows)
    report.append("=" * 60)
    report.append("POOLED SUMMARY (both test sets)")
    report.append(f"  Supervised (CV):   Macro F1 {res['f1'].mean():.4f}   "
                  f"Macro Kappa {res['kappa'].mean():.4f}")
    hybrid = pd.read_csv("evaluation/results/hybrid_vs_human.csv")
    for method in ["Keyword Pipeline", "Semantic Tagger",
                   "Hybrid Soft Boost (CV)"]:
        sub = hybrid[hybrid["method"] == method]
        report.append(f"  {method + ':':<19}Macro F1 {sub['f1'].mean():.4f}   "
                      f"Macro Kappa {sub['kappa'].mean():.4f}")
    report.append("=" * 60)

    text = "\n".join(report)
    with open(OUT_TXT, "w") as f:
        f.write(text)
    res.to_csv(OUT_CSV, index=False)
    print(text)
    print(f"\nSaved: {OUT_TXT}")
    print(f"Saved: {OUT_CSV}")


if __name__ == "__main__":
    main()
