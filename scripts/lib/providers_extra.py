"""Extra search-engine providers. All are OFF by default; enable them in config/sources.json (or a sources-*.json extra file).
Each one needs its own API key in a GitHub secret. Response formats were taken from each vendor's public docs,
so treat them as experimental and check the Status tab after the first run."""
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


# Query parameter name each SerpApi engine expects.
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
    """Marginalia: independent search engine. The shared key 'public' works but is often rate limited.
    Request a free key from the Marginalia team for steady use. Experimental: confirm the endpoint in their docs."""
    key = os.environ.get(p.get("api_key_env", ""), "") or "public"
    out = []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 2)):
        r = http.get("https://api2.marginalia-search.com/search", headers={"API-Key": key}, params={"query": q, "count": 20})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("description", "") or it.get("desc", ""), "marginalia", q))
    return out
