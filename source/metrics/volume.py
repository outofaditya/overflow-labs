from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# monthly counts of questions and answers from the posts table
def monthly_volume(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            SUM(CASE WHEN PostTypeId = 1 THEN 1 ELSE 0 END) AS question_count,
            SUM(CASE WHEN PostTypeId = 2 THEN 1 ELSE 0 END) AS answer_count
        FROM posts
        WHERE CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the monthly volume series as a csv under results/tables
def write_volume_report() -> None:
    df = monthly_volume()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "monthly_volume.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_volume_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
