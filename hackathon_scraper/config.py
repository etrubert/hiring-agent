"""Paths, env, and global knobs for the hackathon scraper."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env", override=False)

SOURCES_DIR = BASE_DIR / "sources"
DATA_DIR = BASE_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_FILTERED = DATA_DIR / "filtered"
DATA_FINAL = DATA_DIR / "final"
DATA_CACHE = DATA_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"

for d in (DATA_RAW, DATA_FILTERED, DATA_FINAL, DATA_CACHE, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_TOKEN", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "hackathon_scraper/0.1")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
)
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MIN_RELEVANCE_SCORE = int(os.getenv("MIN_RELEVANCE_SCORE", "30"))

TARGET_ROLES = [
    "Agent Builder",
    "AI Engineering Manager",
    "Senior AI Engineer",
    "Senior Data Scientist",
]
