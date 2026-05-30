from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# per-month fraction of questions with a non-null accepted_answer_id
def monthly_accepted_rate(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count,
            SUM(CASE WHEN AcceptedAnswerId IS NOT NULL THEN 1 ELSE 0 END)::DOUBLE
              / COUNT(*) AS accepted_rate
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the accepted-rate series as a csv under results/tables
def write_accepted_report() -> None:
    df = monthly_accepted_rate()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "accepted_rate.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_accepted_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
