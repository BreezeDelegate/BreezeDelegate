import datetime as dt
import unittest

from scripts import render_metrics as rm


UTC = dt.timezone.utc


class ProfileMetricsTests(unittest.TestCase):
    def test_calendar_start_clips_pre_account_history(self):
        created = dt.datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        now = dt.datetime(2026, 9, 11, 18, 0, tzinfo=UTC)

        start = rm.calendar_start(created, now)

        self.assertEqual(start, dt.date(2026, 4, 5))
        self.assertLess((created.date() - start).days, 7)

    def test_calendar_start_keeps_only_one_year_for_old_accounts(self):
        created = dt.datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
        now = dt.datetime(2026, 9, 11, 18, 0, tzinfo=UTC)

        start = rm.calendar_start(created, now)

        self.assertGreaterEqual(start, dt.date(2025, 9, 7))
        self.assertLessEqual(start, dt.date(2025, 9, 11))

    def test_public_activity_calendar_ignores_private_events(self):
        created = dt.datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
        now = dt.datetime(2026, 9, 11, 18, 0, tzinfo=UTC)
        events = [
            {"date": "2026-09-10", "count": 2, "visibility": "public"},
            {"date": "2026-09-10", "count": 99, "visibility": "private"},
            {"date": "2026-09-11", "count": 1, "visibility": "public"},
        ]

        weeks = rm.build_activity_weeks(events, created, now)
        days = {
            day["date"]: day["contributionCount"]
            for week in weeks
            for day in week["contributionDays"]
        }

        self.assertEqual(days["2026-09-10"], 2)
        self.assertEqual(days["2026-09-11"], 1)
        self.assertEqual(sum(days.values()), 3)

    def test_private_summary_keeps_only_aggregate_fields(self):
        now = dt.datetime(2026, 9, 11, 18, 0, tzinfo=UTC)
        repos = [
            {
                "full_name": "BreezeDelegate/secret-one",
                "html_url": "https://github.com/BreezeDelegate/secret-one",
                "size": 1024,
                "language": "TypeScript",
                "fork": False,
                "updated_at": "2026-09-10T10:00:00Z",
            },
            {
                "full_name": "BreezeDelegate/secret-two",
                "html_url": "https://github.com/BreezeDelegate/secret-two",
                "size": 2048,
                "language": "Go",
                "fork": True,
                "updated_at": "2026-07-01T10:00:00Z",
            },
        ]

        summary = rm.summarize_private_repos(repos, now)
        rendered = repr(summary).lower()

        self.assertEqual(summary["repositories"], 2)
        self.assertEqual(summary["disk_kb"], 3072)
        self.assertEqual(summary["forks"], 1)
        self.assertEqual(summary["active_30d"], 1)
        self.assertEqual(summary["languages"], [("TypeScript", 1), ("Go", 1)])
        self.assertEqual(summary["language_total"], 2)
        self.assertNotIn("secret-one", rendered)
        self.assertNotIn("secret-two", rendered)
        self.assertNotIn("html_url", rendered)

    def test_private_section_never_renders_repository_identifiers(self):
        summary = {
            "repositories": 2,
            "disk_kb": 3072,
            "forks": 1,
            "active_30d": 1,
            "languages": [("TypeScript", 1), ("Go", 1)],
        }

        section = rm.private_work_section(summary)

        self.assertIn("Private work", section)
        self.assertIn("2 private repositories", section)
        self.assertIn("1 updated in the last 30 days", section)
        self.assertIn("Private languages", section)
        self.assertIn("Aggregated only", section)
        self.assertNotIn("BreezeDelegate/", section)
        self.assertNotIn("github.com/", section)


    def test_public_activity_events_are_explicitly_public(self):
        commits = [
            {"commit": {"author": {"date": "2026-09-10T08:00:00Z"}}},
            {"commit": {"committer": {"date": "2026-09-11T09:00:00Z"}}},
        ]
        prs = [{"created_at": "2026-09-10T12:00:00Z"}]
        issues = [{"created_at": "2026-09-11T13:00:00Z"}]

        events = rm.public_activity_events(commits, prs, issues)

        self.assertEqual(len(events), 4)
        self.assertTrue(all(event["visibility"] == "public" for event in events))
        self.assertEqual([event["date"] for event in events].count("2026-09-10"), 2)
        self.assertEqual([event["date"] for event in events].count("2026-09-11"), 2)

    def test_private_work_insertion_precedes_languages_and_extends_height(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="878"><foreignObject><div>before</div><section><h2>25 Languages</h2></section></foreignObject></svg>'
        section = '<section class="private-work">Private work</section>'

        result = rm.inject_private_work(svg, section)

        self.assertIn('height="974"', result)
        self.assertLess(result.index('Private work'), result.index('25 Languages'))
        self.assertEqual(result.count('private-work'), 1)

    def test_public_activity_labels_make_heatmap_scope_unambiguous(self):
        svg = 'Contributions calendar | Commits streaks | Commits per day | These metrics include private contributions'

        result = rm.apply_public_activity_labels(svg)

        self.assertIn('Public activity calendar', result)
        self.assertIn('Public activity streaks', result)
        self.assertIn('Public activity per day', result)
        self.assertIn('Public activity excludes private repositories', result)
        self.assertNotIn('include private contributions', result)


    def test_public_issue_search_is_hard_scoped_to_public(self):
        sample = {"total_count": 1, "items": [{"created_at": "2026-09-11T10:00:00Z"}]}
        from unittest import mock

        with mock.patch.object(rm, "gh_json", return_value=sample) as gh:
            items = rm.public_issue_pages("pr")

        self.assertEqual(items, sample["items"])
        args = gh.call_args.args
        query_arg = next(arg for arg in args if str(arg).startswith("q="))
        self.assertIn("is:pr", query_arg)
        self.assertIn("author:BreezeDelegate", query_arg)
        self.assertIn("is:public", query_arg)

    def test_private_repo_fetch_is_hard_scoped_to_owned_private_repositories(self):
        sample = [{"full_name": "BreezeDelegate/secret", "private": True}]
        from unittest import mock

        with mock.patch.object(rm, "gh_json", return_value=sample) as gh:
            repos = rm.private_repo_pages()

        self.assertEqual(repos, sample)
        args = gh.call_args.args
        self.assertIn("visibility=private", args)
        self.assertIn("affiliation=owner", args)


    def test_render_uses_public_activity_sources_and_private_aggregates(self):
        from unittest import mock

        user = {
            "login": "BreezeDelegate",
            "name": "Breeze",
            "createdAt": "2026-04-08T12:00:00Z",
            "avatarUrl": "https://example.invalid/avatar.png",
            "followers": {"totalCount": 3},
            "following": {"totalCount": 2},
            "organizations": {"totalCount": 0},
            "starredRepositories": {"totalCount": 19},
            "sponsors": {"totalCount": 0},
            "sponsorshipsAsSponsor": {"totalCount": 0},
            "issueComments": {"totalCount": 44},
            "repositoriesContributedTo": {"totalCount": 32},
            "repositories": {
                "totalCount": 57,
                "nodes": [
                    {
                        "isFork": False,
                        "stargazerCount": 0,
                        "forkCount": 0,
                        "diskUsage": 235,
                        "watchers": {"totalCount": 0},
                        "releases": {"totalCount": 0},
                        "licenseInfo": {"spdxId": "MIT"},
                    }
                ],
            },
        }
        public_commits = [
            {"commit": {"author": {"date": "2026-09-10T08:00:00Z"}}}
        ]
        public_prs = [{"created_at": "2026-09-11T09:00:00Z"}]
        public_issues = []
        private_repos = [
            {
                "full_name": "BreezeDelegate/never-render-this-name",
                "html_url": "https://github.com/BreezeDelegate/never-render-this-name",
                "size": 2048,
                "language": "TypeScript",
                "fork": False,
                "updated_at": "2026-09-10T10:00:00Z",
            }
        ]

        template_markers = [
            "Mero",
            "Joined GitHub 3 years ago",
            "Followed by 22 users",
            "Contributed to 44 repositories",
            "4063 Commits",
            "10 Pull requests reviewed",
            "4 Pull requests opened",
            "0 Issues opened",
            "30 issue comments",
            "Member of 10 organizations",
            "Following 1 users",
            "Sponsoring 0 repositories",
            "Starred 7 repositories",
            "Watching 33 repositories",
            "65 Repositories",
            "Prefers MIT license",
            "11 Releases",
            "0 Packages",
            "287 MB used",
            "968k added, 545k removed",
            "0 Sponsors",
            "3 Stargazers",
            "1 Forker",
            "33 Watchers",
            "25 Languages",
            "Best streak 209 days",
            "Highest in a day at 76",
            "Average per day at ~5.66",
            "These metrics include private contributions",
            "Last updated 11 Sept 2026, 03:53:49 (timezone Europe/Berlin) with lowlighter/metrics@3.34.0",
            "Contributions calendar",
            "Commits streaks",
            "Commits per day",
        ]
        marker_html = "".join(f"<section><div>{value}</div></section>" for value in template_markers)
        mini = "".join(
            f'<rect class="day" x="{i}" y="0" width="11" height="11" fill="#ebedf0"/>'
            for i in range(14)
        )
        lang_bar = '<svg class="bar" xmlns="http://www.w3.org/2000/svg" width="460" height="8"><rect/></svg>'
        lang_rows = "".join(
            '<div class="field language details"><div>x</div><small><div>x</div></small></div>'
            for _ in range(8)
        )
        iso = '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" style="margin-top: -130px;" viewBox="0,0 480,270"><g/></svg>'
        avatar = '<img class="avatar" src="data:image/png;base64,OLD" width="20" height="20" />'
        template = f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="878"><foreignObject><div>{avatar}{marker_html}{mini}{lang_bar}{lang_rows}{iso}</div></foreignObject></svg>'

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return template.encode()

        captured_graphql = []
        def fake_gh_json(*args):
            if "graphql" in args:
                captured_graphql.append(next(arg for arg in args if str(arg).startswith("query=")))
                return {"data": {"user": user}}
            raise AssertionError(f"unexpected gh_json call: {args}")

        with (
            mock.patch.object(rm, "gh_json", side_effect=fake_gh_json),
            mock.patch.object(rm, "search_count", side_effect=[1, 0, 0, 1]),
            mock.patch.object(rm, "commit_pages", return_value=public_commits),
            mock.patch.object(rm, "public_issue_pages", side_effect=[public_prs, public_issues]),
            mock.patch.object(rm, "private_repo_pages", return_value=private_repos),
            mock.patch.object(rm, "public_code_activity", return_value=(10, 2, rm.collections.Counter({"Python": 8}))),
            mock.patch.object(rm, "run", return_value=""),
            mock.patch.object(rm, "fetch_avatar_data", return_value="data:image/png;base64,AA=="),
            mock.patch.object(rm.urllib.request, "urlopen", return_value=Response()),
        ):
            rendered = rm.render()

        self.assertEqual(len(captured_graphql), 1)
        self.assertNotIn("contributionsCollection", captured_graphql[0])
        self.assertIn("Private work", rendered)
        self.assertIn("1 private repository", rendered)
        self.assertIn("Public activity calendar", rendered)
        self.assertIn("Public activity excludes private repositories", rendered)
        self.assertNotIn("never-render-this-name", rendered)


    def test_short_calendar_is_balanced_inside_left_activity_column(self):
        weeks = [{"contributionDays": []} for _ in range(25)]

        svg, *_ = rm.calendar_svg(weeks)

        self.assertIn('scale(4) translate(13.000, 0)', svg)


    def test_short_calendar_stays_inside_left_activity_slot(self):
        weeks = [{"contributionDays": []} for _ in range(25)]

        svg, *_ = rm.calendar_svg(weeks)

        match = rm.re.search(r'scale\(4\) translate\(([0-9.]+), 0\)', svg)
        self.assertIsNotNone(match)
        offset = float(match.group(1))
        left_px = (offset - 10.2) * 4
        right_px = (offset + 1.7 * (len(weeks) - 1) + 3.4) * 4
        self.assertGreaterEqual(left_px, 0)
        self.assertLessEqual(right_px, 240)

    def test_private_languages_use_compact_colored_bar_and_legend(self):
        summary = {
            "repositories": 8,
            "disk_kb": 4096,
            "active_30d": 4,
            "language_total": 8,
            "languages": [
                ("TypeScript", 3),
                ("JavaScript", 2),
                ("Go", 1),
                ("Rust", 1),
                ("Shell", 1),
            ],
        }

        section = rm.private_work_section(summary)

        self.assertIn('class="private-language-bar"', section)
        self.assertIn('#3178c6', section)
        self.assertIn('#f1e05a', section)
        self.assertIn('#00ADD8', section)
        self.assertIn('TypeScript 38%', section)
        self.assertIn('JavaScript 25%', section)
        self.assertIn('Go 12%', section)
        self.assertIn('Other 25%', section)
        self.assertNotIn('Primary languages by repository', section)


if __name__ == "__main__":
    unittest.main()
