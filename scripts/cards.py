#!/usr/bin/env python3
"""Generate self-hosted GitHub stat and repo cards as SVG.

Replaces github-readme-stats / github-profile-trophy which rely on
shared public instances that go down or hit rate limits.

Run:
    python scripts/cards.py --user s7ex-j --projects assets/projects.json --out assets

Requires a PAT with `repo` scope in METRICS_TOKEN (or GITHUB_TOKEN fallback)
to read contribution graph and private repo stats.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ─── Constants ──────────────────────────────────────────────────────────────
CARD_W, CARD_H = 480, 195
AVATAR_SIZE = 56
THEMES = {
    "dark": {
        "bg": "#0D1628",
        "panel": "#101B30",
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "accent": "#10B981",
        "accent2": "#22D3EE",
        "title": "#93A9EE",
    },
    "light": {
        "bg": "#FFFFFF",
        "panel": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "accent": "#10B981",
        "accent2": "#0891B2",
        "title": "#3B4A7A",
    },
}
FONT = 'font-family="ui-monospace,SFMono-Regular,Consolas,monospace"'
MONO = FONT

# ─── Helpers ────────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def num_fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".rstrip("0").rstrip(".")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".rstrip("0").rstrip(".")
    return str(n)


def make_svg_card(
    theme: str,
    title: str,
    rows: list[tuple[str, str]],
    *,
    icon: str | None = None,
    subtitle: str | None = None,
) -> str:
    """Build a single 480×195 stat card."""
    t = THEMES[theme]
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-labelledby="title">',
        f'<title id="title">{esc(title)}</title>',
        '<defs>',
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="{t["panel"]}" '
        'flood-opacity=".35"/></filter>',
        "</defs>",
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{t["bg"]}" '
        f'stroke="{t["line"]}" filter="url(#shadow)"/>',
        f'<rect x="16" y="16" width="448" height="38" rx="6" fill="{t["panel"]}"/>',
        f'<text x="20" y="41" fill="{t["title"]}" {MONO} font-size="13" font-weight="700">{esc(title)}</text>',
    ]

    if icon:
        parts.append(
            f'<text x="440" y="41" text-anchor="end" fill="{t["accent2"]}" {MONO} '
            f'font-size="20">{esc(icon)}</text>'
        )

    if subtitle:
        parts.append(
            f'<text x="20" y="60" fill="{t["muted"]}" {MONO} font-size="11">{esc(subtitle)}</text>'
        )

    y_start = 72 if subtitle else 60
    for i, (label, value) in enumerate(rows):
        y = y_start + i * 30
        parts.extend([
            f'<text x="24" y="{y}" fill="{t["muted"]}" {MONO} font-size="13">{esc(label)}</text>',
            f'<text x="{CARD_W - 24}" y="{y}" text-anchor="end" fill="{t["text"]}" '
            f'{MONO} font-size="13" font-weight="600">{esc(value)}</text>',
        ])

    parts.append("</svg>")
    return "".join(parts)


def make_repo_card(
    theme: str,
    repo: dict[str, Any],
    *,
    show_lang: bool = True,
    icon: str | None = None,
) -> str:
    """Build a repo card (wider, shows description + stars/forks + lang)."""
    t = THEMES[theme]
    name = repo.get("name", "")
    desc = repo.get("description", "No description")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    lang = repo.get("language", "—")
    updated = repo.get("pushed_at", "")
    url = repo.get("html_url", "")

    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            updated_fmt = dt.strftime("%b %d, %Y")
        except Exception:
            updated_fmt = updated[:10]
    else:
        updated_fmt = "—"

    W, H = 480, 220
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title">',
        f'<title id="title">{esc(name)}</title>',
        '<defs>',
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="{t["panel"]}" '
        'flood-opacity=".35"/></filter>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="12" fill="{t["bg"]}" '
        f'stroke="{t["line"]}" filter="url(#shadow)"/>',
        f'<a href="{esc(url)}" target="_blank" rel="noopener">',
        f'<rect x="16" y="16" width="448" height="188" rx="6" fill="{t["panel"]}" '
        'style="transition:fill .15s"/>',
        "</a>",
        f'<text x="20" y="40" fill="{t["title"]}" {MONO} font-size="15" font-weight="700">'
        f'{esc(name)}</text>',
    ]
    if icon:
        parts.append(
            f'<text x="440" y="40" text-anchor="end" fill="{t["accent2"]}" {MONO} '
            f'font-size="20">{esc(icon)}</text>'
        )
    parts.extend([
        f'<text x="20" y="62" fill="{t["muted"]}" {MONO} font-size="11" '
        f'style="max-width:400px">{esc((desc or "No description")[:90])}{"…" if desc and len(desc) > 90 else ""}</text>',
        f'<text x="20" y="90" fill="{t["accent"]}" {MONO} font-size="12">★ {num_fmt(stars)}</text>',
        f'<text x="130" y="90" fill="{t["muted"]}" {MONO} font-size="12">⑂ {num_fmt(forks)}</text>',
    ])
    if show_lang and lang:
        parts.append(
            f'<text x="240" y="90" fill="{t["accent2"]}" {MONO} font-size="12">{esc(lang)}</text>'
        )
    parts.append(
        f'<text x="20" y="118" fill="{t["muted"]}" {MONO} font-size="11">Updated {esc(updated_fmt)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# ─── GitHub API ──────────────────────────────────────────────────────────────

class GitHub:
    def __init__(self, token: str | None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["User-Agent"] = "s7ex-j-cards/1.0"

    def get(self, url: str, params: dict | None = None) -> Any:
        r = self.session.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def user(self, login: str) -> dict:
        return self.get(f"https://api.github.com/users/{login}")

    def repos(self, login: str) -> list[dict]:
        # Fetch all public + private (if token has scope)
        all_repos = []
        page = 1
        while True:
            data = self.get(
                f"https://api.github.com/users/{login}/repos",
                params={"per_page": 100, "page": page, "sort": "pushed", "type": "all"},
            )
            if not data:
                break
            all_repos.extend(data)
            page += 1
        return all_repos

    def contributions(self, login: str) -> dict:
        """Fetch contribution graph via GraphQL (requires PAT)."""
        if not self.token:
            return {"total": 0, "weeks": []}
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays { contributionCount date }
                }
              }
            }
          }
        }
        """
        r = self.session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": login}},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        cal = data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})
        return {
            "total": cal.get("totalContributions", 0),
            "weeks": cal.get("weeks", []),
        }

    def languages(self, login: str) -> dict[str, int]:
        """Aggregate language bytes across repos."""
        repos = self.repos(login)
        totals: dict[str, int] = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            try:
                langs = self.get(f"https://api.github.com/repos/{login}/{repo['name']}/languages")
                for k, v in langs.items():
                    totals[k] = totals.get(k, 0) + v
            except Exception:
                pass
        return dict(sorted(totals.items(), key=lambda x: -x[1]))


# ─── Card generators ─────────────────────────────────────────────────────────

PULSE_W, PULSE_H = 960, 280
PULSE_SECTION_GAP = 24
PULSE_CARD_RADIUS = 14

def build_pulse_card(theme: str, user: dict, contrib: dict, langs: dict[str, int], repos: list[dict]) -> str:
    """Build a unified wide Pulse card: stats + top languages + activity summary."""
    t = THEMES[theme]

    # Calculate stats
    total_contrib = contrib.get("total", 0)
    weeks = contrib.get("weeks", [])
    streak = 0
    for w in reversed(weeks):
        if any(d.get("contributionCount", 0) > 0 for d in w.get("contributionDays", [])):
            streak += 1
        else:
            break

    public_repos = user.get("public_repos", 0)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    followers = user.get("followers", 0)

    # Top languages
    total_bytes = sum(langs.values())
    top_langs = list(langs.items())[:6]
    max_bytes = top_langs[0][1] if top_langs else 1

    # Activity: last 4 weeks contribution counts
    recent_weeks = weeks[-4:] if weeks else []
    week_labels = ["W-3", "W-2", "W-1", "This W"]
    week_values = []
    for i, w in enumerate(recent_weeks):
        week_total = sum(d.get("contributionCount", 0) for d in w.get("contributionDays", []))
        week_values.append(week_total)
    # Pad if less than 4 weeks
    while len(week_values) < 4:
        week_values.insert(0, 0)

    max_week = max(week_values) if week_values else 1
    if max_week == 0:
        max_week = 1

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PULSE_W}" height="{PULSE_H}" '
        f'viewBox="0 0 {PULSE_W} {PULSE_H}" role="img" aria-labelledby="pulse-title">',
        f'<title id="pulse-title">GitHub Pulse</title>',
        '<defs>',
        '<filter id="pulse-shadow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="10" stdDeviation="16" flood-color="{t["panel"]}" '
        'flood-opacity=".35"/></filter>',
        '<filter id="bar-glow" x="-50%" y="-50%" width="200%" height="200%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/>'
        f'<feFlood flood-color="{t["accent"]}" flood-opacity=".4"/>'
        '<feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>',
        '</defs>',
        # Background card
        f'<rect width="{PULSE_W}" height="{PULSE_H}" rx="{PULSE_CARD_RADIUS}" fill="{t["bg"]}" '
        f'stroke="{t["line"]}" filter="url(#pulse-shadow)"/>',

        # Title bar
        f'<rect x="0" y="0" width="{PULSE_W}" height="56" rx="{PULSE_CARD_RADIUS}" '
        f'ry="{PULSE_CARD_RADIUS}" fill="{t["panel"]}"/>',
        # Fix bottom corners of title bar
        f'<rect x="0" y="42" width="{PULSE_W}" height="14" fill="{t["panel"]}"/>',
        f'<text x="24" y="37" fill="{t["title"]}" {FONT} font-size="16" font-weight="700">GitHub Pulse</text>',
        f'<text x="{PULSE_W - 24}" y="37" text-anchor="end" fill="{t["muted"]}" {FONT} font-size="11">'
        f'Updated {datetime.now(timezone.utc).strftime("%b %d, %Y")}</text>',
    ]

    # Three columns layout
    col_w = (PULSE_W - 48 - 2 * PULSE_SECTION_GAP) // 3
    col_x = [24, 24 + col_w + PULSE_SECTION_GAP, 24 + 2 * (col_w + PULSE_SECTION_GAP)]
    content_y = 72
    content_h = PULSE_H - 88

    # ─── Column 1: Key Stats ───
    x = col_x[0]
    stats = [
        ("Total Contributions", num_fmt(total_contrib)),
        ("Current Streak", f"{streak} weeks"),
        ("Public Repos", num_fmt(public_repos)),
        ("Stars Received", num_fmt(total_stars)),
        ("Followers", num_fmt(followers)),
    ]

    y = content_y
    parts.append(f'<text x="{x}" y="{y}" fill="{t["muted"]}" {FONT} font-size="11" font-weight="600">Overview</text>')
    y += 22
    for label, value in stats:
        parts.extend([
            f'<text x="{x}" y="{y}" fill="{t["muted"]}" {FONT} font-size="12">{esc(label)}</text>',
            f'<text x="{x + col_w - 4}" y="{y}" text-anchor="end" fill="{t["text"]}" '
            f'{FONT} font-size="13" font-weight="600">{esc(value)}</text>',
        ])
        y += 28

    # ─── Column 2: Top Languages ───
    x = col_x[1]
    y = content_y
    parts.append(f'<text x="{x}" y="{y}" fill="{t["muted"]}" {FONT} font-size="11" font-weight="600">Top Languages</text>')
    y += 22

    bar_h = 10
    bar_gap = 8
    bar_max_w = col_w - 16

    for lang, bytes_ in top_langs:
        pct = bytes_ * 100 / total_bytes
        w = max(4, int((bytes_ / max_bytes) * bar_max_w))
        parts.extend([
            f'<text x="{x}" y="{y + 9}" fill="{t["muted"]}" {FONT} font-size="10">{esc(lang)}</text>',
            f'<text x="{x + col_w - 4}" y="{y + 9}" text-anchor="end" fill="{t["text"]}" '
            f'{FONT} font-size="10" font-weight="600">{pct:.1f}%</text>',
            f'<rect x="{x}" y="{y + 14}" width="{w}" height="{bar_h}" rx="3" '
            f'fill="{t["accent"]}" filter="url(#bar-glow)"/>',
            f'<rect x="{x + w}" y="{y + 14}" width="{bar_max_w - w}" height="{bar_h}" '
            f'rx="3" fill="{t["line"]}"/>',
        ])
        y += bar_h + bar_gap + 12

    # ─── Column 3: Recent Activity ───
    x = col_x[2]
    y = content_y
    parts.append(f'<text x="{x}" y="{y}" fill="{t["muted"]}" {FONT} font-size="11" font-weight="600">Recent Activity</text>')
    y += 22

    # Mini contribution bars for last 4 weeks
    for i, (label, val) in enumerate(zip(week_labels, week_values)):
        w = max(2, int((val / max_week) * bar_max_w))
        parts.extend([
            f'<text x="{x}" y="{y + 9}" fill="{t["muted"]}" {FONT} font-size="10">{esc(label)}</text>',
            f'<text x="{x + col_w - 4}" y="{y + 9}" text-anchor="end" fill="{t["text"]}" '
            f'{FONT} font-size="10" font-weight="600">{num_fmt(val)}</text>',
            f'<rect x="{x}" y="{y + 14}" width="{w}" height="{bar_h}" rx="3" '
            f'fill="{t["accent2"]}"/>',
            f'<rect x="{x + w}" y="{y + 14}" width="{bar_max_w - w}" height="{bar_h}" '
            f'rx="3" fill="{t["line"]}"/>',
        ])
        y += bar_h + bar_gap + 12

    parts.append("</svg>")
    return "".join(parts)


def build_stats_card(theme: str, user: dict, contrib: dict) -> str:
    total_contrib = contrib.get("total", 0)
    weeks = contrib.get("weeks", [])
    # Current streak (simplified: count recent weeks with any activity)
    streak = 0
    for w in reversed(weeks):
        if any(d.get("contributionCount", 0) > 0 for d in w.get("contributionDays", [])):
            streak += 1
        else:
            break

    rows = [
        ("Total Contributions", num_fmt(total_contrib)),
        ("Current Streak", f"{streak} weeks"),
        ("Public Repos", num_fmt(user.get("public_repos", 0))),
        ("Followers", num_fmt(user.get("followers", 0))),
        ("Following", num_fmt(user.get("following", 0))),
    ]
    return make_svg_card(
        theme,
        "GitHub Statistics",
        rows,
        icon="▣",
        subtitle=f"@{user.get('login', 'unknown')} · Updated {datetime.now(timezone.utc).strftime('%b %d, %Y')}",
    )


def build_lang_card(theme: str, langs: dict[str, int]) -> str:
    total = sum(langs.values())
    top = list(langs.items())[:8]
    rows = [
        (f"{lang} {bytes * 100 / total:.1f}%", num_fmt(bytes))
        for lang, bytes in top
    ]
    return make_svg_card(
        theme,
        "Most Used Languages",
        rows,
        icon="≬",
        subtitle=f"{len(langs)} languages · {num_fmt(total)} bytes analyzed",
    )


def build_repo_cards(theme: str, repos: list[dict], projects_cfg: list[dict]) -> list[str]:
    """Build cards for featured projects from projects.json + fallback to top repos."""
    featured_names = {p.get("repo") for p in projects_cfg if p.get("repo")}
    cards = []

    # First, featured projects in order
    for proj in projects_cfg:
        repo_name = proj.get("repo")
        if not repo_name:
            continue
        repo = next((r for r in repos if r["name"] == repo_name), None)
        if repo:
            icon = proj.get("icon")
            cards.append(make_repo_card(theme, repo, show_lang=True, icon=icon))

    # Then top non-fork, non-featured repos by stars
    other = [
        r for r in repos
        if not r.get("fork") and r["name"] not in featured_names
    ]
    other.sort(key=lambda r: -r.get("stargazers_count", 0))
    for repo in other[:4 - len(cards)]:
        cards.append(make_repo_card(theme, repo, show_lang=True))

    return cards


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GitHub stat cards")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--projects", required=True, help="Path to projects.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--token", help="GitHub PAT (or use METRICS_TOKEN env)")
    args = parser.parse_args()

    token = args.token or os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("WARNING: No token provided (METRICS_TOKEN or GITHUB_TOKEN). Private stats unavailable.", file=sys.stderr)

    gh = GitHub(token)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching user {args.user}...")
    user = gh.user(args.user)

    print("Fetching contributions...")
    contrib = gh.contributions(args.user)

    print("Fetching repos...")
    repos = gh.repos(args.user)

    print("Fetching languages...")
    langs = gh.languages(args.user)

    print("Loading projects config...")
    with open(args.projects, encoding="utf-8") as f:
        projects_cfg = json.load(f)

    for theme in ("dark", "light"):
        stats_svg = build_stats_card(theme, user, contrib)
        (out_dir / f"card-stats-{theme}.svg").write_text(stats_svg, encoding="utf-8")
        print(f"  card-stats-{theme}.svg")

        lang_svg = build_lang_card(theme, langs)
        (out_dir / f"card-lang-{theme}.svg").write_text(lang_svg, encoding="utf-8")
        print(f"  card-lang-{theme}.svg")

        pulse_svg = build_pulse_card(theme, user, contrib, langs, repos)
        (out_dir / f"card-pulse-{theme}.svg").write_text(pulse_svg, encoding="utf-8")
        print(f"  card-pulse-{theme}.svg")

        repo_cards = build_repo_cards(theme, repos, projects_cfg)
        for i, card in enumerate(repo_cards):
            (out_dir / f"card-repo-{i}-{theme}.svg").write_text(card, encoding="utf-8")
            print(f"  card-repo-{i}-{theme}.svg")

    # Also create a combined languages chart (metrics.languages.svg style)
    # This is a simple horizontal bar chart
    for theme in ("dark", "light"):
        t = THEMES[theme]
        total = sum(langs.values())
        top = list(langs.items())[:8]
        max_bytes = top[0][1] if top else 1

        W, H = 480, 165
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" role="img">',
            '<defs>',
            '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="{t["panel"]}" '
            'flood-opacity=".3"/></filter>',
            "</defs>",
            f'<rect width="{W}" height="{H}" rx="10" fill="{t["bg"]}" '
            f'stroke="{t["line"]}" filter="url(#shadow)"/>',
            f'<text x="20" y="28" fill="{t["title"]}" {MONO} font-weight="700" font-size="14">Top Languages</text>',
        ]
        bar_h = 14
        gap = 4
        y = 48
        for lang, bytes_ in top:
            w = int((bytes_ / max_bytes) * 380)
            pct = bytes_ * 100 / total
            parts.extend([
                f'<rect x="20" y="{y}" width="{w}" height="{bar_h}" rx="3" fill="{t["accent"]}"/>',
                f'<text x="16" y="{y + 10}" text-anchor="end" fill="{t["muted"]}" {MONO} font-size="11">{esc(lang)}</text>',
                f'<text x="{20 + w + 8}" y="{y + 10}" fill="{t["text"]}" {MONO} font-size="11">{pct:.1f}%</text>',
            ])
            y += bar_h + gap
        parts.append("</svg>")
        (out_dir / f"metrics.languages-{theme}.svg").write_text("".join(parts), encoding="utf-8")
        print(f"  metrics.languages-{theme}.svg")

    print("Done.")


if __name__ == "__main__":
    main()