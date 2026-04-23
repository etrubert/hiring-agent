"""Scan a freelance's missions to detect which of the 12 Mirakl competitors
they have worked for."""

from typing import Any, Dict, List, Tuple

from src.utils.text_cleaner import lower_no_accent


def detect_competitors(
    missions: List[Dict[str, Any]],
    bio: str,
    competitors: Dict[str, Dict[str, List[str]]],
) -> List[Tuple[str, List[str]]]:
    """Return [(competitor_key, [mission_titles_matched])...]."""
    out: List[Tuple[str, List[str]]] = []
    bio_norm = lower_no_accent(bio)
    for key, spec in competitors.items():
        needles = [lower_no_accent(n) for n in spec.get("names", [])]
        needles += [lower_no_accent(k) for k in spec.get("keywords", [])]
        needles = [n for n in needles if n]
        hits: List[str] = []
        for m in missions:
            haystack = lower_no_accent(
                f"{m.get('client_name', '')} {m.get('mission_title', '')} "
                f"{m.get('mission_description', '')} "
                f"{' '.join(m.get('technologies') or [])}"
            )
            if any(n in haystack for n in needles):
                hits.append(m.get("mission_title", "") or "(no title)")
        if not hits and any(n in bio_norm for n in needles):
            hits.append("(from bio)")
        if hits:
            out.append((key, hits))
    return out
