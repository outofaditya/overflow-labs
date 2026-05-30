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

# load environment variables
load_dotenv(ROOT / ".env")

# use configured external dump archive
_external = os.getenv("DATA_DUMP")
DATA_DUMP: Path | None = Path(_external).resolve() if _external else None

# data paths
DATA: Path | None = DATA_DUMP
RAW: Path | None = DATA_DUMP / "raw" if DATA_DUMP else None
PROCESSED: Path | None = DATA_DUMP / "processed" if DATA_DUMP else None

# results paths
RESULTS: Path = ROOT / "results"
FIGURES: Path = RESULTS / "figures"
TABLES: Path = RESULTS / "tables"

# analysis window
START: date = date(2020, 1, 1)
RELEASE: date = date(2022, 11, 30)

# sampling parameters
SAMPLES: int = 50_000
SEED: int = 42

# hugging face dataset identifiers
HF_TOKEN: str | None = os.getenv("HF_TOKEN")
HF_REPO_ID: str = os.getenv("HF_REPO_ID", "outofaditya/overflow-labs-dump")
