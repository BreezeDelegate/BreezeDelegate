#!/usr/bin/env python3
from __future__ import annotations

import base64
import collections
import concurrent.futures
import datetime as dt
import html
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

USER = "BreezeDelegate"
TZ = ZoneInfo("Europe/Paris")
TEMPLATE_URL = "https://raw.githubusercontent.com/hyfetch/hyfetch/ce41ae1508522f69836f3b06913ab8f132b49dea/github-metrics.svg"
OUTPUT = Path(__file__).resolve().parents[1] / "github-metrics.svg"

LEVEL_COLORS = {
    "NONE": "#ebedf0",
    "FIRST_QUARTILE": "#9be9a8",
    "SECOND_QUARTILE": "#40c463",
    "THIRD_QUARTILE": "#30a14e",
    "FOURTH_QUARTILE": "#216e39",
}
LANG_COLORS = {
    "TypeScript": "#3178c6", "Python": "#3572A5", "C++": "#f34b7d", "C": "#555555",
    "Rust": "#dea584", "Go": "#00ADD8", "Swift": "#F05138", "JavaScript": "#f1e05a",
    "Lua": "#000080", "Kotlin": "#A97BFF", "Svelte": "#ff3e00", "Dart": "#00B4AB",
    "HTML": "#e34c26", "CSS": "#663399", "Shell": "#89e051", "PowerShell": "#012456",
    "Java": "#b07219", "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95",
}
EXT_LANG = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".py": "Python", ".pyi": "Python", ".go": "Go", ".rs": "Rust",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".hh": "C++", ".hxx": "C++",
    ".c": "C", ".h": "C", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".lua": "Lua", ".swift": "Swift", ".kt": "Kotlin", ".kts": "Kotlin", ".dart": "Dart",
    ".cs": "C#", ".java": "Java", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "SCSS", ".svelte": "Svelte",
    ".vue": "Vue", ".rb": "Ruby", ".php": "PHP", ".sql": "SQL", ".ps1": "PowerShell",
}


def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def gh_json(*args: str) -> dict:
    return json.loads(run("gh", *args))


def search_count(endpoint: str, query: str) -> int:
    data = gh_json("api", "--method", "GET", endpoint, "-f", f"q={query}", "-f", "per_page=1")
    return int(data.get("total_count", 0))


def age_text(created: dt.datetime, now: dt.datetime) -> str:
    days = max(0, (now.date() - created.date()).days)
    if days >= 365:
        years = max(1, days // 365)
        return f"{years} year" + ("" if years == 1 else "s") + " ago"
    if days >= 30:
        months = max(1, days // 30)
        return f"{months} month" + ("" if months == 1 else "s") + " ago"
    return f"{days} day" + ("" if days == 1 else "s") + " ago"


def fmt_size_kb(kb: int) -> str:
    if kb >= 1024 * 1024:
        return f"{kb / 1024 / 1024:.1f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} kB"


def fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2g}M"
    if n >= 1000:
        return f"{n / 1000:.2g}k"
    return str(n)


def fetch_avatar_data(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "BreezeDelegate-profile/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read()
        mime = response.headers.get_content_type() or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def commit_pages() -> list[dict]:
    items: list[dict] = []
    page = 1
    while page <= 10:
        data = gh_json(
            "api", "--method", "GET", "search/commits",
            "-f", f"q=author:{USER} is:public", "-f", "per_page=100", "-f", f"page={page}",
        )
        items.extend(data.get("items", []))
        if len(items) >= min(int(data.get("total_count", 0)), 1000) or not data.get("items"):
            break
        page += 1
    return items


def fetch_commit(item: dict) -> dict | None:
    repo = item.get("repository", {}).get("full_name")
    sha = item.get("sha")
    if not repo or not sha:
        return None
    try:
        return gh_json("api", f"repos/{repo}/commits/{sha}")
    except Exception:
        return None


def public_code_activity() -> tuple[int, int, collections.Counter[str]]:
    additions = deletions = 0
    languages: collections.Counter[str] = collections.Counter()
    items = commit_pages()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for commit in pool.map(fetch_commit, items):
            if not commit:
                continue
            stats = commit.get("stats") or {}
            additions += int(stats.get("additions") or 0)
            deletions += int(stats.get("deletions") or 0)
            for f in commit.get("files") or []:
                ext = os.path.splitext(str(f.get("filename", "")).lower())[1]
                lang = EXT_LANG.get(ext)
                if lang:
                    languages[lang] += int(f.get("changes") or 0)
    return additions, deletions, languages


def calendar_svg(weeks: list[dict]) -> tuple[str, int, int, float]:
    values = [int(day.get("contributionCount") or 0) for week in weeks for day in week.get("contributionDays", [])]
    reference = max(values, default=1) or 1
    best = current = maximum = 0
    for value in values:
        maximum = max(maximum, value)
        current = current + 1 if value else 0
        best = max(best, current)
    average = sum(values) / len(values) if values else 0.0

    parts = [
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" style="margin-top: -130px;" viewBox="0,0 480,270">',
        '<filter id="brightness1"><feComponentTransfer><feFuncR type="linear" slope="0.6"/><feFuncG type="linear" slope="0.6"/><feFuncB type="linear" slope="0.6"/></feComponentTransfer></filter>',
        '<filter id="brightness2"><feComponentTransfer><feFuncR type="linear" slope="0.2"/><feFuncG type="linear" slope="0.2"/><feFuncB type="linear" slope="0.2"/></feComponentTransfer></filter>',
        '<g transform="scale(4) translate(12, 0)">',
    ]
    size = 6
    for i, week in enumerate(weeks):
        parts.append(f'<g transform="translate({i * 1.7}, {i})">')
        for j, day in enumerate(week.get("contributionDays", [])):
            count = int(day.get("contributionCount") or 0)
            ratio = count / reference if reference else 0
            color = LEVEL_COLORS.get(day.get("contributionLevel"), "#ebedf0")
            y = j + (1 - ratio) * size
            parts.append(
                f'<g transform="translate({j * -1.7}, {y})">'
                f'<path fill="{color}" d="M1.7,2 0,1 1.7,0 3.4,1 z"/>'
                f'<path fill="{color}" filter="url(#brightness1)" d="M0,1 1.7,2 1.7,{2 + ratio * size} 0,{1 + ratio * size} z"/>'
                f'<path fill="{color}" filter="url(#brightness2)" d="M1.7,2 3.4,1 3.4,{1 + ratio * size} 1.7,{2 + ratio * size} z"/>'
                '</g>'
            )
        parts.append('</g>')
    parts.append('</g></svg>')
    return ''.join(parts), best, maximum, average


def language_bar(langs: list[tuple[str, int]], total: int) -> str:
    x = 0.0
    rects = ['<rect mask="url(#languages-bar)" x="0" y="0" width="0" height="8" fill="#d1d5da"/>']
    for name, amount in langs:
        width = 460 * amount / total if total else 0
        rects.append(
            f'<rect mask="url(#languages-bar)" x="{x:.6f}" y="0" width="{width:.6f}" height="8" fill="{LANG_COLORS.get(name, "#555555")}"/>'
        )
        x += width
    return (
        '<svg class="bar" xmlns="http://www.w3.org/2000/svg" width="460" height="8">'
        '<mask id="languages-bar"><rect x="0" y="0" width="460" height="8" fill="white" rx="5"/></mask>'
        + ''.join(rects) + '</svg>'
    )


def language_block(name: str, amount: int, total: int) -> str:
    pct = (100 * amount / total) if total else 0
    color = LANG_COLORS.get(name, "#555555")
    amount_text = f"{amount / 1000:.2f}k lines" if amount >= 1000 else f"{amount} lines"
    return f'''<div class="field language details">
                            <div class="field">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">
                                    <path fill="{color}" fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"/>
                                </svg>
                                {html.escape(name)}
                            </div>
                            <small>
                                <div>{amount_text}</div>
                                <div>{pct:.2f}%</div>
                            </small>
                        </div>'''


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"template marker missing: {old}")
    return text.replace(old, new, 1)


def render() -> str:
    now = dt.datetime.now(TZ)
    start = now.replace(year=now.year - 1)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    query = f'''query {{
      user(login: "{USER}") {{
        login name createdAt avatarUrl
        followers {{ totalCount }} following {{ totalCount }}
        organizations(first:1) {{ totalCount }}
        starredRepositories {{ totalCount }}
        sponsors(first:1) {{ totalCount }}
        sponsorshipsAsSponsor(first:1) {{ totalCount }}
        issueComments {{ totalCount }}
        repositoriesContributedTo(first:1, privacy:PUBLIC, contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]) {{ totalCount }}
        repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER, orderBy:{{field:UPDATED_AT,direction:DESC}}) {{
          totalCount
          nodes {{ isFork stargazerCount forkCount diskUsage watchers {{ totalCount }} releases {{ totalCount }} licenseInfo {{ spdxId }} }}
        }}
        contributionsCollection(from: "{start.astimezone(dt.timezone.utc).isoformat()}", to: "{now.astimezone(dt.timezone.utc).isoformat()}") {{
          contributionCalendar {{ totalContributions weeks {{ contributionDays {{ date contributionCount contributionLevel }} }} }}
        }}
      }}
    }}'''
    user = gh_json("api", "graphql", "-f", f"query={query}")["data"]["user"]
    repos = user["repositories"]["nodes"]
    nonfork = [r for r in repos if not r["isFork"]]

    public_prs = search_count("search/issues", f"is:pr author:{USER} is:public")
    reviewed_prs = search_count("search/issues", f"is:pr reviewed-by:{USER} is:public")
    public_issues = search_count("search/issues", f"is:issue author:{USER} is:public")
    public_commits = search_count("search/commits", f"author:{USER} is:public")
    watched = len([x for x in run("gh", "api", "--paginate", f"users/{USER}/subscriptions", "--jq", ".[].full_name").splitlines() if x.strip()])
    additions, deletions, lang_counter = public_code_activity()

    licenses = collections.Counter(
        r["licenseInfo"]["spdxId"] for r in repos if r.get("licenseInfo") and r["licenseInfo"].get("spdxId") not in {None, "NOASSERTION"}
    )
    preferred_license = licenses.most_common(1)[0][0] if licenses else "custom"
    releases = sum(int(r["releases"]["totalCount"]) for r in repos)
    stars = sum(int(r["stargazerCount"]) for r in nonfork)
    forks = sum(int(r["forkCount"]) for r in nonfork)
    watchers = sum(int(r["watchers"]["totalCount"]) for r in nonfork)
    disk_kb = sum(int(r.get("diskUsage") or 0) for r in nonfork)

    days = [d for w in user["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    iso_svg, best_streak, max_day, average = calendar_svg(weeks)

    top_langs = lang_counter.most_common(8)
    lang_total = sum(lang_counter.values())
    while len(top_langs) < 8:
        top_langs.append(("Other", 0))
    language_count = len([x for x in lang_counter.values() if x > 0])

    with urllib.request.urlopen(TEMPLATE_URL, timeout=30) as response:
        svg = response.read().decode("utf-8")

    created = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).astimezone(TZ)
    replacements = {
        "Mero": user.get("name") or USER,
        "Joined GitHub 3 years ago": f"Joined GitHub {age_text(created, now)}",
        "Followed by 22 users": f"Followed by {user['followers']['totalCount']} users",
        "Contributed to 44 repositories": f"Contributed to {user['repositoriesContributedTo']['totalCount']} repositories",
        "4063 Commits": f"{public_commits} Commits",
        "10 Pull requests reviewed": f"{reviewed_prs} Pull requests reviewed",
        "4 Pull requests opened": f"{public_prs} Pull requests opened",
        "0 Issues opened": f"{public_issues} Issues opened",
        "30 issue comments": f"{user['issueComments']['totalCount']} issue comments",
        "Member of 10 organizations": f"Member of {user['organizations']['totalCount']} organizations",
        "Following 1 users": f"Following {user['following']['totalCount']} users",
        "Sponsoring 0 repositories": f"Sponsoring {user['sponsorshipsAsSponsor']['totalCount']} repositories",
        "Starred 7 repositories": f"Starred {user['starredRepositories']['totalCount']} repositories",
        "Watching 33 repositories": f"Watching {watched} repositories",
        "65 Repositories": f"{user['repositories']['totalCount']} Repositories",
        "Prefers MIT license": f"Prefers {preferred_license} license",
        "11 Releases": f"{releases} Releases",
        "0 Packages": "0 Packages",
        "287 MB used": f"{fmt_size_kb(disk_kb)} used",
        "968k added, 545k removed": f"{fmt_count(additions)} added, {fmt_count(deletions)} removed",
        "0 Sponsors": f"{user['sponsors']['totalCount']} Sponsors",
        "3 Stargazers": f"{stars} Stargazers",
        "1 Forker": f"{forks} Forkers",
        "33 Watchers": f"{watchers} Watchers",
        "25 Languages": f"{language_count} Languages",
        "Best streak 209 days": f"Best streak {best_streak} days",
        "Highest in a day at 76": f"Highest in a day at {max_day}",
        "Average per day at ~5.66": f"Average per day at ~{average:.2f}",
        "These metrics include private contributions": "These metrics use public contributions only",
        "Last updated 11 Sept 2026, 03:53:49 (timezone Europe/Berlin) with lowlighter/metrics@3.34.0":
            f"Last updated {now.strftime('%-d %b %Y, %H:%M:%S')} (timezone Europe/Paris) · layout adapted from lowlighter/metrics@3.34.0",
    }
    for old, new in replacements.items():
        svg = replace_once(svg, old, html.escape(str(new)))

    avatar = fetch_avatar_data(user["avatarUrl"] + "&s=40")
    svg, n = re.subn(
        r'<img class="avatar" src="data:image/[^;]+;base64,[^"]+" width="20" height="20" />',
        f'<img class="avatar" src="{avatar}" width="20" height="20" />',
        svg,
        count=1,
    )
    if n != 1:
        raise RuntimeError("avatar marker missing")

    recent = sorted(days, key=lambda d: d["date"])[-14:]
    fills = [LEVEL_COLORS.get(d.get("contributionLevel"), "#ebedf0") for d in recent]
    idx = 0
    def mini_day(match: re.Match[str]) -> str:
        nonlocal idx
        color = fills[idx] if idx < len(fills) else "#ebedf0"
        idx += 1
        return re.sub(r'fill="#[0-9a-fA-F]+"', f'fill="{color}"', match.group(0), count=1)
    svg, n = re.subn(r'<rect class="day"[^>]+/>', mini_day, svg, count=14)
    if n != 14:
        raise RuntimeError(f"expected 14 mini-calendar days, found {n}")

    svg, n = re.subn(r'<svg class="bar" xmlns="http://www.w3.org/2000/svg" width="460" height="8">.*?</svg>', language_bar(top_langs, lang_total), svg, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError("language bar marker missing")

    blocks = iter(language_block(name, amount, lang_total) for name, amount in top_langs)
    svg, n = re.subn(r'<div class="field language details">.*?</small>\s*</div>', lambda _m: next(blocks), svg, count=8, flags=re.S)
    if n != 8:
        raise RuntimeError(f"expected 8 language rows, found {n}")

    svg, n = re.subn(
        r'<svg version="1\.1" xmlns="http://www\.w3\.org/2000/svg" style="margin-top: -130px;" viewBox="0,0 480,270">.*?</svg>',
        iso_svg,
        svg,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError("isocalendar marker missing")

    if "Mero" in svg or "hyfetch" in svg.lower():
        raise RuntimeError("reference identity leaked into output")
    if "github-metrics.svg" in svg:
        raise RuntimeError("unexpected recursive reference")
    return svg


def main() -> None:
    svg = render()
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
