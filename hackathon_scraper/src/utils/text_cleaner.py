"""Minimal text normalization helpers used across scrapers and extractors."""

import html
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    return html.unescape(no_tags)


def normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not text:
        return ""
    text = strip_html(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    return _WHITESPACE_RE.sub(" ", text).strip()


def collapse(text: str) -> str:
    """Strip HTML but preserve case and accents."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", strip_html(text)).strip()
