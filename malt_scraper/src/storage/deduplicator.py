"""Deduplicate profiles by profile_url."""

from typing import Any, Dict, Iterable, List


def dedupe(profiles: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for p in profiles:
        url = (p.get("profile_url") or "").split("?")[0].rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(p)
    return out
