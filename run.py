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
import calendar
from datetime import datetime


def _days_in_current_month() -> int:
    """Return the number of days in the current calendar month (28–31)."""
    today = datetime.now()
    return calendar.monthrange(today.year, today.month)[1]


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
        "--days", type=int, default=_days_in_current_month(),
        help="Rolling window in days (default: days in current month)"
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


def _make_output_dir(run_date: str) -> str:
    """
    Create outputs/<run_date>/ (e.g. outputs/2026-03-27/).
    If the directory already exists (re-run on same day), append -2, -3, etc.
    """
    base = os.path.join("outputs", run_date)
    candidate = base
    n = 2
    while os.path.exists(candidate) and os.listdir(candidate):
        candidate = f"{base}-{n}"
        n += 1
    os.makedirs(candidate, exist_ok=True)
    return candidate


def _update_latest_symlink(output_dir: str) -> None:
    """Point outputs/latest → the current run's dated directory (Unix only)."""
    latest = os.path.join("outputs", "latest")
    target = os.path.relpath(output_dir, "outputs")  # e.g. "2026-03-27"
    try:
        if os.path.islink(latest) or os.path.exists(latest):
            os.remove(latest)
        os.symlink(target, latest)
        print(f"  outputs/latest → {target}")
    except OSError:
        pass  # Windows or permission issue — skip silently


def run_pipeline():
    args = parse_args()
    start_time = time.time()
    run_date = datetime.now().strftime("%Y-%m-%d")

    banner("Black Media Intelligence Pipeline")
    print(f"  Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Run date: {run_date}")
    print(f"  Window:   {args.days} days")
    print(f"  Scrape:   {'Skipped' if args.skip_scrape else 'Yes'}")
    print(f"  Upload:   {'Skipped' if args.skip_upload else 'Yes'}")

    os.makedirs("outputs", exist_ok=True)
    output_dir = _make_output_dir(run_date)
    _update_latest_symlink(output_dir)
    print(f"  Output:   {output_dir}\n")

    results = {}

    # ── Stage 1: Scrape ───────────────────────────────────────────────
    if not args.skip_scrape:
        banner("Stage 1 · Scraping Articles")
        try:
            from scraper.scrape import run_scraper
            df = run_scraper(days=args.days, output_dir=output_dir)
            results["articles"] = len(df)
            print(f"\n✓ Stage 1 complete — {len(df)} articles scraped")
        except Exception as e:
            print(f"\n✗ Stage 1 FAILED: {e}")
            sys.exit(1)
    else:
        print(f"\n[Stage 1 skipped — using existing articles.csv in {output_dir}]")

    # ── Stage 2: Analyze ──────────────────────────────────────────────
    banner("Stage 2 · Analysis + Visualizations")
    try:
        from analysis.analyze import run_analysis
        analysis_results = run_analysis(output_dir=output_dir)
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
        pdf_path = run_report(output_dir=output_dir)
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
            run_upload(output_dir=output_dir, run_date=run_date)
            print(f"\n✓ Stage 4 complete — Files uploaded to Drive/{run_date}/")
        except Exception as e:
            print(f"\n✗ Stage 4 FAILED: {e}")
    else:
        print("\n[Stage 4 skipped — Drive upload disabled]")

    # ── Summary ───────────────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 1)
    banner("Pipeline Complete")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Duration: {elapsed}s")
    print(f"\n  Outputs in {output_dir}/:")
    for fname in [
        "articles.csv",
        "thegrio_com.csv", "theroot_com.csv", "newsone_com.csv",
        "capitalbnews_org.csv", "ebony_com.csv", "essence_com.csv",
        "blavity_com.csv", "21ninety_com.csv", "travelnoire_com.csv", "afrotech_com.csv",
        "editorial_report.html",
        "editorial_report.pdf",
    ]:
        f = os.path.join(output_dir, fname)
        exists = "✓" if os.path.exists(f) else "✗"
        print(f"    {exists}  {f}")
    print()


if __name__ == "__main__":
    run_pipeline()
