from __future__ import annotations

import sys
import pandas as pd
from datetime import date
from source import constants
from source.logger import get_logger
from source.data.query import _resolve_parquet_root, run_query

# initialize logger
log = get_logger(__name__)

# tables with a creation date that qualify for date-range summary
TABLES_WITH_DATES = ["posts", "users", "comments", "postlinks"]
TABLES_FLAT = ["tags"]


# count partition directories on disk for a table
def _count_partitions(table: str) -> int:
    root = _resolve_parquet_root()
    return len(list((root / table).glob("year_month=*")))


# summarize a single table: row count, partitions, optional date range
def summarize_table(table: str, has_dates: bool = True) -> dict:
    log.info("Summarizing %s", table)
    row_count = run_query(f"SELECT COUNT(*) AS n FROM {table}")["n"].iloc[0]
    summary: dict = {
        "table": table,
        "row_count": int(row_count),
        "partitions": _count_partitions(table),
        "first_date": None,
        "last_date": None,
    }
    if has_dates:
        bounds = run_query(
            f"SELECT MIN(CreationDate) AS first, MAX(CreationDate) AS last FROM {table}"
        )
        summary["first_date"] = bounds["first"].iloc[0]
        summary["last_date"] = bounds["last"].iloc[0]
    return summary


# build the questions-per-month series and mark missing months as gaps
def questions_per_month(start: date | None = None) -> pd.DataFrame:
    start = start or constants.START
    df = run_query(
        """
        SELECT
            strftime(CreationDate, '%Y-%m') AS year_month,
            COUNT(*) AS question_count
        FROM posts
        WHERE PostTypeId = 1 AND CreationDate >= $start_date
        GROUP BY 1
        ORDER BY 1
        """,
        params={"start_date": start},
    )
    if df.empty:
        return df.assign(is_gap=[]).astype({"question_count": "int64"})

    # build a complete month index from start to the latest observed month
    expected = pd.date_range(
        start=pd.Timestamp(start),
        end=pd.Timestamp(df["year_month"].max() + "-01"),
        freq="MS",
    ).strftime("%Y-%m")
    full = pd.DataFrame({"year_month": expected})
    merged = full.merge(df, on="year_month", how="left").fillna({"question_count": 0})
    merged["question_count"] = merged["question_count"].astype(int)
    merged["is_gap"] = merged["question_count"] == 0
    return merged


# write the per-table summary and the monthly question series as csv files
def write_validation_report() -> None:
    rows = [summarize_table(t, has_dates=True) for t in TABLES_WITH_DATES]
    rows += [summarize_table(t, has_dates=False) for t in TABLES_FLAT]
    summary_df = pd.DataFrame(rows)
    monthly_df = questions_per_month()

    constants.TABLES.mkdir(parents=True, exist_ok=True)
    summary_path = constants.TABLES / "data_validation.csv"
    monthly_path = constants.TABLES / "posts_per_month.csv"

    summary_df.to_csv(summary_path, index=False)
    monthly_df.to_csv(monthly_path, index=False)

    gap_count = int(monthly_df["is_gap"].sum())
    log.info("Wrote %s (%d Tables)", summary_path.name, len(summary_df))
    log.info(
        "Wrote %s (%d Months, %d Gaps)", monthly_path.name, len(monthly_df), gap_count
    )


# main function
def main() -> int:
    write_validation_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
