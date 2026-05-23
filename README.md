# From Crowd Knowledge to AI-Assisted Development: A Longitudinal Semantic Analysis of Stack Overflow After 2020

A Study of How Developer Behavior Shifted in the Generative-AI Era

## Repository Structure

- `source/` — Python Source (Importable + Testable)
- `commands/` — BigQuery Query Files
- `data/` — Raw and Processed Data (Regenerated from BigQuery)
- `notebooks/` — Exploratory Analysis
- `tests/` — Testing Suite
- `results/` — Figures and Tables That Back the Paper
- `options/` — YAML Configs (Tag Groups + Sampling Parameters + More)

## Project Settings

```bash
# clone and enter the repository
git clone <repository-url>
cd overflow-labs

# create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# configure credentials
cp .env.example .env
# edit your credentials
# place your token in credentials/service-account.json

# run the test suite
pytest -v
```
