from __future__ import annotations

import sys
import yaml
import hashlib
from pathlib import Path
from source import constants
from source.logger import get_logger
from datetime import datetime, timezone

# initialize logger
log = get_logger(__name__)

# streaming chunk size: 1MiB
CHUNK_SIZE: int = 1024 * 1024


# stream a file and compute the checksum
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    total = path.stat().st_size
    read = 0
    next_progress = 0.05  # log every 5 percent

    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
            read += len(chunk)
            if total > 0 and read / total >= next_progress:
                log.info(f"Hashing {path.name}: {read / total:.0%}")
                next_progress += 0.05
    return h.hexdigest()


# build a manifest
def build_manifest() -> dict:
    # check for configuration of dump archive
    if constants.DATA_DUMP is None:
        raise RuntimeError("DATA_DUMP Not Configured in .env")
    # check for raw data directory
    raw = constants.RAW
    if not raw.is_dir():
        raise RuntimeError(f"RAW Directory Does Not Exist: {raw}")
    # check for .7z archives
    archives = sorted(raw.glob("*.7z"))
    if not archives:
        raise RuntimeError(f"No .7z Archives Found in {raw}")
    log.info(f"Found {len(archives)} .7z archives in {raw}")

    files: list[dict] = []
    for archive in archives:
        size_gib = archive.stat().st_size / 1024**3
        log.info(f"Processing {archive.name} ({size_gib:.1f} GiB)")
        files.append(
            {
                "name": archive.name,
                "size_bytes": archive.stat().st_size,
                "sha256": sha256_of(archive),
                "downloaded_at": datetime.fromtimestamp(
                    archive.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )

    return {
        "manifest_generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


# main function
def main() -> int:
    manifest = build_manifest()
    out = constants.TABLES / "manifest.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, default_flow_style=False)
    log.info(f"Manifest written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
