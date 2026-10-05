#!/usr/bin/env python3
"""Regenerate languages.svg from live GitHub data and refresh the Substack
post list in README.md. Standard library only; run by .github/workflows/profile.yml."""
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "6sLOGAN78")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
FEED = "https://thelearningcurvenjack.substack.com/feed"
AUTHOR = "ayush maurya"
# Markup/notebook bytes swamp real source code, so they are left out.
EXCLUDE = {"Jupyter Notebook", "HTML", "CSS", "SCSS", "TeX", "Makefile", "Dockerfile", "Procfile"}
TOP = 6
SHADES = ["#ffffff", "#d4d4d8", "#a1a1aa", "#71717a", "#52525b", "#3f3f46"]
ROOT = Path(__file__).resolve().parent.parent
R = 70


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def gh(path):
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return json.loads(get(f"https://api.github.com{path}", headers))


def language_totals():
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    repos = [r for r in repos if not r["fork"]]
    totals, counted = {}, 0
    for repo in repos:
        # A repo deleted or made private mid-run 404s; skip it rather than fail.
        try:
            langs = gh(f"/repos/{repo['full_name']}/languages")
        except urllib.error.HTTPError as err:
            print(f"skipped {repo['full_name']}: {err}", file=sys.stderr)
            continue
        counted += 1
        for lang, size in langs.items():
            if lang not in EXCLUDE:
                # Square root per repo so one vendored SDK dump cannot dominate.
                totals[lang] = totals.get(lang, 0) + math.sqrt(size)
    return totals, counted


def render_svg(totals, repo_count):
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    top, rest = ranked[:TOP], ranked[TOP:]
    if rest:
        top = ranked[: TOP - 1] + [("Other", sum(size for _, size in rest))]
    total = sum(size for _, size in top)
    rows = [(name, size / total * 100) for name, size in top]

    segments, legend, start = [], [], 0.0
    for i, (name, pct) in enumerate(rows):
        shade, end = SHADES[i], start + min(pct, 99.99) / 100 * 2 * math.pi
        x1, y1 = 150 + R * math.sin(start), 135 - R * math.cos(start)
        x2, y2 = 150 + R * math.sin(end), 135 - R * math.cos(end)
        segments.append(
            f'    <path d="M {x1:.2f} {y1:.2f} A {R} {R} 0 {int(end - start > math.pi)} 1 {x2:.2f} {y2:.2f}"'
            f' fill="none" stroke="{shade}" stroke-width="26" />'
        )
        start = end
        legend.append(
            f'    <g transform="translate(0, {i * 24})">\n'
            f'      <rect x="0" y="0" width="10" height="10" rx="2" fill="{shade}" />\n'
            f'      <text x="18" y="9" class="label">{escape(name)}</text>\n'
            f'      <text x="280" y="9" class="percent" text-anchor="end">{pct:.1f}%</text>\n'
            f'      <rect x="110" y="2" width="115" height="6" class="bar-bg" />\n'
            f'      <rect x="110" y="2" width="{max(115 * pct / 100, 2):.2f}" height="6" rx="3" fill="{shade}" />\n'
            f"    </g>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 260" width="100%">
  <defs>
    <style>
      .title {{ font-family: 'Orbitron', 'JetBrains Mono', monospace; font-weight: 800; font-size: 13px; fill: #ffffff; letter-spacing: 2px; }}
      .subtitle {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 10px; fill: #71717a; letter-spacing: 1px; }}
      .label {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; fill: #fafafa; font-weight: 600; }}
      .percent {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; fill: #a1a1aa; font-weight: 400; }}
      .center-title {{ font-family: 'Orbitron', 'JetBrains Mono', monospace; font-size: 16px; fill: #ffffff; font-weight: 800; text-anchor: middle; }}
      .center-sub {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 8px; fill: #71717a; text-anchor: middle; letter-spacing: 1px; }}
      .bar-bg {{ fill: #18181b; rx: 3px; }}
      .pulse {{ animation: pulse 2s ease-in-out infinite; }}
      @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.25; }} }}
    </style>

    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255, 255, 255, 0.02)" stroke-width="1"/>
    </pattern>
  </defs>

  <rect width="650" height="260" rx="10" fill="#030303" stroke="#27272a" stroke-width="1.5" />
  <rect width="650" height="260" rx="10" fill="url(#grid)" />

  <g transform="translate(25, 30)">
    <text x="0" y="0" class="title">MOST USED LANGUAGES</text>
    <text x="0" y="16" class="subtitle">// TELEMETRY &amp; CODEBASE DISTRIBUTION</text>
    <line x1="0" y1="26" x2="600" y2="26" stroke="#27272a" stroke-width="1" stroke-dasharray="4 4" />
  </g>

  <g transform="translate(0, 15)">
    <circle cx="150" cy="135" r="{R}" fill="none" stroke="#18181b" stroke-width="26" />
{chr(10).join(segments)}
    <circle cx="150" cy="135" r="54" fill="#030303" stroke="#27272a" stroke-width="1" />
    <text x="150" y="134" class="center-title">{repo_count}</text>
    <text x="150" y="148" class="center-sub">PUBLIC REPOS</text>
  </g>

  <g transform="translate(280, 85)">
{chr(10).join(legend)}
  </g>

  <g transform="translate(25, 238)">
    <circle class="pulse" cx="4" cy="-4" r="3" fill="#ffffff" />
    <text x="14" y="-1" class="subtitle" style="font-size: 8px;">LIVE // AUTO-GENERATED DAILY FROM GITHUB API</text>
  </g>
</svg>
"""


def substack_posts():
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    posts = []
    for item in ET.fromstring(get(FEED)).iter("item"):
        if AUTHOR in (item.findtext("dc:creator", "", ns) or "").lower():
            posts.append((item.findtext("title", "").strip(), item.findtext("link", "").strip()))
    return posts


def update_readme(posts):
    readme = ROOT / "README.md"
    block = "\n".join(f'- <a href="{escape(link)}"><b>{escape(title)}</b></a>' for title, link in posts)
    text = readme.read_text()
    new = re.sub(
        r"(<!-- SUBSTACK:START -->).*?(<!-- SUBSTACK:END -->)",
        lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}",
        text,
        flags=re.S,
    )
    if new != text:
        readme.write_text(new)


def main():
    totals, repo_count = language_totals()
    if not totals:
        sys.exit("no language data returned")
    (ROOT / "languages.svg").write_text(render_svg(totals, repo_count))

    # The feed only carries recent posts and may be unreachable from CI;
    # in either case keep whatever the README already lists.
    try:
        posts = substack_posts()
    except Exception as err:
        print(f"substack feed skipped: {err}", file=sys.stderr)
        posts = []
    if posts:
        update_readme(posts)


if __name__ == "__main__":
    main()
