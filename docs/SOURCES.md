# Sources the scanner uses

Last reviewed: 17 Nov 2026. Platforms change their rules often, so recheck before relying on any of these.

## Runs with no keys (already enabled)
| Source | How | Notes |
|---|---|---|
| `config/curated.json` | Hand-picked | Published instantly. Currently Kick's Sunset Reward Case and GTA BOOM's launch-day draw. |
| GamerPower RSS (all, PlayStation, Xbox) | RSS | Giveaway aggregator. Publishes official RSS feeds. |
| Reddit subreddit RSS (r/giveaways, r/GrandTheftAutoVI, r/GamesGiveaway, r/FreeGameFindings, r/GiftofGames, r/giveawaysforgaming, r/FreeGameGiveaway, r/steam_giveaway, r/RandomActsOfGaming) + 3 search feeds | RSS | Reddit may block or rate-limit GitHub's servers. If the Status tab shows no results, use the Reddit API provider instead. |
| Mastodon hashtag RSS (#gta6, #gtavi, #gta6giveaway, #giveaway, #giveaways) | RSS | Every public Mastodon hashtag has a feed. Add more instances in `sources.json`. |
| Gaming news RSS (PC Gamer, Kotaku, Polygon, RPS, Eurogamer, GamesRadar, PlayStation Blog, Xbox Wire, Ars Technica Gaming, Gamer Guides GTA VI hub) | RSS | `review_only`: an article about a giveaway is not the giveaway, so these go to the review queue and a moderator fixes the link. |
| Watch list (GTA BOOM, TheGiveaway.com, GamerPower) | Polite page reads | robots.txt respected. |

## Needs an API key
| Source | Secret(s) | Cost / limits |
|---|---|---|
| Brave Search (~100 queries incl. site: and 15 languages) | `BRAVE_API_KEY` | About $5 per 1,000 searches, with $5 free credit each month. |
| YouTube Data API | `YOUTUBE_API_KEY` | Free quota; each search uses 100 of 10,000 daily units. |
| Twitch Helix | `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | Free. |
| Reddit API (disabled) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Free tier needs approval. |
| Bluesky (disabled, experimental) | `BSKY_HANDLE`, `BSKY_APP_PASSWORD` | Post search needs a logged-in session. Use an App Password. |
| X API (disabled) | `X_BEARER_TOKEN` | Paid tier. |
| Serper (disabled) | `SERPER_API_KEY` | Paid third-party Google results. |

## Not scanned directly
Kick (no public search; found via Brave `site:kick.com` and the curated list), Discord, Instagram, TikTok, Facebook, Threads, Telegram. Their terms restrict scraping. They appear only if a search API returns them.

## Adding more
See the README section "Adding things". Put verified hand-picked giveaways in `config/curated.json`.
