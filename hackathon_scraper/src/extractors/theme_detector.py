"""Decide whether a hackathon's theme is AI/ML based on its title+description."""

import logging
from pathlib import Path
from typing import Dict, List

import yaml

import config
from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _load_keywords() -> Dict[str, List[str]]:
    path: Path = config.SOURCES_DIR / "theme_keywords.yaml"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "ai": [k.lower() for k in data.get("ai_keywords", [])],
        "non_ai": [k.lower() for k in data.get("non_ai_keywords", [])],
    }


_KW = _load_keywords()


def ai_keyword_hits(text: str) -> List[str]:
    if not text:
        return []
    n = normalize(text)
    padded = f" {n} "
    hits: List[str] = []
    for kw in _KW["ai"]:
        needle = f" {kw} "
        if needle in padded and kw not in hits:
            hits.append(kw)
    return hits


def non_ai_hits(text: str) -> List[str]:
    if not text:
        return []
    n = normalize(text)
    padded = f" {n} "
    return [kw for kw in _KW["non_ai"] if f" {kw} " in padded]


def theme_is_ai(text: str) -> bool:
    hits = ai_keyword_hits(text)
    if hits:
        return True
    return False
