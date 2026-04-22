"""Extract guest name + social links from episode title/description."""

import re
from typing import Dict, List, Optional

GUEST_PATTERNS = [
    re.compile(r"\bwith\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE),
    re.compile(r"\bft\.?\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE),
    re.compile(r"\bfeaturing\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE | re.IGNORECASE),
    re.compile(r"\binterview\s+with\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE | re.IGNORECASE),
    re.compile(r"\binterview\s+avec\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE | re.IGNORECASE),
    re.compile(r"\bavec\s+([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE),
    re.compile(r"\bguest:\s*([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){0,3})", re.UNICODE | re.IGNORECASE),
    re.compile(r"^([A-Z][\w'\-\.]+(?:\s+[A-Z][\w'\-\.]+){1,3})\s*[–—-]\s+", re.UNICODE),
]

LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|pub|company)/[\w\-_/%\.]+", re.IGNORECASE)
TWITTER_RE = re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[\w_]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[\w\-]+(?:/[\w\-\.]+)?", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s\)]+", re.IGNORECASE)

NOISE_NAMES = {"Episode", "Podcast", "Season", "Part", "Interview", "Guest", "Host"}


def extract_guest_name(title: str, description: str = "") -> Optional[str]:
    for text in (title, description[:500]):
        if not text:
            continue
        for pattern in GUEST_PATTERNS:
            m = pattern.search(text)
            if m:
                name = m.group(1).strip().rstrip(".,;:")
                tokens = name.split()
                if any(t in NOISE_NAMES for t in tokens):
                    continue
                if len(tokens) < 2:
                    continue
                return name
    return None


def _first(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(0) if m else None


def _filter_website(urls: List[str]) -> Optional[str]:
    for u in urls:
        low = u.lower()
        if any(bad in low for bad in ("linkedin.com", "twitter.com", "x.com", "github.com", "youtube.com", "youtu.be", "spotify.com", "apple.com/podcast")):
            continue
        return u
    return None


def extract_links(text: str) -> Dict[str, Optional[str]]:
    if not text:
        return {"linkedin": None, "twitter": None, "github": None, "website": None}
    all_urls = URL_RE.findall(text)
    return {
        "linkedin": _first(LINKEDIN_RE, text),
        "twitter": _first(TWITTER_RE, text),
        "github": _first(GITHUB_RE, text),
        "website": _filter_website(all_urls),
    }


def extract_all(episode: Dict) -> Dict:
    title = episode.get("title", "")
    description = episode.get("description", "")
    combined = f"{title}\n{description}"
    guest = extract_guest_name(title, description)
    links = extract_links(combined)
    episode_out = dict(episode)
    episode_out["guest_name"] = guest
    episode_out["linkedin"] = links["linkedin"]
    episode_out["twitter"] = links["twitter"]
    episode_out["github"] = links["github"]
    episode_out["website"] = links["website"]
    return episode_out
