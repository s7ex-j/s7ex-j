#!/usr/bin/env python3
"""Generate radar (spider) charts as SVG from JSON data.

Two modes:
- Skills radar: categorical skills with self-rated proficiency (0-100)
- Language/stack radar: languages with relative weights

Usage:
    python scripts/radar.py --data assets/skills.json -o assets/radar
    python scripts/radar.py --data assets/langmix.json -o assets/radar-langs --values
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

THEMES = {
    "dark": {
        "bg": "#0A101F",
        "grid": "#25344C",
        "axis": "#3A4F6B",
        "fill": "#93A9EE33",  # 20% opacity
        "stroke": "#93A9EE",
        "text": "#DDE7F5",
        "muted": "#8291A8",
        "accent": "#10B981",
    },
    "light": {
        "bg": "#F6F8FA",
        "grid": "#CBD7E1",
        "axis": "#94A3B8",
        "fill": "#3B4A7A33",
        "stroke": "#3B4A7A",
        "text": "#172033",
        "muted": "#64748B",
        "accent": "#10B981",
    },
}

W, H = 400, 400
CENTER_X, CENTER_Y = W // 2, H // 2
MAX_RADIUS = 155  # leaves margin for labels
RINGS = 5  # 0, 25, 50, 75, 100


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def polar_to_cartesian(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    """Convert polar to cartesian. Angle 0 = top (-Y), clockwise."""
    angle_rad = math.radians(angle_deg - 90)
    return cx + radius * math.cos(angle_rad), cy + radius * math.sin(angle_rad)


def make_polygon_points(cx: float, cy: float, radius: float, n_sides: int, rotation: float = 0) -> str:
    """Generate SVG polygon points for a regular n-gon."""
    pts = []
    for i in range(n_sides):
        angle = rotation + i * 360 / n_sides
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def render_radar(
    theme_name: str,
    data: dict[str, Any],
    *,
    show_values: bool = False,
) -> str:
    """Render a radar chart SVG."""
    t = THEMES[theme_name]

    # Data: {"categories": [{"name": "...", "value": 80, "color": "..."}, ...]}
    # or for langmix: {"categories": [{"name": "Python", "value": 35000}, ...]}
    categories = data.get("categories", [])
    if not categories:
        raise ValueError("No categories in data")

    n = len(categories)
    rotation = -90 / n if n > 0 else 0  # align first axis to top

    # Find max value for scaling (if not using 0-100)
    max_val = max(c.get("value", 0) for c in categories)
    if max_val == 0:
        max_val = 100
    use_100_scale = all(0 <= c.get("value", 0) <= 100 for c in categories)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(data.get("title", "Radar Chart"))}</title>',
        f'<desc id="desc">{esc(data.get("description", "Skill/language radar chart"))}</desc>',
        '<defs>',
        '<filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">'
        f'<feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="{t["bg"]}" '
        'flood-opacity=".35"/></filter>',
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
    ]

    # Draw grid rings
    for ring in range(1, RINGS + 1):
        r = MAX_RADIUS * ring / RINGS
        points = make_polygon_points(CENTER_X, CENTER_Y, r, n, rotation)
        parts.append(
            f'<polygon points="{points}" fill="none" stroke="{t["grid"]}" '
            'stroke-width="1" stroke-dasharray="4,4"/>'
        )

    # Draw axis lines
    for i in range(n):
        angle = rotation + i * 360 / n
        x, y = polar_to_cartesian(CENTER_X, CENTER_Y, MAX_RADIUS, angle)
        parts.append(
            f'<line x1="{CENTER_X}" y1="{CENTER_Y}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{t["axis"]}" stroke-width="1"/>'
        )

    # Draw data polygon
    data_points = []
    for i, cat in enumerate(categories):
        val = cat.get("value", 0)
        if use_100_scale:
            r = MAX_RADIUS * val / 100
        else:
            r = MAX_RADIUS * val / max_val
        angle = rotation + i * 360 / n
        x, y = polar_to_cartesian(CENTER_X, CENTER_Y, r, angle)
        data_points.append(f"{x:.1f},{y:.1f}")

    points_str = " ".join(data_points)
    parts.append(
        f'<polygon points="{points_str}" fill="{t["fill"]}" stroke="{t["stroke"]}" '
        'stroke-width="2" filter="url(#shadow)"/>'
    )

    # Draw data points (dots)
    for x, y in [tuple(map(float, p.split(","))) for p in data_points]:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{t["stroke"]}" '
            f'stroke="{t["bg"]}" stroke-width="2"/>'
        )

    # Category labels
    label_radius = MAX_RADIUS + 28
    for i, cat in enumerate(categories):
        angle = rotation + i * 360 / n
        x, y = polar_to_cartesian(CENTER_X, CENTER_Y, label_radius, angle)
        name = cat.get("name", "")
        # Adjust text anchor based on angle
        if 90 < angle < 270:
            anchor = "end"
            dx = -6
        elif angle == 90 or angle == 270:
            anchor = "middle"
            dx = 0
        else:
            anchor = "start"
            dx = 6
        parts.append(
            f'<text x="{x + dx:.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" '
            f'fill="{t["text"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="12" font-weight="600">{esc(name)}</text>'
        )

    # Value labels (if requested)
    if show_values:
        for i, cat in enumerate(categories):
            val = cat.get("value", 0)
            angle = rotation + i * 360 / n
            r = (MAX_RADIUS * val / 100) if use_100_scale else (MAX_RADIUS * val / max_val)
            # Place value slightly inside the point
            x, y = polar_to_cartesian(CENTER_X, CENTER_Y, r + 18, angle)
            parts.append(
                f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" '
                f'fill="{t["accent"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                f'font-size="11" font-weight="700">{val}</text>'
            )

    # Legend / subtitle
    if "subtitle" in data:
        parts.append(
            f'<text x="{CENTER_X}" y="{H - 12}" text-anchor="middle" '
            f'fill="{t["muted"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="10">{esc(data["subtitle"])}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate radar chart SVG")
    parser.add_argument("--data", required=True, help="Path to JSON data file")
    parser.add_argument("-o", "--out", required=True, help="Output directory (will create dark/light)")
    parser.add_argument("--values", action="store_true", help="Show numeric values on chart")
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for theme in ("dark", "light"):
        svg = render_radar(theme, data, show_values=args.values)
        output = out_dir / f"{out_dir.name}-{theme}.svg"
        output.write_text(svg, encoding="utf-8")
        print(f"  {output}")

    print("Done.")


if __name__ == "__main__":
    main()