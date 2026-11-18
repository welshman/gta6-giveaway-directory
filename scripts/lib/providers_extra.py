"""Extra search-engine providers. All are OFF by default; enable them in config/sources.json (or a sources-*.json extra file).
Each one needs its own API key in a GitHub secret. Formats follow each vendor's public docs, so treat them as experimental
and check the Status tab after the first run."""
import os
from datetime import timedelta
from .providers import provider, pick, secret, cand
from .util import ProviderError, now


@provider("exa")
def exa(p, qs, http, src):
    """Exa: neural web search with its own index."""
    key, out = secret(p, "api_key_env"), []
    start = (now() - timedelta(days=p.get("days", 14))).strftime("%Y-%m-%dT00:00:00.000Z")
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 4)):
        r = http.post("https://api.exa.ai/search", headers={"x-api-key": key},
                      json={"query": q, "numResults": p.get("count", 10), "startPublishedDate": start, "contents": {"text": {"maxCharacters": 600}}})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title") or "", it.get("text") or "", "exa", q))
    return out


@provider("tavily")
def tavily(p, qs, http, src):
    """Tavily: search API built for AI agents. Free monthly credits."""
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 4)):
        r = http.post("https://api.tavily.com/search", headers={"Authorization": "Bearer " + key},
                      json={"query": q, "max_results": p.get("count", 10), "time_range": "month", "search_depth": "basic"})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("content", ""), "tavily", q))
    return out


@provider("perplexity")
def perplexity(p, qs, http, src):
    """Perplexity Search API (ranked web results from Perplexity's index)."""
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 4)):
        r = http.post("https://api.perplexity.ai/search", headers={"Authorization": "Bearer " + key},
                      json={"query": q, "max_results": p.get("count", 10)})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("snippet", ""), "perplexity", q))
    return out


_SERPAPI_QUERY_PARAM = {"google": "q", "bing": "q", "duckduckgo": "q", "baidu": "q", "yandex": "text", "yahoo": "p", "naver": "query"}


@provider("serpapi")
def serpapi(p, qs, http, src):
    """SerpApi: one paid key gives Google, Bing, DuckDuckGo, Yandex, Yahoo, Baidu and Naver results as JSON.
    These are scraped result pages run by SerpApi. Read their terms and the engines' terms before enabling."""
    key, out = secret(p, "api_key_env"), []
    for engine in p.get("engines", ["google", "bing"]):
        param = _SERPAPI_QUERY_PARAM.get(engine, "q")
        for q in pick(qs["web_queries"], p.get("max_queries_per_run", 1)):
            params = {"engine": engine, param: q, "api_key": key}
            if engine == "google":
                params["tbs"] = "qdr:m"
            r = http.get("https://serpapi.com/search.json", params=params)
            if r.status_code != 200:
                raise ProviderError(f"{engine} HTTP {r.status_code}")
            for it in r.json().get("organic_results", []):
                if it.get("link"):
                    out.append(cand(it["link"], it.get("title", ""), it.get("snippet", ""), "serpapi:" + engine, q))
    return out


@provider("marginalia")
def marginalia(p, qs, http, src):
    """Marginalia: independent search engine. The shared key 'public' works but is often rate limited."""
    key = os.environ.get(p.get("api_key_env", ""), "") or "public"
    out = []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 2)):
        r = http.get("https://api2.marginalia-search.com/search", headers={"API-Key": key}, params={"query": q, "count": 20})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("description", "") or it.get("desc", ""), "marginalia", q))
    return out


@provider("kakao")
def kakao(p, qs, http, src):
    """Daum Search (Korea) via the official Kakao Developers REST API. Free, with daily and monthly quotas."""
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 4)):
        r = http.get("https://dapi.kakao.com/v2/search/web", headers={"Authorization": "KakaoAK " + key},
                     params={"query": q, "sort": "recency", "size": 30})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for d in r.json().get("documents", []):
            out.append(cand(d["url"], d.get("title", ""), d.get("contents", ""), "kakao", q))
    return out


@provider("naver")
def naver(p, qs, http, src):
    """Naver (Korea) via the official Naver Search Open API. Free, about 25,000 calls a day per app.
    Endpoints: webkr (web), blog, news, cafearticle, kin."""
    cid, sec, out = secret(p, "client_id_env"), secret(p, "client_secret_env"), []
    hdr = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 3)):
        for ep in p.get("endpoints", ["webkr", "blog", "news"]):
            params = {"query": q, "display": 20}
            if ep in ("blog", "news", "cafearticle"):
                params["sort"] = "date"
            r = http.get(f"https://openapi.naver.com/v1/search/{ep}.json", headers=hdr, params=params)
            if r.status_code != 200:
                raise ProviderError(f"{ep} HTTP {r.status_code}")
            for it in r.json().get("items", []):
                out.append(cand(it.get("originallink") or it["link"], it.get("title", ""), it.get("description", ""), "naver:" + ep, q))
    return out


@provider("kagi")
def kagi(p, qs, http, src):
    """Kagi Search API (pay as you go, about $12 per 1,000 searches). Experimental: response shape follows Kagi's OpenAPI docs."""
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 3)):
        r = http.post("https://kagi.com/api/v1/search", headers={"Authorization": "Bot " + key}, json={"query": q})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        j = r.json()
        items = j.get("results") or j.get("data") or []
        if isinstance(items, dict):
            items = items.get("search") or items.get("results") or []
        for it in items:
            if isinstance(it, dict) and it.get("url"):
                out.append(cand(it["url"], it.get("title", ""), it.get("snippet", "") or it.get("description", ""), "kagi", q))
    return out


@provider("youcom")
def youcom(p, qs, http, src):
    """You.com Search API. Experimental: response shape follows You.com's public OpenAPI description."""
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 3)):
        r = http.get("https://api.you.com/v1/search", headers={"X-API-Key": key}, params={"query": q, "count": p.get("count", 20)})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        res = r.json().get("results", {})
        items = res.get("web", []) + res.get("news", []) if isinstance(res, dict) else res
        for it in items:
            if isinstance(it, dict) and it.get("url"):
                snip = it.get("description") or " ".join(it.get("snippets", []) or [])
                out.append(cand(it["url"], it.get("title", ""), snip, "youcom", q))
    return out


@provider("yacy")
def yacy(p, qs, http, src):
    """YaCy peer-to-peer search. Point base_url at a YaCy node you run (or one whose owner allows API use)."""
    base, out = p["base_url"].rstrip("/"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 4)):
        r = http.get(base + "/yacysearch.json", params={"query": q, "maximumRecords": 20, "resource": "global"})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for ch in r.json().get("channels", []):
            for it in ch.get("items", []):
                if it.get("link"):
                    out.append(cand(it["link"], it.get("title", ""), it.get("description", ""), "yacy", q))
    return out
