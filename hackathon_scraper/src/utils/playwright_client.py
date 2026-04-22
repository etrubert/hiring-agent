"""Optional Playwright helper. No-op unless playwright is installed.

We keep this as a stub so scrapers that would otherwise need a JS runtime
(Luma, LinkedIn, Meetup) can import it without a hard dependency.
"""

import logging

logger = logging.getLogger(__name__)


def is_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_rendered_html(url: str) -> str:
    if not is_available():
        logger.warning("playwright not installed — cannot render %s", url)
        return ""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)
            content = page.content()
            browser.close()
            return content
    except Exception as exc:
        logger.warning("playwright render failed for %s: %s", url, exc)
        return ""
