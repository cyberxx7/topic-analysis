# Data Card: Black Media Intelligence Dataset

> Following the Data Card framework proposed by Pushkarna et al. (2022)
> and the dataset documentation guidelines of the NeurIPS Datasets and Benchmarks Track.

---

## 1. Dataset Overview

| Field | Details |
|---|---|
| **Name** | Black Media Intelligence Dataset (BMID) |
| **Version** | Monthly rolling release |
| **Created by** | Ademola Adeniyi |
| **Contact** | graygraphics67@gmail.com |
| **License** | MIT |
| **Repository** | https://github.com/cyberxx7/topic-analysis |
| **Format** | CSV |
| **Language** | English |
| **Domain** | News media / Computational social science |

---

## 2. Dataset Description

### What is this dataset?

The Black Media Intelligence Dataset (BMID) is a structured, monthly-updated collection of editorial articles sourced from 10 prominent Black American media publications. Each article is annotated with metadata (title, description, author, publication date, source, category, URL) and automatically tagged against a taxonomy of 12 social conflict topics relevant to the Black American experience.

The dataset is produced by an open, reproducible pipeline that runs automatically on the 1st of every month, collecting all articles published during the preceding calendar month.

### Why was it created?

Existing NLP and AI evaluation benchmarks are overwhelmingly sourced from mainstream, predominantly white media outlets (e.g., Reuters, Associated Press, The New York Times). AI models trained and evaluated on these corpora have been shown to underperform on text produced by and for communities of color, due to differences in language, framing, topic prioritization, and cultural context.

BMID was created to:
1. Fill a systematic gap in AI/NLP benchmark coverage by providing a large, clean, reproducible corpus from Black media
2. Enable evaluation of whether AI models generalize across media ecosystems with different editorial perspectives
3. Support computational social science research on how Black media covers social conflict topics over time

---

## 3. Composition

### Publications Covered (10)

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

### Data Schema

Each article record contains the following fields:

| Field | Type | Description |
|---|---|---|
| `title` | string | Article headline (up to 500 characters) |
| `description` | string | Excerpt or meta description (up to 500 characters) |
| `source` | string | Publication domain (e.g. `thegrio.com`) |
| `date_of_publication` | date | Format: `YYYY-MM-DD` |
| `category` | string | Publication-assigned editorial category |
| `author` | string | Article byline |
| `link` | string | Canonical article URL |
| `topics` | string | Matched social conflict topic(s), semicolon-separated |
| `topic_ids` | string | Topic identifier codes |
| `matched_phrases` | JSON | Phrases that triggered each topic match |
| `topic_count` | integer | Number of topics matched (0 if untagged) |
| `match_score` | float | Normalized confidence score (0–1) |

### Topic Taxonomy (12 Topics)

| # | Topic | Description |
|---|---|---|
| 1 | Policing & Public Safety | Police reform, use of force, accountability, officer-involved shootings |
| 2 | Voter Suppression | Voting rights, ballot access, gerrymandering, disenfranchisement |
| 3 | Book Bans & Anti-DEI | Censorship of Black literature, DEI rollbacks, critical race theory bans |
| 4 | Housing & Displacement | Affordable housing, eviction, gentrification, housing discrimination |
| 5 | Maternal Health | Black maternal mortality, obstetric racism, prenatal care disparities |
| 6 | Redlining & Fair Housing | Historical redlining legacy, lending discrimination, appraisal bias |
| 7 | Anti-Black Surveillance | Facial recognition bias, predictive policing, government monitoring |
| 8 | Reparations | Reparations for slavery, wealth redistribution, community investment |
| 9 | School Funding | Education funding disparities, underfunded schools, HBCU funding |
| 10 | Criminal Justice Reform | Mass incarceration, sentencing disparities, bail reform |
| 11 | Environmental Justice | Environmental racism, pollution in Black communities, climate vulnerability |
| 12 | Economic Equity & Wealth Gap | Racial wealth gap, Black entrepreneurship, wage discrimination |

### Sample Statistics (March 2026 Run)

| Metric | Value |
|---|---|
| Total articles | 1,221 |
| Date range | February 25, 2026 – March 27, 2026 |
| Articles with at least one topic tag | 179 (14.7%) |
| Articles with no topic tag | 1,042 (85.3%) |
| Most covered topic | School Funding (47 articles) |
| Least covered topic | Redlining & Fair Housing (1 article) |

**Per-source article counts:**

| Source | Articles |
|---|---|
| thegrio.com | 469 |
| theroot.com | 357 |
| newsone.com | 176 |
| ebony.com | 133 |
| essence.com | 38 |
| capitalbnews.org | 28 |
| blavity.com | 20 |

*Note: 21ninety.com, travelnoire.com, and afrotech.com were added after this sample run and will appear in subsequent monthly releases.*

---

## 4. Collection Process

### Scraping

Articles are collected using four scraping strategies depending on the publication's technical infrastructure:

- **WordPress REST API** — Used for The Grio, The Root, NewsOne, and Ebony. Queries the `/wp-json/wp/v2/posts` endpoint with date filters for the full calendar month.
- **Synapse RSS Feed** — Used for all four Blavity Inc. publications (Blavity, 21Ninety, Travel Noire, AfroTech). Fetches from `synapse.blavityinc.com`, a first-party content platform that provides a paginated RSS 2.0 feed sourced directly from the WordPress backend.
- **Paginated HTML** — Used for Essence. Scrapes category listing pages with BeautifulSoup.
- **Sitemap + HTML** — Used for Capital B News. Parses the XML sitemap to discover article URLs.
- **RSS fallback** — Applied automatically when any primary method returns fewer than 5 articles.

The scrape window is set dynamically to the exact number of days in the current calendar month (28, 29, 30, or 31 days).

### Topic Annotation

Topic tagging uses a two-stage approach:

1. **Text construction** — Each article's title, description, and category are concatenated into a single lowercase string.
2. **Seed-phrase matching** — The text is matched against a curated dictionary of seed phrases for each of the 12 topics. Single-word phrases use flexible suffix matching (e.g., "officer" matches "officers"). Multi-word phrases allow up to one intervening word for flexibility.

An article can be tagged with multiple topics. Articles that match no seed phrases receive no topic tag (shown as empty in the `topics` column).

### Deduplication

Articles are deduplicated by canonical URL before being saved. Duplicate URLs are removed and reported in the pipeline log.

---

## 5. Preprocessing

- HTML tags are stripped from titles and descriptions
- Text is truncated to 500 characters for the description field
- Dates are normalized to `YYYY-MM-DD` format
- Articles without a parseable publication date are excluded
- All fields are UTF-8 encoded

---

## 6. Intended Uses

### Appropriate Uses

- **NLP model evaluation** — Benchmarking named entity recognition, sentiment analysis, topic classification, and summarization models on Black media text
- **Domain generalization research** — Evaluating whether models trained on mainstream media transfer to Black media
- **Computational social science** — Studying how Black media covers social conflict topics over time
- **Media bias research** — Comparing editorial prioritization across publications
- **Temporal analysis** — Tracking topic salience month by month as new releases become available

### Uses to Avoid

- **As a complete picture of Black media** — The dataset covers 10 online publications. It does not represent print, broadcast, radio, podcasts, or community newspapers.
- **As ground truth for topic classification without validation** — The seed-phrase annotation method is not a learned model and has not been validated against all possible phrasings. Human validation is ongoing.
- **Training data for generative models without review** — Articles may contain reporting on sensitive topics including violence, discrimination, and death. Downstream use in generative model training should include additional ethical review.

---

## 7. Limitations

### Coverage Limitations
- Only English-language publications are included
- Only online editorial articles are collected — no op-eds identified separately, no letters to the editor, no paywalled content
- Publications are limited to those with reliable programmatic access (REST API, RSS, or scrapeable HTML)
- The 10 publications were selected by the researchers — this selection reflects editorial judgment and does not claim to be exhaustive

### Annotation Limitations
- Topic tagging is performed by seed-phrase matching, not a trained classifier. It will miss articles that discuss a topic using language outside the seed dictionary.
- The topic taxonomy (12 topics) was defined by the researchers and reflects their framing of social conflict issues relevant to Black communities. Other researchers may define these categories differently.
- Articles can match multiple topics, which may overestimate coverage of some topics
- 85.3% of articles in the sample run were untagged — many articles cover general lifestyle, entertainment, and culture content outside the 12 tracked topics

### Temporal Limitations
- Each monthly release reflects only that calendar month's coverage
- Historical data prior to pipeline deployment is not included
- Publication volume varies by month and by outlet

### Scraping Limitations
- Article availability depends on each publication's website remaining accessible and structurally stable
- Changes to a publication's website may require scraper updates
- Rate limiting or blocking by publications could reduce coverage

---

## 8. Ethical Considerations

- All articles are publicly available editorial content. No paywalled, private, or user-generated content is collected.
- No personally identifiable information beyond author bylines (which appear in published articles) is collected.
- The dataset covers topics including police violence, racial discrimination, and other sensitive subjects. Researchers should apply appropriate content warnings when using this data.
- The pipeline is designed to study editorial coverage patterns, not to profile individuals mentioned in articles.

---

## 9. Maintenance & Updates

- The dataset is updated automatically on the **1st of every month** via a GitHub Actions workflow
- Each monthly release is saved to a dated folder (`outputs/YYYY-MM-DD/`) and tagged in the repository (`run-YYYY-MM-DD`)
- All outputs are simultaneously uploaded to Google Drive for non-technical access
- The pipeline source code, scraper logic, and topic taxonomy are fully open source

To add a new publication or modify the topic taxonomy, see the contribution guide in `README.md`.

---

## 10. Citation

If you use this dataset, please cite:

```
@misc{adeniyi2026bmid,
  title   = {Bridging the Data Gap: Towards Infrastructure for Custom,
             Dynamic Dataset Curation & Analysis},
  author  = {Adeniyi, Ademola},
  year    = {2026},
  url     = {https://github.com/cyberxx7/topic-analysis}
}
```

---

## 11. Changelog

| Date | Change |
|---|---|
| 2026-04 | Expanded from 7 to 10 publications; added Synapse integration for Blavity Inc. |
| 2026-04 | Switched Drive delivery from OAuth to Service Account for reliability |
| 2026-04 | Dynamic scrape window now matches exact days in calendar month |
| 2026-04 | Validation framework added (200-article stratified sample + evaluation scripts) |
