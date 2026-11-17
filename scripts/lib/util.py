"""Shared helpers: JSON IO, time, URL normalising, HTTP with rate limiting."""
import glob, hashlib, json, os, re, time
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UA = os.environ.get("SCAN_USER_AGENT", "GTA6GiveawayDirectoryBot/1.0 (+https://github.com/welshman/gta6-giveaway-directory)")


class RateLimited(Exception): pass
class MissingSecret(Exception): pass
class ProviderError(Exception): pass


def _merge(a, b):
    """Merge config 'extra' files into the base: dicts merge, lists are added to (no duplicates), other values are overridden."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _merge(a[k], v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + [x for x in b if x not in a]
    return b


def load(rel, default=None):
    """Load a JSON file. For config/NAME.json, any config/NAME-*.json files are merged in too,
    so you can add sources/queries/keywords in small extra files without touching the base file."""
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return default
    if rel.startswith("config/") and rel.endswith(".json") and rel != "config/moderation.json":
        for extra in sorted(glob.glob(os.path.join(ROOT, rel[:-5] + "-*.json"))):
            with open(extra, encoding="utf-8") as f:
                data = _merge(data, json.load(f))
    return data


def save(rel, data):
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


_TRACK = {"fbclid", "gclid", "igshid", "ref", "si", "feature", "s", "t", "mc_cid", "mc_eid"}


def domain(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def domain_matches(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def site_root(host):
    return ".".join(host.split(".")[-2:])


def normalize_url(url):
    """Stable key for de-duplication: no scheme, www, tracking params, or trailing slash."""
    u = urlparse(url.strip())
    host = domain(url)
    if host in ("twitter.com", "mobile.twitter.com"):
        host = "x.com"
    path = u.path.rstrip("/")
    if host == "youtu.be":
        host, path = "youtube.com", "/watch"
        q = [("v", u.path.strip("/"))]
    else:
        q = [(k, v) for k, v in parse_qsl(u.query) if not k.startswith("utm_") and k not in _TRACK]
    if host.endswith("youtube.com") and path == "/watch":
        q = [(k, v) for k, v in q if k == "v"]
    else:
        q = sorted(q)
    return f"{host}{path}" + (f"?{urlencode(q)}" if q else "")


def listing_id(url):
    return "gv-" + hashlib.sha1(normalize_url(url).encode()).hexdigest()[:10]


def dup_hash(title, creator):
    words = sorted(set(re.findall(r"[a-z0-9]+", f"{title} {creator}".lower())))
    return hashlib.sha1(" ".join(words).encode()).hexdigest()[:16]


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


class Http:
    """requests wrapper: custom User-Agent, polite delay, retries, 429 detection."""
    def __init__(self, delay=1.0):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.delay, self._last = delay, 0.0

    def request(self, method, url, **kw):
        kw.setdefault("timeout", 15)
        for attempt in range(3):
            wait = self.delay - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                r = self.s.request(method, url, **kw)
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                raise RateLimited(url)
            if r.status_code >= 500 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return r

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)
