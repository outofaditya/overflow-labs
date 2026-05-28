from __future__ import annotations

import sys
import time
import argparse
import pyarrow as pa
from lxml import etree
from pathlib import Path
import pyarrow.parquet as pq
from datetime import datetime
from collections import defaultdict
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)

# per-table schema from dump
SCHEMAS: dict[str, pa.Schema] = {
    "Posts": pa.schema(
        [
            ("Id", pa.int64()),
            ("PostTypeId", pa.int32()),
            ("AcceptedAnswerId", pa.int64()),
            ("ParentId", pa.int64()),
            ("CreationDate", pa.timestamp("us")),
            ("Score", pa.int32()),
            ("ViewCount", pa.int32()),
            ("Body", pa.string()),
            ("OwnerUserId", pa.int64()),
            ("LastEditorUserId", pa.int64()),
            ("LastEditDate", pa.timestamp("us")),
            ("LastActivityDate", pa.timestamp("us")),
            ("Title", pa.string()),
            ("Tags", pa.string()),
            ("AnswerCount", pa.int32()),
            ("CommentCount", pa.int32()),
            ("FavoriteCount", pa.int32()),
            ("ClosedDate", pa.timestamp("us")),
            ("ContentLicense", pa.string()),
        ]
    ),
    "Users": pa.schema(
        [
            ("Id", pa.int64()),
            ("Reputation", pa.int32()),
            ("CreationDate", pa.timestamp("us")),
            ("DisplayName", pa.string()),
            ("LastAccessDate", pa.timestamp("us")),
            ("Location", pa.string()),
            ("AboutMe", pa.string()),
            ("Views", pa.int32()),
            ("UpVotes", pa.int32()),
            ("DownVotes", pa.int32()),
            ("AccountId", pa.int64()),
        ]
    ),
    "Comments": pa.schema(
        [
            ("Id", pa.int64()),
            ("PostId", pa.int64()),
            ("Score", pa.int32()),
            ("Text", pa.string()),
            ("CreationDate", pa.timestamp("us")),
            ("UserId", pa.int64()),
            ("UserDisplayName", pa.string()),
            ("ContentLicense", pa.string()),
        ]
    ),
    "PostLinks": pa.schema(
        [
            ("Id", pa.int64()),
            ("CreationDate", pa.timestamp("us")),
            ("PostId", pa.int64()),
            ("RelatedPostId", pa.int64()),
            ("LinkTypeId", pa.int32()),
        ]
    ),
    "Tags": pa.schema(
        [
            ("Id", pa.int64()),
            ("TagName", pa.string()),
            ("Count", pa.int32()),
            ("ExcerptPostId", pa.int64()),
            ("WikiPostId", pa.int64()),
        ]
    ),
}

# choose columns to drive partitioning
PARTITION_COLUMN: dict[str, str | None] = {
    "Posts": "CreationDate",
    "Users": "CreationDate",
    "Comments": "CreationDate",
    "PostLinks": "CreationDate",
    "Tags": None,
}


# convert .xml attributes to pyarrow fields
def _coerce_row(table: str, attribs: dict[str, str]) -> dict:
    out: dict = {}
    for field in SCHEMAS[table]:
        col = field.name
        val = attribs.get(col)
        if val is None or val == "":
            out[col] = None
        elif pa.types.is_integer(field.type):
            out[col] = int(val)
        elif pa.types.is_timestamp(field.type):
            out[col] = datetime.fromisoformat(val)
        else:
            out[col] = val
    return out


# derive the year_month key for a row
def _partition_of(row: dict, partition_col: str | None) -> str:
    if partition_col is None:
        return "all"
    val = row.get(partition_col)
    if val is None:
        return "unknown"
    # val is a datetime here (already coerced); format as YYYY-MM
    return val.strftime("%Y-%m")


# flush one partition batch to writer (lazy opening)
def _flush(
    partition: str, rows: list[dict], writers: dict, table: str, out_dir: Path
) -> None:
    if not rows:
        return
    schema = SCHEMAS[table]
    arrow_table = pa.Table.from_pylist(rows, schema=schema)
    # lazy opening of writer for this partition
    if partition not in writers:
        part_dir = out_dir / f"year_month={partition}"
        part_dir.mkdir(parents=True, exist_ok=True)
        writers[partition] = pq.ParquetWriter(
            part_dir / "data.parquet", schema=schema, compression="zstd"
        )
    writers[partition].write_table(arrow_table)


# main streamer function
def convert(table: str, xml_path: Path, out_dir: Path, batch_size: int = 10_000) -> int:
    if table not in SCHEMAS:
        raise ValueError(f"Unknown table: {table}; expected one of {sorted(SCHEMAS)}")
    if not xml_path.is_file():
        raise RuntimeError(f"XML not found: {xml_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    partition_col = PARTITION_COLUMN[table]

    log.info("Converting %s -> %s (Batch=%d)", xml_path.name, out_dir, batch_size)
    start = time.monotonic()

    batches: dict[str, list[dict]] = defaultdict(list)
    writers: dict[str, pq.ParquetWriter] = {}
    total = 0

    try:
        ctx = etree.iterparse(str(xml_path), events=("end",), tag="row")
        # parse the xml file and convert to pyarrow fields
        for _event, elem in ctx:
            row = _coerce_row(table, dict(elem.attrib))
            partition = _partition_of(row, partition_col)
            batches[partition].append(row)
            total += 1

            if len(batches[partition]) >= batch_size:
                _flush(partition, batches[partition], writers, table, out_dir)
                batches[partition].clear()

            # release memory: clear this row, drop already-processed siblings
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

            if total % 1_000_000 == 0:
                log.info("  %s ... %d rows processed", table, total)

        # final flush of any leftovers in each partition
        for partition, rows in list(batches.items()):
            if rows:
                _flush(partition, rows, writers, table, out_dir)
                rows.clear()
    finally:
        for w in writers.values():
            w.close()

    log.info(
        "Wrote %d Rows Across %d Partitions in %.1f s",
        total,
        len(writers),
        time.monotonic() - start,
    )
    return total


# main function
def main() -> int:
    p = argparse.ArgumentParser(
        description="Stream Stack Exchange .xml Tables Into Partitioned Parquet."
    )
    p.add_argument("--table", required=True, choices=sorted(SCHEMAS))
    p.add_argument(
        "--xml", required=True, type=Path, help="Path To The Source .xml File"
    )
    p.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output Directory For Partitioned Parquet",
    )
    p.add_argument("--batch-size", type=int, default=10_000)
    args = p.parse_args()
    convert(args.table, args.xml, args.out, batch_size=args.batch_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
