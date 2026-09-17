#!/usr/bin/env python3
"""Generate the animated GitHub profile banners for s7ex-j.

Run from the repository root:
    python scripts/banner/generate.py
"""

from __future__ import annotations

import html
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/avatar.png"
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
DATA = Path(__file__).resolve().parent / "data"

W, H = 1180, 610
LOOP_SECONDS = 14.2
INTRO_SECONDS = 3.2
TRAVELLER_COUNT = 900
SEED = 314159

ROWS = [
    ("Subject", "Andre"),
    ("Role", "Data Analyst Jr · BI Practitioner"),
    ("Origin", "Lima, Perú"),
    ("Education", "Industrial Eng + Data Science"),
    ("Status", "Elasticity · Stacking · Power BI · SQL"),
    ("ToolChain", "VS Code · Git · Jupyter"),
    ("Core.Lang", "Python · SQL · R"),
    ("Core.Data", "Pandas · NumPy · scikit-learn · statsmodels"),
    ("Core.BI", "Power BI · DAX · Matplotlib · Seaborn · Plotly"),
    ("Core.DB", "PostgreSQL · MySQL · BigQuery"),
    ("Grid.Mail", "—"),
    ("Grid.LinkedIn", "/in/andre-vilca-ramos"),
    ("Grid.GitHub", "s7ex-j"),
    ("Grid.ORCID", "0009-0009-7897-3439"),
]

THEMES = {
    "dark": {
        "bg": "#0A101F",
        "panel": "#0D1628",
        "panel2": "#101B30",
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "portrait": "#93A9EE",
        "chrome": "#22D3EE",
        "accent": "#10B981",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "portrait": "#3B4A7A",
        "chrome": "#0891B2",
        "accent": "#10B981",
        "shadow": "#AAB7C4",
    },
}

def make_logos() -> dict[str, Image.Image]:
    """Create clean 400px black-on-transparent silhouette sources."""
    LOGOS.mkdir(parents=True, exist_ok=True)
    size = 400
    logos: dict[str, Image.Image] = {}

    # Kali Linux logo - dragon silhouette with clear shape
    kali = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(kali)
    # Main dragon head shape (filled black silhouette)
    d.ellipse((100, 100, 300, 300), fill="black")
    # Eyes as cutouts
    d.ellipse((150, 160, 175, 185), fill=(0,0,0,0))
    d.ellipse((225, 160, 250, 185), fill=(0,0,0,0))
    # Nose
    d.polygon([(200, 210), (185, 235), (215, 235)], fill=(0,0,0,0))
    # Horns (pointing up)
    d.polygon([(140, 95), (170, 140), (200, 120)], fill="black")
    d.polygon([(230, 95), (260, 140), (200, 120)], fill="black")
    # Mouth cutout
    d.arc((160, 220, 240, 280), start=180, end=360, fill=(0,0,0,0), width=20)
    # Scale pattern on cheek
    d.ellipse((120, 200, 160, 240), fill=(0,0,0,0))
    d.ellipse((240, 200, 280, 240), fill=(0,0,0,0))
    logos["kali"] = kali

    # VS Code editor silhouette with visible UI elements
    vscode = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(vscode)
    # Main window (black border + lighter fill to show content)
    d.rectangle((80, 80, 320, 320), outline="black", width=6)
    # Title bar
    d.rectangle((80, 80, 320, 105), fill="black")
    # Activity bar (left sidebar)
    d.rectangle((80, 105, 120, 320), fill="black")
    # Window control dots
    for cx in [100, 125, 150]:
        d.ellipse((cx, 90, cx+8, 98), fill="black")
    d.ellipse((100, 90, 108, 98), fill=(0,0,0,0))
    d.ellipse((125, 90, 133, 98), fill=(0,0,0,0))
    d.ellipse((150, 90, 158, 98), fill=(0,0,0,0))
    # File explorer icons
    for y in [130, 160, 190, 220, 260, 290]:
        d.rectangle((130, y, 160, y+5), fill="black")
    # Code lines
    for y, w in [(155, 180), (185, 140), (215, 200), (245, 160), (275, 190)]:
        d.line([(200, y), (200+w, y)], fill="black", width=5)
    logos["vscode"] = vscode

    # Hacker silhouette - hooded figure with laptop
    hacker = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(hacker)
    # Head/hood shape
    d.ellipse((130, 90, 270, 250), fill="black")
    # Hood inner shadow (darker cutout)
    d.ellipse((145, 110, 255, 230), fill=(0,0,0,0))
    # Face cutout (shadowed eyes)
    d.ellipse((160, 150, 240, 210), fill=(0,0,0,0))
    # Shoulders/body
    d.polygon([(100, 240), (180, 310), (220, 310), (300, 240)], fill="black")
    # Arms
    d.line([(110, 250), (85, 290)], fill="black", width=14)
    d.line([(290, 250), (315, 290)], fill="black", width=14)
    # Laptop base
    d.rectangle((110, 310, 290, 320), fill="black")
    # Laptop screen
    d.rectangle((140, 320, 260, 380), outline="black", width=4)
    # Screen content (code/text lines inside screen)
    for y in [340, 355, 370]:
        d.line([(160, y), (240, y)], fill="black", width=3)
    logos["hacker"] = hacker

    for name, image in logos.items():
        image.save(LOGOS / f"{name}.png", optimize=True)
    return logos

def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Serpentine 1-bit Floyd-Steinberg diffusion; True means a lit pixel."""
    work = gray.astype(np.float32) / 255.0
    out = np.zeros_like(work, dtype=bool)
    height, width = work.shape
    for y in range(height):
        left_to_right = y % 2 == 0
        xs = range(width) if left_to_right else range(width - 1, -1, -1)
        direction = 1 if left_to_right else -1
        for x in xs:
            old = work[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            out[y, x] = bool(new)
            err = old - new
            nx = x + direction
            if 0 <= nx < width:
                work[y, nx] += err * 7 / 16
            if y + 1 < height:
                if 0 <= x - direction < width:
                    work[y + 1, x - direction] += err * 3 / 16
                work[y + 1, x] += err * 5 / 16
                if 0 <= nx < width:
                    work[y + 1, nx] += err * 1 / 16
    return out

def portrait_points(theme: str, rng: np.random.Generator) -> np.ndarray:
    """Return sampled x/y banner coordinates from a 300x340 dither grid."""
    if not SOURCE.exists():
        # Fallback: generate synthetic portrait points
        print(f"WARNING: {SOURCE} not found, generating placeholder")
        xs = np.tile(np.arange(300), 340)
        ys = np.repeat(np.arange(340), 300)
        mask = ((xs - 150)**2 + (ys - 170)**2) < 130**2
        xs, ys = xs[mask], ys[mask]
        points = np.column_stack((74 + xs, 154 + ys)).astype(np.float32)
        return points

    source = Image.open(SOURCE).convert("RGBA")
    # Crop for head+shoulders, resize to 300x340
    crop = source.crop((18, 28, 390, 450)).resize((300, 340), Image.Resampling.LANCZOS)
    rgb = crop.convert("RGB")
    alpha = np.asarray(crop.getchannel("A"), dtype=np.float32) / 255.0

    if theme == "dark":
        lum = np.asarray(ImageOps.grayscale(rgb), dtype=np.float32)
        prepared = Image.fromarray(np.uint8(np.clip(lum * alpha, 0, 255)), "L")
        select_lit = True
    else:
        white = Image.new("RGBA", crop.size, "white")
        white.alpha_composite(crop)
        prepared = ImageOps.grayscale(white.convert("RGB"))
        select_lit = False

    # Equalize against subject only
    if theme == "dark":
        mask = Image.fromarray(np.uint8((alpha > 0.08) * 255), "L")
        prepared = ImageOps.equalize(prepared, mask=mask)
    else:
        prepared = ImageOps.autocontrast(prepared, cutoff=1)
    prepared = ImageEnhance.Contrast(prepared).enhance(1.35)
    prepared = prepared.filter(ImageFilter.UnsharpMask(radius=2, percent=175, threshold=1))
    bits = floyd_steinberg(np.asarray(prepared))
    active = bits if select_lit else ~bits
    if theme == "dark":
        active &= alpha > 0.08

    ys, xs = np.where(active)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    points = np.column_stack((74 + xs, 154 + ys)).astype(np.float32)
    if len(points) > 18000:
        points = points[rng.choice(len(points), 18000, replace=False)]
    return points

def sample_logo_points(
    image: Image.Image, rng: np.random.Generator, count: int
) -> np.ndarray:
    """Sample a silhouette into the portrait frame's visual coordinate space."""
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 127)
    chosen = rng.choice(len(xs), count, replace=len(xs) < count)
    return np.column_stack((89 + xs[chosen] * 0.675, 188 + ys[chosen] * 0.675)).astype(
        np.float32
    )

def transport(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Order target points by minimum-cost assignment from source points."""
    rows, cols = linear_sum_assignment(cdist(source, target, metric="sqeuclidean"))
    ordered = np.empty_like(target)
    ordered[rows] = target[cols]
    return ordered

def num(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")

def point_path(points: np.ndarray) -> str:
    """Aggregate adjacent horizontal one-pixel dots into compact SVG path runs."""
    if not len(points):
        return ""
    integer = np.rint(points).astype(int)
    unique = sorted({(int(x), int(y)) for x, y in integer}, key=lambda p: (p[1], p[0]))
    chunks: list[str] = []
    i = 0
    while i < len(unique):
        x0, y = unique[i]
        x1 = x0
        i += 1
        while i < len(unique) and unique[i][1] == y and unique[i][0] <= x1 + 1:
            x1 = unique[i][0]
            i += 1
        chunks.append(f"M{x0} {y}h{x1 - x0 + 1}")
    return "".join(chunks)

def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1:
        return ""
    return "".join(f"M{x} {num(y)}h1" for x in np.arange(x1, x2, 5.0))

def text_width(text: str, font_size: float) -> float:
    """Stable monospace width used both for textLength and leader placement."""
    return len(text) * font_size * 0.605

def animate_values(points: list[np.ndarray], index: int) -> str:
    return ";".join(f"{num(p[index, 0])} {num(p[index, 1])}" for p in points)

def render_svg(
    theme_name: str,
    portrait: np.ndarray,
    logo_points: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> str:
    t = THEMES[theme_name]
    n = min(TRAVELLER_COUNT, len(portrait))
    source = portrait[rng.choice(len(portrait), n, replace=False)]
    kali_pts = transport(source, logo_points["kali"][:n])
    vscode_pts = transport(kali_pts, logo_points["vscode"][:n])
    hacker_pts = transport(vscode_pts, logo_points["hacker"][:n])

    times = [0, 3.0, 4.3, 6.3, 7.6, 9.6, 10.9, 12.9, 14.2]
    key_times = ";".join(num(v / LOOP_SECONDS) for v in times)
    frames = [source, source, kali_pts, kali_pts, vscode_pts, vscode_pts, hacker_pts, hacker_pts, source]
    opacity_values = "0;0;1;1;1;1;1;1;0"

    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-labelledby="title desc">',
        "<title id=\"title\">Andre's live system profile</title>",
        '<desc id="desc">Animated terminal profile with a dithered portrait and '
        "Kali Linux, VS Code, and hacker silhouettes.</desc>",
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" '
        'flood-opacity=".28"/></filter>',
        '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/><feFlood flood-color="{t["chrome"]}" '
        'flood-opacity=".35"/><feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>',
        f'<rect x="13" y="13" width="1154" height="584" rx="13" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#shadow)"/>',
        f'<path d="M13 62H1167" stroke="{t["line"]}"/>',
        '<circle cx="38" cy="38" r="6" fill="#FF5F57"/>'
        '<circle cx="59" cy="38" r="6" fill="#FEBC2E"/>'
        '<circle cx="80" cy="38" r="6" fill="#28C840"/>',
        f'<text x="590" y="43" text-anchor="middle" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'letter-spacing=".4">profile.sh --live</text>',
        # Left visual frame.
        f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{t["panel2"]}" '
        f'stroke="{t["line"]}"/>',
        f'<path d="M35 124H453" stroke="{t["line"]}"/>',
        f'<text x="49" y="111" fill="{t["chrome"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>',
        f'<text x="438" y="111" text-anchor="end" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">300×340 / 1-BIT</text>',
        f'<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 539h12M49 539v-12'
        f'M439 539h-12M439 539v-12" fill="none" stroke="{t["chrome"]}" opacity=".55"/>',
        '<g clip-path="url(#visualClip)" shape-rendering="crispEdges">',
        '<g opacity="1">',
    ]

    # Dense portrait drift bands toward Kali centroid
    kali_centroid = kali_pts.mean(axis=0)
    band_ids = rng.integers(0, 94, size=len(portrait))
    noise = rng.normal(0, 4, size=(94, 2))
    for band in range(94):
        pts = portrait[band_ids == band]
        if not len(pts):
            continue
        centroid = pts.mean(axis=0)
        delta = (kali_centroid - centroid) * 0.18 + noise[band]
        d = point_path(pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{t["portrait"]}" stroke-width="1" '
            'opacity=".94">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="0 0;0 0;{num(delta[0])} {num(delta[1])};'
            f'{num(delta[0])} {num(delta[1])};0 0;0 0;0 0;0 0;0 0"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            'values=".94;.94;0;0;0;0;0;0;.94"/></path>'
        )

    # Optimal-transport travellers
    for i in range(n):
        positions = animate_values(frames, i)
        parts.append(
            f'<path d="M-.65-.65h1.3v1.3h-1.3z" fill="{t["portrait"]}">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="{positions}"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{key_times}" '
            f'values="{opacity_values}"/></path>'
        )
    parts.append("</g>")

    # One-shot scattered intro
    intro_ids = rng.integers(0, 60, size=len(portrait))
    order = rng.permutation(60)
    starts = np.empty(60)
    starts[order] = np.linspace(0.05, 1.2, 60)
    for group in range(60):
        pts = portrait[intro_ids == group]
        if not len(pts):
            continue
        parts.append(
            f'<path d="{point_path(pts)}" fill="none" stroke="{t["portrait"]}" '
            'stroke-width="1" opacity="0">'
            f'<animate attributeName="opacity" begin="{num(starts[group])}s" dur=".8s" '
            'values="0;1" fill="freeze"/>'
            '<animate attributeName="opacity" begin="3.08s" dur=".12s" values="1;0" fill="freeze"/>'
            "</path>"
        )
    parts.extend(
        [
            "</g>",
            # Small frame telemetry.
            f'<text x="58" y="551" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10">'
            f'PTS {len(portrait):05d} · FS/SERPENTINE</text>',
            # Right information panel.
            f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{t["panel2"]}" '
            f'stroke="{t["line"]}"/>',
            f'<path d="M474 124H1146" stroke="{t["line"]}"/>',
            f'<text x="490" y="111" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
            'font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>',
            # LIVE badge and handle pill.
            '<g filter="url(#glow)"><circle cx="915" cy="106" r="4" fill="#FF4D5A">'
            '<animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/>'
            '</circle></g>',
            '<text x="927" y="111" fill="#FF4D5A" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="12" '
            'font-weight="700">LIVE</text>',
            f'<rect x="982" y="94" width="146" height="24" rx="12" fill="{t["chrome"]}" opacity=".16" '
            f'stroke="{t["chrome"]}"/>',
            f'<text x="1055" y="111" text-anchor="middle" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14" '
            'font-weight="700">@s7ex-j</text>',
        ]
    )

    value_right = 1127.0
    row_y = 153.0
    for label, value in ROWS:
        value_len = text_width(value, 14)
        label_len = text_width(label, 14)
        leader_start = 491 + label_len + 12
        leader_end = value_right - value_len - 12
        parts.extend(
            [
                f'<text x="491" y="{num(row_y)}" fill="{t["muted"]}" '
                'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14">'
                f"{html.escape(label)}</text>",
                f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
                f'fill="none" stroke="{t["line"]}" stroke-width="1" shape-rendering="crispEdges"/>',
                f'<text x="{num(value_right)}" y="{num(row_y)}" text-anchor="end" '
                f'fill="{t["text"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                f'font-size="14" textLength="{num(value_len)}" lengthAdjust="spacingAndGlyphs">'
                f"{html.escape(value)}</text>",
            ]
        )
        row_y += 23

    parts.extend(
        [
            f'<path d="M490 530H1130" stroke="{t["line"]}"/>',
            f'<text x="491" y="548" fill="{t["accent"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "● ALL SYSTEMS NOMINAL</text>",
            f'<text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "UTC-5 · LATAM NODE</text>",
            "</svg>",
        ]
    )
    return "".join(parts)

def main() -> None:
    if not SOURCE.exists():
        print(f"WARNING: {SOURCE} not found - banner will use placeholder dots")
        print("Place a square photo at assets/source/avatar.png for best results")
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    logos = make_logos()

    portraits: dict[str, np.ndarray] = {}
    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + index)
        points = portrait_points(theme, rng)
        portraits[theme] = points
        np.save(DATA / f"portrait-{theme}.npy", points)

    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + 100 + index)
        sampled = {
            name: sample_logo_points(image, rng, TRAVELLER_COUNT)
            for name, image in logos.items()
        }
        for name, points in sampled.items():
            np.save(DATA / f"{name}-{theme}.npy", points)
        svg = render_svg(theme, portraits[theme], sampled, rng)
        output = ASSETS / f"banner-{theme}.svg"
        output.write_text(svg, encoding="utf-8")
        byte_size = output.stat().st_size
        print(
            f"{output.relative_to(ROOT)}: {byte_size:,} bytes "
            f"({byte_size / 1024:.1f} KiB), {len(portraits[theme]):,} portrait dots, "
            f"{TRAVELLER_COUNT} travellers"
        )

    for name in logos:
        output = LOGOS / f"{name}.png"
        print(f"{output.relative_to(ROOT)}: {output.stat().st_size:,} bytes")

if __name__ == "__main__":
    main()