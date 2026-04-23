"""Structured logging to logs/scraper.log (INFO) and logs/errors.log (ERROR)."""

import logging
from pathlib import Path


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    info_h = logging.FileHandler(log_dir / "scraper.log", encoding="utf-8")
    info_h.setLevel(logging.INFO)
    info_h.setFormatter(fmt)

    err_h = logging.FileHandler(log_dir / "errors.log", encoding="utf-8")
    err_h.setLevel(logging.ERROR)
    err_h.setFormatter(fmt)

    con_h = logging.StreamHandler()
    con_h.setLevel(logging.INFO)
    con_h.setFormatter(fmt)

    root.addHandler(info_h)
    root.addHandler(err_h)
    root.addHandler(con_h)

    return root
