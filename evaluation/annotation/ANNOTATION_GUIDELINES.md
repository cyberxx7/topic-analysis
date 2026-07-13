# Annotation Guidelines
## Black Media Social Topics Study — May 2025–May 2026

**Version:** 1.0  
**Project:** Computational Analysis of Black Media Coverage  
**Annotator task:** Determine whether each article covers one or more of 12 pre-defined social topics, and flag any additional topics not in the list.

---

## 1. Overview

You will be given a spreadsheet (`annotation_sheet.xlsx`) containing approximately 1,000 news articles drawn from 10 Black media publications. For each article, you will read the **Title** and **Description** and decide whether it covers any of the 12 social topics below.

Your annotations will be used to:
- Evaluate the accuracy of the automated topic-detection pipeline.
- Build a gold-standard dataset for training and benchmarking.
- Support a peer-reviewed study on racial equity coverage in Black media.

**Time estimate:** 3–5 seconds per article. The full dataset should take 60–90 minutes.

---

## 2. How to Use the Spreadsheet

### Opening the file
Open `annotation_sheet.xlsx` in **Microsoft Excel** or **Google Sheets**. Click the **Annotation** tab at the bottom.

### Column layout

| Columns | Contents |
|---------|----------|
| A – F   | Article info: ID, Source, Date, Title, Description, Link |
| G – R   | One column per social topic (12 total) |
| S       | **Other** — for topics not in our list |
| T       | **Other Description** — type the topic name if you marked Other = Yes |
| U       | **Notes** — any comments, uncertainty, or reasoning |

### Marking a topic

Click any cell in columns G–S. A **dropdown arrow** will appear. Select:

- **Yes** → the article covers this topic (cell turns **green**)
- **No**  → the article does not cover this topic (cell turns grey)

Pipeline predictions are pre-filled. You are reviewing and correcting them — not starting from scratch.

### Using "Other"

If the article covers a racial justice or social equity topic that does **not** fit any of the 12 categories:

1. Select **Yes** in the **Other** column (column S).
2. Type a brief topic label in the **Other Description** column (column T), e.g., `Black mental health`, `LGBTQ+ rights in Black communities`, `Colorism`.

### Using "Notes"

Use the **Notes** column (column U) to:
- Flag articles you are unsure about.
- Explain a non-obvious Yes/No decision.
- Note if the article's description is too short to judge.

---

## 3. The 12 Social Topics

### Decision rule for all topics
**Mark Yes if the article's main subject or a significant portion of its content concerns the topic.** A passing mention does not count. When in doubt, ask: *"Would a reader primarily searching for coverage of this topic be satisfied by this article?"*

---

### 1. Policing & Public Safety
**What it covers:** Police use of force, officer-involved shootings, police misconduct, police reform legislation, qualified immunity, racial profiling, community policing, immigration enforcement.

**Mark Yes for:**
- Articles about specific incidents of police violence or misconduct.
- News about police reform bills, consent decrees, or union contracts.
- Coverage of officers being disciplined, fired, charged, or acquitted.
- Reports about ICE raids, deportation enforcement, or federal agents.

**Mark No for:**
- Articles that mention crime statistics without discussing policing practices.
- General crime reporting not connected to police conduct.

**Examples:**
- "Officer acquitted in shooting of unarmed Black man" → **Yes**
- "City council votes on police oversight board" → **Yes**
- "Local crime rates rise in Q3" → **No**

---

### 2. Voter Suppression
**What it covers:** Voting rights restrictions, voter ID laws, gerrymandering, voter roll purges, polling place closures, election law changes that affect minority voters.

**Mark Yes for:**
- News about state or federal voting rights legislation.
- Reports on polling place closures, reduced early voting, or ID requirements.
- Coverage of redistricting and gerrymandering affecting Black communities.
- Election integrity debates framed around ballot access.

**Mark No for:**
- General election coverage (candidate profiles, election results) with no voting-access angle.

**Examples:**
- "State legislature passes law requiring photo ID to vote" → **Yes**
- "Senator wins re-election by 5 points" → **No**

---

### 3. Book Bans & Anti-DEI
**What it covers:** Banning of books by Black authors, removal of DEI programs, rollbacks of affirmative action, restrictions on teaching about race in schools, critical race theory legislation.

**Mark Yes for:**
- Articles about specific book challenges or bans in schools or libraries.
- News about DEI office closures, diversity program eliminations, or executive orders targeting DEI.
- Coverage of affirmative action lawsuits or bans.
- Debate over curriculum content related to Black history or race.

**Mark No for:**
- General education policy articles unrelated to race or DEI.

**Examples:**
- "School district removes 'Beloved' from curriculum" → **Yes**
- "University eliminates its diversity, equity, and inclusion office" → **Yes**
- "School board holds budget meeting" → **No**

---

### 4. Housing & Displacement
**What it covers:** Affordable housing crisis, eviction, gentrification, homelessness, housing discrimination, tenant rights, public housing conditions.

**Mark Yes for:**
- Reports on eviction filings or tenant displacement.
- Coverage of gentrification and neighborhood change.
- News about housing voucher availability, public housing, or Section 8.
- Housing discrimination lawsuits or fair housing enforcement.

**Mark No for:**
- Real estate market news (home prices, mortgage rates) without a racial equity or displacement angle.

---

### 5. Maternal Health
**What it covers:** Black maternal mortality, obstetric racism, birth outcomes, prenatal care disparities, midwifery and doula access, postpartum care.

**Mark Yes for:**
- Statistics or stories about Black women dying in or around childbirth.
- Reports on hospitals or providers with poor outcomes for Black mothers.
- News about policy changes affecting maternal health access.
- Personal stories of pregnancy-related mistreatment or near-death experiences.

**Mark No for:**
- General women's health articles with no maternal/birth angle.
- Abortion policy articles (mark under a different topic or "Other").

---

### 6. Redlining & Fair Housing
**What it covers:** Historical and ongoing effects of redlining, biased home appraisals, lending discrimination, neighborhood disinvestment, housing segregation history.

**Mark Yes for:**
- Investigative reports on appraisal gaps for Black homeowners.
- Stories connecting current neighborhood conditions to historical redlining.
- Mortgage denial disparities or bank lending patterns.
- Community reinvestment act enforcement.

**Note:** There is overlap with Housing & Displacement. Mark both if appropriate. Redlining is more specifically about the financial/credit/disinvestment angle; Housing is more about the current displacement/eviction angle.

---

### 7. Anti-Black Surveillance
**What it covers:** Government and corporate surveillance of Black communities, facial recognition bias, predictive policing algorithms, social media monitoring, gang databases, data privacy.

**Mark Yes for:**
- Reports on police using facial recognition or predictive algorithms.
- News about government monitoring of Black activists or organizations.
- Coverage of biometric data misuse affecting Black people.
- Stories about wrongful arrests from flawed AI identification.

**Mark No for:**
- General privacy or technology news without a racial surveillance angle.

---

### 8. Reparations
**What it covers:** Reparations legislation (HR 40, state-level bills), reparations programs (Evanston, California task force), debates about slavery's legacy and economic repair.

**Mark Yes for:**
- Any article primarily about reparations proposals, legislation, or programs.
- Coverage of the California Reparations Task Force or local reparations funds.
- Debates about whether and how to compensate descendants of enslaved people.

**Mark No for:**
- Articles that mention "reparations" only in passing within a broader economic story.

---

### 9. School Funding
**What it covers:** Education funding disparities, underfunded Black schools, school closures, HBCU funding, student loan policy, achievement/opportunity gaps.

**Mark Yes for:**
- Reports on per-pupil spending disparities between districts.
- HBCU funding cuts or expansions, federal HBCU policy.
- School closure announcements affecting Black communities.
- Student loan forgiveness debates with equity implications.
- Articles about Black student enrollment, retention, or academic access.

**Note:** Articles about specific HBCUs (Howard, Spelman, Morehouse, FAMU) almost always qualify. NCAA/sports coverage of HBCU athletes qualifies only if the article discusses the school itself, not just athletic performance.

---

### 10. Criminal Justice Reform
**What it covers:** Mass incarceration, sentencing disparities, bail reform, wrongful convictions, prison conditions, reentry programs, drug war, juvenile justice.

**Mark Yes for:**
- Articles about criminal cases involving Black defendants (arrest, charges, trial, sentencing, appeals).
- Reports on policy changes to sentencing, bail, or parole.
- Prison conditions, solitary confinement, or incarceration statistics.
- Wrongful conviction exonerations.

**Note:** This is the broadest category. An article about any criminal case with a Black defendant likely qualifies if the article discusses systemic issues, disparities, or the justice process in detail. A brief celebrity crime item without systemic context does not qualify.

---

### 11. Environmental Justice
**What it covers:** Environmental racism, pollution in Black neighborhoods, toxic exposure, clean air/water access, climate vulnerability, hurricane recovery.

**Mark Yes for:**
- Reports on industrial facilities, landfills, or highways disproportionately placed near Black communities.
- Water contamination stories (lead, PFAS, etc.) affecting Black residents.
- Climate vulnerability and disaster recovery disparities.
- Environmental health disparities (asthma rates, cancer clusters).

**Mark No for:**
- General climate change coverage with no racial equity angle.

---

### 12. Economic Equity & Wealth Gap
**What it covers:** Racial wealth gap, Black entrepreneurship, wage discrimination, economic mobility, financial inclusion, predatory lending, access to capital.

**Mark Yes for:**
- Reports on racial gaps in income, wealth, or homeownership.
- Coverage of Black-owned businesses, funding disparities for Black entrepreneurs.
- Pay discrimination lawsuits or wage gap studies.
- Financial access (banking deserts, payday loan targeting, credit access).

**Mark No for:**
- General business/tech profiles of Black entrepreneurs unless the article explicitly discusses racial equity or economic disparities.

---

## 4. Using "Other"

Mark **Other = Yes** when the article covers a racial justice or social equity topic that does NOT fit the 12 categories. In the **Other Description** cell, type a brief label.

**Common "Other" categories:**
- Black mental health / mental health disparities
- LGBTQ+ rights within Black communities
- Colorism
- Cultural representation / media representation
- Black women's rights / gender equity
- Reproductive rights / abortion access for Black women
- Immigration and Black immigrants
- Hate crimes / white supremacy
- Anti-Black violence (non-policing)
- Land rights / Black land loss
- International / diaspora issues

---

## 5. Difficult Cases

**Q: The article covers multiple topics. What do I do?**  
Mark Yes for every topic that applies. There is no limit.

**Q: The description is very short and I can't tell.**  
Click the link (column F) to read the full article if needed. If still unclear, mark No and leave a note.

**Q: The pipeline predicted Yes but I think it's No.**  
Correct it — change to No. Your judgment overrides the pipeline.

**Q: The article is entertainment, lifestyle, or sports with no equity angle.**  
Mark No for all topics. Not all Black media content is about social issues.

**Q: The article is about a policy that affects all Americans, not specifically Black people.**  
Mark Yes only if the article explicitly discusses the disproportionate impact on Black communities.

---

## 6. Quality Standards

- **Aim for consistency:** If you would mark Yes for one article about voter ID laws, mark Yes for all similar articles.
- **Inter-rater reliability:** A random 10% of articles will be annotated by a second annotator. Disagreements will be resolved by discussion.
- **Contact:** If you encounter a pattern of unclear cases, flag them in the Notes column and reach out to the research team before continuing.

---

## 7. Quick Reference Card

| Mark Yes if... | Mark No if... |
|----------------|---------------|
| Article's main focus is the topic | Topic is only a passing reference |
| Article discusses systemic issues | Article covers only individual/celebrity story |
| Article explicitly discusses racial disparities | Article covers general policy with no racial angle |
| Article is about a Black community experiencing the issue | Entertainment/lifestyle with no equity angle |

---

*Thank you for your time and careful attention to this work.*
