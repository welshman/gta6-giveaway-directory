#!/usr/bin/env python3
"""Hourly scanner. Usage: python scripts/scan.py [--dry-run] [--offline]
--dry-run  : do everything but don't write files
--offline  : skip all network access (only runs expiry / archive housekeeping)
"""
import argparse, os, re, sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))
from lib.util import (Http, MissingSecret, RateLimited, domain, domain_matches, dup_hash, iso, listing_id, load, normalize_url,
                      now, parse_iso, save, site_root, strip_html, ROOT)
from lib.analyze import Analyzer, ENTRY_LABEL, fetch_page, fetchable, parse_page
from lib.providers import PROVIDERS
from lib.notify import discord, write_feed


class Scanner:
    def __init__(self, args):
        self.args = args
        self.src = load("config/sources.json")
        self.kw = load("config/keywords.json")
        self.qs = load("config/search-queries.json")
        self.mod = load("config/moderation.json")
        self.an = Analyzer(self.kw, self.src, self.mod)
        self.http = Http(self.src["rate_limits"]["delay_seconds"])
        self.gv = load("data/giveaways.json", {"giveaways": []})["giveaways"]
        self.review = load("data/review-queue.json", {"giveaways": []})["giveaways"]
        self.archive = load("data/archive.json", {"giveaways": []})["giveaways"]
        self.log = load("data/discovery-log.json", {"runs": [], "events": []})
        self.rejected = {normalize_url(u) for u in self.mod.get("rejected_urls", [])}
        self.stats = dict(found=0, published=0, review=0, rejected=0, duplicates=0, expired=0, errors=0)
        self.new = []
        self.health = {}
        rl = self.src["rate_limits"]
        self.fetch_budget, self.check_budget = rl["page_fetch_budget_per_run"], rl["recheck_budget_per_run"]
        self.ex = self.src["expiry"]

    # ---------- helpers ----------
    def event(self, kind, url, title, reason="", score=None):
        self.log["events"].append({"t": iso(now()), "type": kind, "url": url, "title": (title or "")[:100], "reason": reason, "score": score})

    def build_index(self):
        self.index, self.hashes = {}, {}
        for l in self.gv + self.review + self.archive:
            self.index[normalize_url(l["url"])] = l
            if l.get("duplicate_hash"):
                self.hashes[l["duplicate_hash"]] = l

    def reject(self, c, reason, score=None):
        self.stats["rejected"] += 1
        self.event("rejected", c["url"], c.get("title"), reason, score)

    def platform_of(self, url, hint=None):
        if hint:
            return hint
        host = domain(url)
        for d, name in self.src["platform_map"].items():
            if domain_matches(host, [d]):
                return name
        return "Website"

    # ---------- discovery ----------
    def run_providers(self):
        cands = []
        for name, p in self.src["providers"].items():
            if not p.get("enabled") or name not in PROVIDERS:
                continue
            h = {"last_run": iso(now()), "ok": False, "results": 0}
            try:
                res = PROVIDERS[name](p, self.qs, self.http, self.src)
                h.update(ok=True, results=len(res))
                cands += res
            except MissingSecret as e:
                h.update(skipped=True, error=str(e))
            except RateLimited:
                h.update(rate_limited=True, error="rate limited"); self.stats["errors"] += 1
            except Exception as e:
                h.update(error=f"{type(e).__name__}: {e}"[:150]); self.stats["errors"] += 1
            self.health[name] = h
        return cands

    def github_issues(self, label):
        repo, token = os.environ.get("GITHUB_REPOSITORY") or self.src["site"]["repo"], os.environ.get("GITHUB_TOKEN")
        hdr = {"Accept": "application/vnd.github+json"}
        if token:
            hdr["Authorization"] = "Bearer " + token
        try:
            r = self.http.get(f"https://api.github.com/repos/{repo}/issues", headers=hdr, params={"labels": label, "state": "open", "per_page": 100})
            return [i for i in r.json() if "pull_request" not in i] if r.status_code == 200 else []
        except Exception:
            return []

    def submissions(self):
        out = []
        for i in self.github_issues("submission"):
            body = i.get("body") or ""
            f = lambda k: (re.search(rf"^{k}:\s*(.+)$", body, re.M | re.I) or [None, ""])[1].strip()
            url = f("URL")
            if url.startswith("http"):
                out.append({"url": url, "title": f("Title") or i["title"], "snippet": f"{f('Title')} {body}", "creator": f("Creator"), "creator_url": "",
                            "platform": None, "source": "user-submission", "query": None, "thumbnail": None, "end_date": None,
                            "force_review": self.mod.get("submissions_require_review", True), "issue": i["number"]})
        return out

    # ---------- processing ----------
    def add_curated(self, c):
        """Hand-picked listing from config/curated.json: published as-is."""
        end, start = parse_iso(c.get("end_date")), parse_iso(c.get("start_date"))
        if (end and end < now()) or (start and start > now()):
            return
        t, plat = iso(now()), self.platform_of(c["url"], c.get("platform"))
        l = {
            "id": listing_id(c["url"]), "title": c["title"], "platform": plat, "url": c["url"], "creator": c.get("creator", ""), "creator_url": c.get("creator_url", ""),
            "prize": c.get("prize", ""), "entry_method": c.get("entry_method", []), "entry_types": c.get("entry_types", []),
            "start_date": c.get("start_date"), "end_date": c.get("end_date"), "region_text": c.get("region_text", ""), "regions": c.get("regions", []),
            "verification": c.get("verification", "Verified"), "confidence": 95, "source": "curated", "search_query": None,
            "date_first_found": t, "date_last_checked": t, "date_last_seen": t, "date_expired": None,
            "summary": c.get("summary", ""), "thumbnail": None, "tags": ["GTA 6", "Giveaway", plat] + c.get("tags", []), "status": "Active",
            "warnings": c.get("warnings", []), "trusted_source": c.get("trusted_source", False), "moderation_notes": "Curated entry from config/curated.json",
            "report_count": 0, "duplicate_hash": dup_hash(c["title"], c.get("creator", "")), "fetch_failures": 0, "curated": True,
        }
        self.gv.append(l); self.new.append(l); self.stats["published"] += 1
        self.index[normalize_url(c["url"])] = l
        self.event("published", c["url"], c["title"], "curated", 95)

    def process(self, c):
        url = c["url"]
        if not url.startswith(("http://", "https://")):
            return
        key, host = normalize_url(url), domain(url)
        if self.an.is_blocked(url, c.get("creator", "")):
            return self.reject(c, "blocked domain or creator")
        if key in self.rejected:
            return
        if key in self.index:
            self.index[key]["date_last_seen"] = iso(now())
            self.stats["duplicates"] += 1
            return
        if c.get("curated"):
            return self.add_curated(c)
        title, body, flags, info, thumb = c["title"], c.get("snippet", ""), [], None, c.get("thumbnail")
        if fetchable(url, self.src) and self.fetch_budget > 0 and not self.args.offline:
            self.fetch_budget -= 1
            pg = fetch_page(self.http, url)
            if pg["status"] == 200 and pg["html"]:
                info = parse_page(pg["html"])
                if info["has_password"]:
                    return self.reject(c, "page asks for a password")
                if info["bad_links"]:
                    flags.append("Page links to a downloadable file")
                if site_root(domain(pg["final_url"])) != site_root(host):
                    flags.append("Redirects to a different website")
                title = title or info["title"]
                body += "\n" + info["description"] + "\n" + info["text"]
                thumb = thumb or info["image"] or None
        creator = c.get("creator", "")
        ev = self.an.evaluate(title, body, url, creator, parse_iso(c.get("end_date")) if c.get("end_date") else None)
        if ev["reject"]:
            return self.reject(c, ev["reject"])
        if ev["end"] and ev["end"] < now():
            return self.reject(c, "end date already passed")
        score = min(100, ev["score"] + (5 if info else 0) - 10 * len(flags))
        h = dup_hash(title, creator)
        if h in self.hashes:
            self.stats["duplicates"] += 1
            return self.event("duplicate", url, title, "same title+creator as " + self.hashes[h]["id"], score)
        t = iso(now())
        entry_labels = [ENTRY_LABEL[e] for e in ev["entry_types"]]
        plat = self.platform_of(url, c.get("platform"))
        trusted = self.an.is_trusted(url, creator)
        l = {
            "id": listing_id(url), "title": title[:140] or "GTA 6 giveaway", "platform": plat, "url": url, "creator": creator, "creator_url": c.get("creator_url", ""),
            "prize": ev["prize"], "entry_method": entry_labels, "entry_types": ev["entry_types"], "start_date": None,
            "end_date": iso(ev["end"]) if ev["end"] else None, "region_text": "", "regions": ev["regions"],
            "verification": "Needs Review", "confidence": score, "source": c["source"], "search_query": c.get("query"),
            "date_first_found": t, "date_last_checked": t, "date_last_seen": t, "date_expired": None,
            "summary": strip_html(body)[:200], "thumbnail": thumb, "tags": ev["tags"] + [plat], "status": "Needs Review",
            "warnings": ev["flags"] + flags, "trusted_source": trusted, "moderation_notes": "", "report_count": 0, "duplicate_hash": h, "fetch_failures": 0,
        }
        if c.get("force_review") or score < self.mod["auto_publish_threshold"]:
            if score < self.mod["review_threshold"] and not c.get("force_review"):
                return self.reject(c, "low confidence", score)
            self.review.append(l); self.stats["review"] += 1
            self.event("review", url, title, "needs human review", score)
        else:
            l.update(status="Active", verification="Verified" if trusted else self.mod["auto_publish_status"])
            self.gv.append(l); self.new.append(l); self.stats["published"] += 1
            self.event("published", url, title, "", score)
        self.index[key] = l
        self.hashes[h] = l

    # ---------- expiry / re-checking ----------
    def expire(self, l, reason):
        l.update(status="Expired", verification="Expired", date_expired=iso(now()))
        l["moderation_notes"] = (l.get("moderation_notes", "") + f" [auto] {reason}").strip()
        self.stats["expired"] += 1
        self.event("expired", l["url"], l["title"], reason)

    def recheck(self, l):
        t = now()
        l["date_last_checked"] = iso(t)
        end = parse_iso(l.get("end_date"))
        if end and end < t:
            return self.expire(l, "end date passed")
        if l.get("sample") or self.args.offline:
            return
        if fetchable(l["url"], self.src) and not l.get("curated") and self.check_budget > 0:
            self.check_budget -= 1
            pg = fetch_page(self.http, l["url"])
            st = pg["status"]
            if st in (404, 410, 451):
                return self.expire(l, f"link returned {st}")
            if st == 200 and pg["html"]:
                info = parse_page(pg["html"])
                if site_root(domain(pg["final_url"])) != site_root(domain(l["url"])):
                    return self.expire(l, "link now redirects to another site")
                text = info["title"] + " " + info["text"]
                ex = self.an.has_exclusion(text)
                if ex:
                    return self.expire(l, f"page says: {ex}")
                if self.an.has_hard_scam(text) or info["has_password"]:
                    return self.expire(l, "scam pattern appeared on page")
                l["fetch_failures"], l["date_last_seen"] = 0, iso(t)
                if not l.get("end_date"):
                    e = self.an.extract_end(text)
                    if e and e > t:
                        l["end_date"] = iso(e)
                return
            if st not in (0, 401, 403, 429) and not pg["blocked"]:
                l["fetch_failures"] = l.get("fetch_failures", 0) + 1
                if l["fetch_failures"] >= self.ex["max_fetch_failures"]:
                    return self.expire(l, f"link failing ({st})")
                return
        hrs = self.ex["unseen_hours"].get(l["platform"].lower(), self.ex["unseen_hours"]["default"])
        seen = parse_iso(l.get("date_last_seen")) or parse_iso(l["date_first_found"])
        if t - seen > timedelta(hours=hrs):
            return self.expire(l, f"not seen in search for {hrs}h")
        if not end and not l.get("curated") and t - parse_iso(l["date_first_found"]) > timedelta(days=self.ex["max_age_days_without_end_date"]):
            self.expire(l, "no end date and listing is old")

    def housekeeping(self):
        t = now()
        active = sorted([l for l in self.gv if l["status"] == "Active"], key=lambda x: x.get("date_last_checked", ""))
        for l in active:
            self.recheck(l)
        for l in list(self.review):
            e = parse_iso(l.get("end_date"))
            if (e and e < t) or t - parse_iso(l["date_first_found"]) > timedelta(days=14):
                self.review.remove(l); self.event("dropped", l["url"], l["title"], "review item expired")
        grace = timedelta(hours=self.ex["grace_hours"])
        for l in list(self.gv):
            if l["status"] != "Active" and t - (parse_iso(l.get("date_expired")) or t) > grace:
                self.gv.remove(l); self.archive.append(l)
        keep = timedelta(days=self.ex["archive_delete_after_days"])
        self.archive[:] = [l for l in self.archive if t - (parse_iso(l.get("date_expired")) or t) < keep]

    def apply_reports(self):
        by_id = {}
        for i in self.github_issues("report"):
            m = re.search(r"ID:\s*(gv-[a-z0-9]+)", i.get("body") or "")
            if m:
                by_id.setdefault(m.group(1), []).append(i)
        for l in list(self.gv) + list(self.review):
            rs = [i for i in by_id.get(l["id"], []) if i["created_at"] > l.get("reports_cleared_at", "")]
            l["report_count"] = len(rs)
            if l in self.gv and l["status"] == "Active" and len(rs) >= self.mod["auto_hide_after_reports"]:
                self.gv.remove(l)
                l.update(status="Reported", verification="Needs Review", moderation_notes=l.get("moderation_notes", "") + " [auto] hidden after reports")
                self.review.append(l)
                self.event("reported", l["url"], l["title"], f"{len(rs)} reports")

    # ---------- main ----------
    def run(self):
        self.build_index()
        if not self.args.offline:
            cands = self.run_providers() + self.submissions()
            self.stats["found"] = len(cands)
            cands.sort(key=lambda c: not c.get("curated"))      # curated entries first so they are never cut by the cap
            for c in cands[: self.src["rate_limits"]["max_candidates_per_run"]]:
                self.process(c)
            self.apply_reports()
        self.housekeeping()
        t = iso(now())
        active = [l for l in self.gv if l["status"] == "Active"]
        self.log["runs"] = (self.log["runs"] + [{"t": t, **self.stats}])[-200:]
        self.log["events"] = self.log["events"][-2000:]
        print("run:", self.stats, "| active:", len(active))
        if self.args.dry_run:
            return
        save("data/giveaways.json", {"updated_at": t, "count": len(active), "repo": self.src["site"]["repo"], "giveaways": self.gv})
        save("data/review-queue.json", {"updated_at": t, "giveaways": self.review})
        save("data/archive.json", {"updated_at": t, "giveaways": self.archive})
        save("data/discovery-log.json", self.log)
        old = load("data/status.json", {"providers": {}})["providers"]
        save("data/status.json", {"updated_at": t, "providers": {**old, **self.health}})
        write_feed(os.path.join(ROOT, "feed.xml"), sorted(active, key=lambda x: x["date_first_found"], reverse=True), self.src["site"]["base_url"])
        discord(self.src["notifications"].get("discord_webhook_env"), self.new)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--offline", action="store_true")
    Scanner(ap.parse_args()).run()
