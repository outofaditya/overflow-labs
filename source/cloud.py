from __future__ import annotations

import sys
import argparse
from pathlib import Path
from source import constants
from source.logger import get_logger
from huggingface_hub import HfApi, create_repo, snapshot_download

# initialize logger
log = get_logger(__name__)

# files we want to ignore from the snapshot
IGNORE_PATTERNS = [".DS_Store", "*.tmp", "*.swp"]


# fail fast when token is missing
def _require_token() -> str:
    if not constants.HF_TOKEN:
        raise RuntimeError("HF_TOKEN Not Configured in .env")
    return constants.HF_TOKEN


# upload processed .parquet files to hugging face
def push_to_hf() -> None:
    token = _require_token()
    if constants.PROCESSED is None:
        raise RuntimeError("DATA_DUMP Not Set. Producer Mode Required For Push.")
    if not constants.PROCESSED.is_dir():
        raise RuntimeError(f"PROCESSED Directory Does Not Exist: {constants.PROCESSED}")
    log.info("Pushing %s to Hugging Face", constants.PROCESSED)

    # create a repository if it doesn't exist
    create_repo(
        token=token,
        private=True,
        exist_ok=True,
        repo_type="dataset",
        repo_id=constants.HF_REPO_ID,
    )
    api = HfApi(token=token)
    log.info("Uploading %s -> %s", constants.PROCESSED, constants.HF_REPO_ID)
    api.upload_large_folder(
        repo_type="dataset",
        repo_id=constants.HF_REPO_ID,
        ignore_patterns=IGNORE_PATTERNS,
        folder_path=str(constants.PROCESSED),
    )
    log.info("Upload Complete!")


# download the dataset from hugging face to local cache
def pull_from_hf() -> Path:
    token = _require_token()
    log.info("Pulling %s from Hugging Face", constants.HF_REPO_ID)
    local = snapshot_download(
        token=token,
        repo_type="dataset",
        repo_id=constants.HF_REPO_ID,
    )
    log.info("Pull Complete!")
    return Path(local)


# main function
def main() -> int:
    p = argparse.ArgumentParser(
        description="Sync The Stack Overflow Parquet Dataset With Hugging Face."
    )
    p.add_argument("action", choices=["push", "pull"])
    args = p.parse_args()

    if args.action == "push":
        push_to_hf()
    else:
        pull_from_hf()
    return 0


if __name__ == "__main__":
    sys.exit(main())
