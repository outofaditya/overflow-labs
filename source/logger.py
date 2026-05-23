import sys
import logging

# time format
_FORMAT: str = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT: str = "%Y-%m-%d %H:%M:%S"
_configured: bool = False


# configuration
def _configure() -> None:
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))

    root = logging.getLogger()
    root.handlers.clear()  # drop duplicate handlers
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # silence chatty loggers
    for noisy in ("urllib3", "google.auth", "google.api_core"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


# instantiation
def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
