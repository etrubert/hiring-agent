"""Deduplicate episodes on normalized guest name + URL."""

import re
import unicodedata
from typing import Dict, List


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[^\w\s]", "", name)
    return name.lower().strip()


def deduplicate(episodes: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for ep in episodes:
        guest_key = _normalize_name(ep.get("guest_name") or "")
        url_key = (ep.get("url") or "").split("?")[0].rstrip("/")
        key = (guest_key, url_key) if guest_key else ("", url_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(ep)
    return out
