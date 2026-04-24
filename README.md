# Black Media Intelligence Pipeline

An automated media intelligence pipeline that scrapes, analyzes, and reports on article coverage across ten prominent Black media publications. On the 1st of every month it collects all articles from the previous month, runs topic analysis using TF-IDF and seed-phrase matching across 12 social conflict topics, generates a styled PDF research report, and uploads everything to Google Drive — all without manual intervention.

---

## What It Does

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────┐
│  Stage 1    │    │   Stage 2    │    │   Stage 3     │    │   Stage 4    │
│  Scrape     │───▶│   Analyze    │───▶│   Report      │───▶│   Deliver    │
│  10 sources │    │  TF-IDF +    │    │  HTML + PDF   │    │  Google      │
│  ~1,500 art │    │  12 topics   │    │  with charts  │    │  Drive       │
└─────────────┘    └──────────────┘    └───────────────┘    └──────────────┘
```

**Publications covered:**

| Publication | Domain | Scrape Method |
|---|---|---|
| The Grio | thegrio.com | WordPress REST API |
| The Root | theroot.com | WordPress REST API |
| NewsOne | newsone.com | WordPress REST API |
| Ebony | ebony.com | WordPress REST API |
| Capital B News | capitalbnews.org | Sitemap + HTML |
| Essence | essence.com | Paginated HTML |
| Blavity | blavity.com | Synapse RSS Feed |
| 21Ninety | 21ninety.com | Synapse RSS Feed |
| Travel Noire | travelnoire.com | Synapse RSS Feed |
| AfroTech | afrotech.com | Synapse RSS Feed |

**Topics tracked (12):**

| # | Topic |
|---|---|
| 1 | Policing & Public Safety |
| 2 | Voter Suppression |
| 3 | Book Bans & Anti-DEI |
| 4 | Housing & Displacement |
| 5 | Maternal Health |
| 6 | Redlining & Fair Housing |
| 7 | Anti-Black Surveillance |
| 8 | Reparations |
| 9 | School Funding |
| 10 | Criminal Justice Reform |
| 11 | Environmental Justice |
| 12 | Economic Equity & Wealth Gap |

---

## Output Structure

Each pipeline run writes to a dated subfolder. Outputs are version-controlled in git and tagged:

```
outputs/
├── latest -> 2026-04-01/          ← symlink, always points to newest run
├── 2026-03-01/
│   ├── articles.csv               ← all sources combined
│   ├── thegrio_com.csv
│   ├── theroot_com.csv
│   ├── newsone_com.csv
│   ├── capitalbnews_org.csv
│   ├── ebony_com.csv
│   ├── essence_com.csv
│   ├── blavity_com.csv
│   ├── 21ninety_com.csv
│   ├── travelnoire_com.csv
│   ├── afrotech_com.csv
│   ├── articles_tagged.csv        ← with topic annotations
│   ├── editorial_report.html
│   └── editorial_report.pdf
├── 2026-04-01/
│   └── ...
```

Google Drive mirrors this structure — each run uploads into a `YYYY-MM-DD/` subfolder inside your configured Drive folder.

Git tags mark each run: `run-2026-03-01`, `run-2026-04-01`, etc.

---

## Data Schema

### `articles.csv`

| Field | Type | Description |
|---|---|---|
| title | string | Article headline |
| description | string | Excerpt or meta description (up to 500 chars) |
| source | string | Publication domain (e.g. `thegrio.com`) |
| date_of_publication | date | `YYYY-MM-DD` |
| category | string | Publication-assigned category |
| author | string | Byline |
| link | string | Full canonical URL |

### `articles_tagged.csv`

Same as above, plus:

| Field | Type | Description |
|---|---|---|
| topics | string | Matched social conflict topic(s), pipe-separated, or empty |

---

## Project Structure

```
topic-analysis/
│
├── run.py                        ← Master orchestrator (runs all 4 stages)
│
├── scraper/
│   ├── scrape.py                 ← Scraper dispatcher + deduplication
│   ├── wp_scraper.py             ← WordPress REST API scraper
│   ├── synapse_scraper.py        ← Blavity Inc. Synapse RSS feed (4 publications)
│   ├── capitalb_scraper.py       ← Sitemap + category scraper for Capital B
│   ├── html_scraper.py           ← Paginated HTML scraper (Essence)
│   ├── rss_scraper.py            ← Generic RSS fallback scraper
│   └── utils.py                  ← Shared helpers (date filtering, dedup)
│
├── analysis/
│   ├── analyze.py                ← Analysis orchestrator
│   ├── tfidf.py                  ← TF-IDF keyword extraction
│   ├── topic_matcher.py          ← Seed-phrase topic matching
│   ├── topics.py                 ← Topic taxonomy (edit here to add/change topics)
│   └── visualizations.py        ← Charts: bar, heatmap, word clouds, etc.
│
├── report/
│   ├── generate_report.py        ← Renders HTML template → PDF
│   ├── template.html             ← Jinja2 report template
│   └── assets/
│       └── styles.css            ← Report styles
│
├── delivery/
│   └── upload_drive.py           ← Google Drive uploader (OAuth 2.0)
│
├── outputs/                      ← Generated at runtime (gitignored except CSVs/reports)
│
├── .github/
│   └── workflows/
│       └── run_pipeline.yml      ← GitHub Actions: monthly cron + git tagging
│
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"
```

### 2. Set up Google Drive upload (one-time)

Create an OAuth 2.0 Desktop App credential in [Google Cloud Console](https://console.cloud.google.com):

1. Enable the **Google Drive API**
2. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
3. Choose **Desktop app** → download the JSON → save as `credentials.json` in the project root
4. Run the auth flow once:

```bash
python delivery/upload_drive.py --auth
```

A browser window opens. Sign in and approve access. This saves `token.json` — you never need to authenticate again.

5. Copy your Drive folder ID from the URL:
   `https://drive.google.com/drive/folders/<FOLDER_ID>`

6. Create a `.env` file:

```
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

### 3. Run the full pipeline

```bash
python run.py
```

### 4. Run individual stages

```bash
python run.py --skip-scrape          # re-run analysis + report on existing data
python run.py --skip-upload          # run everything except Drive upload
python run.py --days 60              # extend the window to 60 days
python run.py --html-only            # skip PDF generation
```

---

## GitHub Actions (Automated Monthly Runs)

The pipeline runs automatically on the **1st of every month at 06:00 UTC**. You can also trigger it manually from the Actions tab.

### Setup

Add these three secrets to your GitHub repo (**Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `GOOGLE_DRIVE_FOLDER_ID` | Your Drive folder ID |
| `GOOGLE_OAUTH_CREDENTIALS` | Full contents of `credentials.json` |
| `GOOGLE_OAUTH_TOKEN` | Full contents of `token.json` |

The easiest way to add the JSON secrets is via the GitHub CLI:

```bash
gh secret set GOOGLE_OAUTH_CREDENTIALS < credentials.json
gh secret set GOOGLE_OAUTH_TOKEN < token.json
gh secret set GOOGLE_DRIVE_FOLDER_ID --body "your_folder_id"
```

### What happens on each run

1. Scrapes all 10 publications for the full current calendar month (30 or 31 days automatically)
2. Runs TF-IDF analysis and topic matching
3. Generates HTML + PDF editorial report
4. Uploads all files to `GoogleDrive/YourFolder/YYYY-MM-DD/`
5. Commits the dated output folder to the `main` branch
6. Creates a git tag `run-YYYY-MM-DD`
7. Archives all outputs as a GitHub Actions artifact (retained 90 days)

---

## Customising Topics

All 12 topics and their seed phrases live in `analysis/topics.py`. This is the **only file you need to edit** to add, remove, or modify topics. No other file needs to change.

Each topic entry looks like:

```python
{
    "id":          "policing",
    "name":        "Policing & Public Safety",
    "description": "Police reform, use of force, accountability, community safety",
    "color":       "#ef4444",
    "seeds": [
        "police brutality", "use of force", "qualified immunity",
        "police reform", "defund the police", "community policing",
        ...
    ],
}
```

---

## Adding a New Publication

1. Add an entry to the `PUBLICATIONS` list in `scraper/scrape.py`:

```python
{
    "name":     "newsite.com",
    "method":   "wp",          # "wp", "html", "rss", "blavity", or "capitalb"
    "base_url": "https://newsite.com",
    "rss_url":  "https://newsite.com/feed/",
},
```

2. If the site needs a custom scraper, create `scraper/newsite_scraper.py` following the pattern of existing scrapers, then add a method handler in `scrape.py`.

3. Add the output CSV filename to `UPLOAD_FILENAMES` in `delivery/upload_drive.py` and to the artifacts list in `.github/workflows/run_pipeline.yml`.

---

## Tech Stack

| Layer | Library |
|---|---|
| Scraping | `requests`, `beautifulsoup4`, `feedparser`, `playwright` |
| Data | `pandas` |
| NLP | `scikit-learn` (TF-IDF), `nltk` (stopwords) |
| Visualizations | `matplotlib`, `seaborn`, `wordcloud` |
| Report | `weasyprint` (HTML→PDF), `Jinja2` |
| Drive Upload | `google-api-python-client`, `google-auth-oauthlib` |
| Scheduling | GitHub Actions (`cron`) |
| Runtime | Python 3.11, ubuntu-22.04 |

---

## Annotation Validation

To validate the pipeline's topic annotations against human judgment, use the scripts in `validation/`:

**Step 1 — Generate a sample for labeling:**
```bash
python -m validation.sample_articles
```
This draws 200 articles stratified by source and exports `validation/validation_sample.csv` with the pipeline's predictions pre-filled.

**Step 2 — Label the sample:**
Open the CSV in Excel or Google Sheets. For each article, review the title and description, then correct the `label_<topic>` columns (1 = covers this topic, 0 = does not).

**Step 3 — Evaluate:**
```bash
python -m validation.evaluate
```
Outputs per-topic precision, recall, and F1 scores to the terminal and saves `validation/validation_metrics.json` and `validation/confusion_matrix.csv`.

---

## Common Issues

| Issue | Fix |
|---|---|
| Blavity/Synapse returns 0 articles | Check that `synapse.blavityinc.com` is accessible and the date range is correct for the current month |
| PDF not generated | Ensure `cairocffi==1.3.0` and `pydyf==0.3.0` are installed (pinned in `requirements.txt`) |
| Drive auth fails | Re-run `python delivery/upload_drive.py --auth` locally and update the `GOOGLE_OAUTH_TOKEN` secret |
| GitHub Actions timeout | Increase `timeout-minutes` in `run_pipeline.yml` (current: 60 min) |
| New source returns 0 articles | Check if it's WordPress (`/wp-json/wp/v2/posts`), a SPA (needs Playwright), or has a working RSS feed |
| WeasyPrint font warnings | Install system fonts: `apt-get install fonts-liberation fonts-dejavu-core` |

---

## License
MIT

## Outputs: 

![2D4122EE-1F77-4193-8C37-58E6D4F2C694](https://github.com/user-attachments/assets/ee2378ea-3b5d-4bd4-ac25-dc5465390891)
![ED0A4866-16C0-4416-8DC0-4B2DA01D0EF4](https://github.com/user-attachments/assets/bcb4045a-b06f-4a39-8d01-e698d52735ff)
![F972DBE4-DCED-440A-A212-ABE1D4B407EB](https://github.com/user-attachments/assets/0c45462b-2384-4d95-84fa-c9a8aea31260)

