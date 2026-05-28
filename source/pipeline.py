from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path
from source import constants
import pyarrow.parquet as pq
from source.extract import extract
from source.logger import get_logger
from source.dump import SCHEMAS, convert

# initialize logger
log = get_logger(__name__)

ARCHIVE_TEMPLATE = "stackoverflow.com-{}.7z"
TABLE_ORDER = ["Tags", "PostLinks", "Users", "Comments", "Posts"]


# count total rows in all parquet partitions in an output dir
def _count_parquet_rows(out_dir: Path) -> int:
    return sum(
        pq.read_metadata(p).num_rows for p in out_dir.glob("year_month=*/data.parquet")
    )


# run full pipeline for a single table
def ingest_table(table: str, *, keep_archives: bool = False) -> None:
    if table not in SCHEMAS:
        raise ValueError(f"Unknown table: {table}")

    raw = constants.RAW
    archive = raw / ARCHIVE_TEMPLATE.format(table)
    out_dir = constants.PROCESSED / table.lower()
    success_marker = out_dir / "_SUCCESS"

    if success_marker.is_file():
        log.info("[%s] _Success Marker Present — Skipping", table)
        return

    if out_dir.is_dir() and any(out_dir.glob("year_month=*")):
        raise RuntimeError(
            f"[{table}] Output Dir Has Partitions But No _Success Marker. "
            f"Partial Run? Delete {out_dir} And Retry."
        )

    if not archive.is_file():
        raise RuntimeError(f"[{table}] Archive Missing: {archive}")

    log.info("=" * 60)
    log.info("[%s] Starting Ingestion", table)
    log.info("=" * 60)
    start = time.monotonic()

    xml_path = extract(archive, out_dir=raw)
    rows_written = convert(table, xml_path, out_dir)
    parquet_rows = _count_parquet_rows(out_dir)
    if parquet_rows != rows_written:
        raise RuntimeError(
            f"[{table}] Verification Failed: Convert Wrote {rows_written} Rows, "
            f"Parquet Contains {parquet_rows}"
        )
    log.info("[%s] Verified %d Rows In Parquet", table, parquet_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    success_marker.touch()

    if not keep_archives:
        log.info("[%s] Removing %s", table, xml_path.name)
        xml_path.unlink()
        log.info("[%s] Removing %s", table, archive.name)
        archive.unlink()

    elapsed = time.monotonic() - start
    log.info("[%s] Done In %.1f S (%.1f Min)", table, elapsed, elapsed / 60)


# run the pipeline for all tables in order
def ingest_all(*, keep_archives: bool = False) -> None:
    total_start = time.monotonic()
    for table in TABLE_ORDER:
        ingest_table(table, keep_archives=keep_archives)
    elapsed = time.monotonic() - total_start
    log.info("All Tables Done In %.1f S (%.1f Min)", elapsed, elapsed / 60)


# entry point for script
def main() -> int:
    p = argparse.ArgumentParser(description="Run the SE dump ingestion pipeline.")
    p.add_argument("--table", choices=TABLE_ORDER, help="Process only this table.")
    p.add_argument(
        "--keep-archives",
        action="store_true",
        help="Do not delete .xml and .7z after successful ingestion.",
    )
    args = p.parse_args()

    if args.table:
        ingest_table(args.table, keep_archives=args.keep_archives)
    else:
        ingest_all(keep_archives=args.keep_archives)
    return 0


if __name__ == "__main__":
    sys.exit(main())
