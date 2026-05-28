import os
import pytest
import logging
from pathlib import Path
from datetime import date
from source import constants
from source.logger import get_logger


def test_root_resolves_to_repo() -> None:
    assert constants.ROOT.is_dir()
    assert (constants.ROOT / "pyproject.toml").is_file()


def test_analysis_window_ordering() -> None:
    assert isinstance(constants.START, date)
    assert isinstance(constants.RELEASE, date)
    assert constants.START < constants.RELEASE


def test_sampling_constants_sane() -> None:
    assert constants.SAMPLES > 0
    assert constants.SEED >= 0


def test_logger_returns_logger_instance() -> None:
    log = get_logger("smoke")
    assert isinstance(log, logging.Logger)
    assert log.name == "smoke"


def test_data_paths_have_expected_names() -> None:
    assert constants.RAW.name == "raw"
    assert constants.PROCESSED.name == "processed"
    assert isinstance(constants.DATA, Path)


def test_data_dump_readable_when_set() -> None:
    if constants.DATA_DUMP is None:
        pytest.skip("DATA_DUMP Not Configured in .env")
    assert (
        constants.DATA_DUMP.is_dir()
    ), f"DATA_DUMP Does Not Exist: {constants.DATA_DUMP}"
    assert os.access(
        constants.DATA_DUMP, os.R_OK
    ), f"DATA_DUMP Not Readable: {constants.DATA_DUMP}"


def test_hf_repo_id_is_set() -> None:
    assert isinstance(constants.HF_REPO_ID, str)
    assert "/" in constants.HF_REPO_ID


def test_hf_token_optional() -> None:
    assert constants.HF_TOKEN is None or isinstance(constants.HF_TOKEN, str)
