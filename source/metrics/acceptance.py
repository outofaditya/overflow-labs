from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# per-month median and p90 of time-to-acceptance in seconds
def monthly_time_to_acceptance(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        WITH accepted_pair AS (
            SELECT
                q.Id AS question_id,
                q.CreationDate AS question_created,
                a.CreationDate AS accepted_created
            FROM posts q
            JOIN posts a ON a.Id = q.AcceptedAnswerId
            WHERE q.PostTypeId = 1
              AND q.AcceptedAnswerId IS NOT NULL
              AND q.CreationDate >= $start_date
        )
        SELECT
            strftime(question_created, '%Y-%m') AS year_month,
            COUNT(*) AS accepted_count,
            MEDIAN(epoch(accepted_created - question_created)) AS median_seconds,
            QUANTILE_CONT(epoch(accepted_created - question_created), 0.9) AS p90_seconds
        FROM accepted_pair
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the acceptance-time series as a csv under results/tables
def write_acceptance_report() -> None:
    df = monthly_time_to_acceptance()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "time_to_acceptance.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_acceptance_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
