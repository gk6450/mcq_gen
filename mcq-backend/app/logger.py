import logging
import os
from logging import StreamHandler, Formatter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGGER_NAME = "mcq_gen"

def configure_logging():
    """
    Configure a root logger for the application. Call once at startup.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        # already configured
        return logger

    logger.setLevel(LOG_LEVEL)
    handler = StreamHandler()
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    handler.setFormatter(Formatter(fmt))
    logger.addHandler(handler)
    # avoid duplicate logs for uvicorn/root
    logger.propagate = False
    return logger

def get_logger():
    return logging.getLogger(LOGGER_NAME)
