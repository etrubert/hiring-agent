"""YouTube scraper using yt-dlp (no API key required).

Two-phase per source:
  1. Flat listing (fast) to get video IDs + titles from a channel or search.
  2. Per-video fetch in parallel to pull the full description used by the classifier.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import yt_dlp

logger = logging.getLogger(__name__)

_FLAT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "ignoreerrors": True,
    "skip_download": True,
}

_VIDEO_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "ignoreerrors": True,
}


def _fetch_video(video_id: str) -> Optional[Dict]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(_VIDEO_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.debug("yt-dlp failed for %s: %s", video_id, exc)
        return None
    if not info:
        return None
    upload_date = info.get("upload_date", "") or ""
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return {
        "video_id": info.get("id", video_id),
        "url": info.get("webpage_url") or url,
        "title": info.get("title", "") or "",
        "description": info.get("description", "") or "",
        "channel_title": info.get("uploader") or info.get("channel") or "",
        "published_at": upload_date,
    }


def _list_entries(target_url: str, max_results: int) -> List[Dict]:
    opts = {**_FLAT_OPTS, "playlistend": max_results}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
    except Exception as exc:
        logger.warning("yt-dlp listing failed for %s: %s", target_url, exc)
        return []
    if not info:
        return []
    entries = info.get("entries") or []
    return [e for e in entries if e and e.get("id")][:max_results]


def _enrich_entries(entries: List[Dict], source_tag: str, max_workers: int = 6, extra: Optional[Dict] = None) -> List[Dict]:
    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_video, e["id"]): e for e in entries}
        for fut in as_completed(futures):
            video = fut.result()
            if not video:
                continue
            video["source_type"] = source_tag
            if extra:
                video.update(extra)
            results.append(video)
    return results


class YouTubeScraper:
    """yt-dlp backed scraper — no API key needed."""

    def __init__(self, api_key: Optional[str] = None, max_workers: int = 6):
        # api_key kept for signature compatibility; ignored.
        self.max_workers = max_workers

    def fetch_channel(self, handle: str, max_videos: int = 50) -> List[Dict]:
        handle = handle.strip()
        if handle.startswith("@"):
            url = f"https://www.youtube.com/{handle}/videos"
        elif handle.startswith("http"):
            url = handle
        else:
            url = f"https://www.youtube.com/channel/{handle}/videos"
        entries = _list_entries(url, max_videos)
        if not entries:
            logger.warning("no entries for channel %s", handle)
            return []
        return _enrich_entries(entries, source_tag="youtube_channel", max_workers=self.max_workers)

    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        target = f"ytsearch{max_results}:{query}"
        entries = _list_entries(target, max_results)
        if not entries:
            return []
        return _enrich_entries(
            entries,
            source_tag="youtube_search",
            max_workers=self.max_workers,
            extra={"query": query},
        )
