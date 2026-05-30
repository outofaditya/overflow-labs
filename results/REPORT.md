# From Crowd Knowledge to AI-Assisted Development: A Longitudinal Semantic Analysis of Stack Overflow After 2020

_Living draft of the final report. Updated as part of closing every atom of the research plan. Co-authored by Roham Koohestani, Aditya Patil, and Tomasz Soróbka for the Web Science and Engineering course at TU Delft._

> **Style rule.** Academic but accessible. Use simple words where they work. Prefer direct active sentences over passive ones. Keep paragraphs short. Define a term the first time it appears.
>
> **Update rule.** Each atom is closed only when this file has been updated with: (a) any methodology decisions made, (b) any numbers or figures produced, (c) any caveats or threats to validity observed. No atom ships without touching the matching section here.

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

_Metric definitions are formalised in later atoms — interaction speed and engagement metrics in the RQ1 atom, text complexity features in the RQ2 atoms. This section is updated as each is added._

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

_To be populated in Atom 3. Will include monthly volume of questions and answers, accepted-answer rate, time-to-first-answer (median and p90), and engagement signals (mean score, mean comment count). Each figure gets a draft caption here._

### 4.2 Question Complexity and Difficulty (RQ2)

_To be populated in Atoms 4 and 5. Atom 4 reports cheap lexical features (title length, body length, code block count, etc.). Atom 5 reports the CodeT5 + XGBoost difficulty classifier and its monthly Hard/Medium/Easy mix._

### 4.3 Topic and Intent Distribution (RQ3)

_To be populated in Atom 6. Reports the Beyer-et-al. seven-category taxonomy extended with two AI-era categories (Machine-Authored Discrepancy, Architectural Consensus), per-author labelling agreement, the chosen classifier, the monthly topic mix, and focused trajectories for the new categories._

### 4.4 Tag-Group and Domain Comparison (RQ4)

_To be populated in Atom 7. Replays metrics per technology group (legacy stable, fast-moving web, AI-native libraries) to test the concept-drift hypothesis._

### 4.5 Temporal Statistics

_To be populated in Atom 8. Reports structural-break tests at the ChatGPT cutoff, interrupted time-series regression on each key metric, and robustness reruns excluding the 2025-2026 confounded period._

---

## 5. Limitations and Threats to Validity

_Living section — every atom appends here when new caveats appear._

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
