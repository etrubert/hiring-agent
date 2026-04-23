"""Central config: env vars, paths, YAML loaders."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env", override=False)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "oui"}


SCRAPER_MODE = os.getenv("SCRAPER_MODE", "stealth").lower()
HEADLESS = _bool("HEADLESS", True)

DELAY_REQ_MIN = _int("DELAY_BETWEEN_REQUESTS_MIN", 3)
DELAY_REQ_MAX = _int("DELAY_BETWEEN_REQUESTS_MAX", 8)
DELAY_PAGE_MIN = _int("DELAY_BETWEEN_PAGES_MIN", 5)
DELAY_PAGE_MAX = _int("DELAY_BETWEEN_PAGES_MAX", 12)

MAX_PROFILES = _int("MAX_PROFILES", 100)
MAX_RETRIES = _int("MAX_RETRIES", 3)
PROXY_URL = os.getenv("PROXY_URL", "") or None

MALT_BASE_URL = "https://www.malt.fr"

SOURCES_DIR = BASE_DIR / "sources"
DATA_DIR = BASE_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_JSON = DATA_DIR / "json"
DATA_FINAL = DATA_DIR / "final"
DATA_SCREENSHOTS = DATA_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"

for d in (DATA_RAW, DATA_JSON, DATA_FINAL, DATA_SCREENSHOTS, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _load_yaml(name: str) -> Dict[str, Any]:
    with (SOURCES_DIR / name).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_roles() -> Dict[str, Any]:
    return _load_yaml("target_roles.yaml").get("roles", {})


def load_skills() -> Dict[str, Any]:
    data = _load_yaml("skills.yaml")
    return {
        "by_category": data.get("skills_by_category", {}),
        "min_match": int(data.get("min_skills_match", 2)),
    }


def load_competitors() -> Dict[str, Any]:
    return _load_yaml("competitors.yaml").get("mirakl_competitors", {})


def load_locations() -> Dict[str, Any]:
    data = _load_yaml("locations.yaml")
    return {
        "allowed": data.get("allowed_locations", {}),
        "remote_ok": bool(data.get("remote_ok", False)),
    }


def load_search_queries() -> Dict[str, Any]:
    data = _load_yaml("search_queries.yaml")
    return {
        "queries": data.get("search_queries", []),
        "max_per_query": int(data.get("max_profiles_per_query", 15)),
        "max_total": int(data.get("max_total_profiles", 100)),
    }
