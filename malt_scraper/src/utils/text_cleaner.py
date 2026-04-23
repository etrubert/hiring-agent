"""Text normalization helpers for Malt-scraped content."""

import re
import unicodedata
from typing import Optional


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def lower_no_accent(s: Optional[str]) -> str:
    return strip_accents(normalize(s).lower())


def clean_name(s: Optional[str]) -> str:
    return normalize(s).strip(" .,-")


def clean_company(s: Optional[str]) -> str:
    if not s:
        return ""
    s = normalize(s)
    s = re.sub(r"\b(sas|sarl|sa|inc|ltd|llc|gmbh)\b\.?", "", s, flags=re.I)
    return s.strip(" .,-")
