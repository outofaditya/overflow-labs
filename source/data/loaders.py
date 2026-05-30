from __future__ import annotations

import pandas as pd
from datetime import date
from source import constants
from source.logger import get_logger
from source.data.query import run_query

# initialize logger
log = get_logger(__name__)


# read a .sql file from commands/
def load_sql(name: str) -> str:
    path = constants.COMMANDS / name
    if not path.exists():
        raise FileNotFoundError(f"SQL File Not Found: {path}")
    return path.read_text()


# fetch questions posted on or after start
def fetch_questions(
    start: date | None = None, max_rows: int = 10_000_000
) -> pd.DataFrame:
    start = start or constants.START
    sql = load_sql("questions.sql")
    log.info("Fetching Questions From %s Onward", start)
    return run_query(sql, params={"start_date": start}, max_rows=max_rows)


# fetch answers posted on or after start
def fetch_answers(
    start: date | None = None, max_rows: int = 10_000_000
) -> pd.DataFrame:
    start = start or constants.START
    sql = load_sql("answers.sql")
    log.info("Fetching Answers From %s Onward", start)
    return run_query(sql, params={"start_date": start}, max_rows=max_rows)
