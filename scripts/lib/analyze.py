"""Relevance, giveaway and scam detection, field extraction, scoring, polite page fetching."""
import re
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from .util import now, domain, domain_matches, RateLimited

ENTRY = {
    "follow": r"\bfollow", "comment": r"\bcomment|\breply", "repost": r"\brepost|\bretweet|\bRT\b", "like": r"\blike\b",
    "subscribe": r"\bsubscribe|\bsub\b", "join-discord": r"discord", "link-in-bio": r"link in bio",
    "form": r"gleam|rafflecopter|woobox|kingsumo|\benter (?:here|below|now|via)|entry form", "tag-friends": r"\btag (?:a |your |2 |two )?friends?",
    "watch-stream": r"\bwatch|\bin chat\b|!enter|!join|!raffle",
}
ENTRY_LABEL = {"follow": "Follow", "comment": "Comment", "repost": "Repost", "like": "Like", "subscribe": "Subscribe", "join-discord": "Join Discord",
               "link-in-bio": "Link in bio", "form": "Form entry", "tag-friends": "Tag friends", "watch-stream": "Watch the stream"}
END_RE = re.compile(r"(?:ends?|ending|closes?|closing|deadline|until|expires?|drawn on)\b(?:\s+on|\s+at)?[:\s]+([A-Za-z0-9,/\-: .]{6,40})", re.I)
PRIZE_RE = re.compile(r"(?:win|winning|giving away|giveaway of|prize(?: is)?[: ]+)\s+(?:a\s+|an\s+|the\s+|\d+\s*x?\s+)?([^.!?\n]{5,80})", re.I)
MONTHS = re.compile(r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", re.I)


def _re(terms):
    if not terms:
        return None
    parts = [r"\s+".join(re.escape(w) for w in t.split()) for t in terms]
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])", re.I)


class Analyzer:
    def __init__(self, kw, sources, moderation):
        self.kw, self.src, self.mod = kw, sources, moderation
        self.gta = _re(kw["gta6_terms"] + kw["gta_vi_terms"] + kw["grand_theft_auto_terms"])
        self.give, self.contest, self.sweep = _re(kw["giveaway_terms"]), _re(kw["contest_terms"]), _re(kw["sweepstake_terms"])
        self.hard, self.soft = _re(kw["scam_terms_hard"]), _re(kw["scam_terms_soft"])
        self.excl, self.pos, self.neg = _re(kw["exclusion_terms"]), _re(kw["positive_keywords"]), _re(kw["negative_keywords"])
        self.regions = {k: _re(v) for k, v in kw["region_terms"].items()}
        self.blocked = set(sources["blocked_domains"]) | set(moderation.get("blocked_domains", []))
        self.trusted = set(sources["trusted_domains"])
        self.allowed = set(sources["allowed_domains"])
        self.trusted_creators = {c.lower() for c in moderation.get("trusted_creators", [])}
        self.blocked_creators = {c.lower() for c in moderation.get("blocked_creators", [])}

    def is_blocked(self, url, creator=""):
        return domain_matches(domain(url), self.blocked) or (creator or "").lower() in self.blocked_creators

    def is_trusted(self, url, creator=""):
        return domain_matches(domain(url), self.trusted) or (creator or "").lower() in self.trusted_creators

    def extract_end(self, text):
        for m in END_RE.finditer(text):
            frag = m.group(1).strip()
            if not (re.search(r"\d", frag) and (MONTHS.search(frag) or re.search(r"\d[/\-]\d", frag))):
                continue
            try:
                d = dparser.parse(frag, dayfirst=True, fuzzy=True, default=datetime(now().year, 1, 1))
            except (ValueError, OverflowError):
                continue
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if d.hour == 0 and d.minute == 0 and ":" not in frag:
                d = d.replace(hour=23, minute=59, second=59)
            if now().year - 1 <= d.year <= now().year + 1:
                return d
        return None

    def has_exclusion(self, text):
        m = self.excl.search(text) if self.excl else None
        return m.group(0) if m else None

    def has_hard_scam(self, text):
        m = self.hard.search(text) if self.hard else None
        return m.group(0) if m else None

    def evaluate(self, title, body, url, creator="", provided_end=None):
        """Return dict: reject (reason or None), score 0-100, flags, extracted fields."""
        text = f"{title}\n{body}"
        ev = {"reject": None, "flags": [], "score": 0, "regions": [], "entry_types": [], "end": provided_end, "prize": "", "tags": []}
        if not self.gta.search(text):
            ev["reject"] = "not GTA 6 related"; return ev
        if not (self.give.search(text) or (self.contest and self.contest.search(text)) or (self.sweep and self.sweep.search(text))):
            ev["reject"] = "no giveaway wording"; return ev
        m = self.has_hard_scam(text)
        if m:
            ev["reject"] = f"scam pattern: {m}"; return ev
        m = self.has_exclusion(text)
        if m:
            ev["reject"] = f"excluded: {m}"; return ev

        s = 25 if self.gta.search(title) else 10
        s += 20 if self.give.search(title) else 10
        if (self.contest and self.contest.search(text)) or (self.sweep and self.sweep.search(text)):
            s += 5
        if self.pos:
            s += min(15, 5 * len(set(x.lower() for x in self.pos.findall(text))))
        negs = set(x.lower() for x in self.neg.findall(text)) if self.neg else set()
        s -= 8 * len(negs)
        if negs:
            ev["flags"].append("Suspicious wording: " + ", ".join(sorted(negs)))
        softs = set(x.lower() for x in self.soft.findall(text)) if self.soft else set()
        s -= min(30, 10 * len(softs))
        if softs:
            ev["flags"].append("Mentions " + ", ".join(sorted(softs)) + ". Check the rules carefully")
        host = domain(url)
        if domain_matches(host, self.trusted): s += 15
        elif domain_matches(host, self.allowed): s += 8
        if creator and creator.lower() in self.trusted_creators: s += 20
        end = ev["end"] or self.extract_end(text)
        ev["end"] = end
        if end and end > now(): s += 10
        elif not end: ev["flags"].append("No end date found")
        for key, pat in ENTRY.items():
            if re.search(pat, text, re.I): ev["entry_types"].append(key)
        if ev["entry_types"]: s += 5
        if creator: s += 5
        pm = PRIZE_RE.search(text)
        if pm:
            ev["prize"] = pm.group(1).strip(" -:,"); s += 5
        ev["regions"] = [k for k, rx in self.regions.items() if rx and rx.search(text)]
        ev["score"] = max(0, min(100, s))
        t = ["GTA 6", "Giveaway"]
        if "international" in ev["regions"]: t.append("International")
        if "uk" in ev["regions"]: t.append("UK Eligible")
        if re.search(r"no purchase necessary|free to enter", text, re.I): t.append("No purchase necessary")
        if end and 0 < (end - now()).total_seconds() < 86400: t.append("Ends Soon")
        ev["tags"] = t
        return ev


# ---------- polite page fetching ----------
_robots = {}


def robots_allows(http, url):
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        try:
            r = http.get(base + "/robots.txt", timeout=10)
            if r.status_code == 200: rp.parse(r.text.splitlines())
            elif 400 <= r.status_code < 500: rp.parse([])
            else: rp.disallow_all = True
        except Exception:
            rp.disallow_all = True
        _robots[base] = rp
    return _robots[base].can_fetch(http.s.headers["User-Agent"], url)


def fetchable(url, sources):
    return not domain_matches(domain(url), sources["no_fetch_domains"])


def fetch_page(http, url, max_bytes=1_500_000):
    """Returns dict(status, html, final_url, blocked). status 0 = not fetched. Honours robots.txt."""
    out = {"status": 0, "html": "", "final_url": url, "blocked": False}
    if not robots_allows(http, url):
        out["blocked"] = True
        return out
    try:
        r = http.get(url, stream=True, allow_redirects=True)
    except RateLimited:
        out["status"] = 429
        return out
    except Exception:
        return out
    out["status"], out["final_url"] = r.status_code, r.url
    if r.status_code == 200 and "html" in r.headers.get("Content-Type", ""):
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > max_bytes:
                break
        out["html"] = buf.decode(r.encoding or "utf-8", "replace")
    r.close()
    return out


def parse_page(html):
    soup = BeautifulSoup(html or "", "html.parser")
    meta = lambda **kw: (soup.find("meta", attrs=kw) or {}).get("content", "") or ""
    has_pw = bool(soup.find("input", attrs={"type": "password"}))
    bad = [a["href"] for a in soup.find_all("a", href=True) if re.search(r"\.(apk|exe|msi|dmg|zip)(\?|$)", a["href"], re.I)]
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    canon = soup.find("link", rel="canonical")
    return {
        "title": (meta(property="og:title") or (soup.title.string if soup.title and soup.title.string else "")).strip(),
        "description": (meta(property="og:description") or meta(name="description")).strip(),
        "image": meta(property="og:image"),
        "canonical": canon["href"] if canon and canon.get("href") else "",
        "text": re.sub(r"\s+", " ", soup.get_text(" "))[:30000],
        "has_password": has_pw, "bad_links": bad[:3],
    }
