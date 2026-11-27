#!/usr/bin/env python3
"""Render the neon dossier panels for the GitHub profile README.

Standard library only, so it runs on a bare Actions runner. Data comes from the
GraphQL API when GITHUB_TOKEN is set (the daily workflow); without a token it
falls back to the public REST API and contributions page (local previews).

    python scripts/render.py        # writes assets/*.svg

Everything a person would want to edit (text, projects, stack) sits in the
CONTENT section just below.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import math
import os
import re
import urllib.request
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "vaibhav449")
OUT = Path(__file__).resolve().parent.parent / "assets"

# ── CONTENT ───────────────────────────────────────────────────────────────────

FILE_NO = "VC-0449"
SITE = "vaibhavchaubey.live"
NAME = ("VAIBHAV", "CHAUBEY")
ROLE = "FULL-STACK & AI SYSTEMS ENGINEER"
TAGLINE = "> building LLM systems that cite their sources"

BRIEF = [
    ("ROLE", "Full-Stack & AI Systems Engineer"),
    ("FOCUS", "LLM systems that cite their sources"),
    ("", "Retrieval that knows when to abstain"),
    ("BUILDS", "Realtime apps · automation · data pipelines"),
    ("CORE", "TypeScript · Python · PostgreSQL"),
    ("NODE", SITE),
]

# "*" marks a primary module (drawn lit).
LOADOUT = [
    ("LANG", ["*Python", "*TypeScript", "JavaScript", "SQL"]),
    ("INTERFACE", ["*Next.js", "*React", "Tailwind CSS", "Vite", "Framer Motion", "Streamlit"]),
    ("SERVICES", ["*FastAPI", "Node.js", "Express", "Socket.IO", "WebSockets"]),
    ("INTELLIGENCE", ["*Hybrid RAG", "OpenAI API", "Gemini API", "pgvector", "Chroma", "LLM evals"]),
    ("DATA/QUEUES", ["*PostgreSQL", "Prisma", "MongoDB", "Redis", "RabbitMQ", "Celery"]),
    ("OPS", ["*Docker", "GitHub Actions", "Turborepo", "pnpm", "Playwright", "Caddy"]),
]

# status: omit to derive it from the last push (ACTIVE within 30 days, else STABLE).
CASES = [
    dict(
        repo="Retently", title="RETENTLY",
        mission="AI-native study workspace: notes in, spaced-repetition reviews out.",
        evidence=[
            "Turborepo monorepo: Next.js 16 web, WebSocket realtime, RabbitMQ worker",
            "Failed jobs retry, then park in a parking-lot queue for inspection",
            "Pure, swappable schedulers (FSRS-6, SM-2) over Postgres + pgvector",
        ],
        stack=["Next.js", "RabbitMQ", "pgvector", "Prisma"],
    ),
    dict(
        repo="autoapply", title="AUTOAPPLY",
        mission="Job-application pipeline that keeps a human on the submit button.",
        evidence=[
            "Finds, scores and ranks postings; tailors résumé and answers per job",
            "Playwright form-filling on Celery workers; CAPTCHA walls go to a queue",
            "LLM evals on labelled sets, run 5x because temperature 0 still drifts",
        ],
        stack=["FastAPI", "Celery", "Playwright", "Next.js"],
    ),
    dict(
        repo="incident-triage-copilot", title="INCIDENT TRIAGE", status="BUILDING",
        mission="Explains one production alert at a time, with receipts.",
        evidence=[
            "Log lines are counted into an evidence pack, never embedded",
            "Runbook steps retrieved with FAISS + BM25",
            "Every LLM claim cites an ID; a verifier gates it or the system abstains",
        ],
        stack=["Python", "FastAPI", "Postgres", "Streamlit"],
    ),
    dict(
        repo="HealthShield", title="HEALTHSHIELD",
        mission="Insurance knowledge base that says so when the answer isn't there.",
        evidence=[
            "Hybrid vector + BM25 with absolute scores behind a confidence gate",
            "3-layer PII cascade: regex, embedding similarity, LLM span check",
            "Audit-preserving dedup: superseded records are deprecated, not deleted",
        ],
        stack=["FastAPI", "Chroma", "BM25", "OpenAI"],
    ),
    dict(
        repo="HireScope", title="HIRESCOPE",
        mission="AI mock interviewer built from your own résumé.",
        evidence=[
            "Parses PDF and DOCX résumés into a candidate profile",
            "Gemini writes 6 timed questions: 20s, 60s and 120s by difficulty",
            "Model fallback chain, then a score and a written summary",
        ],
        stack=["React 19", "Express", "MongoDB", "Gemini"],
    ),
    dict(
        repo="basic_chat", title="BASIC_CHAT",
        mission="Realtime chat, built as a lab for monorepos and deploys.",
        evidence=[
            "Shared zod wire contract: rename an event and both apps fail typecheck",
            "Express + Socket.IO API and React + Vite client behind one origin",
            "Turborepo-cached builds; a smoke test runs after every deploy",
        ],
        stack=["Socket.IO", "Vite", "Turborepo", "Docker"],
    ),
]

# ── VISUAL SYSTEM ─────────────────────────────────────────────────────────────

BG = "#05070c"
EDGE = "#14242f"
GRIDLINE = "#0c1821"
DIM = "#4b6a78"
MUTED = "#86a9b8"
TEXT = "#dcf7ff"
CYAN = "#00f3ff"
PINK = "#ff007f"
VIOLET = "#8f6bff"
AMBER = "#ffcf3f"
LIME = "#39ff9e"
SPECTRUM = [CYAN, PINK, VIOLET, AMBER, LIME, "#3d6170"]
LEVELS = {1: "#0d5a78", 2: "#00a8cc", 3: "#00f3ff", 4: "#ff1f8f"}
MONO = "'JetBrains Mono','SFMono-Regular','SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
CHAR = 0.61  # monospace advance per font-size unit, for layout estimates

# A stroke font drawn on a 4 x 6 grid (y down). Chamfered corners give it the HUD cut.
# Each glyph: (advance width, [polyline, ...]); a polyline that ends where it starts is closed.
GLYPHS = {
    "A": (4, [[(0, 6), (0, 1), (1, 0), (4, 0), (4, 6)], [(0, 3.4), (4, 3.4)]]),
    "B": (4, [[(0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3)]]),
    "C": (4, [[(4, 0), (1, 0), (0, 1), (0, 5), (1, 6), (4, 6)]]),
    "D": (4, [[(0, 0), (3, 0), (4, 1), (4, 5), (3, 6), (0, 6), (0, 0)]]),
    "E": (4, [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]]),
    "F": (4, [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]]),
    "G": (4, [[(4, 0), (1, 0), (0, 1), (0, 5), (1, 6), (4, 6), (4, 3.4), (2.2, 3.4)]]),
    "H": (4, [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]]),
    "I": (0, [[(0, 0), (0, 6)]]),
    "J": (4, [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]]),
    "K": (4, [[(0, 0), (0, 6)], [(4, 0), (1, 3), (0, 3)], [(1, 3), (4, 6)]]),
    "L": (4, [[(0, 0), (0, 6), (4, 6)]]),
    "M": (4, [[(0, 6), (0, 0), (2, 2.6), (4, 0), (4, 6)]]),
    "N": (4, [[(0, 6), (0, 0), (4, 6), (4, 0)]]),
    "O": (4, [[(1, 0), (4, 0), (4, 5), (3, 6), (0, 6), (0, 1), (1, 0)]]),
    "P": (4, [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]]),
    "Q": (4, [[(1, 0), (4, 0), (4, 6), (0, 6), (0, 1), (1, 0)], [(2.4, 4.4), (4, 6)]]),
    "R": (4, [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]]),
    "S": (4, [[(4, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]]),
    "T": (4, [[(0, 0), (4, 0)], [(2, 0), (2, 6)]]),
    "U": (4, [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]]),
    "V": (4, [[(0, 0), (0, 3), (2, 6), (4, 3), (4, 0)]]),
    "W": (4, [[(0, 0), (0, 6), (2, 3.6), (4, 6), (4, 0)]]),
    "X": (4, [[(0, 0), (4, 6)], [(4, 0), (0, 6)]]),
    "Y": (4, [[(0, 0), (0, 2), (2, 3.4), (4, 2), (4, 0)], [(2, 3.4), (2, 6)]]),
    "Z": (4, [[(0, 0), (4, 0), (0, 6), (4, 6)]]),
    "0": (4, [[(1, 0), (4, 0), (4, 5), (3, 6), (0, 6), (0, 1), (1, 0)], [(3, 1.5), (1, 4.5)]]),
    "1": (3, [[(0, 1.2), (1.6, 0), (1.6, 6)], [(0, 6), (3, 6)]]),
    "2": (4, [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2.4), (0, 5), (0, 6), (4, 6)]]),
    "3": (4, [[(0, 0), (3, 0), (4, 1), (4, 5), (3, 6), (0, 6)], [(1.2, 3), (4, 3)]]),
    "4": (4, [[(3, 6), (3, 0), (0, 4), (4, 4)]]),
    "5": (4, [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]]),
    "6": (4, [[(4, 0), (1, 0), (0, 1), (0, 6), (4, 6), (4, 3), (0, 3)]]),
    "7": (4, [[(0, 0), (4, 0), (4, 1), (1.6, 6)]]),
    "8": (4, [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)], [(0, 3), (4, 3)]]),
    "9": (4, [[(4, 3), (0, 3), (0, 0), (4, 0), (4, 5), (3, 6), (0, 6)]]),
    "-": (3, [[(0.4, 3), (2.6, 3)]]),
    "_": (4, [[(0, 6), (4, 6)]]),
    "/": (3, [[(0, 6), (3, 0)]]),
    ".": (0, [[(0, 5.4), (0, 6)]]),
    ":": (0, [[(0, 1.6), (0, 2.4)], [(0, 3.6), (0, 4.4)]]),
    "+": (3, [[(1.5, 1.6), (1.5, 4.4)], [(0, 3), (3, 3)]]),
    " ": (2.2, []),
}
TRACK = 1.7  # gap between glyphs, in grid units


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def glyph_paths(text: str, x: float, y: float, size: float):
    s = size / 6
    paths, cx = [], x
    for ch in text.upper():
        adv, strokes = GLYPHS.get(ch, GLYPHS[" "])
        for st in strokes:
            closed = len(st) > 2 and st[0] == st[-1]
            pts = st[:-1] if closed else st
            d = "M" + " L".join(f"{cx + px * s:.1f} {y + py * s:.1f}" for px, py in pts)
            paths.append(d + ("Z" if closed else ""))
        cx += (adv + TRACK) * s
    return paths, cx - x - TRACK * s


def text_width(text: str, size: float) -> float:
    return glyph_paths(text, 0, 0, size)[1]


def stext(text, x, y, size, color, anchor="start", cls="", draw=None, glow=True, sw=None):
    """Stroke-font text with its cap top at y. draw=(delay, step) animates each stroke on."""
    width = text_width(text, size)
    x -= {"start": 0, "middle": width / 2, "end": width}[anchor]
    paths, _ = glyph_paths(text, x, y, size)
    sw = sw or max(1.3, size * 0.1)
    parts = []
    for i, d in enumerate(paths):
        if draw:
            parts.append(f'<path d="{d}" pathLength="1" style="animation-delay:{draw[0] + i * draw[1]:.2f}s"/>')
        else:
            parts.append(f'<path d="{d}"/>')
    attrs = f' class="{cls}"' if cls else ""
    filt = ' filter="url(#glow)"' if glow else ""
    body = "".join(parts)
    return (f'<g{attrs} fill="none" stroke="{color}" stroke-width="{sw:.2f}" '
            f'stroke-linecap="square" stroke-linejoin="miter"{filt}>{body}</g>'), width


def mtext(x, y, s, size=12, color=TEXT, anchor="start", spacing=0, weight=None, cls="", opacity=None):
    extra = f' letter-spacing="{spacing}"' if spacing else ""
    extra += f' font-weight="{weight}"' if weight else ""
    extra += f' class="{cls}"' if cls else ""
    extra += f' opacity="{opacity}"' if opacity is not None else ""
    if anchor != "start":
        extra += f' text-anchor="{anchor}"'
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}"{extra}>{esc(s)}</text>'


BASE_CSS = (
    "text{font-family:" + MONO + "}"
    ".blink{animation:blink 1.1s steps(1) infinite}"
    "@keyframes blink{50%{opacity:0}}"
    ".pulse{animation:pulse 2.4s ease-in-out infinite}"
    "@keyframes pulse{50%{opacity:.3}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def doc(w, h, body, title, css=""):
    defs = (
        f'<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
        '<feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<filter id="bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
        '<feGaussianBlur stdDeviation="6"/></filter>'
        f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<path d="M24 0H0V24" fill="none" stroke="{GRIDLINE}" stroke-width="1"/></pattern>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#ffffff" opacity=".03"/></pattern>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
        f'<style>{BASE_CSS}{css}</style><defs>{defs}</defs>{body}'
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#scan)"/></svg>'
    )


def frame(w, h):
    b = 16
    brackets = (f"M8 {8 + b}V8H{8 + b} M{w - 8 - b} 8H{w - 8}V{8 + b} "
                f"M{w - 8} {h - 8 - b}V{h - 8}H{w - 8 - b} M{8 + b} {h - 8}H8V{h - 8 - b}")
    return (f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>'
            f'<rect width="{w}" height="{h}" rx="12" fill="url(#grid)"/>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="11.5" fill="none" stroke="{EDGE}"/>'
            f'<path d="{brackets}" fill="none" stroke="{CYAN}" stroke-width="1.5" opacity=".75"/>')


def header(w, title, sub, right=""):
    t, tw = stext(title, 28, 22, 15, CYAN)
    out = [t, mtext(28 + tw + 14, 36, sub, 11, MUTED, spacing=1.5)]
    if right:
        out.append(mtext(w - 28, 36, right, 10.5, DIM, "end", spacing=1.5))
    out.append(f'<path d="M28 52.5H{w - 28}" stroke="{EDGE}"/>')
    out.append(f'<path d="M28 52.5H112" stroke="{PINK}" stroke-width="2"/>')
    return "".join(out)


def barcode(x, y, w, h, seed, color=MUTED):
    digest = hashlib.sha256(seed.encode()).digest() * 4
    out, cx, i = [], x, 0
    while cx < x + w - 3:
        b = digest[i]
        bw = 1 + b % 3
        if i % 2 == 0:
            out.append(f'<rect x="{cx}" y="{y}" width="{bw}" height="{h}"/>')
        cx += bw + 1 + (b >> 5) % 2
        i += 1
    return f'<g fill="{color}" opacity=".75">{"".join(out)}</g>'


def chip(x, y, label, primary=False, size=12, h=22, pad=10):
    w = len(label) * size * CHAR + pad * 2
    c = 5
    d = f"M{x + c:.1f} {y}H{x + w:.1f}V{y + h - c}L{x + w - c:.1f} {y + h}H{x:.1f}V{y + c}Z"
    if primary:
        shape = f'<path d="{d}" fill="{CYAN}" fill-opacity=".08" stroke="{CYAN}" stroke-width="1.2"/>'
        color = CYAN
    else:
        shape = f'<path d="{d}" fill="none" stroke="#24414e" stroke-width="1"/>'
        color = MUTED
    label_svg = mtext(x + w / 2, y + h / 2 + size * 0.36, label, size, color, "middle")
    return shape + label_svg, w


def wrap(text, max_chars):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + ([cur] if cur else [])


def shade(hex_color, k):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    if k <= 1:
        r, g, b = (int(c * k) for c in (r, g, b))
    else:
        r, g, b = (int(c + (255 - c) * (k - 1)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── DATA ──────────────────────────────────────────────────────────────────────

def http(url, token=None, body=None, raw=False):
    headers = {"User-Agent": "profile-telemetry", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = r.read().decode("utf-8")
    return payload if raw else json.loads(payload)


GQL = """
query($login: String!) {
  user(login: $login) {
    createdAt
    all: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { name pushedAt
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
    contributionsCollection { contributionCalendar { totalContributions
      weeks { contributionDays { date contributionCount contributionLevel } } } }
  }
}"""
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def parse_ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_graphql(token):
    res = http("https://api.github.com/graphql", token, {"query": GQL, "variables": {"login": USER}})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    u = res["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"], LEVEL[d["contributionLevel"]])
            for wk in cal["weeks"] for d in wk["contributionDays"]]
    repos, langs = [], {}
    for r in u["repositories"]["nodes"]:
        repos.append({"name": r["name"], "pushed": parse_ts(r["pushedAt"])})
        if r["name"].lower() != USER.lower():
            for e in r["languages"]["edges"]:
                langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return dict(created=parse_ts(u["createdAt"]), public_repos=u["all"]["totalCount"],
                repos=repos, langs=langs, days=days, total=cal["totalContributions"])


def fetch_public(token=None):
    api = "https://api.github.com"
    user = http(f"{api}/users/{USER}", token)
    repos, langs = [], {}
    for r in http(f"{api}/users/{USER}/repos?type=owner&per_page=100", token):
        if r["fork"]:
            continue
        repos.append({"name": r["name"], "pushed": parse_ts(r["pushed_at"])})
        if r["name"].lower() != USER.lower():
            for name, size in http(r["languages_url"], token).items():
                langs[name] = langs.get(name, 0) + size
    page = http(f"https://github.com/users/{USER}/contributions", raw=True)
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', page))
    days = []
    for date, cid, level in re.findall(
            r'<td[^>]*data-date="([\d-]+)"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', page):
        m = re.match(r"([\d,]+) contribution", tips.get(cid, ""))
        days.append((dt.date.fromisoformat(date), int(m.group(1).replace(",", "")) if m else 0, int(level)))
    days.sort()
    total = re.search(r"([\d,]+)\s+contributions?\s+in the last year", page)
    return dict(created=parse_ts(user["created_at"]), public_repos=user["public_repos"], repos=repos,
                langs=langs, days=days,
                total=int(total.group(1).replace(",", "")) if total else sum(c for _, c, _ in days))


def save_cache(path, data):
    out = dict(data, created=data["created"].isoformat(),
               repos=[{"name": r["name"], "pushed": r["pushed"].isoformat()} for r in data["repos"]],
               days=[[d.isoformat(), c, lv] for d, c, lv in data["days"]])
    Path(path).write_text(json.dumps(out), encoding="utf-8")


def load_cache(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(raw, created=parse_ts(raw["created"]),
                repos=[{"name": r["name"], "pushed": parse_ts(r["pushed"])} for r in raw["repos"]],
                days=[(dt.date.fromisoformat(d), c, lv) for d, c, lv in raw["days"]])


def load_data():
    # PROFILE_CACHE (local previews only): reuse a saved snapshot instead of spending API calls.
    cache = os.environ.get("PROFILE_CACHE")
    if cache and Path(cache).exists():
        return load_cache(cache)
    token = os.environ.get("GITHUB_TOKEN")
    data = None
    if token:
        try:
            data = fetch_graphql(token)
        except Exception as exc:  # fall back rather than leave the profile without panels
            print(f"GraphQL failed ({exc}); using REST endpoints")
    data = data or fetch_public(token)
    if cache:
        save_cache(cache, data)
    return data


def streaks(days):
    counts = [c for _, c, _ in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today may simply not have started yet
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


# ── PANELS ────────────────────────────────────────────────────────────────────

def render_hero(data):
    w, h = 840, 330
    cx, cy = 700, 166
    css = (
        ".draw path{stroke-dasharray:1;animation:draw 1s cubic-bezier(.6,0,.2,1) both}"
        "@keyframes draw{from{stroke-dashoffset:1;opacity:0}12%{opacity:1}to{stroke-dashoffset:0}}"
        ".flicker{animation:flicker 9s linear 2.5s infinite}"
        "@keyframes flicker{0%,100%{opacity:1}41%{opacity:1}42%{opacity:.55}43%{opacity:1}"
        "77%{opacity:1}78%{opacity:.7}79.5%{opacity:1}}"
        ".gc,.gp{opacity:0;animation:glitch 6.5s steps(1) 3s infinite}"
        ".gp{animation-name:glitch2}"
        "@keyframes glitch{0%,88%,100%{opacity:0;transform:none}89%{opacity:.9;transform:translate(-5px,1px)}"
        "91%{opacity:.6;transform:translate(4px,-1px)}93%{opacity:.8;transform:translate(-2px,0)}95%{opacity:0}}"
        "@keyframes glitch2{0%,88%,100%{opacity:0;transform:none}89%{opacity:.8;transform:translate(5px,-1px)}"
        "91%{opacity:.5;transform:translate(-3px,1px)}93%{opacity:.7;transform:translate(2px,0)}95%{opacity:0}}"
        f".spin{{transform-origin:{cx}px {cy}px;animation:spin 48s linear infinite}}"
        f".spin-r{{transform-origin:{cx}px {cy}px;animation:spin 30s linear infinite reverse}}"
        f".sweep{{transform-origin:{cx}px {cy}px;animation:spin 5s linear infinite}}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".beam{animation:beam 7s linear infinite}"
        "@keyframes beam{from{transform:translateY(-80px)}to{transform:translateY(410px)}}"
    )
    out = [frame(w, h)]
    out.append(
        '<linearGradient id="beamg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{CYAN}" stop-opacity=".07"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
        f'<rect class="beam" x="1" y="0" width="{w - 2}" height="80" fill="url(#beamg)"/>'
    )
    # meta row + ruler
    out.append(mtext(40, 34, f"FILE NO. {FILE_NO}  //  CLEARANCE: PUBLIC  //  SUBJECT: @{USER}", 10.5, DIM,
                     spacing=1.5))
    status = "UPLINK ONLINE"
    dot_x = w - 40 - len(status) * (10.5 * CHAR + 1.5) - 10
    out.append(f'<circle class="pulse" cx="{dot_x:.1f}" cy="30.5" r="3.5" fill="{PINK}"/>')
    out.append(mtext(w - 40, 34, status, 10.5, PINK, "end", spacing=1.5))
    ticks = "".join(f"M{x} 44V{50 if x % 40 == 0 else 47}" for x in range(40, w - 39, 8))
    out.append(f'<path d="{ticks}" stroke="{EDGE}" stroke-width="1"/>')
    # name: glitch ghosts behind, drawn strokes in front
    size, y1, y2 = 60, 74, 152
    for cls, color, dx in (("gc", CYAN, 0), ("gp", PINK, 0)):
        g1, _ = stext(NAME[0], 40 + dx, y1, size, color, glow=False)
        g2, _ = stext(NAME[1], 40 + dx, y2, size, color, glow=False)
        out.append(f'<g class="{cls}">{g1}{g2}</g>')
    n1, w1 = stext(NAME[0], 40, y1, size, TEXT, draw=(0.1, 0.05))
    n2, w2 = stext(NAME[1], 40, y2, size, PINK, draw=(0.5, 0.05))
    out.append(f'<g class="draw flicker">{n1}{n2}</g>')
    # bracket the name block
    nb = max(w1, w2) + 40 + 18
    out.append(f'<path d="M{nb} {y1 - 6}h10v{y2 + size - y1 + 12}h-10" fill="none" stroke="{DIM}" stroke-width="1.2"/>')
    out.append(mtext(nb + 18, y1 + 8, "01", 9.5, DIM))
    out.append(mtext(nb + 18, y2 + size, "02", 9.5, DIM))
    # role + tagline
    out.append(mtext(40, 246, ROLE, 15, TEXT, spacing=3.2, weight=600))
    out.append(f'<text x="40" y="274" font-size="13" fill="{CYAN}">{esc(TAGLINE)}'
               f'<tspan class="blink" fill="{PINK}"> ▌</tspan></text>')
    # emblem
    ring_ticks = []
    for k in range(72):
        a = math.radians(k * 5)
        r1, r2 = 66, (59 if k % 6 == 0 else 62.5)
        ring_ticks.append(f"M{cx + r1 * math.cos(a):.1f} {cy + r1 * math.sin(a):.1f}"
                          f"L{cx + r2 * math.cos(a):.1f} {cy + r2 * math.sin(a):.1f}")
    hexagon = " ".join(f"{cx + 46 * math.cos(math.radians(60 * k + 30)):.1f},"
                       f"{cy + 46 * math.sin(math.radians(60 * k + 30)):.1f}" for k in range(6))
    a2 = math.radians(38)
    out.append(
        f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="{EDGE}"/>'
        f'<circle class="spin" cx="{cx}" cy="{cy}" r="86" fill="none" stroke="{DIM}" stroke-width="1" '
        f'stroke-dasharray="2 6"/>'
        f'<circle class="spin-r" cx="{cx}" cy="{cy}" r="77" fill="none" stroke="{CYAN}" stroke-width="2" '
        f'stroke-dasharray="70 51" opacity=".55"/>'
        f'<path class="spin" d="{"".join(ring_ticks)}" stroke="{DIM}" stroke-width="1"/>'
        f'<g class="sweep"><path d="M{cx} {cy}L{cx + 77} {cy}A77 77 0 0 1 {cx + 77 * math.cos(a2):.1f} '
        f'{cy + 77 * math.sin(a2):.1f}Z" fill="{CYAN}" opacity=".1"/>'
        f'<path d="M{cx} {cy}L{cx + 77} {cy}" stroke="{CYAN}" stroke-width="1.2" opacity=".6"/></g>'
        f'<polygon points="{hexagon}" fill="{BG}" stroke="{PINK}" stroke-width="1.6" filter="url(#glow)"/>'
        f'<path d="M{cx - 104} {cy}h14M{cx + 90} {cy}h14M{cx} {cy - 104}v14M{cx} {cy + 90}v14" '
        f'stroke="{CYAN}" stroke-width="1.2" opacity=".7"/>'
    )
    vc, _ = stext("VC", cx, cy - 15, 30, CYAN, "middle")
    out.append(vc)
    # footer strip
    out.append(f'<path d="M40 292.5H{w - 40}" stroke="{EDGE}"/>')
    since = data["created"].strftime("%b %Y").upper()
    out.append(mtext(40, 314, f"NODE {SITE}   ·   HANDLE @{USER}   ·   ACTIVE SINCE {since}", 10.5, MUTED,
                     spacing=1.2))
    out.append(barcode(w - 220, 302, 180, 16, FILE_NO))
    return doc(w, h, "".join(out), f"{' '.join(NAME).title()} - {ROLE.title()}", css)


def render_dossier(data, now):
    w, h = 840, 300
    out = [frame(w, h), header(w, "DOSSIER", f"// SUBJECT FILE {FILE_NO}",
                                f"SYNC {now:%Y-%m-%d} UTC")]
    # brief
    y = 90
    for label, value in BRIEF:
        if label:
            out.append(mtext(32, y, label, 10.5, DIM, spacing=2))
            out.append(f'<path d="M{32 + len(label) * 10.5 * CHAR + len(label) * 2 + 8:.0f} {y - 3}H122" '
                       f'stroke="{EDGE}" stroke-dasharray="1 3"/>')
        out.append(mtext(132, y, value, 13, TEXT if label else MUTED))
        y += 27
    # stamp
    out.append(f'<g transform="rotate(-6 128 262)" opacity=".85">'
               f'<rect x="32" y="246" width="196" height="30" fill="none" stroke="{PINK}" stroke-width="1.6"/>'
               f'<rect x="36" y="250" width="188" height="22" fill="none" stroke="{PINK}" stroke-width=".6"/>'
               + mtext(130, 266, "OPEN SOURCE · VERIFIED", 11, PINK, "middle", spacing=1.8, weight=700)
               + "</g>")
    out.append(f'<path d="M482.5 72V276" stroke="{EDGE}" stroke-dasharray="2 4"/>')
    # signals
    x0 = 508
    latest = next((r for r in sorted(data["repos"], key=lambda r: r["pushed"], reverse=True)
                   if r["name"].lower() != USER.lower()), None)
    ago = (now - latest["pushed"]).days if latest else 0
    metrics = [
        ("PUBLIC REPOS", str(data["public_repos"]), ""),
        ("LAST PUSH", str(ago), "D AGO"),
        ("SINCE " + data["created"].strftime("%b").upper(), data["created"].strftime("%Y"), ""),
    ]
    for i, (label, value, unit) in enumerate(metrics):
        mx = x0 + i * 100
        out.append(mtext(mx, 84, label, 9.5, DIM, spacing=1.5))
        num, nw = stext(value, mx, 94, 26, CYAN)
        out.append(num)
        if unit:
            out.append(mtext(mx + nw + 7, 120, unit, 10, MUTED, spacing=1))
    if latest:
        out.append(mtext(x0, 146, f"↳ latest: {latest['name']}  ·  {latest['pushed']:%Y-%m-%d}", 11, MUTED))
    # language spectrum
    langs = sorted(data["langs"].items(), key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in langs) or 1
    top = langs[:5]
    rest = total - sum(v for _, v in top)
    if rest > 0:
        top.append(("Other", rest))
    out.append(mtext(x0, 178, "LANGUAGE SPECTRUM // BYTES, OWN PUBLIC REPOS", 9.5, DIM, spacing=1.2))
    bx, bw = x0, w - 32 - x0
    for i, (name, size) in enumerate(top):
        seg = bw * size / total
        out.append(f'<rect x="{bx:.1f}" y="188" width="{max(seg - 2, 1):.1f}" height="10" fill="{SPECTRUM[i]}"/>')
        bx += seg
    for i, (name, size) in enumerate(top):
        lx = x0 + (i % 2) * 160
        ly = 222 + (i // 2) * 22
        out.append(f'<rect x="{lx}" y="{ly - 9}" width="9" height="9" fill="{SPECTRUM[i]}"/>')
        out.append(mtext(lx + 16, ly, name, 11.5, TEXT))
        out.append(mtext(lx + 148, ly, f"{100 * size / total:.1f}%", 11, MUTED, "end"))
    return doc(w, h, "".join(out), "Dossier: role, focus and live GitHub signals")


def render_loadout():
    row_h = 38
    w, h = 840, 74 + len(LOADOUT) * row_h + 14
    out = [frame(w, h), header(w, "LOADOUT", "// SYSTEM MODULES IN FIELD USE")]
    legend_x = w - 28
    out.append(mtext(legend_x, 36, "PRIMARY", 10, CYAN, "end", spacing=1.5))
    out.append(f'<rect x="{legend_x - 72}" y="28" width="9" height="9" fill="{CYAN}" fill-opacity=".15" '
               f'stroke="{CYAN}"/>')
    for i, (label, items) in enumerate(LOADOUT):
        y = 70 + i * row_h
        out.append(mtext(32, y + 15, f"{i + 1:02d}", 10.5, PINK, spacing=1))
        out.append(mtext(58, y + 15, label, 11.5, TEXT, spacing=2, weight=600))
        x = 200
        for item in items:
            primary = item.startswith("*")
            c, cw = chip(x, y, item.lstrip("*"), primary)
            out.append(c)
            x += cw + 8
        if i < len(LOADOUT) - 1:
            out.append(f'<path d="M32 {y + 30.5}H{w - 32}" stroke="{GRIDLINE}"/>')
    return doc(w, h, "".join(out), "Loadout: languages, frameworks, AI, data and ops tools in use")


def case_layout(c):
    mission = wrap(c["mission"], 50)
    evidence = [wrap(e, 52) for e in c["evidence"]]
    return mission, evidence, 74 + len(mission) * 17 + 14 + sum(len(e) * 15 + 7 for e in evidence)


COMET_LAP = 6  # seconds for the light to circle a case card once
# (length as % of the perimeter, colour, opacity, stroke width): a long pink tail, a cyan body, a white-hot head
COMET = [(24, PINK, 0.4, 1.6), (10, CYAN, 0.75, 2), (2.5, "#e8fdff", 1, 2.8)]


def comet(w, h, phase):
    """A light that runs around the card's rounded edge instead of a static border."""
    r, e = 11, 1
    x1, y1 = w - e, h - e
    d = (f"M{e + r} {e}H{x1 - r}A{r} {r} 0 0 1 {x1} {e + r}V{y1 - r}A{r} {r} 0 0 1 {x1 - r} {y1}"
         f"H{e + r}A{r} {r} 0 0 1 {e} {y1 - r}V{e + r}A{r} {r} 0 0 1 {e + r} {e}Z")
    delay = f"animation-delay:-{phase:.2f}s"
    paths = "".join(
        f'<path class="lap{k}" d="{d}" pathLength="100" fill="none" stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" opacity="{op}" style="{delay}"/>'
        for k, (_, color, op, sw) in enumerate(COMET))
    return f'<g class="comet" filter="url(#glow)">{paths}</g>'


def comet_css():
    # Each layer's leading edge sits at the same point, so the head leads and the tails trail behind it.
    rules = []
    for k, (length, *_rest) in enumerate(COMET):
        rules.append(f".lap{k}{{stroke-dasharray:{length} {100 - length};"
                     f"animation:lap{k} {COMET_LAP}s linear infinite}}"
                     f"@keyframes lap{k}{{from{{stroke-dashoffset:{length}}}to{{stroke-dashoffset:{length - 100}}}}}")
    return "".join(rules) + "@media (prefers-reduced-motion:reduce){.comet{display:none}}"


def render_case(i, c, meta, height, now):
    w, h = 410, height
    mission, evidence, _ = case_layout(c)
    pushed = meta.get("pushed")
    status = c.get("status") or ("ACTIVE" if pushed and (now - pushed).days <= 30 else "STABLE")
    scolor = {"ACTIVE": LIME, "BUILDING": AMBER}.get(status, CYAN)
    out = [f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>'
           f'<rect width="{w}" height="{h}" rx="12" fill="url(#grid)"/>']
    out.append(f'<path d="M1 1H124L136 24H1Z" fill="{PINK}" fill-opacity=".12"/>'
               f'<path d="M124 1L136 24H1" fill="none" stroke="{PINK}" stroke-width="1"/>')
    out.append(mtext(16, 17, f"CASE {i:02d}", 10.5, PINK, spacing=2, weight=700))
    out.append(f'<circle class="pulse" cx="{w - 34 - len(status) * (10 * CHAR + 1.5) - 8:.1f}" '
               f'cy="14.5" r="3" fill="{scolor}"/>')
    out.append(mtext(w - 34, 18, status, 10, scolor, "end", spacing=1.5))
    title, _ = stext(c["title"], 20, 38, 19, CYAN)
    out.append(title)
    y = 84
    for line in mission:
        out.append(mtext(20, y, line, 12.5, TEXT))
        y += 17
    y += 12
    for lines in evidence:
        out.append(mtext(20, y, "▸", 11.5, PINK))
        for line in lines:
            out.append(mtext(36, y, line, 11, "#a8cad8"))
            y += 15
        y += 7
    cx = 20
    for item in c["stack"]:
        ch, cw = chip(cx, h - 58, item, size=10, h=18, pad=7)
        out.append(ch)
        cx += cw + 6
    out.append(f'<path d="M20 {h - 29.5}H{w - 20}" stroke="{EDGE}"/>')
    when = f"LAST PUSH {pushed:%Y-%m-%d}" if pushed else ""
    out.append(mtext(20, h - 13, when, 9.5, DIM, spacing=1.2))
    out.append(mtext(w - 20, h - 13, "OPEN FILE ↗", 10, PINK, "end", spacing=1.5, weight=700))
    out.append(comet(w, h, phase=(i - 1) * COMET_LAP / len(CASES) * 2.5 % COMET_LAP))
    return doc(w, h, "".join(out), f"Case {i:02d}: {c['title'].title()} - {c['mission']}", comet_css())


def render_cases_header():
    w, h = 840, 64
    out = [frame(w, h), stext("CASE FILES", 28, 22, 15, CYAN)[0]]
    tw = text_width("CASE FILES", 15)
    out.append(mtext(28 + tw + 14, 36, f"// {len(CASES):02d} RECORDS · SELECT A FILE TO OPEN THE REPO", 11, MUTED,
                     spacing=1.5))
    out.append(mtext(w - 28, 36, "PUBLIC RECORDS", 10.5, DIM, "end", spacing=1.5))
    return doc(w, h, "".join(out), "Case files: selected projects")


def render_skyline(data, now):
    w, h = 840, 444
    days = data["days"]
    start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    cells = [((d - start).days // 7, (d.weekday() + 1) % 7, d, c, lv or (1 if c else 0)) for d, c, lv in days]
    weeks = max(c[0] for c in cells) + 1
    peak_count = max([c[3] for c in cells] + [1])
    UX, UY, VX, VY, HMAX = 12.4, 3.3, -7.6, 6.8, 118
    ox, oy = 118, 190

    def P(wk, wd, z=0.0):
        return ox + wk * UX + wd * VX, oy + wk * UY + wd * VY - z

    def poly(pts, fill, stroke=None, sw=0.6):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{fill}"{s}/>'

    # An <img> SVG can't see the page scroll, so the city rebuilds on a loop instead: a scanner
    # sweeps left to right, buildings rise behind it, hold, then fold away for the next pass.
    cycle = 16
    css = (
        f".b{{transform-box:fill-box;transform-origin:50% 100%;animation:rise {cycle}s infinite both}}"
        "@keyframes rise{0%{transform:scaleY(.02);opacity:0;animation-timing-function:cubic-bezier(.2,.9,.25,1)}"
        "9%{transform:scaleY(1);opacity:1}90%{transform:scaleY(1);opacity:1;animation-timing-function:ease-in}"
        "96%,100%{transform:scaleY(.02);opacity:0}}"
        f".scanner{{animation:scan {cycle}s linear infinite both}}"
        "@keyframes scan{0%{transform:translateX(0);opacity:0}1%{opacity:1}11%{transform:translateX(760px);opacity:1}"
        "12%,100%{transform:translateX(760px);opacity:0}}"
        f".late{{animation:late {cycle}s infinite both}}"
        "@keyframes late{0%,17%{opacity:0}21%,88%{opacity:1}92%,100%{opacity:0}}"
        ".beacon{animation:pulse 1.6s ease-in-out infinite}"
    )
    out = [frame(w, h), header(w, "TELEMETRY", "// CONTRIBUTION SKYLINE · LAST 12 MONTHS",
                                f"SYNC {now:%Y-%m-%d} UTC")]
    out.append(
        '<linearGradient id="scang" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset=".8" stop-color="{CYAN}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity=".55"/></linearGradient>'
        f'<g class="scanner"><rect x="-40" y="60" width="80" height="{h - 100}" fill="url(#scang)"/>'
        f'<path d="M40 60V{h - 40}" stroke="{CYAN}" stroke-width="1.5" opacity=".8"/></g>'
    )
    ground = [P(0, 0), P(weeks, 0), P(weeks, 7), P(0, 7)]
    out.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in ground)}" fill="none" '
               f'stroke="{EDGE}" stroke-dasharray="3 4"/>')
    g = 0.13
    peak = max(cells, key=lambda c: (c[3], c[2]))
    peak_top = None
    for wk, wd, date, count, lv in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):
        a, b = wk + g, wk + 1 - g
        c0, c1 = wd + g, wd + 1 - g
        if count == 0:
            out.append(poly([P(a, c0), P(b, c0), P(b, c1), P(a, c1)], "#0a131b", "#13232e"))
            continue
        z = 5 + (HMAX - 5) * math.sqrt(count / peak_count)
        top = LEVELS[min(lv, 4)]
        faces = (
            poly([P(a, c1), P(b, c1), P(b, c1, z), P(a, c1, z)], shade(top, 0.5)),
            poly([P(b, c0), P(b, c1), P(b, c1, z), P(b, c0, z)], shade(top, 0.3)),
            poly([P(a, c0, z), P(b, c0, z), P(b, c1, z), P(a, c1, z)], top, shade(top, 1.35), 0.7),
        )
        delay = (P(wk, wd)[0] - 40) / 760 * 1.76  # rise just as the scanner passes overhead
        out.append(f'<g class="b" style="animation-delay:{delay:.2f}s">{"".join(faces)}</g>')
        if (wk, wd) == (peak[0], peak[1]):
            peak_top = P(wk + 0.5, wd + 0.5, z)
    # month ticks along the front edge
    last_label = -9
    for wk in range(weeks):
        d = start + dt.timedelta(days=wk * 7)
        if (d.day <= 7 or wk == 0) and wk - last_label >= 3:
            x, y = P(wk, 7.4)
            out.append(mtext(x - 2, y + 12, d.strftime("%b").upper(), 9, DIM, spacing=1))
            last_label = wk
    # peak beacon
    if peak_top and peak[3] > 0:
        px, py = peak_top
        ty = max(py - 34, 70)
        label = f"PEAK {peak[3]} · {peak[2]:%Y-%m-%d}"
        anchor = "end" if px > w - 220 else "start"
        dx = -8 if anchor == "end" else 8
        out.append(f'<g class="late"><path class="beacon" d="M{px:.1f} {py - 3:.1f}V{ty:.1f}" stroke="{PINK}" '
                   f'stroke-width="1.2"/><circle class="beacon" cx="{px:.1f}" cy="{ty:.1f}" r="2.6" fill="{PINK}"/>'
                   + mtext(px + dx, ty + 4, label, 10, PINK, anchor, spacing=1, weight=700) + "</g>")
    # stats block
    current, longest = streaks(days)
    active = sum(1 for _, c, _ in days if c)
    weekday_totals = [0] * 7
    for wk, wd, _, c, _ in cells:
        weekday_totals[wd] += c
    busiest = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][weekday_totals.index(max(weekday_totals))]
    sx = 590
    out.append(mtext(sx, 82, "TOTAL // LAST 12 MONTHS", 9.5, DIM, spacing=1.5))
    num, nw = stext(f"{data['total']:,}".replace(",", " "), sx, 92, 30, CYAN)
    out.append(num)
    out.append(mtext(sx + nw + 9, 122, "CONTRIBUTIONS", 10, MUTED, spacing=1.2))
    stats = [("STREAK NOW", f"{current}D"), ("LONGEST", f"{longest}D"),
             ("ACTIVE DAYS", f"{active}/{len(days)}"), ("BUSIEST DAY", busiest)]
    for i, (label, value) in enumerate(stats):
        x = sx + (i % 2) * 112
        y = 150 + (i // 2) * 34
        out.append(mtext(x, y, label, 9, DIM, spacing=1.4))
        out.append(mtext(x, y + 17, value, 15, TEXT, weight=700))
    # legend
    lx, ly = 32, h - 22
    out.append(mtext(lx, ly, "LESS", 9, DIM, spacing=1))
    for i, lv in enumerate([0, 1, 2, 3, 4]):
        color = "#0a131b" if lv == 0 else LEVELS[lv]
        out.append(f'<rect x="{lx + 34 + i * 14}" y="{ly - 9}" width="10" height="10" fill="{color}" '
                   f'stroke="#1b2f3b" stroke-width=".6"/>')
    out.append(mtext(lx + 34 + 5 * 14 + 4, ly, "MORE   ·   HEIGHT ∝ √COUNT", 9, DIM, spacing=1))
    return doc(w, h, "".join(out), f"Contribution skyline: {data['total']} contributions in the last 12 months", css)


# Pixel-art builder (facing right), one character per pixel. Y hat, K hair, S skin, E eye,
# N shirt, C cyan stripe, P trousers, B boots, H hammer handle, G hammer head.
BUILDER_BODY = [
    "...YYYYY...",
    "..YYYYYYY..",
    "..YYYYYYYYY",
    "...KSSSS...",
    "...SSSES...",
    "...SSSSS...",
    "..NNNNNN...",
    "..NCNNNN...",
    "..NNCNNN...",
    "..NNNCNN...",
    "...PPPP....",
]
BUILDER_LEGS = (["...P..P....", "...P..P....", "..BB..BB..."],
                ["....PP.....", "....PP.....", "...BBBB...."])
BUILDER_ARM = ["...........", "...........", "...........", "........GGG", ".........H.",
               ".........H.", ".........H.", ".......N.H.", "........NS."]
BUILDER_PAL = {"Y": AMBER, "K": "#1a1208", "S": "#c68a5a", "E": "#1a1208", "N": "#0d2238", "C": CYAN,
               "P": "#22303f", "B": "#4a3420", "H": "#8a5a2b", "G": "#9fb3c8"}


def pixels(rows, u):
    out = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            ch, run = row[c], 1
            if ch == ".":
                c += 1
                continue
            while c + run < len(row) and row[c + run] == ch:
                run += 1
            out.append(f'<rect x="{c * u:.1f}" y="{r * u:.1f}" width="{run * u:.1f}" height="{u:.1f}" '
                       f'fill="{BUILDER_PAL[ch]}"/>')
            c += run
    return "".join(out)


def pct(t, total):
    return f"{100 * t / total:.3f}%"


def render_construction(data, now):
    """The builder walks the contribution grid in date order and lays a block on every active day."""
    w, h = 840, 268
    days = data["days"]
    start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    cells = [((d - start).days // 7, (d.weekday() + 1) % 7, d, c, lv or (1 if c else 0)) for d, c, lv in days]
    weeks = max(c[0] for c in cells) + 1
    gx, gy, cs, pitch = 46, 116, 11.5, 14.1

    def centre(wk, wd):
        return gx + wk * pitch + cs / 2, gy + wd * pitch + cs / 2

    stops = [c for c in cells if c[3] > 0]
    # Timeline: walk (manhattan, along the grid), stop, swing, lay the block, move on.
    step, dwell, hit = 0.055, 0.28, 0.14
    est = len(stops) * (dwell + 3 * step) + weeks * step
    k = min(1.0, 40 / est) if est else 1.0  # keep one lap under ~45s however busy the year was
    step, dwell, hit = step * k, dwell * k, hit * k
    # He stands just left of the lot he's building, so the hammer lands on it in plain view.
    reach_x, reach_y = 15.3, 0.8
    x, y = gx - 30, centre(0, stops[0][1] if stops else 3)[1] - reach_y
    t, pos, swings, builds = 0.6, [(0.0, x, y)], [], []
    for wk, wd, _, count, lv in stops:
        tx, ty = centre(wk, wd)
        tx, ty = tx - reach_x, ty - reach_y
        if tx != x:
            t += abs(tx - x) / pitch * step
            x = tx
            pos.append((t, x, y))
        if ty != y:
            t += abs(ty - y) / pitch * step
            y = ty
            pos.append((t, x, y))
        swings.append(t)
        builds.append((wk, wd, lv, t + hit))
        t += dwell
        pos.append((t, x, y))
    exit_x = gx + weeks * pitch + 26
    t += abs(exit_x - x) / pitch * step
    pos.append((t, exit_x, y))
    done, T = t, t + 3.4
    fade = T - 0.8

    css = [f".bw{{animation:walk {T:.2f}s linear infinite}}",
           "@keyframes walk{" + "".join(f"{pct(tt, T)}{{transform:translate({px:.1f}px,{py:.1f}px)}}"
                                       for tt, px, py in pos) + f"100%{{transform:translate({exit_x:.1f}px,{y:.1f}px)}}}}",
           f".bv{{animation:bv {T:.2f}s linear infinite}}",
           f"@keyframes bv{{0%{{opacity:0}}{pct(0.4, T)},{pct(done + 0.2, T)}{{opacity:1}}{pct(done + 0.6, T)},100%{{opacity:0}}}}",
           ".la{animation:la .3s steps(1) infinite}@keyframes la{50%{opacity:0}}",
           ".lb{opacity:0;animation:lb .3s steps(1) infinite}@keyframes lb{50%{opacity:1}}",
           ".bob{animation:bob .3s steps(1) infinite}@keyframes bob{50%{transform:translateY(-1px)}}"]
    swing = ["0%{transform:rotate(0)}"]
    for a in swings:
        swing += [f"{pct(a, T)}{{transform:rotate(0)}}", f"{pct(a + hit * 0.55, T)}{{transform:rotate(-70deg)}}",
                  f"{pct(a + hit, T)}{{transform:rotate(97deg)}}", f"{pct(a + hit + 0.09 * k, T)}{{transform:rotate(0)}}"]
    u = 2.8  # one sprite pixel, in SVG units
    css.append(f".arm{{transform-origin:{7.5 * u:.1f}px {7.2 * u:.1f}px;animation:swing {T:.2f}s linear infinite}}"
               "@keyframes swing{" + "".join(swing) + "100%{transform:rotate(0)}}")
    burst = 0.5 / T * 100
    for name, (dx, dy) in {"ne": (7, -8), "nw": (-7, -8), "se": (8, 3), "sw": (-8, 3)}.items():
        css.append(f".s{name}{{opacity:0;animation:s{name} {T:.2f}s linear infinite}}"
                   f"@keyframes s{name}{{0%{{opacity:1;transform:translate(0,0)}}"
                   f"{burst:.3f}%,100%{{opacity:0;transform:translate({dx}px,{dy}px)}}}}")
    css.append(f".stamp{{opacity:0;animation:stamp {T:.2f}s linear infinite}}"
               f"@keyframes stamp{{0%,{pct(done, T)}{{opacity:0}}{pct(done + 0.25, T)},{pct(fade, T)}{{opacity:1}}"
               f"100%{{opacity:0}}}}")

    out = [frame(w, h), header(w, "CONSTRUCTION", "// CONTRIBUTION GRID · BUILDER ON SITE",
                                f"SYNC {now:%Y-%m-%d} UTC")]
    # empty lots
    lots = "".join(f'<rect x="{gx + wk * pitch:.1f}" y="{gy + wd * pitch:.1f}" width="{cs}" height="{cs}" rx="2"/>'
                   for wk, wd, *_ in cells)
    out.append(f'<g fill="#0a131b" stroke="#13232e" stroke-width=".6">{lots}</g>')
    # blocks, each laid the moment the hammer lands
    for i, (wk, wd, lv, th) in enumerate(builds):
        color = LEVELS[min(lv, 4)]
        p = 100 * th / T
        css.append(f".k{i}{{transform-box:fill-box;transform-origin:50% 50%;animation:k{i} {T:.2f}s linear infinite both}}"
                   f"@keyframes k{i}{{0%,{p:.3f}%{{opacity:0;transform:scale(.2);fill:#ffffff}}"
                   f"{p + 0.5:.3f}%{{opacity:1;transform:scale(1.35);fill:#ffffff}}"
                   f"{p + 1.6:.3f}%,{pct(fade, T)}{{opacity:1;transform:scale(1);fill:{color}}}"
                   f"100%{{opacity:0;transform:scale(1);fill:{color}}}}}")
        bx, by = gx + wk * pitch, gy + wd * pitch
        out.append(f'<rect class="k{i}" x="{bx:.1f}" y="{by:.1f}" width="{cs}" height="{cs}" rx="2" fill="{color}"/>')
        cx, cy = centre(wk, wd)
        spark = AMBER if lv < 4 else PINK
        out.append("".join(f'<rect class="s{d}" x="{cx - 1:.1f}" y="{cy - 1:.1f}" width="2" height="2" fill="{spark}" '
                           f'style="animation-delay:{th:.2f}s"/>' for d in ("ne", "nw", "se", "sw")))
    # axis labels
    for wd, name in ((1, "MON"), (3, "WED"), (5, "FRI")):
        out.append(mtext(14, gy + wd * pitch + 9, name, 8.5, DIM, spacing=1))
    last = -9
    for wk in range(weeks):
        d = start + dt.timedelta(days=wk * 7)
        if (d.day <= 7 or wk == 0) and wk - last >= 3:
            out.append(mtext(gx + wk * pitch, gy + 7 * pitch + 12, d.strftime("%b").upper(), 9, DIM, spacing=1))
            last = wk
    # the builder: walk (position) > visibility > sprite offset so (0,0) is between his boots
    legs_a, legs_b = (pixels(rows, u) for rows in BUILDER_LEGS)
    sprite = (f'<ellipse cx="{5.5 * u:.1f}" cy="{14 * u + 0.5:.1f}" rx="{4 * u:.1f}" ry="{0.9 * u:.1f}" '
              f'fill="#000000" opacity=".55"/>'
              f'<g transform="translate(0 {11 * u:.1f})"><g class="la">{legs_a}</g><g class="lb">{legs_b}</g></g>'
              f'<g class="bob">{pixels(BUILDER_BODY, u)}<g class="arm">{pixels(BUILDER_ARM, u)}</g></g>')
    out.append(f'<g class="bw"><g class="bv"><g transform="translate({-5.5 * u:.1f} {-(14 * u - 5):.1f})">'
               f'{sprite}</g></g></g>')
    # completion stamp
    active = len(stops)
    out.append(f'<g class="stamp"><g transform="rotate(-4 {w - 150} 84)">'
               f'<rect x="{w - 262}" y="68" width="226" height="30" fill="{BG}" stroke="{PINK}" stroke-width="1.6"/>'
               + mtext(w - 149, 88, f"SITE COMPLETE // {active} BLOCKS", 11, PINK, "middle", spacing=1.6, weight=700)
               + "</g></g>")
    # footer: stats + legend
    out.append(mtext(32, h - 20, f"BLOCKS LAID {active}   ·   {data['total']} CONTRIBUTIONS   ·   LAST 12 MONTHS",
                     9.5, MUTED, spacing=1.2))
    lx = w - 210
    out.append(mtext(lx, h - 20, "LESS", 9, DIM, spacing=1))
    for i, lv in enumerate([0, 1, 2, 3, 4]):
        color = "#0a131b" if lv == 0 else LEVELS[lv]
        out.append(f'<rect x="{lx + 34 + i * 14}" y="{h - 29}" width="10" height="10" rx="2" fill="{color}" '
                   f'stroke="#1b2f3b" stroke-width=".6"/>')
    out.append(mtext(lx + 34 + 5 * 14 + 4, h - 20, "MORE", 9, DIM, spacing=1))
    return doc(w, h, "".join(out), f"Construction site: a builder lays {active} blocks across the last 12 months",
               "".join(css))


def render_footer():
    w, h = 840, 96
    out = [frame(w, h), barcode(32, 28, 190, 30, FILE_NO + "-EOF")]
    out.append(mtext(32, 76, f"{FILE_NO} · SYS", 9, DIM, spacing=2))
    title, _ = stext("END OF FILE", w / 2, 30, 16, TEXT, "middle")
    out.append(title)
    out.append(mtext(w / 2, 72, "this dossier rebuilds itself daily from live GitHub data", 10.5, MUTED, "middle"))
    out.append(mtext(w - 32, 44, "TRANSMIT ↗", 10.5, PINK, "end", spacing=2, weight=700))
    out.append(mtext(w - 32, 66, SITE, 13, CYAN, "end"))
    return doc(w, h, "".join(out), f"End of file - {SITE}")


def main():
    data = load_data()
    now = dt.datetime.now(dt.timezone.utc)
    OUT.mkdir(parents=True, exist_ok=True)
    pushed = {r["name"].lower(): r["pushed"] for r in data["repos"]}
    files = {
        "hero.svg": render_hero(data),
        "dossier.svg": render_dossier(data, now),
        "loadout.svg": render_loadout(),
        "cases.svg": render_cases_header(),
        "skyline.svg": render_skyline(data, now),
        "construction.svg": render_construction(data, now),
        "footer.svg": render_footer(),
    }
    height = max(case_layout(c)[2] for c in CASES) + 66
    for i, c in enumerate(CASES, 1):
        meta = {"pushed": pushed.get(c["repo"].lower())}
        files[f"case-{c['repo'].lower()}.svg"] = render_case(i, c, meta, height, now)
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
    print(f"wrote {len(files)} panels to {OUT} - {data['total']} contributions, {len(data['repos'])} repos")


if __name__ == "__main__":
    main()
