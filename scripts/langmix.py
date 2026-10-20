#!/usr/bin/env python3
"""Write assets/langmix.json from the real language bytes of the user's repos.

Usage:
    python scripts/langmix.py --user s7ex-j -o assets/langmix.json
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from cards import GitHub

TOP_N = 8


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate langmix.json from GitHub language stats")
    parser.add_argument("--user", required=True)
    parser.add_argument("-o", "--out", required=True)
    args = parser.parse_args()

    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    langs = GitHub(token).languages(args.user)
    top = list(langs.items())[:TOP_N]
    if len(top) < 3:
        raise SystemExit(f"Need at least 3 languages for a radar, got {len(top)}")

    data = {
        "title": "Language & Stack Mix",
        "description": "Bytes per language across public repos (GitHub linguist)",
        "subtitle": f"Aggregated from GitHub repos · Updated {date.today():%b %Y}",
        "categories": [{"name": name, "value": value} for name, value in top],
    }
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: " + ", ".join(f"{n}={v}" for n, v in top))


if __name__ == "__main__":
    main()
