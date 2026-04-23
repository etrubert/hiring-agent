"""Detect French hackathons: returns the French city name if the hackathon's
title/description/location/tags indicate it happens in France.

Conservative on purpose — false positives on "paris, texas" are filtered by
requiring either 'france' nearby or a less ambiguous French city.
"""

import re
from typing import Dict, Optional

_UNAMBIGUOUS_FR_CITIES = [
    "Paris",
    "Lyon",
    "Marseille",
    "Toulouse",
    "Bordeaux",
    "Lille",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Rennes",
    "Nice",
    "Grenoble",
    "Sophia Antipolis",
    "Sophia-Antipolis",
    "Station F",
    "La Defense",
    "La Défense",
    "Cergy",
    "Saclay",
    "Palaiseau",
    "Villeurbanne",
    "Aix-en-Provence",
    "Aix en Provence",
]

_AMBIGUOUS_FR_CITIES = [
    "Nice",  # Nice is also ambiguous (English word) but often a FR city in context
]

_FR_KEYWORDS = [
    r"\bfrance\b",
    r"\bîle[- ]de[- ]france\b",
    r"\bile[- ]de[- ]france\b",
]

_NON_FR_CITY_REGEX = re.compile(
    r"\b(berlin|london|new york|nyc|san francisco|sf|boston|seattle|austin|"
    r"tokyo|singapore|amsterdam|toronto|sydney|dubai|bangalore|mumbai|"
    r"los angeles|la |chicago|denver|miami|madrid|barcelona|rome|milan|"
    r"warsaw|prague|vienna|zurich|geneva|stockholm|oslo|copenhagen|helsinki|"
    r"tel aviv|melbourne|brisbane|hong kong)\b",
    re.IGNORECASE,
)

_CITY_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in _UNAMBIGUOUS_FR_CITIES) + r")\b",
    re.IGNORECASE,
)

_FRANCE_REGEX = re.compile("|".join(_FR_KEYWORDS), re.IGNORECASE)


def _clean_city(match: str) -> str:
    m = match.strip().title()
    # Normalize variants
    replacements = {
        "Sophia-Antipolis": "Sophia Antipolis",
        "La Defense": "La Défense",
        "Aix-En-Provence": "Aix-en-Provence",
        "Aix En Provence": "Aix-en-Provence",
    }
    return replacements.get(m, m)


def detect_french_city(hackathon: Dict) -> Optional[str]:
    """Return the French city name if confidently detected, else None.

    Strategy: we require either (a) the location field itself points to France,
    or (b) a French city appears AND no competing non-FR city dominates the
    description (to avoid 'engineers from France at a Berlin hackathon').
    """
    location = (hackathon.get("location") or "").strip()
    title = hackathon.get("title") or ""
    desc = hackathon.get("description") or ""
    tags = hackathon.get("tags_raw") or ""
    url = hackathon.get("url") or ""

    blob = " ".join([location, title, desc, tags, url])

    # 1. AI Tinkerers Paris URL is unambiguous (event domain IS the location)
    if "paris.aitinkerers.org" in url.lower():
        return "Paris"

    # 2. location field explicitly mentions France
    if re.search(r"\bfrance\b", location, re.IGNORECASE):
        city_m = _CITY_REGEX.search(location) or _CITY_REGEX.search(blob)
        if city_m:
            return _clean_city(city_m.group(1))
        return "France"

    # 3. location field names a French city
    city_in_loc = _CITY_REGEX.search(location)
    if city_in_loc:
        city = _clean_city(city_in_loc.group(1))
        # Paris ambiguity: only accept if no competing non-FR city in title/desc
        if city.lower() == "paris":
            title_desc = f"{title} {desc}"
            if re.search(r"\bparis,?\s*(tx|texas|kentucky|ontario|tennessee|ohio)\b", blob, re.IGNORECASE):
                return None
            return "Paris"
        return city

    # 4. Title/desc contains French city AND the 'France' marker AND no
    #    competing non-FR city is named in the location.
    city_in_blob = _CITY_REGEX.search(blob)
    has_france_marker = bool(_FRANCE_REGEX.search(blob))
    has_non_fr_city = bool(_NON_FR_CITY_REGEX.search(blob))

    if city_in_blob and has_france_marker and not has_non_fr_city:
        return _clean_city(city_in_blob.group(1))

    return None


def is_french(hackathon: Dict) -> bool:
    return detect_french_city(hackathon) is not None
