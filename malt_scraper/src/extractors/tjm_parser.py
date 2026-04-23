"""Parse TJM (tarif journalier) strings like '750 €/j' or '1 200 € / jour'."""

import re
from typing import Optional


def parse_tjm(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    clean = re.sub(r"[ \s]", " ", text)
    m = re.search(r"(\d[\d\s]{1,5})\s*€", clean)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    if not digits:
        return None
    try:
        v = int(digits)
    except ValueError:
        return None
    if 100 <= v <= 5000:
        return v
    return None
