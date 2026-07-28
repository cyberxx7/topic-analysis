"""
corpus_audit.py — Mainstream Corpus Presence Audit

Queries the Common Crawl CDX index for each of our 10 Black media publication
domains in CC-MAIN-2019-18 — the April 2019 snapshot that C4 (Raffel et al.,
2020) was derived from — plus mainstream comparator outlets.

A low capture count in the source crawl bounds the domain's possible presence
in C4 from above (C4's filtering — English-only, dedup, blocklists, length
heuristics — only removes further pages). This provides empirical evidence
for the paper's data-gap claim.

Usage:
    python3.11 evaluation/scripts/corpus_audit.py

Outputs:
    evaluation/results/corpus_audit.txt
    evaluation/results/corpus_audit.csv
"""

import csv
import json
import time
import urllib.parse
import urllib.request

C4_SOURCE_CRAWL = "CC-MAIN-2019-18"   # April 2019 snapshot → C4
CDX = "https://index.commoncrawl.org/{crawl}-index"

OUR_DOMAINS = [
    "thegrio.com", "theroot.com", "newsone.com", "capitalbnews.org",
    "ebony.com", "essence.com", "blavity.com", "afrotech.com",
    "travelnoire.com", "21ninety.com",
]
COMPARATORS = ["nytimes.com", "cnn.com"]

CAP = 200_000          # stop counting past this many captures
RETRIES = 4


def count_captures(crawl: str, domain: str) -> int | None:
    """Count CDX captures for a domain in one crawl (capped at CAP).
    Returns None if the index could not be queried."""
    params = urllib.parse.urlencode({
        "url": domain, "matchType": "domain",
        "output": "json", "limit": CAP, "fl": "urlkey",
    })
    url = f"{CDX.format(crawl=crawl)}?{params}"
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "corpus-audit-research/1.0 (academic paper audit)"
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                n = sum(1 for line in resp if line.strip())
            return n
        except urllib.error.HTTPError as e:
            if e.code == 404:          # no captures at all for this domain
                return 0
            time.sleep(8 * (attempt + 1))
        except Exception:
            time.sleep(8 * (attempt + 1))
    return None


def main():
    rows = []
    for group, domains in [("ours", OUR_DOMAINS), ("mainstream", COMPARATORS)]:
        for dom in domains:
            n = count_captures(C4_SOURCE_CRAWL, dom)
            shown = "ERROR" if n is None else (f">={CAP:,}" if n >= CAP else f"{n:,}")
            print(f"[{C4_SOURCE_CRAWL}] {dom:<20} ({group}): {shown}", flush=True)
            rows.append({"crawl": C4_SOURCE_CRAWL, "group": group,
                         "domain": dom, "captures": n})
            time.sleep(2)   # be polite to the index

    with open("evaluation/results/corpus_audit.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["crawl", "group", "domain", "captures"])
        w.writeheader()
        w.writerows(rows)

    lines = [
        "MAINSTREAM CORPUS PRESENCE AUDIT",
        "",
        f"Common Crawl {C4_SOURCE_CRAWL} (April 2019) — the snapshot C4 was built from.",
        "Capture count = pages of the domain present in the raw crawl. C4's filtering",
        "(English-only, dedup, blocklists, length heuristics) only removes pages, so",
        "these counts are an UPPER BOUND on each domain's possible C4 presence.",
        "",
        f"{'Domain':<22} {'Group':<12} {'Captures in source crawl':>26}",
        "-" * 62,
    ]
    for r in rows:
        n = r["captures"]
        shown = "ERROR" if n is None else (f">={CAP:,}" if n >= CAP else f"{n:,}")
        lines.append(f"{r['domain']:<22} {r['group']:<12} {shown:>26}")
    text = "\n".join(lines)
    with open("evaluation/results/corpus_audit.txt", "w") as f:
        f.write(text + "\n")
    print("\nSaved: evaluation/results/corpus_audit.txt")
    print("Saved: evaluation/results/corpus_audit.csv")


if __name__ == "__main__":
    main()
