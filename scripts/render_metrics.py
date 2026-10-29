#!/usr/bin/env python3
"""Render a small, public-only GitHub profile snapshot."""

from __future__ import annotations

import html
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

USER = "BreezeDelegate"
OUTPUT = Path(__file__).resolve().parents[1] / "github-metrics.svg"


def gh_json(*args: str) -> dict:
    result = subprocess.run(
        ["gh", "api", *args],
        check=True, text=True, capture_output=True, timeout=30,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("unexpected GitHub API response")
    return data


def checked_count(data: dict, field: str) -> int:
    value = data.get(field)
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid GitHub count: {field}")
    return value


def fetch_stats() -> dict[str, int]:
    # The public user endpoint cannot expose private repository metadata.
    user = gh_json(f"users/{USER}")
    if str(user.get("login", "")).lower() != USER.lower():
        raise ValueError("GitHub returned an unexpected user")

    # Search is explicitly restricted to public, merged PRs.
    prs = gh_json(
        "--method", "GET", "search/issues",
        "-f", f"q=is:pr is:merged author:{USER} is:public",
        "-f", "per_page=1",
    )
    if prs.get("incomplete_results") is not False:
        raise ValueError("GitHub's public PR search was incomplete")

    return {
        "public_repos": checked_count(user, "public_repos"),
        "merged_prs": checked_count(prs, "total_count"),
        "followers": checked_count(user, "followers"),
        "following": checked_count(user, "following"),
    }


def render(stats: dict[str, int]) -> str:
    # Fixed positions, no foreignObject, fonts, scripts, or remote images.
    cells = (
        ("public_repos", "Public repos"),
        ("merged_prs", "Merged PRs"),
        ("followers", "Followers"),
        ("following", "Following"),
    )
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="138" viewBox="0 0 640 138" role="img" aria-labelledby="metric-title metric-desc">',
        '  <title id="metric-title">GitHub public activity</title>',
        '  <desc id="metric-desc">Public repositories, merged public pull requests, followers and following.</desc>',
        '  <rect x="0.5" y="0.5" width="639" height="137" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '  <text x="25" y="29" font-family="Arial,Helvetica,sans-serif" font-size="13" fill="#8b949e">GitHub / public activity</text>',
        '  <path d="M25 43 H615" stroke="#30363d"/>',
    ]
    for i, (key, label) in enumerate(cells):
        count = checked_count(stats, key)
        x = 25 + i * 153
        if i:
            lines.append(f'  <path d="M{x - 13} 60 V117" stroke="#21262d"/>')
        lines.extend((
            f'  <text x="{x}" y="90" font-family="Arial,Helvetica,sans-serif" font-size="29" font-weight="600" fill="#e6edf3">{count:,}</text>',
            f'  <text x="{x}" y="113" font-family="Arial,Helvetica,sans-serif" font-size="12" fill="#9da7b3">{html.escape(label)}</text>',
        ))
    lines.append("</svg>")
    result = "\n".join(lines) + "\n"
    ET.fromstring(result)
    return result


def main() -> None:
    svg = render(fetch_stats())
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != svg:
        OUTPUT.write_text(svg, encoding="utf-8")
        print("GitHub public metrics updated")
    else:
        print("GitHub public metrics unchanged")


if __name__ == "__main__":
    main()
