from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.query import run_query
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# monthly count of distinct non-anonymous askers (null owner_user_id is excluded)
def monthly_active_askers(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(DISTINCT OwnerUserId) AS distinct_askers
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    return df


# write the active-askers series as a csv under results/tables
def write_askers_report() -> None:
    df = monthly_active_askers()
    constants.TABLES.mkdir(parents=True, exist_ok=True)
    out = constants.TABLES / "active_askers.csv"
    df.to_csv(out, index=False)
    log.info("Wrote %s (%d Months)", out.name, len(df))


# main function
def main() -> int:
    write_askers_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
