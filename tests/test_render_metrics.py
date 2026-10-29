import unittest
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest import mock

from scripts import render_metrics as rm


class PublicProfileMetricsTests(unittest.TestCase):
    def setUp(self):
        self.stats = {
            "public_repos": 74,
            "merged_prs": 39,
            "followers": 5,
            "following": 10,
        }

    def test_current_public_profile_counts_render(self):
        svg = rm.render(self.stats)
        ET.fromstring(svg)
        for value in ("74", "39", "5", "10"):
            self.assertIn(">" + value + "</text>", svg)
        for label in ("Public repos", "Merged PRs", "Followers", "Following"):
            self.assertIn(label, svg)

    def test_snapshot_is_small_dark_and_privacy_safe(self):
        svg = rm.render(self.stats)
        self.assertIn('width="640" height="138"', svg)
        self.assertIn('fill="#0d1117"', svg)
        self.assertNotIn("private", svg.lower())
        self.assertNotIn("foreignObject", svg)
        self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))
        self.assertLess(len(svg), 2500)

    def test_render_is_stable_for_unchanged_counts(self):
        self.assertEqual(rm.render(self.stats), rm.render(dict(self.stats)))

    def test_reads_only_public_stats(self):
        public_user = {
            "login": "BreezeDelegate",
            "public_repos": 74, "followers": 5, "following": 10,
            "private_repos": 999,
        }
        merged_prs = {"total_count": 39, "incomplete_results": False}
        with mock.patch.object(rm, "gh_json", side_effect=[public_user, merged_prs]) as api:
            self.assertEqual(rm.fetch_stats(), self.stats)
        self.assertEqual(api.call_count, 2)
        self.assertEqual(api.call_args_list[0].args, ("users/BreezeDelegate",))
        query = api.call_args_list[1].args
        self.assertIn("q=is:pr is:merged author:BreezeDelegate is:public", query)

    def test_incomplete_search_fails_without_publishing_counts(self):
        user = {"login": "BreezeDelegate", "public_repos": 74, "followers": 5, "following": 10}
        with mock.patch.object(rm, "gh_json", side_effect=[
            user, {"total_count": 0, "incomplete_results": True},
        ]):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                rm.fetch_stats()

    def test_invalid_counts_are_not_silently_converted(self):
        for invalid in (None, -1, True, "5"):
            with self.subTest(invalid=invalid):
                bad = dict(self.stats, following=invalid)
                with self.assertRaises(ValueError):
                    rm.render(bad)

    def test_failed_fetch_does_not_replace_last_good_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-metrics.svg"
            output.write_text("previous good snapshot", encoding="utf-8")
            with (
                mock.patch.object(rm, "OUTPUT", output),
                mock.patch.object(rm, "fetch_stats", side_effect=RuntimeError("offline")),
            ):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    rm.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "previous good snapshot")

    def test_unexpected_user_is_rejected(self):
        with mock.patch.object(rm, "gh_json", return_value={"login": "SomeoneElse"}):
            with self.assertRaisesRegex(ValueError, "unexpected user"):
                rm.fetch_stats()


if __name__ == "__main__":
    unittest.main()
