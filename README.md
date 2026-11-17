# GTA 6 Giveaway Directory

Independent directory of active GTA 6 / GTA VI giveaways. Static site on GitHub Pages. An hourly GitHub Action finds, scores, re-checks and expires listings, and commits the result to `data/*.json`.

Live site (after you enable Pages): https://welshman.github.io/gta6-giveaway-directory/

## Deploy in 5 minutes
1. **Settings > Pages**: Source = *Deploy from a branch*, Branch = `main`, folder `/ (root)`.
2. **Settings > Actions > General > Workflow permissions**: choose *Read and write permissions*.
3. **Issues > Labels**: create two labels, `report` and `submission` (the site's Report and Suggest buttons use them).
4. **Settings > Secrets and variables > Actions > New repository secret**: add the keys below (all optional; a provider with no key is skipped and shown as "Skipped" on the Source status tab).
5. **Actions > Scan giveaways > Run workflow** to test. Tick *dry run* first if you like.
6. Clean out the demo listings: Actions > Moderate > action `purge-samples`.

## Secrets
| Secret | Used by | Notes |
|---|---|---|
| `BRAVE_API_KEY` | Brave Search | Main web discovery. Prepaid credits with a small free monthly credit. |
| `YOUTUBE_API_KEY` | YouTube Data API | Free quota 10,000 units/day. Each search costs 100 units, so keep `max_queries_per_run` at 2. |
| `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | Twitch Helix | Free. Register an app at dev.twitch.tv. |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Reddit API | Disabled by default. Reddit API access can need approval. |
| `X_BEARER_TOKEN` | X API | Disabled by default. Needs a paid tier with recent search. |
| `SERPER_API_KEY` | Serper (Google results) | Disabled by default. Third-party service; check its terms. |
| `DISCORD_WEBHOOK_URL` | Discord alerts | Posts newly published listings. |

Never put keys in the repo. Only reference them by name in `config/sources.json`.

## What runs automatically vs needs a human
- **Automatic**: Brave/SearXNG/Serper search, YouTube, Twitch, (Reddit/X if you add keys), RSS feeds, your watch list, ordinary public pages (robots.txt respected), Gleam-style landing pages, GitHub Issue submissions, expiry, archiving, duplicate removal, report counting, RSS feed output.
- **Human review**: anything scoring 40 to 69, every user submission, anything auto-hidden by reports.
- **Never fetched directly**: X, Instagram, TikTok, Facebook, Discord, Kick, and (for page fetches) Twitch, YouTube and Reddit. See `no_fetch_domains`. They are only found via search APIs or official APIs, and expire if no longer seen.

## Moderating
Public listings appear only when `status` is `Active`. Uncertain ones sit in `data/review-queue.json`.
- Locally: `python scripts/moderate.py list`, then `approve ID`, `reject ID`, `remove ID`, `edit ID field value`.
- From GitHub: Actions > Moderate > Run workflow, fill the inputs.
- Reports and suggestions arrive as GitHub Issues labelled `report` / `submission`. Two reports auto-hide a listing into the review queue (`auto_hide_after_reports`). Close the issue once handled.

## Adding things
- **Search query**: add a line to `web_queries` (or `api_queries` for YouTube/Reddit/Twitch) in `config/search-queries.json`.
- **Keyword / scam term**: edit `config/keywords.json`.
- **RSS feed**: add `{"name":..., "url":...}` to `providers.rss.feeds`.
- **Creator page, Linktree, Carrd, Discord invite page**: add the URL to `providers.watch.urls`.
- **Trusted or blocked domain**: `trusted_domains` / `blocked_domains` in `config/sources.json`, or use the moderation commands.
- **New search engine or API**: add a function with `@provider("name")` in `scripts/lib/providers.py` returning candidates (see `brave`), then add a block under `providers` in `config/sources.json`.
- **Schedule**: edit the `cron` line in `.github/workflows/scan-giveaways.yml`.
- **How long expired items stay**: `expiry.grace_hours` and `expiry.archive_delete_after_days`.

## Test locally
```
pip install -r requirements.txt
python scripts/scan.py --offline --dry-run     # no network, checks expiry logic
BRAVE_API_KEY=xxx python scripts/scan.py --dry-run
python -m http.server 8000                      # view the site at http://localhost:8000
```

## Staying compliant
- Use official APIs. Don't scrape X, Instagram, TikTok, Facebook, Discord or Kick pages.
- The scanner identifies itself with a User-Agent, obeys robots.txt (and skips a site if robots.txt can't be read), and waits between requests.
- Keep query counts low to stay inside quotas. A 429 response stops that provider for the run and shows on the status tab.
- Don't join Discord servers with bots or user tokens. Add public invite pages to the watch list only if their terms allow it.
- Google Custom Search JSON API is closed to new customers and Bing Search API was retired, so they are not included.

## Troubleshooting
- **Provider shows Skipped**: the secret is missing or misspelt (names must match exactly).
- **Push fails in the Action**: set workflow permissions to read and write.
- **Site shows the load error**: Pages not enabled, or `data/giveaways.json` is invalid JSON.
- **Nothing found**: check `data/discovery-log.json` for rejection reasons; lower `review_threshold` in `config/moderation.json`.
- **Scheduled runs stop**: GitHub pauses schedules on repos with no activity for 60 days. Re-enable under the Actions tab.
- **Report buttons say label not found**: create the `report` and `submission` labels.

This is an independent directory. It does not run giveaways and is not affiliated with Rockstar Games, Take-Two, or any platform.
