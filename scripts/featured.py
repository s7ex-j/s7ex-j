#!/usr/bin/env python3
"""Generate custom Featured Work hero cards with project branding.

Run:
    python scripts/featured.py --projects assets/projects.json --logos assets/source/project-logos --out assets

Each project gets a 480x220 card with:
- Project logo as background (referenced by URL, not embedded)
- Project name + tagline
- Tech stack badges
- Entire card links to repo
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image

# Constants
CARD_W, CARD_H = 480, 220
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

# Project-specific accent colors for badges/accents
PROJECT_COLORS = {
    "A.N.D.R.E-Modelo-predictivo-mundiales": {
        "primary": "#10B981",
        "secondary": "#059669",
        "glow": "#34D399",
    },
    "Dophamine": {
        "primary": "#A855F7",
        "secondary": "#9333EA",
        "glow": "#C084FC",
    },
    "plantillas-latex-ieee-apa7": {
        "primary": "#3B82F6",
        "secondary": "#2563EB",
        "glow": "#60A5FA",
    },
}


def esc(s: str) -> str:
    return (
        s.replace("&", "&")
        .replace("<", "<")
        .replace(">", ">")
        .replace('"', '"' + '"' + '"')
    )


def prepare_logo(path: Path, out_dir: Path, repo_name: str) -> str:
    """Copy and resize logo to output directory, return absolute URL."""
    logo_out = out_dir / f"logo-{repo_name}.png"

    with Image.open(path) as img:
        img = img.convert("RGBA")
        # Resize to cover card (maintain aspect, fill 480x220)
        img.thumbnail((CARD_W, CARD_H), Image.Resampling.LANCZOS)
        # Create canvas and center the image
        canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        x = (CARD_W - img.width) // 2
        y = (CARD_H - img.height) // 2
        canvas.paste(img, (x, y), img)
        canvas.save(logo_out, format="PNG")

    # Return absolute URL for raw.githubusercontent.com
    return f"https://raw.githubusercontent.com/s7ex-j/s7ex-j/output/assets/logo-{repo_name}.png"


def make_featured_card(
    theme: str,
    project: dict[str, Any],
    logo_url: str,
) -> str:
    """Build a branded hero card for a featured project."""
    t = THEMES[theme]
    colors = PROJECT_COLORS.get(project["repo"], {"primary": t["accent"], "secondary": t["accent2"], "glow": t["accent2"]})

    name = project.get("title", project.get("repo", ""))
    desc = project.get("description", "No description")
    url = f"https://github.com/s7ex-j/{project['repo']}"
    tech_stack = project.get("tech", [])
    icon = project.get("icon", "")

    short_desc = desc[:100] + "..." if len(desc) > 100 else desc

    primary = colors["primary"]
    secondary = colors["secondary"]
    glow = colors["glow"]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-labelledby="title">',
        f'<title id="title">{esc(name)}</title>',
        '<defs>',
        '<filter id="hero-shadow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="20" flood-color="{t["panel"]}" flood-opacity=".4"/></filter>',
        '<filter id="accent-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="4" result="b"/>'
        f'<feFlood flood-color="{glow}" flood-opacity=".5"/>'
        '<feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>',
        f'<linearGradient id="overlay-gradient" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="{t["bg"]}" stop-opacity="0.3"/>'
        f'<stop offset="60%" stop-color="{t["bg"]}" stop-opacity="0.85"/>'
        f'<stop offset="100%" stop-color="{t["bg"]}" stop-opacity="0.95"/>'
        '</linearGradient>',
        f'<linearGradient id="badge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{primary}"/>'
        f'<stop offset="100%" stop-color="{secondary}"/>'
        '</linearGradient>',
        '</defs>',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="16" fill="{t["bg"]}" stroke="{t["line"]}" filter="url(#hero-shadow)"/>',
        f'<image x="0" y="0" width="{CARD_W}" height="{CARD_H}" href="{logo_url}" preserveAspectRatio="xMidYMid slice"/>',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="16" fill="url(#overlay-gradient)"/>',
        f'<rect x="0" y="0" width="{CARD_W}" height="4" rx="16" ry="0" fill="url(#badge-gradient)"/>',
        f'<text x="24" y="150" fill="{t["text"]}" {FONT} font-size="22" font-weight="800">{esc(icon)} {esc(name)}</text>',
        f'<text x="24" y="180" fill="{t["muted"]}" {FONT} font-size="12" style="max-width:432px">{esc(short_desc)}</text>',
        f'<text x="24" y="208" fill="{t["accent2"]}" {FONT} font-size="10" font-weight="600">{esc(" | ".join(tech_stack[:4]))}</text>',
    ]

    link_wrap_start = f'<a href="{esc(url)}" target="_blank" rel="noopener">'
    link_wrap_end = '</a>'

    final_parts = [parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], link_wrap_start]
    final_parts.extend(parts[6:])
    final_parts.append(link_wrap_end)
    final_parts.append("</svg>")

    return "".join(final_parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Featured Work hero cards")
    parser.add_argument("--projects", required=True, help="Path to projects.json")
    parser.add_argument("--logos", required=True, help="Path to project logos directory")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    logos_dir = Path(args.logos)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.projects, encoding="utf-8") as f:
        projects = json.load(f)

    for theme in ("dark", "light"):
        for i, project in enumerate(projects):
            repo_name = project["repo"]
            logo_path = logos_dir / f"{repo_name}.png"

            if not logo_path.exists():
                print(f"WARNING: Logo not found for {repo_name}, skipping")
                continue

            print(f"  Processing {repo_name} ({theme})...")
            logo_url = prepare_logo(logo_path, out_dir, repo_name)
            card_svg = make_featured_card(theme, project, logo_url)
            out_file = out_dir / f"card-featured-{i}-{theme}.svg"
            out_file.write_text(card_svg, encoding="utf-8")
            print(f"    {out_file.name}")

    print("Done.")


if __name__ == "__main__":
    main()