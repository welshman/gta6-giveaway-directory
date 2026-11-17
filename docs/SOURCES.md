# Sources the scanner uses

Last reviewed: 17 Nov 2026. Platforms change their rules often, so recheck before relying on any of these. Failed sources show on the site's Status tab.

## Runs with no keys (enabled)
| Source | How | Notes |
|---|---|---|
| `config/curated.json` | Hand-picked | Published instantly. Add entries you have checked yourself. |
| GamerPower RSS (all, PlayStation, Xbox, Steam) | RSS | Giveaway aggregator with official RSS feeds. |
| Reddit subreddit RSS: giveaways, sweepstakes, pcgiveaways, GiveawaysOnDiscord, xboxgiveaways, freebies, GrandTheftAutoVI, GamesGiveaway, FreeGameFindings, GiftofGames, giveawaysforgaming, FreeGameGiveaway, steam_giveaway, RandomActsOfGaming | RSS | Reddit may block or rate-limit GitHub's servers. If results are empty, switch on the Reddit API provider. |
| Reddit search RSS (GTA 6 / GTA VI giveaway, free code, raffle) and in-subreddit searches (PS5, xboxone, gaming, GTA, gtaonline) | RSS | Same caveat. |
| Steam group RSS: GrabFreeGames, FREE GAMES! GIVEAWAYS!, IndieGala | RSS | Low odds for GTA 6 but cheap. |
| Mastodon hashtag RSS on mastodon.social, mastodon.online, mstdn.social | RSS | #gta6, #gtavi, #gta6giveaway, #gtavigiveaway, #giveaway, #giveaways, #sweepstakes, #contest, #rockstargames, #grandtheftauto. Add any instance and tag with the same URL pattern. |
| Lemmy search (lemmy.world, lemmy.ml, sh.itjust.works) | Public API | Experimental. |
| Gaming news RSS (10 sites) | RSS | `review_only`. Every match goes to the review queue so a person finds the real giveaway link. |
| Watch list with link-following: TheGiveaway.com, GamerPower, Gleam giveaways, GiveOwl, Sweepstakes Radar, Sweeties Sweeps, GTA BOOM coverage and news, GTA6-forum blog | Polite page reads | Reads each page, follows only links that mention GTA 6 / GTA VI, then checks those pages. robots.txt respected. JavaScript-only pages may return nothing. |

## Needs an API key
| Source | Secret(s) | Cost / limits |
|---|---|---|
| Brave Search (about 150 queries incl. `site:` for 40+ sites and 15 languages) | `BRAVE_API_KEY` | About $5 per 1,000 searches, $5 free credit monthly. |
| YouTube Data API | `YOUTUBE_API_KEY` | Free quota. Each search costs 100 of 10,000 daily units. |
| Twitch Helix | `TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET` | Free. |
| Mojeek (disabled, experimental) | `MOJEEK_API_KEY` | Check their API terms and price. |
| Reddit API (disabled) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Free tier may need approval. |
| Bluesky (disabled, experimental) | `BSKY_HANDLE`, `BSKY_APP_PASSWORD` | Post search needs login. Use an App Password. |
| X API (disabled) | `X_BEARER_TOKEN` | Paid tier. |
| Serper (disabled) | `SERPER_API_KEY` | Paid third-party Google results. |

## Reached only through search results
Kick, Discord (including Disboard and Top.gg server lists), Instagram, TikTok, Facebook, Threads, Telegram, link-in-bio pages (Linktree, Beacons, Carrd, bio.link, solo.to, lnk.bio, allmylinks, taplink, linkin.bio). Their terms restrict scraping, so we never fetch these pages directly. Add confirmed ones to `config/curated.json`.

## Not possible
- Rockstar Newswire has no RSS feed, and third-party trackers scrape it, so it isn't used.
- Facebook groups, private Discords, and anything behind a login.
