#!/usr/bin/env python3
"""Moderation CLI (also used by the 'Moderate' GitHub Action).

  python scripts/moderate.py list
  python scripts/moderate.py approve  gv-abc123 [Verified|Likely|Unverified]
  python scripts/moderate.py reject   gv-abc123          (also blocks that URL forever)
  python scripts/moderate.py remove   gv-abc123          (take down a live listing)
  python scripts/moderate.py edit     gv-abc123 field value   (value may be JSON)
  python scripts/moderate.py block-domain example.com
  python scripts/moderate.py block-creator "Some Name"
  python scripts/moderate.py trust-creator "Some Name"
  python scripts/moderate.py purge-samples
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from lib.util import iso, load, normalize_url, now, parse_iso, save

gv_f, rv_f, ar_f = "data/giveaways.json", "data/review-queue.json", "data/archive.json"
gv, rv, ar = load(gv_f), load(rv_f), load(ar_f)
mod = load("config/moderation.json")


def find(i):
    for name, box in (("giveaways", gv), ("review", rv), ("archive", ar)):
        for l in box["giveaways"]:
            if l["id"] == i:
                return name, box, l
    sys.exit(f"No listing with id {i}")


def write():
    t = iso(now())
    gv["updated_at"], rv["updated_at"], ar["updated_at"] = t, t, t
    gv["count"] = sum(1 for l in gv["giveaways"] if l["status"] == "Active")
    save(gv_f, gv); save(rv_f, rv); save(ar_f, ar); save("config/moderation.json", mod)


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "list":
        for l in rv["giveaways"]:
            print(f"{l['id']}  score={l['confidence']:>3}  {l['status']:<12} {l['platform']:<9} {l['title'][:60]}\n    {l['url']}")
    elif cmd == "approve":
        _, box, l = find(a[1])
        end = parse_iso(l.get("end_date"))
        if end and end < now():
            sys.exit("That giveaway has already ended.")
        box["giveaways"].remove(l)
        l.update(status="Active", verification=a[2] if len(a) > 2 else "Verified", reports_cleared_at=iso(now()), report_count=0, date_expired=None)
        l["moderation_notes"] = (l.get("moderation_notes", "") + " [moderator] approved").strip()
        gv["giveaways"].append(l)
    elif cmd == "reject":
        _, box, l = find(a[1])
        box["giveaways"].remove(l)
        mod["rejected_urls"].append(normalize_url(l["url"]))
    elif cmd == "remove":
        _, box, l = find(a[1])
        box["giveaways"].remove(l)
        l.update(status="Removed", verification="Expired", date_expired=iso(now()))
        ar["giveaways"].append(l)
        mod["rejected_urls"].append(normalize_url(l["url"]))
    elif cmd == "edit":
        _, _, l = find(a[1])
        try:
            val = json.loads(a[3])
        except ValueError:
            val = a[3]
        l[a[2]] = val
    elif cmd == "block-domain":
        mod["blocked_domains"].append(a[1])
    elif cmd == "block-creator":
        mod["blocked_creators"].append(a[1])
    elif cmd == "trust-creator":
        mod["trusted_creators"].append(a[1])
    elif cmd == "purge-samples":
        for box in (gv, rv, ar):
            box["giveaways"] = [l for l in box["giveaways"] if not l.get("sample")]
    else:
        sys.exit(__doc__)
    write()
    print("done")


main(sys.argv[1:])
