# Search engines: what is wired in, and what is not

Checked 18 Nov 2026 against the engine list on Wikipedia's "Search engine" article (the "Current status" column). Engines Wikipedia marks Inactive (AltaVista, Ask.com, Excite-era leftovers such as Infoseek, HotBot, Cuil, Blekko, Gigablast, Exalead, Searx, Presearch, Cliqz and others) were skipped. Wikipedia's Active flag is not proof an engine is open to automated queries, so the right-hand column says what I could actually confirm.

To switch one on: set `"enabled": true` for it in `config/sources-extra-engines.json` or `config/sources-extra-engines2.json`, add its key as a GitHub secret, run the scan manually, and read the Status tab.

## Built into the scanner
| Engine (Wikipedia: Active) | Provider | Access |
|---|---|---|
| Brave Search | `brave` (on) | Official API, about $5 per 1,000 searches, $5 free credit a month |
| Mojeek | `mojeek` (off) | Paid API |
| Google, Blackle and Kiddle (both Google skins) | `serper`, `serpapi` (off) | Google's own Custom Search API is closed to new customers. Only third-party resellers remain |
| Bing (MSN Search, Live Search) | `serpapi` (off) | Bing Web Search API was retired on 11 Aug 2025 |
| Yahoo! Search | `serpapi` engine `yahoo` (off) | Yahoo shut its BOSS search API on 31 Mar 2016 and has none now. Third parties only. Yahoo has just rebuilt its search around Yahoo Scout |
| DuckDuckGo | `serpapi` engine `duckduckgo` (off) | No official web-search API. Their terms prohibit scraping |
| Yandex | `serpapi` engine `yandex` (off) | Official Yandex Cloud Search API v2 exists (about $4 per 1,000 daytime requests) but returns Base64 XML and needs a Yandex Cloud account, so I did not build it |
| Baidu | `serpapi` engine `baidu` (off) | No official English API. Third-party only |
| Naver | `naver` (off) | Official Open API, free, about 25,000 calls a day per app. Also endpoints for blogs, news and cafes |
| Daum | `kakao` (off) | Official Kakao Developers API, free with daily and monthly quotas |
| Kagi | `kagi` (off) | Paid API, about $12 per 1,000 searches |
| You.com | `youcom` (off) | API key from you.com/platform |
| Perplexity | `perplexity` (off) | Search API, about $5 per 1,000 |
| YaCy (P2P) | `yacy` (off) | Free. Needs a YaCy node you control. Its API returns JSON and RSS |
| SearXNG | `searxng` (off) | Your own instance only |
| Exa, Tavily, Marginalia (not on the Wikipedia list) | `exa`, `tavily`, `marginalia` (off) | Paid or free-tier APIs |

## Active on Wikipedia but not added, and why
- **No search API and scraping is not permitted:** Startpage (Ixquick), Ecosia, Qwant, Swisscows, Sogou, Petal, Parsijoo, Egerin, goo.ne.jp, SAPO, Search.ch, NATE, Scout (Goby), TinEye (image search).
- **Metasearch front ends with no API (they re-sell Google or Bing results):** WebCrawler, Lycos, Excite, MetaCrawler, Dogpile, AOL Search, Info.com, Search.com, Yippy (Clusty).
- **Qwant and Ecosia:** they now share a European index called Staan, which has an API for AI tools. I couldn't confirm its address or response format, so I did not build it.
- Any of these can still be reached through your own SearXNG instance if you enable the engine there and the engine's terms allow it.

## Cost warning
Every engine you enable multiplies the hourly cost. `max_queries_per_run` controls queries per engine per hour. The list rotates, so a small number still covers every query over time. For a giveaway directory I'd start with Brave, then add Naver and Kakao (free) only if you want Korean coverage.
