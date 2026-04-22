# podcast_scraper

Scrape YouTube + podcast RSS feeds to find episodes where AI engineers are interviewed, extract guest names + social links, classify the guest's role with Claude, and export CSV/Excel/JSON.

## Setup

```bash
cd podcast_scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: ANTHROPIC_API_KEY, CLAUDE_MODEL (default claude-haiku-4-5)
```

- Anthropic API key: https://console.anthropic.com/settings/keys
- YouTube scraping uses `yt-dlp` — no API key required. (Rate limited by YouTube; expect the listing to be slower than the official API.)

## Run

```bash
# RSS only, no classification
python main.py --sources rss

# YouTube only (via yt-dlp, no key)
python main.py --sources youtube --max-per-channel 30

# Full pipeline: YouTube + RSS + Claude classification, AI-only final CSV
python main.py --sources youtube,rss --classify --ai-only \
  --output data/final/podcasts.csv --excel --json
```

### Main flags

- `--sources youtube,rss` — pick which collectors to run
- `--max-per-channel N` — cap videos pulled per YouTube channel (default 50)
- `--max-per-query N` — cap videos per YouTube search query
- `--max-per-feed N` — cap episodes per RSS feed
- `--classify` — run Claude classification (needs `ANTHROPIC_API_KEY`)
- `--ai-only` — keep only `is_ai_guest=True` rows in the final export
- `--output path.csv` — final CSV path
- `--excel` — also write `.xlsx` with a tab per role
- `--json` — also write `.json`

## Data layout

- `sources/youtube_channels.yaml` — channel handles + search queries
- `sources/rss_feeds.yaml` — RSS feed URLs
- `data/raw/` — raw scraped episodes (json)
- `data/processed/` — enriched + classified episodes (json, intermediate saves every 100)
- `data/final/` — final CSV / xlsx / json
- `logs/scraper_YYYY-MM-DD.log` — run log

## Output columns

`guest_name`, `role_detected`, `confidence`, `is_ai_guest`, `podcast_source`, `episode_title`, `episode_url`, `published_at`, `linkedin`, `twitter`, `github`, `website`, `source_type`, `description_snippet`, `reasoning`.

Roles: `AI Engineer`, `ML Engineer`, `AI Researcher`, `Agent Builder`, `LLM Engineer`, `AI Founder`, `AI Product Manager`, `AI Engineering Manager`, `Data Scientist`, `Other`.

## Cost

Classifier uses `claude-haiku-4-5` by default (~$1/M input, $5/M output). Each episode prompt ≈ 2–3k tokens in, 150 tokens out — budget ≈ $3 per 1000 episodes. Set `CLAUDE_MODEL=claude-sonnet-4-6` in `.env` if you want higher-quality classification at ~3x the cost.

The system prompt is cached (`cache_control: ephemeral`) — the per-call cost stays dominated by the unique episode content.
