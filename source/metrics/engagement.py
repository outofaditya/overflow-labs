from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# per-month mean score and mean comment count on questions
def monthly_engagement(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count,
            AVG(Score) AS mean_score,
            AVG(COALESCE(CommentCount, 0)) AS mean_comments
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the engagement series as a csv under results/tables
def write_engagement_report() -> None:
    df = monthly_engagement()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "engagement.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_engagement_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
