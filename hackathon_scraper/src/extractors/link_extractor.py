"""Extract social / profile URLs from arbitrary HTML or text."""

import re
from typing import Dict, List
from urllib.parse import urlparse

_URL_RE = re.compile(r"https?://[^\s'\"<>)]+", re.IGNORECASE)

_SOCIAL_DOMAINS = {
    "linkedin": ("linkedin.com",),
    "twitter": ("twitter.com", "x.com"),
    "github": ("github.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "discord": ("discord.gg", "discord.com"),
}


def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    return list(dict.fromkeys(_URL_RE.findall(text)))


def classify_social(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for label, domains in _SOCIAL_DOMAINS.items():
        if any(host.endswith(d) for d in domains):
            return label
    return "website"


def extract_socials(text: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for url in extract_urls(text):
        label = classify_social(url)
        found.setdefault(label, url)
    return found
