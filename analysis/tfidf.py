"""
tfidf.py — TF-IDF Keyword Extraction

Extracts top trending keywords from the scraped article corpus
using scikit-learn's TF-IDF vectorizer. Returns keywords ranked
by their aggregate TF-IDF score across all documents.
"""

import json
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import nltk
from nltk.corpus import stopwords

# Download stopwords if needed
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

STOP_WORDS = set(stopwords.words("english"))

# Additional domain-specific stopwords
EXTRA_STOPS = {
    "said", "says", "also", "one", "two", "three", "new", "year",
    "years", "time", "people", "community", "black", "white", "american",
    "states", "united", "national", "news", "report", "week", "month",
    "day", "first", "last", "make", "made", "like", "would", "could",
    "many", "more", "most", "get", "got", "may", "just", "back",
    "according", "told", "added", "noted", "however", "despite",
    "including", "amid", "across", "within", "among", "per",
}

ALL_STOPS = STOP_WORDS | EXTRA_STOPS


def extract_tfidf_keywords(df: pd.DataFrame, top_n: int = 50) -> dict:
    """
    Run TF-IDF over the article corpus and return top keywords
    globally and per publication.

    Args:
        df: DataFrame with at least 'title', 'description', 'source' columns
        top_n: number of top keywords to return

    Returns:
        dict with keys:
            - 'global': list of {keyword, score} dicts
            - 'by_source': dict of source -> list of {keyword, score}
    """
    if df.empty:
        return {"global": [], "by_source": {}}

    # Combine title + description into a single text field
    df = df.copy()
    df["text"] = (
        df["title"].fillna("") + " " + df["description"].fillna("")
    ).str.lower()

    results = {}

    # --- Global TF-IDF ---
    results["global"] = _run_tfidf(df["text"].tolist(), top_n)

    # --- Per-source TF-IDF ---
    results["by_source"] = {}
    for source, group in df.groupby("source"):
        if len(group) < 3:
            continue
        results["by_source"][source] = _run_tfidf(group["text"].tolist(), top_n=20)

    return results


def _run_tfidf(texts: list, top_n: int = 50) -> list:
    """
    Internal: run TF-IDF on a list of text strings and return top keywords.
    """
    if not texts:
        return []

    vectorizer = TfidfVectorizer(
        stop_words=list(ALL_STOPS),
        ngram_range=(1, 3),      # unigrams, bigrams, trigrams
        min_df=2,                 # must appear in at least 2 docs
        max_df=0.85,              # ignore terms in >85% of docs
        max_features=5000,
        sublinear_tf=True,        # log normalization
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    # Sum TF-IDF scores across all documents
    scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()

    # Sort descending
    top_indices = scores.argsort()[::-1][:top_n]

    return [
        {"keyword": feature_names[i], "score": round(float(scores[i]), 4)}
        for i in top_indices
    ]


def save_tfidf(results: dict, path: str = "outputs/tfidf_keywords.json") -> None:
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[tfidf] Saved TF-IDF results → {path}")
