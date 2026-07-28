"""
bootstrap_significance.py — Paired bootstrap CI for the Table 3 headline
comparison: Supervised (CV) vs. the best honest baseline, Hybrid Soft
Boost (CV).

Both methods are already scored by evaluation/taggers/supervised_tagger.py
and evaluation/taggers/hybrid_tagger.py, but only as point estimates
(one macro F1 / kappa number per direction). This script regenerates the
supervised classifier's per-article predictions (retrained identically,
same leak-free cross-annotator protocol, same features, same fallback
rule), pairs them article-for-article with the already-saved Hybrid Soft
Boost (CV) per-article predictions, and bootstraps the article set
(resampling with replacement, 200 articles per direction) to get a
confidence interval and an empirical p-value on the pooled macro F1 and
macro kappa gap between the two methods.

Usage (from repo root):
    python3.11 evaluation/scripts/bootstrap_significance.py

Outputs:
    evaluation/results/bootstrap_significance.txt
    evaluation/results/bootstrap_significance.csv
"""

import os
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "evaluation", "taggers"))

from sklearn.linear_model import LogisticRegression
from sentence_transformers import SentenceTransformer

from supervised_tagger import (
    ANNOTATOR_FILES, PIPELINE_CSV, TOPIC_MAP, LABEL_COLS,
    load_annotator_matched, compute_metrics,
)

HYBRID_PRED_CSV = "evaluation/results/hybrid_vs_human_predictions.csv"
OUT_TXT = "evaluation/results/bootstrap_significance.txt"
OUT_CSV = "evaluation/results/bootstrap_significance.csv"

N_BOOT = 5000
RNG = np.random.default_rng(20260727)

# LABEL_COLS (as used by supervised_tagger) -> column-name slug used in
# hybrid_vs_human_predictions.csv
SLUG = {
    "Policing/Public Safety":      "policing_public_safety",
    "Voter Suppression":           "voter_suppression",
    "Book Bans/Anti-DEI":          "book_bans_anti-dei",
    "Housing/Displacement":        "housing_displacement",
    "Maternal Health":             "maternal_health",
    "Redlining/Fair Housing":      "redlining_fair_housing",
    "Anti-Black Surveillance":     "anti-black_surveillance",
    "Reparations":                 "reparations",
    "School Funding":              "school_funding",
    "Criminal Justice\nReform":    "criminal_justice_reform",
    "Environmental Justice":       "environmental_justice",
    "Economic Equity/Wealth\nGap": "economic_equity_wealth_gap",
}


def macro_f1_kappa(y_true_mat, y_pred_mat, idx):
    """y_true_mat, y_pred_mat: (n_articles, n_topics) 0/1 arrays.
    idx: resampled article indices (with replacement).
    Returns (macro F1, macro kappa) over topics, on the resampled subset."""
    f1s, ks = [], []
    for j in range(y_true_mat.shape[1]):
        m = compute_metrics(y_true_mat[idx, j], y_pred_mat[idx, j])
        f1s.append(m["f1"])
        ks.append(m["kappa"])
    return float(np.mean(f1s)), float(np.mean(ks))


def main():
    print("[bootstrap] Loading annotator data + pipeline predictions...")
    pipe = pd.read_csv(PIPELINE_CSV)
    sets = {ann: load_annotator_matched(path, pipe)
            for ann, path in ANNOTATOR_FILES.items()}

    print("[bootstrap] Encoding articles (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = {ann: model.encode(df["text"].tolist(), batch_size=32,
                             show_progress_bar=False)
           for ann, df in sets.items()}

    hybrid_pred = pd.read_csv(HYBRID_PRED_CSV)

    directions = [("annotator_1", "annotator_3"), ("annotator_3", "annotator_1")]
    report = ["PAIRED BOOTSTRAP: Supervised (CV) vs Hybrid Soft Boost (CV)",
              "",
              f"{N_BOOT} resamples per direction, articles resampled with "
              "replacement (paired: both methods scored on the identical",
              "resampled article set each iteration). Positive values favor "
              "the supervised classifier.", ""]

    per_direction_boot_f1_sup, per_direction_boot_f1_hyb = [], []
    per_direction_boot_k_sup, per_direction_boot_k_hyb = [], []
    point = {}

    for train_ann, test_ann in directions:
        tr, te = sets[train_ann], sets[test_ann]
        Xtr_emb, Xte_emb = emb[train_ann], emb[test_ann]
        n_test = len(te)
        n_topics = len(LABEL_COLS)

        # ---- retrain supervised classifier, keep per-article predictions ----
        y_true_sup = np.zeros((n_test, n_topics), dtype=int)
        y_pred_sup = np.zeros((n_test, n_topics), dtype=int)
        for j, col in enumerate(LABEL_COLS):
            y_train = tr[f"human_{col}"].values.astype(int)
            y_test = te[f"human_{col}"].values.astype(int)
            Xtr = np.hstack([Xtr_emb, tr[[f"kw_{col}", f"sem_{col}"]].values])
            Xte = np.hstack([Xte_emb, te[[f"kw_{col}", f"sem_{col}"]].values])
            if y_train.sum() < 2:
                y_pred = te[f"kw_{col}"].values.astype(int)
            else:
                clf = LogisticRegression(class_weight="balanced",
                                         max_iter=2000, C=1.0)
                clf.fit(Xtr, y_train)
                y_pred = clf.predict(Xte)
            y_true_sup[:, j] = y_test
            y_pred_sup[:, j] = y_pred

        # ---- pull matching Hybrid Soft Boost (CV) per-article predictions ----
        hy = hybrid_pred[hybrid_pred["annotator"] == test_ann].copy()
        hy = hy.set_index("title")
        y_true_hyb = np.zeros((n_test, n_topics), dtype=int)
        y_pred_hyb = np.zeros((n_test, n_topics), dtype=int)
        missing = 0
        for i, row in enumerate(te.itertuples()):
            title = row.title
            if title not in hy.index:
                missing += 1
                continue
            hrow = hy.loc[title]
            if isinstance(hrow, pd.DataFrame):
                hrow = hrow.iloc[0]
            for j, col in enumerate(LABEL_COLS):
                slug = SLUG[col]
                y_true_hyb[i, j] = int(hrow[f"human_{slug}"])
                y_pred_hyb[i, j] = int(hrow[f"hybrid_soft_cv_{slug}"])
        if missing:
            report.append(f"[warning] {missing}/{n_test} articles in "
                          f"{test_ann} had no title match in "
                          f"{HYBRID_PRED_CSV}; left as zero rows.")

        # sanity check: the two methods' ground truth must agree
        assert np.array_equal(y_true_sup, y_true_hyb), (
            f"Ground-truth label mismatch between supervised and hybrid "
            f"predictions for {test_ann} — article alignment is wrong.")

        f1_sup_pt, k_sup_pt = macro_f1_kappa(y_true_sup, y_pred_sup, np.arange(n_test))
        f1_hyb_pt, k_hyb_pt = macro_f1_kappa(y_true_hyb, y_pred_hyb, np.arange(n_test))
        point[test_ann] = dict(f1_sup=f1_sup_pt, f1_hyb=f1_hyb_pt,
                               k_sup=k_sup_pt, k_hyb=k_hyb_pt)

        report.append(f"[{test_ann}] point estimate: "
                      f"Supervised F1={f1_sup_pt:.4f} kappa={k_sup_pt:.4f}  |  "
                      f"Hybrid Soft Boost (CV) F1={f1_hyb_pt:.4f} kappa={k_hyb_pt:.4f}")

        boot_f1_sup = np.empty(N_BOOT)
        boot_f1_hyb = np.empty(N_BOOT)
        boot_k_sup = np.empty(N_BOOT)
        boot_k_hyb = np.empty(N_BOOT)
        for b in range(N_BOOT):
            idx = RNG.integers(0, n_test, size=n_test)
            f1s, ks = macro_f1_kappa(y_true_sup, y_pred_sup, idx)
            boot_f1_sup[b], boot_k_sup[b] = f1s, ks
            f1h, kh = macro_f1_kappa(y_true_hyb, y_pred_hyb, idx)
            boot_f1_hyb[b], boot_k_hyb[b] = f1h, kh

        per_direction_boot_f1_sup.append(boot_f1_sup)
        per_direction_boot_f1_hyb.append(boot_f1_hyb)
        per_direction_boot_k_sup.append(boot_k_sup)
        per_direction_boot_k_hyb.append(boot_k_hyb)

    # ---- pool: average the two directions' bootstrap draws per iteration ----
    # (matches how Table 3's "pooled" macro F1 is the average of the two
    # per-direction macro F1s)
    pooled_f1_sup = (per_direction_boot_f1_sup[0] + per_direction_boot_f1_sup[1]) / 2
    pooled_f1_hyb = (per_direction_boot_f1_hyb[0] + per_direction_boot_f1_hyb[1]) / 2
    pooled_k_sup = (per_direction_boot_k_sup[0] + per_direction_boot_k_sup[1]) / 2
    pooled_k_hyb = (per_direction_boot_k_hyb[0] + per_direction_boot_k_hyb[1]) / 2

    diff_f1 = pooled_f1_sup - pooled_f1_hyb
    diff_k = pooled_k_sup - pooled_k_hyb

    pt_f1_sup = (point["annotator_3"]["f1_sup"] + point["annotator_1"]["f1_sup"]) / 2
    pt_f1_hyb = (point["annotator_3"]["f1_hyb"] + point["annotator_1"]["f1_hyb"]) / 2
    pt_k_sup = (point["annotator_3"]["k_sup"] + point["annotator_1"]["k_sup"]) / 2
    pt_k_hyb = (point["annotator_3"]["k_hyb"] + point["annotator_1"]["k_hyb"]) / 2

    ci_f1 = np.percentile(diff_f1, [2.5, 97.5])
    ci_k = np.percentile(diff_k, [2.5, 97.5])
    p_f1 = float(np.mean(diff_f1 <= 0)) * 2  # two-sided empirical p-value
    p_f1 = min(p_f1, 1.0)
    p_k = float(np.mean(diff_k <= 0)) * 2
    p_k = min(p_k, 1.0)

    report += [
        "",
        "POOLED (average of both cross-annotator directions)",
        "=" * 60,
        f"Supervised (CV):          Macro F1 {pt_f1_sup:.4f}   Macro kappa {pt_k_sup:.4f}",
        f"Hybrid Soft Boost (CV):   Macro F1 {pt_f1_hyb:.4f}   Macro kappa {pt_k_hyb:.4f}",
        "",
        f"Macro F1 gap (Supervised - Hybrid Soft Boost CV): {pt_f1_sup - pt_f1_hyb:+.4f}",
        f"  95% bootstrap CI: [{ci_f1[0]:+.4f}, {ci_f1[1]:+.4f}]",
        f"  two-sided bootstrap p-value: {p_f1:.4f}",
        "",
        f"Macro kappa gap (Supervised - Hybrid Soft Boost CV): {pt_k_sup - pt_k_hyb:+.4f}",
        f"  95% bootstrap CI: [{ci_k[0]:+.4f}, {ci_k[1]:+.4f}]",
        f"  two-sided bootstrap p-value: {p_k:.4f}",
        "=" * 60,
    ]

    text = "\n".join(report)
    with open(OUT_TXT, "w") as f:
        f.write(text)
    pd.DataFrame({
        "bootstrap_iter": np.arange(N_BOOT),
        "pooled_f1_supervised": pooled_f1_sup,
        "pooled_f1_hybrid_soft_cv": pooled_f1_hyb,
        "pooled_f1_diff": diff_f1,
        "pooled_kappa_supervised": pooled_k_sup,
        "pooled_kappa_hybrid_soft_cv": pooled_k_hyb,
        "pooled_kappa_diff": diff_k,
    }).to_csv(OUT_CSV, index=False)

    print(text)
    print(f"\nSaved: {OUT_TXT}")
    print(f"Saved: {OUT_CSV}")


if __name__ == "__main__":
    main()
