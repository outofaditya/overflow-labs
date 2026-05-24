import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# instantiate logger
log = get_logger(__name__)


# load the query text from the files
def load_sql(name: str) -> str:
    path = constants.COMMANDS / name
    if not path.exists():
        raise FileNotFoundError(f"Query File Not Found: {path}")
    return path.read_text()


# fetch questions
def fetch_questions(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    sql = load_sql("questions.sql")
    log.info(f"Fetching Questions: From {start}")
    return run_query(sql, {"start_date": start})
