"""Anti-detection helpers: UA rotation, gaussian delays, humanized scroll/click."""

import asyncio
import random
from typing import List, Optional

try:
    from fake_useragent import UserAgent
    _UA = UserAgent()
except Exception:
    _UA = None

_FALLBACK_UAS: List[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]


def random_user_agent() -> str:
    if _UA is not None:
        try:
            return _UA.random
        except Exception:
            pass
    return random.choice(_FALLBACK_UAS)


def random_viewport() -> dict:
    return random.choice(VIEWPORTS)


def gaussian_delay(min_s: float, max_s: float) -> float:
    mu = (min_s + max_s) / 2
    sigma = (max_s - min_s) / 4
    v = random.gauss(mu, sigma)
    return max(min_s, min(max_s, v))


async def sleep_random(min_s: float, max_s: float) -> None:
    await asyncio.sleep(gaussian_delay(min_s, max_s))


async def human_scroll(page, total_steps: int = 6) -> None:
    """Progressively scroll down with small pauses."""
    for _ in range(total_steps):
        delta = random.randint(300, 700)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.4, 1.2))


async def human_mouse_move(page, target_x: Optional[int] = None, target_y: Optional[int] = None) -> None:
    viewport = page.viewport_size or {"width": 1440, "height": 900}
    tx = target_x if target_x is not None else random.randint(100, viewport["width"] - 100)
    ty = target_y if target_y is not None else random.randint(100, viewport["height"] - 100)
    steps = random.randint(10, 25)
    await page.mouse.move(tx, ty, steps=steps)
    await asyncio.sleep(random.uniform(0.15, 0.5))
