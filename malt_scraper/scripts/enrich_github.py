"""Enrich Malt profiles with public GitHub data.

For every profile in data/final/malt-1.json that has a `github_url`:
  - fetch user metadata (bio, public_repos, followers)
  - fetch all non-fork repos, keep top 5 by stars

Uses GitHub's public REST API (no auth → 60 req/h rate limit; enough for ~30 users).
Output: data/final/github_profiles.json

Usage:
    python scripts/enrich_github.py
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402


def gh_api(path: str) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "User-Agent": "malt-scraper-github-enrich",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}", "_body": e.read().decode("utf-8", errors="ignore")[:200]}
    except Exception as e:
        return {"_error": str(e)}


def main() -> int:
    src = config.DATA_FINAL / "malt-1.json"
    data = json.loads(src.read_text(encoding="utf-8"))

    report = []
    for p in data["profiles"]:
        gh = (p.get("github_url") or "").strip()
        if not gh:
            continue
        user = gh.rstrip("/").split("/")[-1]
        u = gh_api(f"/users/{user}")
        if u.get("_error") or "login" not in u:
            report.append({
                "name": p["name"],
                "user": user,
                "url": gh,
                "error": u.get("_error") or u.get("message", "?"),
            })
            print(f"  ! {p['name']} ({user}): {u.get('_error') or u.get('message')}")
            continue
        repos = gh_api(f"/users/{user}/repos?per_page=100&sort=updated")
        if isinstance(repos, dict) and repos.get("_error"):
            repos = []
        own = [r for r in repos if isinstance(r, dict) and not r.get("fork")]
        own.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
        report.append({
            "name": p["name"],
            "user": user,
            "url": gh,
            "bio": u.get("bio") or "",
            "public_repos": u.get("public_repos"),
            "followers": u.get("followers"),
            "top_repos": [
                {
                    "name": r["name"],
                    "desc": (r.get("description") or "")[:120],
                    "stars": r.get("stargazers_count", 0),
                    "lang": r.get("language") or "",
                    "updated": (r.get("updated_at") or "")[:10],
                    "url": r.get("html_url", ""),
                }
                for r in own[:5]
            ],
        })
        print(f"  ✓ {p['name']} ({user}): {u.get('public_repos')} repos, {u.get('followers')} followers")
        time.sleep(0.5)

    out = config.DATA_FINAL / "github_profiles.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ wrote {out} ({len(report)} profiles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
