import os
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# general paths
ROOT: Path = Path(__file__).resolve().parent.parent
SOURCE: Path = ROOT / "source"
COMMANDS: Path = ROOT / "commands"
OPTIONS: Path = ROOT / "options"
NOTEBOOKS: Path = ROOT / "notebooks"
TESTS: Path = ROOT / "tests"

# data paths
DATA: Path = ROOT / "data"
RAW: Path = DATA / "raw"
PROCESSED: Path = DATA / "processed"

# results paths
RESULTS: Path = ROOT / "results"
FIGURES: Path = RESULTS / "figures"
TABLES: Path = RESULTS / "tables"

# load environment variables
load_dotenv(ROOT / ".env")

# analysis window
START: date = date(2020, 1, 1)
RELEASE: date = date(2022, 11, 30)

# bigquery window
DATASET: str = "bigquery-public-data.stackoverflow"
PROJECT: str | None = os.getenv("GCP_PROJECT")
BILLING: int = 50 * 1024**3  # 50 GiB

# sampling parameters
SAMPLES: int = 50_000
SEED: int = 42