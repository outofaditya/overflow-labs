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
def extract(
    archive: Path,
    out_dir: Path,
    targets: list[str] | None = None,
) -> Path:
    if not archive.is_file():
        raise RuntimeError(f"Expected Archive File Does Not Exist: {archive}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # peek inside the archive to get the file names
    with py7zr.SevenZipFile(archive, mode="r") as z:
        names = z.getnames()

    # pick which files to pull based on targets
    if targets is None:
        wanted = [n for n in names if n.lower().endswith(".xml")]
    else:
        missing = [t for t in targets if t not in names]
        if missing:
            raise RuntimeError(f"Targets Not Found In Archive: {missing}")
        wanted = list(targets)
    if not wanted:
        raise RuntimeError(f"No Matching Files Inside Archive: {archive}")

    outputs = [out_dir / n for n in wanted]
    if all(p.is_file() and p.stat().st_size > 0 for p in outputs):
        log.info(f"Already Extracted: {archive.name} -> Skipping")
        return outputs[0]

    log.info(
        f"Extracting {archive.name} ({archive.stat().st_size / 1024**3:.2f} GiB) Targets={wanted}"
    )
    start = time.monotonic()
    with py7zr.SevenZipFile(archive, mode="r") as z:
        z.extract(targets=wanted, path=out_dir)
    log.info(f"Extraction Complete: {archive.name} in {time.monotonic() - start:.1f} s")

    primary = outputs[0]
    _verify_xml(primary)
    log.info(
        f"Verified XML: {primary.name} ({primary.stat().st_size / 1024**3:.2f} GiB)"
    )
    return primary


# main function
def main() -> int:
    p = argparse.ArgumentParser(description="Decompress Stack Exchange .7z archives.")
    p.add_argument(
        "--archive",
        required=True,
        help="Filename (Under DATA_DUMP/raw/) Of The .7z Archive.",
    )
    p.add_argument(
        "--targets",
        help="Comma-Separated Filenames Inside The Archive To Extract.",
    )
    args = p.parse_args()

    targets = args.targets.split(",") if args.targets else None
    extract(constants.RAW / args.archive, out_dir=constants.RAW, targets=targets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
