"""Classify profile location into paris | bordeaux | other."""

from typing import Dict, Optional, Tuple

from src.utils.text_cleaner import lower_no_accent


def classify_location(location: str, allowed: Dict[str, list]) -> str:
    """Return 'paris', 'bordeaux', or 'other'."""
    if not location:
        return "other"
    loc = lower_no_accent(location)
    for bucket, tokens in allowed.items():
        for tok in tokens:
            if lower_no_accent(tok) in loc:
                return bucket
    return "other"


def is_allowed(location: str, allowed: Dict[str, list], remote_ok: bool = False) -> bool:
    bucket = classify_location(location, allowed)
    if bucket != "other":
        return True
    if remote_ok:
        t = lower_no_accent(location)
        if "teletravail" in t or "remote" in t:
            return True
    return False
