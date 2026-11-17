(() => {
"use strict";
const REPO = "welshman/gta6-giveaway-directory";
const PAGE = 12;
const ICONS = {Twitch:"🟣",Kick:"🟢",X:"✖️",YouTube:"▶️",Discord:"💬",Reddit:"🟠",Instagram:"📸",TikTok:"🎵",Facebook:"📘",Website:"🌐"};
const $ = (s) => document.querySelector(s);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  kids.flat().forEach((c) => c != null && n.append(c));
  return n;
};
const S = { active: [], ended: [], status: null, view: "active", shown: PAGE, quick: new Set(), favOnly: false,
  favs: new Set(JSON.parse(localStorage.getItem("favs") || "[]")) };

const safeUrl = (u) => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x.href : "#"; } catch { return "#"; } };
const lower = (s) => String(s || "").toLowerCase();
const HOUR = 36e5;

function timeLeft(iso) {
  if (!iso) return "End date not stated";
  const ms = new Date(iso) - Date.now();
  if (ms <= 0) return "Ended";
  const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / HOUR), m = Math.floor(ms % HOUR / 6e4);
  return "Ends in " + (d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`);
}
const verLabel = (v) => ({Verified:"✔ Verified",Likely:"◐ Likely",Unverified:"? Unverified",Expired:"✖ Expired"}[v] || "? " + v);
const issueUrl = (type, g) => `https://github.com/${REPO}/issues/new?labels=report&title=${encodeURIComponent(`[Report:${type}] ${g.id}`)}&body=${encodeURIComponent(`ID: ${g.id}\nType: ${type}\nURL: ${g.url}\n\nDetails (optional):\n`)}`;

function card(g, ended) {
  const link = safeUrl(g.url);
  const row = (k, v) => v ? [el("dt", { text: k }), el("dd", { text: v })] : [];
  const reports = [["Report this giveaway", "other"], ["This looks like a scam", "scam"], ["This has ended", "ended"], ["Broken link", "broken"]];
  return el("article", { class: "card" + (ended ? " ended" : ""), "data-id": g.id },
    el("div", { class: "top-line" },
      el("span", { class: "plat" }, el("span", { "aria-hidden": "true", text: (ICONS[g.platform] || "🌐") + " " }), g.platform),
      el("span", { class: "badge v-" + lower(g.verification), text: verLabel(g.verification) })),
    el("h3", { text: g.title }),
    el("dl", {},
      row("By", g.creator), row("Prize", g.prize), row("Enter", (g.entry_method || []).join(", ")),
      row("Region", g.region_text || ((g.regions || []).join(", "))),
      [el("dt", { text: "Ends" }), el("dd", { class: "ends", "data-end": g.end_date || "", text: ended ? "Ended – can't enter" : timeLeft(g.end_date) })]),
    g.summary ? el("p", { text: g.summary }) : null,
    ...(g.warnings || []).map((w) => el("p", { class: "warn", text: "⚠ " + w })),
    el("div", { class: "tags" }, (g.tags || []).slice(0, 6).map((t) => el("span", { text: t }))),
    el("div", { class: "actions" },
      el("a", { class: "btn", href: link, target: "_blank", rel: "noopener noreferrer", "aria-disabled": ended ? "true" : null,
        "aria-label": `${ended ? "Ended" : "Enter giveaway"}: ${g.title}`, text: ended ? "Ended" : "Enter Giveaway" }),
      el("button", { class: "btn ghost small", type: "button", onclick: (e) => copy(link, e.target), text: "Copy link" }),
      el("button", { class: "btn ghost small", type: "button", "aria-pressed": S.favs.has(g.id), "aria-label": "Save giveaway",
        onclick: (e) => fav(g.id, e.target), text: S.favs.has(g.id) ? "★ Saved" : "☆ Save" })),
    el("details", { class: "report" }, el("summary", { text: "Report a problem" }),
      reports.map(([label, t]) => el("a", { href: issueUrl(t, g), target: "_blank", rel: "noopener noreferrer", text: label }))));
}

async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); btn.textContent = "Copied ✓"; } catch { btn.textContent = "Copy failed"; }
  setTimeout(() => (btn.textContent = "Copy link"), 1500);
}
function fav(id, btn) {
  S.favs.has(id) ? S.favs.delete(id) : S.favs.add(id);
  localStorage.setItem("favs", JSON.stringify([...S.favs]));
  btn.textContent = S.favs.has(id) ? "★ Saved" : "☆ Save";
  btn.setAttribute("aria-pressed", S.favs.has(id));
}

function filtered(list) {
  const q = lower($("#q").value).split(/\s+/).filter(Boolean);
  const pf = $("#f-platform").value, vf = $("#f-ver").value, rf = $("#f-region").value, ef = $("#f-entry").value;
  const now = Date.now();
  return list.filter((g) => {
    const hay = lower([g.title, g.creator, g.platform, g.prize, g.summary, (g.tags || []).join(" "), (g.entry_method || []).join(" ")].join(" "));
    if (!q.every((w) => hay.includes(w))) return false;
    if (pf !== "all" && g.platform !== pf) return false;
    if (vf !== "all" && g.verification !== vf) return false;
    if (rf !== "all" && !((g.regions || []).includes(rf) || (rf === "uk" && (g.regions || []).includes("international")))) return false;
    if (ef !== "all" && !(g.entry_types || []).includes(ef)) return false;
    if (S.favOnly && !S.favs.has(g.id)) return false;
    const end = g.end_date ? new Date(g.end_date) - now : null;
    if (S.quick.has("soon") && !(end !== null && end > 0 && end < 24 * HOUR)) return false;
    if (S.quick.has("new") && !(now - new Date(g.date_first_found) < 24 * HOUR)) return false;
    if (S.quick.has("nopurchase") && !(g.tags || []).includes("No purchase necessary")) return false;
    if (S.quick.has("verified") && g.verification !== "Verified") return false;
    if (S.quick.has("official") && !g.trusted_source) return false;
    return true;
  });
}
function sorted(list) {
  const s = $("#sort").value, t = (x) => (x ? new Date(x).getTime() : 0);
  const cmp = {
    ending: (a, b) => (a.end_date ? 0 : 1) - (b.end_date ? 0 : 1) || (a.end_date && b.end_date ? t(a.end_date) - t(b.end_date) : 0) || t(b.date_first_found) - t(a.date_first_found),
    newest: (a, b) => t(b.date_first_found) - t(a.date_first_found),
    verified: (a, b) => t(b.date_last_checked) - t(a.date_last_checked),
    az: (a, b) => a.title.localeCompare(b.title),
  }[s];
  return [...list].sort(cmp);
}

function render() {
  const cards = $("#cards"); cards.replaceChildren();
  const isEnded = S.view === "ended";
  $("#status").hidden = S.view !== "status";
  $("#controls").hidden = S.view === "status";
  $("#cards").hidden = $("#more").hidden = S.view === "status";
  if (S.view === "status") { $("#empty").hidden = true; return renderStatus(); }
  const all = sorted(filtered(isEnded ? S.ended : S.active));
  $("#empty").hidden = all.length > 0;
  if (!all.length) $("#empty").textContent = isEnded ? "Nothing has ended recently."
    : S.active.length ? "No giveaways match your filters. Try clearing a filter." : "No active giveaways right now. Check back soon, since we scan every hour.";
  all.slice(0, S.shown).forEach((g) => cards.append(card(g, isEnded)));
  $("#more").hidden = all.length <= S.shown;
  $("#more").textContent = `Load more (${all.length - S.shown} left)`;
}

function renderStatus() {
  const b = $("#status-body"); b.replaceChildren();
  const st = S.status;
  if (!st) return b.append(el("p", { text: "No status data yet." }));
  const rows = Object.entries(st.providers || {}).map(([n, p]) => el("tr", {},
    el("td", { text: n }), el("td", { text: p.ok ? "✔ OK" : p.rate_limited ? "⚠ Rate limited" : p.skipped ? "– Skipped" : "✖ " + (p.error || "Failed") }),
    el("td", { text: String(p.results ?? "–") }), el("td", { text: p.last_run ? new Date(p.last_run).toLocaleString() : "–" })));
  b.append(el("table", {}, el("thead", {}, el("tr", {}, ["Source", "Status", "Results", "Last scanned"].map((h) => el("th", { text: h })))), el("tbody", {}, rows)));
}

function tick() {
  document.querySelectorAll(".card:not(.ended) [data-end]").forEach((n) => { if (n.dataset.end) n.textContent = timeLeft(n.dataset.end); });
}

async function load() {
  const get = async (p, req) => { try { const r = await fetch(p, { cache: "no-cache" }); if (!r.ok) throw 0; return await r.json(); } catch { if (req) throw 0; return null; } };
  try {
    const [g, a, st] = await Promise.all([get("data/giveaways.json", true), get("data/archive.json"), get("data/status.json")]);
    const list = g.giveaways || [];
    S.active = list.filter((x) => x.status === "Active");
    S.ended = [...list.filter((x) => x.status === "Expired"), ...((a && a.giveaways) || [])].sort((x, y) => new Date(y.date_expired) - new Date(x.date_expired));
    S.status = st;
    $("#count").textContent = S.active.length;
    $("#updated").textContent = g.updated_at ? new Date(g.updated_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "unknown";
    $("#updated").setAttribute("datetime", g.updated_at || "");
    [...new Set(S.active.map((x) => x.platform))].sort().forEach((p) => $("#f-platform").append(el("option", { value: p, text: p })));
    $("#loading").hidden = true;
    checkNew();
    render();
  } catch {
    $("#loading").hidden = true; $("#error").hidden = false;
  }
}

function checkNew() {
  const seen = new Set(JSON.parse(localStorage.getItem("seen") || "[]"));
  const fresh = S.active.filter((g) => !seen.has(g.id));
  if (localStorage.getItem("notify") === "1" && fresh.length && "Notification" in window && Notification.permission === "granted" && seen.size)
    new Notification("New GTA 6 giveaways", { body: `${fresh.length} new giveaway(s) added.` });
  localStorage.setItem("seen", JSON.stringify(S.active.map((g) => g.id)));
}

function bind() {
  ["#q", "#f-platform", "#f-ver", "#f-region", "#f-entry", "#sort"].forEach((s) => $(s).addEventListener("input", () => { S.shown = PAGE; render(); }));
  document.querySelectorAll("[data-quick]").forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.quick; S.quick.has(k) ? S.quick.delete(k) : S.quick.add(k);
    b.setAttribute("aria-pressed", S.quick.has(k)); S.shown = PAGE; render();
  }));
  $("#favonly").addEventListener("click", (e) => { S.favOnly = !S.favOnly; e.target.setAttribute("aria-pressed", S.favOnly); render(); });
  $("#more").addEventListener("click", () => { S.shown += PAGE; render(); });
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("is-on", x === t));
    S.view = t.dataset.view; S.shown = PAGE; render();
  }));
  $("#notify").addEventListener("click", async (e) => {
    if (!("Notification" in window)) return alert("Your browser doesn't support notifications.");
    const on = localStorage.getItem("notify") !== "1";
    if (on && (await Notification.requestPermission()) !== "granted") return;
    localStorage.setItem("notify", on ? "1" : "0"); e.target.setAttribute("aria-pressed", on);
  });
  $("#notify").setAttribute("aria-pressed", localStorage.getItem("notify") === "1");
  $("#theme").addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = t; localStorage.setItem("theme", t);
  });
  $("#suggest").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const body = `URL: ${f.get("url")}\nTitle: ${f.get("title")}\nCreator: ${f.get("creator") || ""}\nEnds: ${f.get("ends") || ""}\n`;
    window.open(`https://github.com/${REPO}/issues/new?labels=submission&title=${encodeURIComponent("[Submission] " + f.get("title"))}&body=${encodeURIComponent(body)}`, "_blank", "noopener,noreferrer");
  });
}

const saved = localStorage.getItem("theme"); if (saved) document.documentElement.dataset.theme = saved;
bind(); load(); setInterval(tick, 60000);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
})();
