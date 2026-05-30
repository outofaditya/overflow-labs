from __future__ import annotations

import sys
import duckdb
import argparse
import pandas as pd
from pathlib import Path
from source import constants
from source.logger import get_logger
from huggingface_hub import snapshot_download

# initialize logger
log = get_logger(__name__)

# expose tables as duck-db views
TABLES = ["posts", "users", "comments", "postlinks", "tags"]

# singleton connection per process
_conn: duckdb.DuckDBPyConnection | None = None


# decide on dataset root source
def _resolve_parquet_root() -> Path:
    # you are the producer and have the data locally
    if constants.PROCESSED is not None and constants.PROCESSED.is_dir():
        return constants.PROCESSED
    try:
        # you are the consumer and have pulled the data from hugging face
        cache = snapshot_download(
            repo_id=constants.HF_REPO_ID,
            repo_type="dataset",
            local_files_only=True,
            token=constants.HF_TOKEN,
        )
        return Path(cache)
    except Exception:
        raise RuntimeError(
            "No Parquet Available. Either Set DATA_DUMP (Path A) or Run `python -m source.cloud pull` (Path B)"
        )


# build a connection with one view per table
def _get_connection() -> duckdb.DuckDBPyConnection:
    global _conn

    # reuse the connection if present
    if _conn is not None:
        return _conn

    # resolve the parquet source and create a connection
    root = _resolve_parquet_root()
    log.info("Using Parquet From: %s", root)
    _conn = duckdb.connect()

    # create views: tables with no parquet on disk are skipped with a warning
    for table in TABLES:
        pattern = str(root / table / "year_month=*" / "data.parquet")
        try:
            _conn.execute(
                f"CREATE OR REPLACE VIEW {table} AS "
                f"SELECT * FROM read_parquet('{pattern}', union_by_name=true)"
            )
        except duckdb.Error as e:
            log.warning("No Parquet For %s: %s", table, e)
    log.info("DuckDB View Ready")
    return _conn


# run a parameterized analytical query and return a dataframe
def run_query(sql: str, params=None, max_rows: int = 10_000_000) -> pd.DataFrame:
    conn = _get_connection()
    bound = [] if params is None else params

    # soft cap: count first to avoid materializing too many rows (causes OOM)
    count = conn.execute(f"SELECT COUNT(*) FROM ({sql})", bound).fetchone()[0]
    if count > max_rows:
        raise RuntimeError(f"Query Would Return {count} Rows. Use A Lower Max.")
    df = conn.execute(sql, bound).fetch_df()
    log.info("Query Returned %d Rows, %d Columns", len(df), df.shape[1])
    return df


# main function
def main() -> int:
    p = argparse.ArgumentParser(
        description="Run an analytical SQL query against the parquet cache."
    )
    p.add_argument("sql", help="SQL query to execute (positional).")
    args = p.parse_args()
    df = run_query(args.sql)
    print(df.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
