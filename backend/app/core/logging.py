import logging
import sys

LOGGER_NAME = "interview"


def setup_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
