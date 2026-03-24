"""
topic_matcher.py — Seed-Phrase Topic Matching

Matches each article against the 12 social conflict topic dictionaries.
An article can match multiple topics. Returns enriched article data
with topic labels, match scores, and matched phrases for transparency.
"""

import re
import json
import pandas as pd
from collections import defaultdict
from analysis.topics import TOPICS


def match_topics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each article with matching social conflict topics.

    Args:
        df: DataFrame with 'title', 'description' columns

    Returns:
        DataFrame with added columns:
            - topics: comma-separated matched topic names
            - topic_ids: comma-separated matched topic ids
            - matched_phrases: JSON list of matched phrases per topic
            - topic_count: number of topics matched
            - match_score: aggregate confidence score (0–1)
    """
    if df.empty:
        return df

    df = df.copy()
    df["topics"] = ""
    df["topic_ids"] = ""
    df["matched_phrases"] = ""
    df["topic_count"] = 0
    df["match_score"] = 0.0

    for idx, row in df.iterrows():
        text = _build_text(row)
        matched_topics = []
        matched_ids = []
        phrase_map = {}

        for topic in TOPICS:
            hits, score = _score_topic(text, topic["seed_phrases"])
            if hits:
                matched_topics.append(topic["name"])
                matched_ids.append(topic["id"])
                phrase_map[topic["name"]] = hits

        df.at[idx, "topics"] = "; ".join(matched_topics)
        df.at[idx, "topic_ids"] = "; ".join(matched_ids)
        df.at[idx, "matched_phrases"] = json.dumps(phrase_map)
        df.at[idx, "topic_count"] = len(matched_topics)
        df.at[idx, "match_score"] = round(
            min(len(matched_topics) / 3, 1.0), 3  # normalized 0–1
        )

    return df


def _build_text(row: pd.Series) -> str:
    """Combine title + description into a single lowercase string."""
    title = str(row.get("title", "") or "")
    desc = str(row.get("description", "") or "")
    category = str(row.get("category", "") or "")
    return (title + " " + desc + " " + category).lower()


def _score_topic(text: str, seed_phrases: list) -> tuple[list, float]:
    """
    Score how strongly a text matches a topic's seed phrases.

    Single-word phrases use flexible suffix matching (officers → officer).
    Multi-word phrases use strict whole-phrase matching.

    Returns:
        (matched_phrases, score) where score = matched / total seeds
    """
    hits = []
    for phrase in seed_phrases:
        phrase_lower = phrase.lower()
        words = phrase_lower.split()
        if len(words) == 1:
            # Single word: match with optional common suffixes (s, ed, ing, er)
            pattern = r"\b" + re.escape(phrase_lower) + r"(s|ed|ing|er|ment|ion)?\b"
        else:
            # Multi-word: allow up to 1 word gap between words for flexibility
            pattern = r"\b" + r"\b.{0,15}\b".join(re.escape(w) for w in words) + r"\b"
        if re.search(pattern, text):
            hits.append(phrase)
    score = round(len(hits) / len(seed_phrases), 4) if seed_phrases else 0.0
    return hits, score


def build_topic_summary(df: pd.DataFrame) -> dict:
    """
    Build a rich summary of topic coverage across the corpus.

    Returns:
        dict with:
            - topic_counts: {topic_name: article_count}
            - source_topic_matrix: {source: {topic: count}}
            - top_articles_per_topic: {topic: [{title, link, source, date}]}
            - topic_co_occurrence: {topic_pair: count}
            - coverage_rate: % of articles that matched at least one topic
    """
    summary = {
        "topic_counts": defaultdict(int),
        "source_topic_matrix": defaultdict(lambda: defaultdict(int)),
        "top_articles_per_topic": defaultdict(list),
        "topic_co_occurrence": defaultdict(int),
        "total_articles": len(df),
        "tagged_articles": 0,
        "coverage_rate": 0.0,
    }

    tagged = df[df["topics"].str.strip() != ""]
    summary["tagged_articles"] = len(tagged)
    summary["coverage_rate"] = round(
        len(tagged) / len(df) * 100, 1
    ) if len(df) > 0 else 0.0

    for _, row in tagged.iterrows():
        topics_list = [t.strip() for t in row["topics"].split(";") if t.strip()]
        source = row.get("source", "Unknown")

        for topic in topics_list:
            summary["topic_counts"][topic] += 1
            summary["source_topic_matrix"][source][topic] += 1
            summary["top_articles_per_topic"][topic].append({
                "title": row.get("title", ""),
                "link": row.get("link", ""),
                "source": source,
                "date": str(row.get("date_of_publication", "")),
                "matched_phrases": _get_phrases_for_topic(
                    row.get("matched_phrases", "{}"), topic
                ),
            })

        # Co-occurrence
        for i, t1 in enumerate(topics_list):
            for t2 in topics_list[i + 1:]:
                pair = tuple(sorted([t1, t2]))
                summary["topic_co_occurrence"][str(pair)] += 1

    # Convert defaultdicts to plain dicts for JSON serialization
    summary["topic_counts"] = dict(summary["topic_counts"])
    summary["source_topic_matrix"] = {
        k: dict(v) for k, v in summary["source_topic_matrix"].items()
    }
    summary["top_articles_per_topic"] = dict(summary["top_articles_per_topic"])
    summary["topic_co_occurrence"] = dict(summary["topic_co_occurrence"])

    return summary


def _get_phrases_for_topic(matched_phrases_json: str, topic_name: str) -> list:
    try:
        phrase_map = json.loads(matched_phrases_json)
        return phrase_map.get(topic_name, [])
    except (json.JSONDecodeError, TypeError):
        return []


def save_topic_summary(summary: dict, path: str = "outputs/topic_summary.json") -> None:
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[topic_matcher] Saved topic summary → {path}")
