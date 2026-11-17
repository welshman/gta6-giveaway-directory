# Search engines: what is wired in, and what is not

Checked 17 Nov 2026. To switch one on, set `"enabled": true` for it in `config/sources-extra-engines.json` (or the base file), add its key as a GitHub secret, then run the scan manually and read the Status tab.

| Engine | Status in this repo | Why |
|---|---|---|
| Brave Search | On (needs `BRAVE_API_KEY`) | Official API, own index. About $5 per 1,000 searches, $5 free credit a month. |
| Google | Via third parties only: `serper` or `serpapi` (off) | Google's Custom Search JSON API is closed to new customers and shuts for everyone on 1 Jan 2027. Its suggested replacement, Vertex AI Search, covers up to 50 domains, not the open web. Third-party services scrape results pages, so check their terms and the legal risk first. |
| Google News | On, as RSS (review queue only) | 24 search feeds across 14 countries and 12 languages. This feed format is undocumented by Google and could change. Links go through Google, so a moderator fixes the final URL. |
| Bing | Via `serpapi` (off) | Bing Web Search API was retired on 11 Aug 2025. |
| DuckDuckGo | Via `serpapi` (off) or your own SearXNG | No official web-search API. The only official one (Instant Answer) returns no web results. DuckDuckGo's terms prohibit scraping, so the scanner never queries it directly. |
| Yandex, Yahoo, Baidu, Naver | Via `serpapi` engines (off) | SerpApi supports them. Add the names to its `engines` list. |
| Mojeek | Built, off (`MOJEEK_API_KEY`) | Independent index with a paid API. |
| Exa | Built, off (`EXA_API_KEY`) | Own index. About $4-7 per 1,000 searches plus a monthly credit. |
| Tavily | Built, off (`TAVILY_API_KEY`) | 1,000 free credits a month, then about $8 per 1,000. |
| Perplexity Search API | Built, off (`PERPLEXITY_API_KEY`) | About $5 per 1,000 requests, $1 with Fast Search. |
| Marginalia | Built, off (optional `MARGINALIA_API_KEY`) | Free. The shared `public` key is often rate limited. Favours non-commercial sites, so low yield for giveaways. |
| SearXNG | Built, off | Self-host your own instance. Never use public instances without permission. |
| Serper | Built, off (`SERPER_API_KEY`) | Third-party Google results. |
| Kagi, You.com | Not built | I could not confirm a public web-search API with a documented format. |
| Ecosia, Startpage, Qwant | Not built | No public search API found. Scraping would break their terms. |

## Cost warning
Every engine you enable multiplies the hourly cost. `max_queries_per_run` controls how many queries each engine runs per hour. The list rotates, so a small number still covers every query over time.
