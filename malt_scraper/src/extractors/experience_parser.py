"""Parse years of experience from free text."""

import re
from typing import Optional


_PATTERNS = [
    re.compile(r"(\d{1,2})\s*ans?\s+d['’]?\s*(?:expérience|experience|exp\.?)", re.I),
    re.compile(r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s*)?exp", re.I),
    re.compile(r"(\d{1,2})\s*\+?\s*(?:ans|years)", re.I),
]


def parse_years(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    for pat in _PATTERNS:
        m = pat.search(text)
        if m:
            try:
                v = int(m.group(1))
                if 0 < v < 60:
                    return v
            except ValueError:
                continue
    return None
