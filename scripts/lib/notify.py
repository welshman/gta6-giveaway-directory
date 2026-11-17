"""Outbound notifications and the RSS feed."""
import os
from xml.sax.saxutils import escape
import requests


def discord(webhook_env, listings):
    url = os.environ.get(webhook_env or "", "")
    if not url or not listings:
        return
    lines = [f"**{g['platform']}** - {g['title']} ({g['verification']})\n<{g['url']}>" for g in listings[:10]]
    try:
        requests.post(url, json={"content": "New GTA 6 giveaways found:\n" + "\n".join(lines)}, timeout=10)
    except requests.RequestException:
        pass


def write_feed(path, listings, base_url):
    items = "".join(
        f"<item><title>{escape(g['title'])}</title><link>{escape(g['url'])}</link><guid isPermaLink=\"false\">{escape(g['id'])}</guid>"
        f"<description>{escape(g.get('summary') or g.get('prize') or '')}</description></item>"
        for g in listings[:30])
    xml = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>GTA 6 Giveaway Directory</title>'
           f"<link>{escape(base_url)}</link><description>Newly found GTA 6 giveaways</description>{items}</channel></rss>\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
