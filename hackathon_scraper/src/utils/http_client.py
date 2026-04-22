"""Thin wrapper around requests with retries, a shared user-agent, and JSON helpers."""

import logging
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        }
    )
    return s


SESSION = _session()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.RequestException,)),
    reraise=True,
)
def get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> requests.Response:
    r = SESSION.get(url, params=params, headers=headers, timeout=config.HTTP_TIMEOUT)
    r.raise_for_status()
    return r


def get_json(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[dict]:
    try:
        r = get(url, params=params, headers=headers)
        return r.json()
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def get_html(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[str]:
    try:
        r = get(url, params=params, headers=headers)
        return r.text
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None
