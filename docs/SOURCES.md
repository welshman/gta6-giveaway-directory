# Sources the scanner uses

Last reviewed: 17 Nov 2026. Platforms change their rules often. Failed sources show on the site's Status tab.

## How config is organised
Base files live in `config/`. Any file named `config/NAME-something.json` (for example `sources-extra-regional.json`) is merged into `config/NAME.json` automatically: lists are added to, objects are merged, plain values are overridden. Add new feeds, queries, keywords and curated giveaways in small extra files and never touch the base ones. This works for `sources`, `search-queries`, `keywords` and `curated`.

## Runs with no keys (enabled)
- **Curated** (`config/curated*.json`): hand-picked, published instantly. Remove an entry when it ends if it has no end date.
- **GamerPower RSS** (all, PlayStation, Xbox, Steam).
- **Reddit RSS**: 16 giveaway and GTA subreddits (including GTAVI, GTA6, gta6_official, pcgiveaways, sweepstakes, GiveawaysOnDiscord, xboxgiveaways, freebies), five search feeds, five in-subreddit searches. Reddit may block GitHub's servers.
- **Steam group RSS**: GrabFreeGames, FREE GAMES! GIVEAWAYS!, IndieGala.
- **Mastodon hashtag RSS** on three instances.
- **Lemmy search** on three instances (experimental).
- **MoneySavingExpert Competitions Time** feeds (address guessed, check Status).
- **News RSS** (review queue only): PC Gamer, Kotaku, Polygon, RPS, Eurogamer, GamesRadar, PlayStation Blog, Xbox Wire, Ars Technica, Gamer Guides.
- **Watch list with link-following** (reads the page, checks only links that mention GTA 6 / GTA VI):
  - Global: TheGiveaway, GamerPower, Gleam, GiveOwl, Sweepstakes Radar, Sweeties Sweeps, Contest Girl, Free Stuff Times.
  - UK: Loquax (3 pages), Competitions Time, ThePrizeFinder, Mumsnet (2), MoneySavingExpert forum (2).
  - Australia: AussieComps (2), Competitions.com.au, Comping Club.
  - Canada: Canadian Free Stuff, Contest Canada, Free.ca, SaveALoonie, Contest Scoop.
  - GTA sites: GTA BOOM (3 pages), GTA6-forum blog.

## Needs an API key
| Source | Secret(s) | Notes |
|---|---|---|
| Brave Search (about 240 queries, `site:` for 60+ sites, 15 languages, retailers, streamers) | `BRAVE_API_KEY` | About $5 per 1,000 searches, $5 free credit a month. 8 queries an hour cycles the list in about 30 hours. |
| YouTube Data API | `YOUTUBE_API_KEY` | 100 of 10,000 daily units per search. |
| Twitch Helix | `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | Free. |
| Mojeek (off) | `MOJEEK_API_KEY` | Experimental. |
| Reddit API (off) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | May need approval. |
| Bluesky (off) | `BSKY_HANDLE`, `BSKY_APP_PASSWORD` | Needs login. Experimental. |
| X API (off) | `X_BEARER_TOKEN` | Paid tier. |
| Serper (off) | `SERPER_API_KEY` | Paid third-party Google results. |

## Search results only
Kick, Discord (and Disboard / Top.gg lists), Instagram, TikTok, Facebook, Threads, Telegram, link-in-bio pages. We never fetch these directly.

## Filtered out on purpose
Paid-ticket raffles, "put your PayPal email in the comments" posts, password or card requests, and pages that say the giveaway has ended.

## Not possible
Rockstar Newswire (no RSS), Facebook groups, private Discords, anything behind a login.
