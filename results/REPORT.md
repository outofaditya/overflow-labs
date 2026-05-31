# From Crowd Knowledge to AI-Assisted Development: A Longitudinal Semantic Analysis of Stack Overflow After 2020

_Co-authored by Roham Koohestani, Aditya Patil, and Tomasz Soróbka for the Web Science and Engineering course at TU Delft._

---

## Abstract

_To be drafted near submission once results are stable. Should answer: what we set out to study, how we studied it, what we found, what it means._

---

## 1. Introduction

### 1.1 Motivation

_Why this work matters. Stack Overflow has been the public memory of software engineering for two decades. The arrival of ChatGPT in late 2022 changed how developers ask for help. We study what happened next._

### 1.2 Problem Statement

_The drop in Stack Overflow activity since late 2022 is widely observed, but the underlying shift is not just a decline. We frame it as an "AI verification tax": developers now bring harder, architectural, and AI-debugging problems to the human crowd, because AI handles the easy ones privately._

### 1.3 Research Questions

- **RQ1.** How have Stack Overflow activity levels, answer availability, and response speeds changed from 2020 onward?
- **RQ2.** Has the difficulty and complexity of Stack Overflow questions increased since 2022, and does this reflect the verification tax?
- **RQ3.** How has the distribution of topics and developer intent shifted since 2020?
- **RQ4.** Which technical domains show the strongest changes, and does this highlight AI concept drift?

### 1.4 Contributions

_Filled at the end. Expected: a longitudinal empirical study with real numbers; a difficulty classifier with documented transfer behaviour; an extended topic taxonomy for the AI era; a per-domain comparison; a fully reproducible local pipeline._

---

## 2. Background and Related Work

### 2.1 Stack Overflow as a Developer Knowledge Platform

_Brief history. Structure of the data. Why it has been studied so much._

### 2.2 Past Work on Developer Intent and Question Taxonomies

_Barua et al. on topics and trends; Allamanis and Sutton on why, when, and what developers ask; Beyer et al.'s seven-category taxonomy that we build on; Wang et al. on developer interactions._

### 2.3 Developer Behaviour in the Generative AI Era

_Recent work on the impact of LLMs on Stack Overflow activity, including Da Silva et al.'s reliability and user-activity analyses. The 2025 Stack Overflow Developer Survey on AI usage and trust._

---

## 3. Data Collection

### 3.1 Choice of Data Source

_Our initial plan was to query the Stack Overflow public dataset hosted on Google BigQuery. We found that snapshot had last been refreshed on 2022-09-25, two months before the public release of ChatGPT — useless for a study whose core question is about the AI era. A first attempt with the community-mirrored Stack Exchange dump on Internet Archive (collection `stackexchange_20251231`) proved incomplete: its data ended in early 2024 despite the later naming. We finally moved to the **official Stack Exchange data dump**, downloaded directly from a Stack Overflow profile's Data Dump settings page. This is the authoritative source. Our copy covers all posts through **2026-03-31** (the dump's stated cutoff). The downloaded archive's SHA-256 fingerprint is recorded in `results/tables/manifest.yaml` so a reviewer can verify their dump bytes match ours._

### 3.2 Tables Used

_The official dump contains eight tables. We extract and convert the five relevant to our analysis: **Posts** (questions and answers in one table, distinguished by `PostTypeId`), **Users**, **Comments**, **PostLinks**, and **Tags**. The three we omit — **Badges**, **PostHistory**, **Votes** — do not bear on the present research questions, and skipping them saves both disk space and ingestion time._

### 3.3 Local Ingestion Pipeline

_We extract tables from the single official `.7z` archive on an external SSD, one table at a time. For each table we stream the inner XML through `lxml.iterparse` (constant-memory parsing) and write monthly-partitioned Parquet via `pyarrow.ParquetWriter`. The partition key is `year_month=YYYY-MM`, derived from each row's `CreationDate`; Tags has no useful date dimension and writes as a single file. After each table's Parquet is verified, we delete the source `.7z` and `.xml` to reclaim SSD space. The full pipeline runs in ~3 hours on a 2024 MacBook Air, dominated by the 60-million-row Posts table._

_The materialised dataset is also hosted in a private Hugging Face dataset repository ([outofaditya/overflow-labs-dump](https://huggingface.co/datasets/outofaditya/overflow-labs-dump)) so co-authors can pull the parquet without re-running the ingestion. The repository README documents both reproduction paths in detail._

### 3.4 Definition of Interaction and Complexity Metrics

_The metric definitions used in the analysis are formalised inline in §4. Interaction-speed and engagement metrics accompany §4.1; the six lexical complexity features accompany §4.2._

### 3.5 Data Validation

_Validation outputs land under `results/tables/data_validation.csv` (per-table summary) and `results/tables/posts_per_month.csv` (monthly time series with gap markers). Per-table summary:_

| Table     |            Rows | Partitions | First Date | Last Date  |
| --------- | --------------: | ---------: | ---------- | ---------- |
| Posts     |      60,349,494 |        213 | 2008-07-31 | 2026-03-31 |
| Users     |      31,031,671 |        213 | 2008-07-31 | 2026-03-31 |
| Comments  |      91,268,612 |        212 | 2008-08-01 | 2026-03-31 |
| PostLinks |       6,523,169 |        192 | 2010-04-26 | 2026-03-31 |
| Tags      |          65,941 |          1 | —          | —          |
| **Total** | **189,238,887** |            |            |            |

_The questions-per-month series spans **75 months** from January 2020 through March 2026 with **zero gaps** (no missing months in the analysis window). The headline trajectory is dramatic on its own: question volume fell from **146,664** in January 2020 to **2,033** in March 2026, a ~98% decline. This is the central RQ1 signal — the rest of the analysis quantifies and explains its shape._

---

## 4. Data Analysis

### 4.1 Activity Trends and Interaction Speeds (RQ1)

_We track seven monthly time series from January 2020 through March 2026 (75 months), partitioned at the public release of ChatGPT on 2022-11-30 (35 pre-release months, 40 post). Underlying CSVs sit under `results/tables/`. The corresponding figures sit under `results/figures/one/`, grouped by metric type into four panels: `activity.svg` (question/answer volume and distinct askers), `quality.svg` (accepted-answer rate and answer coverage rate), `response_time.svg` (time to first answer and time to acceptance), and `engagement.svg` (mean score and mean comments per question). The vertical dashed reference line in every figure marks the cutoff. Where rates of resolution are reported (accepted rate, acceptance time), the most recent six months are excluded from pre/post summaries because both metrics lag question creation; figures still display the full tail, dimmable by the `question_count` companion column._

**Volume (left panel of `activity.svg`).** Question and answer volume on Stack Overflow has collapsed. Median monthly questions fell from **129,018 pre-ChatGPT to 29,682 post** (–77%). The two boundary months are even more striking: **146,664 questions in January 2020 versus 2,033 in March 2026, a –98.6% drop**. Answers track questions in lockstep — median 166,903 → 43,968 per month (–74%); 198,173 (Jan 2020) → 4,075 (Mar 2026, –97.9%). Both series begin sliding well before late 2022 (a slow pre-existing decline since the 2014 peak), but the slope steepens visibly after the reference line.

**Active askers (right panel of `activity.svg`).** Distinct non-anonymous askers per month dropped from a pre-ChatGPT median of **90,649 to a post median of 25,130 (–72%)**. The participation drop is therefore _less severe_ than the question-volume drop: the asker base contracted by 72% while questions contracted by 77%. The questions-per-asker ratio fell modestly, from a pre-ChatGPT monthly median of **1.42 to 1.18 (–17%)**. Reading: the community shrank primarily because _fewer people are asking at all_, not because the surviving askers off-loaded most of their questions to AI. Both effects exist, but the participation collapse dominates.

**Accepted-answer rate (lower line of `quality.svg`).** Pre-ChatGPT mean: **43.2%**. Post-ChatGPT mean (excluding the last six months for tail noise): **35.0%**. An 8-percentage-point decline. The most recent month sits even lower at ~29%, but that figure is small-denominator noise (acceptance lags creation by days to weeks).

**Answer coverage rate (upper line of `quality.svg`).** Pre-ChatGPT mean: **80.9%**. Post-ChatGPT mean (excluding tail): **73.9%**. A 7-percentage-point decline. Critically, the coverage-versus-accepted gap — a candidate signal for "community keeps answering but askers stop coming back to accept" — stayed essentially **flat at 37.6% pre vs 38.8% post**. The data does _not_ support a decoupling story: when one falls, both fall together. The community is still about as willing to mark answers accepted, relative to how many it answers, as it has always been.

**Time to first answer (left panel of `response_time.svg`).** Median-of-monthly-medians **tripled, from 1.0 h pre to 3.5 h post** (×3.4). The p90-of-monthly-p90s grew from 129 h (~5.4 days) to 193 h (~8 days), a smaller ×1.5 increase. The _median climbed more than the tail_. This refines (and partly rebuts) the simplest verification-tax framing — it is not just hard questions sitting longer; _every_ question, including the median case, now takes substantially longer to get an answer. The whole answering pipeline is slower, not just its long tail.

**Time to acceptance (right panel of `response_time.svg`).** Same shape: median 1.0 h → 2.8 h (×2.9), p90 69 h → 116 h (×1.7). Resolution times tracked first-response times almost exactly. Again, the median moved more than the tail.

**Engagement (`engagement.svg`).** Mean question score per month dropped from a pre-ChatGPT mean of **0.82 to a post mean of 0.61** (–25%). The headline values bookend it: Jan 2020 averaged 1.13 score per question, Mar 2026 averages 0.74. Mean comment count per question moved the opposite direction, slightly: **2.03 pre to 2.20 post** (+8%). Reading: surviving questions get marginally more discussion (perhaps because the rare hard question that does reach Stack Overflow attracts more back-and-forth) but they are _less popular_ on average. The verification-tax hypothesis predicts "fewer but higher-signal questions"; the data shows fewer-and-modestly-less-upvoted questions, with slightly more comments. The signal-quality story is mixed.

**Headline reading.** The data supports a _structural shift_ in Stack Overflow's role, but with a more nuanced shape than a simple "AI handles easy, humans handle hard" narrative:

1. **Volume collapse is the dominant fact** — ~98% reduction in monthly questions over the full window.
2. **Participation contracted faster than per-user activity** — the asker base shrank 72% while questions-per-asker fell only 17%. The platform thinned because fewer people came, not primarily because each user offloaded most of their work to AI.
3. **Resolution speed deteriorated uniformly** — median response and acceptance times both tripled, with the p90 growing less. The slowdown is platform-wide, not concentrated in the hard tail.
4. **No coverage-acceptance decoupling** — the gap between "got any answer" and "got an accepted answer" is essentially unchanged, contradicting the "community answers but askers stop accepting" hypothesis.
5. **Engagement is mixed** — fewer upvotes per question, more comments per question. Not a clean validation of the "surviving questions are higher quality" prediction.

Formal structural-break tests (Chow, CUSUM) and interrupted time-series regression on each series will quantify the statistical significance of the shift at 2022-11-30 and decompose the level change from the slope change.

### 4.2 Question Complexity and Difficulty (RQ2)

_To characterise question complexity from the surface form of each post, we compute six lexical features per question: title length (characters), body prose length (characters with `<pre>` regions excluded), total code-block length (characters within `<pre>` regions), code-block count, link count (`<a` tag matches in the raw body), and tag count. Features are extracted on a stratified monthly sample (1,000 questions per `year_month`, deterministic via a hash-ordered row number) and aggregated to a monthly median and p90 across all 75 months. Underlying data sits in `results/tables/lex_features.csv`; the corresponding figures sit under `results/figures/two/`. `complexity_trends.svg` is a 2×3 small-multiples panel of all six features over time (top row: title length, body prose length, code-block total length; bottom row: code-block count, link count, tag count), with the vertical dashed reference line marking 2022-11-30. `complexity_change.svg` is a horizontal bar chart of the percent change in each feature's mean-of-monthly-medians between the 35 pre-release months and the 40 post-release months._

**Body prose length (top-centre panel of `complexity_trends.svg`).** The largest movement among the six features. Monthly-median body prose length rose from **428 characters pre-release to 567 post (+32.3%)**, with the p90 rising in lockstep from **972 to 1,273 characters (+30.9%)**. The boundary months are starker: January 2020 carried a median of 450 characters of prose; March 2026 carries 681 (+51%). The near-identical growth rates at the median and the p90 indicate a population-wide shift rather than a long-tail effect — every quintile of the distribution moved together.

**Code-block total length (top-right panel of `complexity_trends.svg`).** The total length of `<pre>` code regions per question rose from a monthly median of **432 characters pre-release to 565 post (+30.9%)**, mirroring the body-prose growth almost exactly. The p90 climbed from **2,428 to 3,276 characters (+34.9%)** — slightly faster than the median, indicating the heavy-code tail expanded marginally more than the typical case. Because code length tracks body length so closely, the additional code is being introduced alongside additional surrounding prose rather than substituting for it: post-release questions are not _replacing_ prose with code, they are doing more of both.

**Code-block count (bottom-left panel of `complexity_trends.svg`).** The number of distinct `<pre>` blocks per question rose at the median from **1.00 pre-release to 1.18 post (+17.5%)**, with the p90 climbing from **3.23 to 3.85 blocks (+19.1%)**. From mid-2025 onward the monthly median sits at 2 — the typical question now ships two separate code blocks rather than one. Combined with the +30.9% increase in total code length, the post-release content is not only larger but structurally segmented: input versus expected output, failing snippet versus surrounding code, original versus reproduction.

**Title length (top-left panel of `complexity_trends.svg`).** A smaller but consistent rise: monthly-median title length grew from **56.5 characters pre-release to 61.8 post (+9.3%)**, the p90 from **91.0 to 99.1 (+9.0%)**. The boundary months bracket this clearly: January 2020 had a 57-character median title; March 2026 has 66. Even the title — the most-constrained component of a Stack Overflow post, often shortened by community norms around brevity — gained material length.

**Link count (bottom-centre panel of `complexity_trends.svg`).** The monthly median is **zero both pre- and post-release** — most questions still contain no embedded hyperlinks. The only meaningful movement is in the upper tail: the p90 rose from **1.57 to 1.98 links per question (+25.7%)**. A widening minority of questions now embed at least one hyperlink (typically a documentation reference or an error-trace permalink), but link inclusion has not become default behaviour for the median question.

**Tag count (bottom-right panel of `complexity_trends.svg`).** Completely flat across the full window. Pre- and post-release monthly medians are both **3 tags**; pre- and post-release p90s are both **5 tags**. Stack Overflow imposes a hard cap of five tags per question at the UI level, and the data confirms this acts as a true structural constraint rather than a user preference that could shift under behavioural change.

**Headline reading.** Every content-size feature moved substantially in the same direction, and every platform-constrained feature held flat:

1. **Surviving questions carry roughly one-third more body text and one-third more code.** Body prose +32.3%, code length +30.9%, code-block count +17.5%. The post-release residual is not just _fewer_ questions but visibly _heavier_ questions by every content measure that is free to move.
2. **The shift is uniform across the distribution.** Median and p90 grew within three percentage points of each other for every length feature. Rather than a small group of users posting unusually verbose questions, the whole population of surviving questions moved together.
3. **The unchanged features are exactly those Stack Overflow constrains structurally.** Tag count is bounded by the UI; link inclusion is voluntary and remains rare at the median. These nulls confirm the positive results are not an artefact of measurement drift or a system-wide composition change.

Taken together with the activity collapse in §4.1, the lexical evidence is consistent with a verification-tax mechanism: questions that can be efficiently resolved by an AI assistant no longer reach Stack Overflow, leaving a residual whose questions are visibly more complex along every content dimension that is free to vary. The six lexical features established here form a content-grounded, interpretable comparison floor; the difficulty classification that follows is required to demonstrate explanatory value beyond what these features already capture.

### 4.3 Topic and Intent Distribution (RQ3)

_This section will report the topic and intent distribution of questions across the analysis window, built on the Beyer et al. seven-category taxonomy extended with two AI-era categories (Machine-Authored Discrepancy, Architectural Consensus). It covers per-author labelling agreement, the chosen classifier, the monthly topic mix, and focused trajectories for the two new categories._

### 4.4 Tag-Group and Domain Comparison (RQ4)

_This section will replay the metrics in §4.1–§4.3 split by technology group (legacy stable, fast-moving web, AI-native libraries) to test the concept-drift hypothesis._

### 4.5 Temporal Statistics

_This section will report formal structural-break tests at the ChatGPT cutoff, interrupted time-series regression on each key metric, and robustness reruns that exclude the 2025–2026 period confounded by platform-level events._

---

## 5. Limitations and Threats to Validity

_The threats to validity catalogued below are updated as additional caveats surface during the analysis._

- **The BigQuery snapshot cutoff.** We attempted to use the Google-maintained BigQuery snapshot of Stack Overflow and discovered it ended on 2022-09-25. The pivot to the community dump introduces a different validity concern: the community-maintained release is not the official Stack Exchange release, and recent community-maintained dumps reportedly miss some posts from deleted users.
- **Deleted-user gap.** Community-mirrored dumps may omit posts whose authors deleted their accounts. We will quantify the gap during ingestion if a measurement is feasible.
- **Confounding platform events.** Stack Overflow opened opinion-based questions to all users in early 2026 and rolled out (then withdrew) a major site redesign between February and April 2026. These events likely shape user engagement during the late period of our window. All charts annotate these events; robustness analyses re-fit without that period.
- **Selection bias.** Our data only reflects public developer activity. Private AI tool usage inside companies is invisible to us.
- **Interaction metrics as proxies.** Time-to-first-answer and accepted-rate are practical signals, not direct measures of user success.

---

## 6. Conclusions

_To be drafted near submission. Should summarise the findings against the four research questions, name the most surprising results, and point at reproducibility materials._

---

## 7. Reproducibility

_The project supports two reproduction paths, and both are first-class:_

_**Path A — Reproduce from scratch (public).** Any reviewer or researcher with their own copy of the Stack Overflow data dump (downloadable from a Stack Overflow user profile's Data Dump settings) can clone this repository, set `DATA_DUMP` to point at the dump location, and run `python -m source.pipeline`. The pipeline decompresses the archive, streams the XML through `lxml.iterparse`, and writes the same `year_month`-partitioned Parquet layout used to produce every number and figure in this report. SHA-256 checksums in `results/tables/manifest.yaml` let reviewers verify their dump bytes match the version we worked from._

_**Path B — Team-internal fast path (private).** Co-authors fetch the materialised Parquet directly from the private Hugging Face dataset repo [outofaditya/overflow-labs-dump](https://huggingface.co/datasets/outofaditya/overflow-labs-dump) using `python -m source.cloud pull`, skipping the ~3-hour ingestion. The pull lands the parquet in the standard local HF cache; downstream code reads from there. This path is private to the team; external reproducers use Path A._

_All code, the dataset manifest, the figure-to-script provenance, and the limitations checklist live under `results/` and the project repository. The pipeline is deterministic given the same dump bytes — a reviewer running Path A should produce identical Parquet row counts and downstream numbers._

---

## References

_Maintained in `results/citations.bib`. The list below is the human-readable form, expanded as citations accrue._

1. Allamanis, M., & Sutton, C. (2013). Why, when, and what: analyzing Stack Overflow questions by topic, type, and code. _MSR 2013_.
2. Barua, A., Thomas, S. W., & Hassan, A. E. (2014). What are developers talking about? An analysis of topics and trends in Stack Overflow. _Empirical Software Engineering_ 19(3).
3. Beyer, S., Macho, C., Di Penta, M., & Pinzger, M. (2020). What kind of questions do developers ask on Stack Overflow? _Empirical Software Engineering_ 25(3).
4. Da Silva, L., et al. (2025). LLMs and Stack Overflow discussions: reliability, impact, and user activity evolution. _Journal of Systems and Software_.
5. Da Silva, L., Samhi, J., & Khomh, F. (2025). LLMs and Stack Overflow discussions: reliability, impact, and challenges. _Journal of Systems and Software_ 230.
6. Wang, S., Lo, D., & Jiang, L. (2013). An empirical study on developer interactions in Stack Overflow. _Symposium on Applied Computing 2013_.
