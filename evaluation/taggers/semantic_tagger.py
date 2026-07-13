"""
annotation/semantic_tagger.py — Semantic Topic Tagging via Sentence Embeddings

Instead of keyword/phrase matching, this uses a pre-trained sentence embedding
model (all-MiniLM-L6-v2) to measure the semantic similarity between each article
and each of the 12 topic descriptions.

How it works:
  1. Each topic is represented as a rich text document (name + description + key themes)
  2. Each article is represented as title + description + body text
  3. Both are converted to embedding vectors by the model
  4. Cosine similarity is computed between every article and every topic
  5. If similarity >= threshold, the article is tagged with that topic

This catches articles that MEAN the same thing as a topic even without exact keywords.

Usage:
    python3.11 annotation/semantic_tagger.py
    python3.11 annotation/semantic_tagger.py --threshold 0.35 --model all-MiniLM-L6-v2
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.topics import TOPICS

TOPIC_IDS  = [t["id"]   for t in TOPICS]
CHECK      = "✓"
SAMPLE_PATH = "evaluation/annotation/annotation_sample_1000.csv"


# ── Build rich topic descriptions for embedding ───────────────────────────────

def _build_topic_text(topic: dict) -> str:
    """
    Combine topic name, description, and sample seed phrases into a single
    rich document. The richer the topic text, the better the embeddings.
    """
    name  = topic["name"]
    desc  = topic["description"]
    # Use first 15 seed phrases as representative examples
    seeds = ", ".join(topic["seed_phrases"][:15])
    return f"{name}. {desc}. Key themes and examples: {seeds}."


def _build_article_text(row: pd.Series, max_body_chars: int = 3000) -> str:
    """
    Combine title + description + body for the article.
    Cap body length to keep embeddings efficient.
    """
    title = str(row.get("title",       "") or "")
    desc  = str(row.get("description", "") or "")
    body  = str(row.get("body",        "") or "")[:max_body_chars]
    return f"{title}. {desc}. {body}".strip()


# ── Main tagging function ─────────────────────────────────────────────────────

def run_semantic_tagging(
    input_path:  str   = SAMPLE_PATH,
    output_path: str   = SAMPLE_PATH,
    model_name:  str   = "all-MiniLM-L6-v2",
    threshold:   float = 0.35,
):
    print(f"\n[semantic] Loading {input_path} ...")
    df = pd.read_csv(input_path)
    print(f"[semantic] {len(df)} articles loaded")

    # ── Load model ────────────────────────────────────────────────────
    print(f"\n[semantic] Loading sentence transformer model: {model_name}")
    print(f"           (downloads ~80MB on first run)")
    model = SentenceTransformer(model_name)
    print(f"[semantic] Model loaded")

    # ── Encode topics ─────────────────────────────────────────────────
    print(f"\n[semantic] Encoding {len(TOPICS)} topic descriptions ...")
    topic_texts      = [_build_topic_text(t) for t in TOPICS]
    topic_embeddings = model.encode(topic_texts, show_progress_bar=False)
    print(f"[semantic] Topics encoded — shape: {topic_embeddings.shape}")

    # ── Encode articles ───────────────────────────────────────────────
    print(f"\n[semantic] Encoding {len(df)} articles (this takes ~2-5 min on CPU) ...")
    article_texts      = [_build_article_text(row) for _, row in df.iterrows()]
    article_embeddings = model.encode(
        article_texts,
        show_progress_bar=True,
        batch_size=32,
    )
    print(f"[semantic] Articles encoded — shape: {article_embeddings.shape}")

    # ── Compute cosine similarity ─────────────────────────────────────
    print(f"\n[semantic] Computing similarities (threshold = {threshold}) ...")
    # Shape: (n_articles, n_topics)
    sim_matrix = cosine_similarity(article_embeddings, topic_embeddings)

    # ── Save similarity scores as new columns ─────────────────────────
    for i, tid in enumerate(TOPIC_IDS):
        df[f"sem_score_{tid}"] = np.round(sim_matrix[:, i], 4)

    # ── Tag articles ──────────────────────────────────────────────────
    tagged_count = 0
    for i, tid in enumerate(TOPIC_IDS):
        col   = f"label_{tid}"
        score = sim_matrix[:, i]
        df[col] = [CHECK if s >= threshold else "" for s in score]

    tagged_count = df[[f"label_{tid}" for tid in TOPIC_IDS]].eq(CHECK).any(axis=1).sum()

    # ── Save ──────────────────────────────────────────────────────────
    df.to_csv(output_path, index=False)

    print(f"\n[semantic] ✓ Saved → {output_path}")
    print(f"\n  Articles tagged (≥{threshold} similarity): {tagged_count} / {len(df)} "
          f"({tagged_count/len(df)*100:.1f}%)")

    print(f"\n  Per-topic results:")
    print(f"  {'Topic':<35} {'Tagged':>8}  {'Avg score':>10}  {'Max score':>10}")
    print(f"  {'─'*35} {'─'*8}  {'─'*10}  {'─'*10}")
    for i, topic in enumerate(TOPICS):
        tid    = topic["id"]
        scores = sim_matrix[:, i]
        tagged = (scores >= threshold).sum()
        print(f"  {topic['name']:<35} {tagged:>8}  {scores.mean():>10.3f}  {scores.max():>10.3f}")

    print(f"\n  Next step: python3.11 annotation/create_excel_sheet.py")
    return df


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic topic tagging via sentence embeddings")
    parser.add_argument("--input",     default=SAMPLE_PATH)
    parser.add_argument("--output",    default=SAMPLE_PATH)
    parser.add_argument("--model",     default="all-MiniLM-L6-v2")
    parser.add_argument("--threshold", type=float, default=0.35,
                        help="Cosine similarity threshold (0–1). Higher = stricter. Default: 0.35")
    args = parser.parse_args()

    run_semantic_tagging(
        input_path=args.input,
        output_path=args.output,
        model_name=args.model,
        threshold=args.threshold,
    )
