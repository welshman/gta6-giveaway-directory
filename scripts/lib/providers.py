"""Discovery providers. Each takes (provider_config, queries, http, sources) and returns a list of candidates.
To add a provider: write a function, decorate with @provider("name"), add a block to config/sources.json."""
import os
from defusedxml import ElementTree as ET
from .util import now, iso, load, strip_html, MissingSecret, ProviderError
from datetime import timedelta

PROVIDERS = {}


def provider(name):
    def deco(fn):
        PROVIDERS[name] = fn
        return fn
    return deco


def pick(queries, n):
    """Rotate through the list so every query gets used over several hourly runs."""
    if not queries:
        return []
    n = min(n, len(queries))
    start = (now().hour * n) % len(queries)
    return [queries[(start + i) % len(queries)] for i in range(n)]


def secret(p, field):
    name = p.get(field, "")
    v = os.environ.get(name, "")
    if not v:
        raise MissingSecret(f"missing secret {name}")
    return v


def cand(url, title, snippet, source, query=None, **extra):
    c = {"url": url, "title": strip_html(title), "snippet": strip_html(snippet), "source": source, "query": query,
         "creator": "", "creator_url": "", "platform": None, "thumbnail": None, "end_date": None}
    c.update(extra)
    return c


@provider("curated")
def curated(p, qs, http, src):
    """Hand-picked listings from config/curated.json (published without scoring)."""
    out = []
    for it in load("config/curated.json", {"giveaways": []})["giveaways"]:
        c = cand(it["url"], it["title"], it.get("summary", ""), "curated")
        c.update(it)
        c["curated"] = True
        out.append(c)
    return out


@provider("brave")
def brave(p, qs, http, src):
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 10)):
        r = http.get("https://api.search.brave.com/res/v1/web/search", params={"q": q, "count": p.get("count", 20), "freshness": p.get("freshness", "pm")},
                     headers={"X-Subscription-Token": key, "Accept": "application/json"})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("web", {}).get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("description", ""), "brave", q))
    return out


@provider("serper")
def serper(p, qs, http, src):
    key, out = secret(p, "api_key_env"), []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 10)):
        r = http.post("https://google.serper.dev/search", headers={"X-API-KEY": key}, json={"q": q, "num": 20, "tbs": "qdr:w"})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("organic", []):
            out.append(cand(it["link"], it.get("title", ""), it.get("snippet", ""), "serper", q))
    return out


@provider("searxng")
def searxng(p, qs, http, src):
    out = []
    for q in pick(qs["web_queries"], p.get("max_queries_per_run", 8)):
        r = http.get(p["base_url"].rstrip("/") + "/search", params={"q": q, "format": "json", "time_range": "month"})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("results", []):
            out.append(cand(it["url"], it.get("title", ""), it.get("content", ""), "searxng", q))
    return out


@provider("youtube")
def youtube(p, qs, http, src):
    key, out = secret(p, "api_key_env"), []
    after = iso(now() - timedelta(days=14))
    for q in pick(qs["api_queries"], p.get("max_queries_per_run", 2)):
        r = http.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "type": "video", "q": q, "order": "date",
                     "publishedAfter": after, "maxResults": 25, "key": key})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for it in r.json().get("items", []):
            sn = it["snippet"]
            out.append(cand(f"https://www.youtube.com/watch?v={it['id']['videoId']}", sn["title"], sn.get("description", ""), "youtube", q,
                            creator=sn.get("channelTitle", ""), creator_url=f"https://www.youtube.com/channel/{sn.get('channelId', '')}",
                            platform="YouTube", thumbnail=sn.get("thumbnails", {}).get("default", {}).get("url")))
    return out


@provider("reddit")
def reddit(p, qs, http, src):
    cid, sec, out = secret(p, "client_id_env"), secret(p, "client_secret_env"), []
    t = http.post("https://www.reddit.com/api/v1/access_token", auth=(cid, sec), data={"grant_type": "client_credentials"})
    if t.status_code != 200:
        raise ProviderError(f"token HTTP {t.status_code}")
    hdr = {"Authorization": "bearer " + t.json()["access_token"]}
    for q in pick(qs["api_queries"], p.get("max_queries_per_run", 3)):
        for sub in [None] + p.get("subreddits", []):
            url = "https://oauth.reddit.com/" + (f"r/{sub}/search" if sub else "search")
            r = http.get(url, headers=hdr, params={"q": q, "sort": "new", "t": "week", "limit": 25, "restrict_sr": 1 if sub else 0})
            if r.status_code != 200:
                raise ProviderError(f"HTTP {r.status_code}")
            for ch in r.json().get("data", {}).get("children", []):
                d = ch["data"]
                out.append(cand("https://www.reddit.com" + d["permalink"], d.get("title", ""), d.get("selftext", "")[:1500], "reddit", q,
                                creator="u/" + d.get("author", ""), creator_url=f"https://www.reddit.com/user/{d.get('author', '')}", platform="Reddit"))
    return out


@provider("twitch")
def twitch(p, qs, http, src):
    cid, sec, out = secret(p, "client_id_env"), secret(p, "client_secret_env"), []
    t = http.post("https://id.twitch.tv/oauth2/token", params={"client_id": cid, "client_secret": sec, "grant_type": "client_credentials"})
    if t.status_code != 200:
        raise ProviderError(f"token HTTP {t.status_code}")
    hdr = {"Client-Id": cid, "Authorization": "Bearer " + t.json()["access_token"]}
    for q in pick(qs["api_queries"], p.get("max_queries_per_run", 3)):
        r = http.get("https://api.twitch.tv/helix/search/channels", headers=hdr, params={"query": q, "live_only": "true", "first": 50})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for ch in r.json().get("data", []):
            login = ch["broadcaster_login"]
            out.append(cand(f"https://www.twitch.tv/{login}", ch.get("title", ""), ch.get("title", ""), "twitch", q, creator=ch.get("display_name", login),
                            creator_url=f"https://www.twitch.tv/{login}", platform="Twitch", thumbnail=ch.get("thumbnail_url")))
    return out


@provider("bluesky")
def bluesky(p, qs, http, src):
    """Experimental. Post search needs a logged-in session (use an App Password, never your main password)."""
    handle, pw, out = secret(p, "handle_env"), secret(p, "password_env"), []
    s = http.post("https://bsky.social/xrpc/com.atproto.server.createSession", json={"identifier": handle, "password": pw})
    if s.status_code != 200:
        raise ProviderError(f"login HTTP {s.status_code}")
    hdr = {"Authorization": "Bearer " + s.json()["accessJwt"], "atproto-proxy": "did:web:api.bsky.app#bsky_appview"}
    for q in pick(qs["api_queries"], p.get("max_queries_per_run", 3)):
        r = http.get("https://bsky.social/xrpc/app.bsky.feed.searchPosts", headers=hdr, params={"q": q, "sort": "latest", "limit": 25})
        if r.status_code != 200:
            raise ProviderError(f"HTTP {r.status_code}")
        for post in r.json().get("posts", []):
            h, text = post["author"]["handle"], post.get("record", {}).get("text", "")
            out.append(cand(f"https://bsky.app/profile/{h}/post/{post['uri'].rsplit('/', 1)[-1]}", text[:100], text, "bluesky", q,
                            creator="@" + h, creator_url=f"https://bsky.app/profile/{h}", platform="Bluesky"))
    return out


@provider("x")
def x_api(p, qs, http, src):
    tok, out = secret(p, "bearer_env"), []
    r = http.get("https://api.x.com/2/tweets/search/recent", headers={"Authorization": "Bearer " + tok},
                 params={"query": '("GTA 6" OR "GTA VI") giveaway -is:retweet', "max_results": 25, "tweet.fields": "created_at,author_id",
                         "expansions": "author_id", "user.fields": "username"})
    if r.status_code != 200:
        raise ProviderError(f"HTTP {r.status_code}")
    d = r.json()
    users = {u["id"]: u["username"] for u in d.get("includes", {}).get("users", [])}
    for tw in d.get("data", []):
        u = users.get(tw["author_id"], "i")
        out.append(cand(f"https://x.com/{u}/status/{tw['id']}", tw["text"][:100], tw["text"], "x", None, creator="@" + u, creator_url=f"https://x.com/{u}", platform="X"))
    return out


def _local(tag):
    return tag.rsplit("}", 1)[-1]


@provider("rss")
def rss(p, qs, http, src):
    """RSS/Atom feeds. A feed with "review_only": true (news sites) sends every match to the review queue."""
    out = []
    for feed in p.get("feeds", []):
        try:
            r = http.get(feed["url"])
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
        except Exception:
            continue
        for item in root.iter():
            if _local(item.tag) not in ("item", "entry"):
                continue
            f = {_local(c.tag): c for c in item}
            link = (f["link"].get("href") or f["link"].text) if "link" in f else None
            if not link:
                continue
            body = "".join((f[k].text or "") for k in ("description", "summary", "content") if k in f)
            title = f["title"].text if "title" in f and f["title"].text else ""
            out.append(cand(link.strip(), title, body, "rss:" + feed.get("name", feed["url"]), force_review=bool(feed.get("review_only"))))
    return out


@provider("watch")
def watch(p, qs, http, src):
    """Your own list of creator/landing pages. Page text is read later by the analyser."""
    return [cand(u, "", "", "watch-list") for u in p.get("urls", [])]
