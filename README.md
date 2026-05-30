# From Crowd Knowledge to AI-Assisted Development: A Longitudinal Semantic Analysis of Stack Overflow After 2020

A Study of How Developer Behavior Shifted in the Generative-AI Era

## Repository Structure

- `source/` — Python Source (Layered by Concern)
  - `source/ingestion/` — Producer-Only Data Pipeline (Manifest, Extract, Dump, Pipeline)
  - `source/data/` — Query Layer (DuckDB, SQL Slice Loaders, Validation)
  - `source/analysis/` — Per-RQ Analyses (Metrics, Figures, Models)
  - `source/cloud.py` — Hugging Face Sync (Push + Pull)
  - `source/constants.py`, `source/logger.py` — Foundations
- `commands/` — SQL Query Files (DuckDB Dialect)
- `tests/` — Testing Suite (Mirrors `source/`)
- `notebooks/` — Exploratory Analysis
- `results/` — Figures, Tables, and the Living Paper Draft (`REPORT.md`)
- `options/` — YAML Configs (Tag Groups + Sampling Parameters + More)

## Project Setup

Common Steps for Both Reproduction Paths.

```bash
git clone <repository-url>
cd overflow-labs

# create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# create a local .env document (edit the values it lists before running the pipeline)
cp .env.example .env

# run the test suite
pytest -v
```

After the Common Setup, Pick One of the Two Reproduction Paths Below.

### Path A — Reproduce From Your Own Dump

For External Researchers Who Want to Regenerate the Parquet From Scratch.

1. Download the Stack Overflow Data Dump From Your SO Profile (Settings → Data Dump).
2. Place the `.7z` Under a Folder Containing a `raw/` Subdirectory; the Pipeline Writes Parquet to a Sibling `processed/`.
3. Set `DATA_DUMP` in `.env` to That Parent Folder.
4. Run the Ingestion (Expect ~3 Hours, Dominated by Posts).

```bash
python -m source.ingestion.pipeline
```

Result: Monthly-Partitioned Parquet Under `DATA_DUMP/processed/`.

### Path B — Team Fast Path

For Team Co-Authors Who Want the Already-Materialised Parquet Without Re-Running Ingestion.

1. Create a Personal Access Token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (Read Scope for Pull; Write Scope for Push).
2. Set `HF_TOKEN` in `.env`.
3. Pull the Parquet From the Team's Private Dataset Repo.

```bash
python -m source.cloud pull
```

Result: Parquet Cached Locally Under `~/.cache/huggingface/hub/datasets--outofaditya--overflow-labs-dump/...`.
