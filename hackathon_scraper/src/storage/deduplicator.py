"""Deduplicate hackathons across platforms."""

import logging
import re
from typing import Dict, List
from urllib.parse import urlparse

from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _canonical_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")
    path = re.sub(r"/+$", "", parsed.path or "")
    return f"{host}{path}"


def _key(ep: Dict) -> str:
    url_key = _canonical_url(ep.get("url") or "")
    if url_key:
        return f"url:{url_key}"
    title = normalize(ep.get("title") or "")
    start = (ep.get("start_date") or "")[:10]
    return f"t:{title}|{start}"


def deduplicate(hackathons: List[Dict]) -> List[Dict]:
    by_key: Dict[str, Dict] = {}
    for h in hackathons:
        k = _key(h)
        if not k or k == "t:|":
            continue
        if k not in by_key:
            by_key[k] = h
            continue
        existing = by_key[k]
        for field in ("description", "people", "companies", "tags_raw", "start_date", "end_date"):
            if not existing.get(field) and h.get(field):
                existing[field] = h[field]
        existing_sources = existing.setdefault("sources", [existing.get("source_platform")])
        if h.get("source_platform") and h["source_platform"] not in existing_sources:
            existing_sources.append(h["source_platform"])
    logger.info("deduplicate: %d -> %d", len(hackathons), len(by_key))
    return list(by_key.values())
