"""Shared logging setup."""

import logging
from datetime import datetime

import config


def setup_logging() -> None:
    log_path = config.LOG_DIR / f"hackathon_scraper_{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
