from __future__ import annotations

import sys
import time
import py7zr
import argparse
from lxml import etree
from pathlib import Path
from source import constants
from source.logger import get_logger

# initialize logger
log = get_logger(__name__)


# verify .xml files exist and are readable
def _verify_xml(xml_path: Path) -> None:
    if not xml_path.is_file():
        raise RuntimeError(f"Expected Output File Does Not Exist: {xml_path}")
    if xml_path.stat().st_size == 0:
        raise RuntimeError(f"Expected Output File Is Empty: {xml_path}")

    # stream the first few rows for verification
    found = False
    with xml_path.open("rb") as f:
        for _event, _elem in etree.iterparse(f, events=("start",), tag="row"):
            found = True
            break
    if not found:
        raise RuntimeError(f"No <row> Elements Found in {xml_path}")


# perform the extraction
def extract(archive: Path, out_dir: Path) -> Path:
    if not archive.is_file():
        raise RuntimeError(f"Expected Archive File Does Not Exist: {archive}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # peek inside the archive to get the file names
    with py7zr.SevenZipFile(archive, mode="r") as z:
        names = z.getnames()
    xml_names = [n for n in names if n.lower().endswith(".xml")]
    if not xml_names:
        raise RuntimeError(f"No .xml File Inside Archive: {archive}")

    outputs = [out_dir / n for n in xml_names]
    if all(p.is_file() and p.stat().st_size > 0 for p in outputs):
        log.info(f"Already Extracted: {archive.name} -> Skipping")
        return outputs[0]

    log.info(f"Extracting {archive.name} ({archive.stat().st_size / 1024**3:.2f} GiB)")
    start = time.monotonic()
    with py7zr.SevenZipFile(archive, mode="r") as z:
        z.extractall(path=out_dir)
    log.info(f"Extraction Complete: {archive.name} in {time.monotonic() - start:.1f} s")

    primary = outputs[0]
    _verify_xml(primary)
    log.info(
        f"Verified XML: {primary.name} ({primary.stat().st_size / 1024**3:.2f} GiB)"
    )
    return primary


# extract all archives
def extract_all() -> list[Path]:
    if constants.DATA_DUMP is None:
        raise RuntimeError("DATA_DUMP Not Configured in .env")
    raw = constants.RAW
    archives = sorted(raw.glob("*.7z"))

    if not archives:
        raise RuntimeError(f"No .7z Archives Found in {raw}")
    log.info(f"Found {len(archives)} .7z archives in {raw}")

    outputs: list[Path] = []
    for i, archive in enumerate(archives, start=1):
        log.info(f"[{i}/{len(archives)}] Extracting {archive.name}")
        outputs.append(extract(archive, out_dir=raw))
    return outputs


# main function
def main() -> int:
    p = argparse.ArgumentParser(description="Decompress Stack Exchange .7z archives.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--archive", help="Filename (Under DATA_DUMP/raw/) Of a Single .7z.")
    g.add_argument(
        "--all", action="store_true", help="Extract Every .7z Under DATA_DUMP/raw/."
    )
    args = p.parse_args()

    if args.all:
        extract_all()
    else:
        extract(constants.RAW / args.archive, out_dir=constants.RAW)
    return 0


if __name__ == "__main__":
    sys.exit(main())
