"""Playwright stealth session for Malt.fr.

Handles cookie banner and exposes a single `new_page` helper that returns a
stealth-enabled page with a fresh User-Agent + viewport.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

try:
    from playwright_stealth import stealth_async  # type: ignore
    _HAS_STEALTH = True
except Exception:
    _HAS_STEALTH = False

from src.utils.anti_detection import random_user_agent, random_viewport, sleep_random

logger = logging.getLogger(__name__)


class MaltSession:
    def __init__(self, headless: bool = True, proxy_url: Optional[str] = None) -> None:
        self.headless = headless
        self.proxy_url = proxy_url
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        launch_kwargs = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ],
        }
        if self.proxy_url:
            launch_kwargs["proxy"] = {"server": self.proxy_url}
        self._browser = await self._pw.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(
            user_agent=random_user_agent(),
            viewport=random_viewport(),
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        if not _HAS_STEALTH:
            logger.warning("playwright-stealth not installed — running without stealth patches")

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Page]:
        assert self._context is not None, "call start() first"
        page = await self._context.new_page()
        if _HAS_STEALTH:
            try:
                await stealth_async(page)
            except Exception as exc:
                logger.warning("stealth_async failed: %s", exc)
        try:
            yield page
        finally:
            await page.close()

    async def accept_cookies(self, page: Page) -> None:
        """Click the Malt cookie banner if present."""
        selectors = [
            "button#axeptio_btn_acceptAll",
            "button:has-text('Tout accepter')",
            "button:has-text('Accepter')",
            "button[data-testid='cookie-accept']",
        ]
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    logger.info("cookies accepted via %s", sel)
                    await sleep_random(1, 2)
                    return
            except Exception:
                continue


async def smoke_test(screenshots_dir) -> bool:
    """Load https://www.malt.fr and screenshot — validates stealth vs Cloudflare."""
    session = MaltSession(headless=True)
    await session.start()
    try:
        async with session.new_page() as page:
            logger.info("smoke: loading https://www.malt.fr")
            await page.goto("https://www.malt.fr", timeout=60000, wait_until="domcontentloaded")
            await sleep_random(3, 5)
            await session.accept_cookies(page)
            out = screenshots_dir / "smoke_homepage.png"
            await page.screenshot(path=str(out), full_page=False)
            logger.info("smoke: screenshot saved to %s", out)
            title = await page.title()
            logger.info("smoke: page title = %r", title)
            return "malt" in (title or "").lower()
    finally:
        await session.close()
