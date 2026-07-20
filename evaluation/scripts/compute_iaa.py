"""
compute_iaa.py — Inter-Annotator Agreement

Compares the expert relabeling (Adeniyi) against each original annotator on the
same articles:

  Set 1: Adeniyi vs Annotator 1  (200 articles)
  Set 3: Adeniyi vs Annotator 3  (200 articles)

Reports per-topic Cohen's Kappa, percent agreement, and disagreement counts,
plus macro and pooled Kappa per set. These figures establish the human
agreement ceiling used to contextualize the automated tagger scores.

Usage:
    python3.11 evaluation/scripts/compute_iaa.py

Outputs:
    evaluation/results/iaa_report.txt
    evaluation/results/iaa_results.csv
"""

import pandas as pd
import numpy as np

PAIRS = [
    ("set1", "annotator_1",
     "evaluation/annotation/annotated/annotator_1.xlsx",
     "evaluation/annotation/iaa/adeniyi_set1_LABELED.xlsx"),
    ("set3", "annotator_3",
     "evaluation/annotation/annotated/annotator_3.xlsx",
     "evaluation/annotation/iaa/adeniyi_set3_LABELED.xlsx"),
]

LABEL_COLS = [
    "Policing/Public Safety",
    "Voter Suppression",
    "Book Bans/Anti-DEI",
    "Housing/Displacement",
    "Maternal Health",
    "Redlining/Fair Housing",
    "Anti-Black Surveillance",
    "Reparations",
    "School Funding",
    "Criminal Justice\nReform",
    "Environmental Justice",
    "Economic Equity/Wealth\nGap",
]


def load_labels(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Annotation").iloc[1:].copy()
    df["ID"] = df["ID"].astype(int)
    for col in LABEL_COLS:
        df[col] = df[col].apply(lambda v: 1 if isinstance(v, str) and "✓" in v else 0)
    return df.set_index("ID").sort_index()


def kappa(y1: np.ndarray, y2: np.ndarray) -> float:
    n11 = int(((y1 == 1) & (y2 == 1)).sum())
    n10 = int(((y1 == 1) & (y2 == 0)).sum())
    n01 = int(((y1 == 0) & (y2 == 1)).sum())
    n00 = int(((y1 == 0) & (y2 == 0)).sum())
    n   = n11 + n10 + n01 + n00
    if n == 0:
        return 0.0
    p_o = (n11 + n00) / n
    p_e = ((n11 + n10) * (n11 + n01) + (n00 + n01) * (n00 + n10)) / (n * n)
    return (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0


def main():
    lines = ["INTER-ANNOTATOR AGREEMENT — EXPERT RELABEL vs ORIGINAL ANNOTATORS", ""]
    rows_out = []

    for set_name, orig_name, orig_path, expert_path in PAIRS:
        orig   = load_labels(orig_path)
        expert = load_labels(expert_path)

        # Sanity: same articles in the same order
        common = orig.index.intersection(expert.index)
        title_match = (orig.loc[common, "Title"].astype(str).str.strip().values ==
                       expert.loc[common, "Title"].astype(str).str.strip().values).all()

        header = (f"[{set_name}] Adeniyi vs {orig_name} — {len(common)} articles"
                  f"  (titles aligned: {'yes' if title_match else 'NO — CHECK ALIGNMENT'})")
        lines.append(header)
        lines.append("=" * 96)
        hdr = (f"{'Topic':<32} {'Kappa':>7} {'Agree%':>7} "
               f"{'Both+':>6} {'OnlyOrig':>9} {'OnlyAde':>8} {'Both-':>6}")
        lines.append(hdr)
        lines.append("-" * 96)

        kappas = []
        y1_all, y2_all = [], []
        for col in LABEL_COLS:
            label = col.replace("\n", " ")
            y1 = orig.loc[common, col].values      # original annotator
            y2 = expert.loc[common, col].values    # Adeniyi
            k  = kappa(y1, y2)
            agree = float((y1 == y2).mean())
            n11 = int(((y1 == 1) & (y2 == 1)).sum())
            n10 = int(((y1 == 1) & (y2 == 0)).sum())
            n01 = int(((y1 == 0) & (y2 == 1)).sum())
            n00 = int(((y1 == 0) & (y2 == 0)).sum())
            kappas.append(k)
            y1_all.append(y1)
            y2_all.append(y2)
            lines.append(f"{label:<32} {k:>7.3f} {agree*100:>6.1f}% "
                         f"{n11:>6} {n10:>9} {n01:>8} {n00:>6}")
            rows_out.append({
                "set": set_name, "original_annotator": orig_name,
                "topic": label, "kappa": round(k, 4),
                "percent_agreement": round(agree, 4),
                "both_positive": n11, "only_original": n10,
                "only_adeniyi": n01, "both_negative": n00,
            })

        pooled = kappa(np.concatenate(y1_all), np.concatenate(y2_all))
        lines.append("-" * 96)
        lines.append(f"{'MACRO AVG KAPPA':<32} {np.mean(kappas):>7.3f}")
        lines.append(f"{'POOLED KAPPA (all decisions)':<32} {pooled:>7.3f}")
        lines.append("")
        rows_out.append({
            "set": set_name, "original_annotator": orig_name,
            "topic": "MACRO AVG", "kappa": round(float(np.mean(kappas)), 4),
            "percent_agreement": None, "both_positive": None,
            "only_original": None, "only_adeniyi": None, "both_negative": None,
        })
        rows_out.append({
            "set": set_name, "original_annotator": orig_name,
            "topic": "POOLED", "kappa": round(pooled, 4),
            "percent_agreement": None, "both_positive": None,
            "only_original": None, "only_adeniyi": None, "both_negative": None,
        })

    report = "\n".join(lines)
    with open("evaluation/results/iaa_report.txt", "w") as f:
        f.write(report)
    pd.DataFrame(rows_out).to_csv("evaluation/results/iaa_results.csv", index=False)

    print(report)
    print("Saved: evaluation/results/iaa_report.txt")
    print("Saved: evaluation/results/iaa_results.csv")


if __name__ == "__main__":
    main()
