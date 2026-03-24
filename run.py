"""
run.py — Master Pipeline Orchestrator

Runs the full pipeline in sequence:
  Stage 1: Scrape articles from 7 Black media publications
  Stage 2: Analyze — TF-IDF + topic matching + visualizations
  Stage 3: Generate PDF report
  Stage 4: Upload to Google Drive

Each stage is independently re-runnable by calling its module directly.
"""

import os
import sys
import time
import argparse
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(
        description="Black Media Intelligence Pipeline"
    )
    parser.add_argument(
        "--skip-scrape", action="store_true",
        help="Skip scraping (use existing articles.csv)"
    )
    parser.add_argument(
        "--skip-upload", action="store_true",
        help="Skip Google Drive upload"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Rolling window in days (default: 30)"
    )
    parser.add_argument(
        "--html-only", action="store_true",
        help="Generate HTML report only (skip PDF conversion)"
    )
    return parser.parse_args()


def banner(text: str) -> None:
    width = 60
    print("\n" + "═" * width)
    print(f"  {text}")
    print("═" * width)


def run_pipeline():
    args = parse_args()
    start_time = time.time()

    banner("Black Media Intelligence Pipeline")
    print(f"  Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Window:   {args.days} days")
    print(f"  Scrape:   {'Skipped' if args.skip_scrape else 'Yes'}")
    print(f"  Upload:   {'Skipped' if args.skip_upload else 'Yes'}")

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("outputs/charts", exist_ok=True)

    results = {}

    # ── Stage 1: Scrape ───────────────────────────────────────────────
    if not args.skip_scrape:
        banner("Stage 1 · Scraping Articles")
        try:
            from scraper.scrape import run_scraper
            df = run_scraper(days=args.days)
            results["articles"] = len(df)
            print(f"\n✓ Stage 1 complete — {len(df)} articles scraped")
        except Exception as e:
            print(f"\n✗ Stage 1 FAILED: {e}")
            sys.exit(1)
    else:
        print("\n[Stage 1 skipped — using existing articles.csv]")

    # ── Stage 2: Analyze ──────────────────────────────────────────────
    banner("Stage 2 · Analysis + Visualizations")
    try:
        from analysis.analyze import run_analysis
        analysis_results = run_analysis()
        topic_counts = analysis_results.get("topic_summary", {}).get("topic_counts", {})
        print(f"\n✓ Stage 2 complete — {len(topic_counts)} topics detected")
    except Exception as e:
        print(f"\n✗ Stage 2 FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Stage 3: Report ───────────────────────────────────────────────
    banner("Stage 3 · Generating Report")
    try:
        from report.generate_report import run_report
        pdf_path = run_report()
        print(f"\n✓ Stage 3 complete — Report: {pdf_path}")
    except Exception as e:
        print(f"\n✗ Stage 3 FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Stage 4: Upload ───────────────────────────────────────────────
    if not args.skip_upload:
        banner("Stage 4 · Uploading to Google Drive")
        try:
            from delivery.upload_drive import run_upload
            run_upload()
            print(f"\n✓ Stage 4 complete — Files uploaded")
        except Exception as e:
            print(f"\n✗ Stage 4 FAILED: {e}")
    else:
        print("\n[Stage 4 skipped — Drive upload disabled]")

    # ── Summary ───────────────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 1)
    banner("Pipeline Complete")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration: {elapsed}s")
    print(f"\n  Outputs:")
    for f in [
        "outputs/articles.csv",
        "outputs/thegrio_com.csv",
        "outputs/theroot_com.csv",
        "outputs/newsone_com.csv",
        "outputs/capitalbnews_org.csv",
        "outputs/ebony_com.csv",
        "outputs/essence_com.csv",
        "outputs/blavity_com.csv",
        "outputs/editorial_report.html",
        "outputs/editorial_report.pdf",
    ]:
        exists = "✓" if os.path.exists(f) else "✗"
        print(f"    {exists}  {f}")
    print()


if __name__ == "__main__":
    run_pipeline()
