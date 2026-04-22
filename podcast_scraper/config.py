"""Central config loader — env vars, paths, role taxonomy."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(ROOT_DIR / ".env", override=False)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

MAX_PER_CHANNEL = int(os.getenv("MAX_PER_CHANNEL", "50"))
MAX_PER_QUERY = int(os.getenv("MAX_PER_QUERY", "50"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DATA_FINAL = BASE_DIR / "data" / "final"
LOG_DIR = BASE_DIR / "logs"
SOURCES_DIR = BASE_DIR / "sources"

for d in (DATA_RAW, DATA_PROCESSED, DATA_FINAL, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

ROLES = [
    "AI Engineer",
    "ML Engineer",
    "AI Researcher",
    "Agent Builder",
    "LLM Engineer",
    "AI Founder",
    "AI Product Manager",
    "AI Engineering Manager",
    "Data Scientist",
    "Other",
]

SAVE_EVERY_N = 100
