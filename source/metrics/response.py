from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# per-month median and p90 of time-to-first-answer in seconds
def monthly_time_to_first_answer(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        WITH first_answer AS (
            SELECT
                q.Id AS question_id,
                q.CreationDate AS question_created,
                MIN(a.CreationDate) AS first_answered
            FROM posts q
            JOIN posts a ON a.ParentId = q.Id
            WHERE q.PostTypeId = 1
              AND a.PostTypeId = 2
              AND q.CreationDate >= $start_date
            GROUP BY q.Id, q.CreationDate
        )
        SELECT
            strftime(question_created, '%Y-%m') AS year_month,
            COUNT(*) AS answered_count,
            MEDIAN(epoch(first_answered - question_created)) AS median_seconds,
            QUANTILE_CONT(epoch(first_answered - question_created), 0.9) AS p90_seconds
        FROM first_answer
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the response-time series as a csv under results/tables
def write_response_report() -> None:
    df = monthly_time_to_first_answer()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "time_to_first_answer.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_response_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
