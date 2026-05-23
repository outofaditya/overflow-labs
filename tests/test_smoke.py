import logging
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
