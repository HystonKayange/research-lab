#!/usr/bin/env python3
"""Unit tests for scripts/data/clean_sources.py."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DATA = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS_DATA))

import clean_sources as clean  # noqa: E402


def _base_config(**overrides) -> dict:
    cfg = {
        "version": "test",
        "random_seed": 3,
        "excerpt_length": 40,
        "sample_count": 2,
        "percentiles": [50, 90, 95, 99],
        "short_line_threshold": 10,
        "long_line_threshold": 40,
        "output": {
            "interim_root": "data/interim/cleaning",
            "cleaned_filename": "cleaned.txt",
            "removal_log_filename": "removal_log.jsonl",
            "transform_log_filename": "transform_log.jsonl",
            "summary_filename": "summary.json",
            "report_filename": "before_after_report.md",
            "readme_filename": "README.md",
        },
        "language_signal": {"min_matches_for_signal": 2},
        "chichewa_signal_terms": ["ndi", "ndipo", "kuti", "mulungu", "anthu"],
        "english_signal_terms": ["the", "and", "of", "to", "in", "is", "was"],
        "german_signal_terms": ["der", "die", "das", "und", "ist", "von"],
        "boilerplate_patterns_for_metrics": [
            {"id": "category_prefix", "pattern": "Category\\s*:", "flags": "i"},
            {"id": "url_http", "pattern": "https?://", "flags": "i"},
        ],
        "disclaimers": ["test disclaimer"],
        "sources": {},
    }
    cfg.update(overrides)
    return cfg


class TestRuleEngine(unittest.TestCase):
    def test_drop_blank_and_log(self) -> None:
        rules = [
            {
                "id": "drop_blank",
                "type": "drop_blank",
                "enabled": True,
                "description": "blank",
            }
        ]
        kept, removals, transforms, counts = clean.apply_rules(
            ["a", "", "  ", "b"],
            rules,
            _base_config(),
            "bible",
        )
        self.assertEqual(kept, ["a", "b"])
        self.assertEqual(len(removals), 2)
        self.assertEqual(counts["drop_blank"], 2)
        self.assertEqual(removals[0]["line_number"], 2)
        self.assertEqual(removals[1]["line_number"], 3)

    def test_drop_regex_category(self) -> None:
        rules = [
            {
                "id": "drop_category",
                "type": "drop_regex",
                "enabled": True,
                "pattern": "Category\\s*:",
                "flags": "i",
                "description": "cat",
            }
        ]
        kept, removals, _, _ = clean.apply_rules(
            ["ok line here", "Category:Foo", "still ok"],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(kept, ["ok line here", "still ok"])
        self.assertEqual(removals[0]["rule_id"], "drop_category")
        self.assertEqual(removals[0]["line_number"], 2)

    def test_drop_url(self) -> None:
        rules = [
            {
                "id": "drop_url",
                "type": "drop_url",
                "enabled": True,
                "description": "url",
            }
        ]
        kept, removals, _, _ = clean.apply_rules(
            ["no url here", "see https://example.com"],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(kept, ["no url here"])
        self.assertEqual(removals[0]["rule_id"], "drop_url")

    def test_drop_min_max_length(self) -> None:
        rules = [
            {
                "id": "drop_min_length",
                "type": "drop_min_length",
                "enabled": True,
                "min_length": 5,
                "description": "short",
            },
            {
                "id": "drop_max_length",
                "type": "drop_max_length",
                "enabled": True,
                "max_length": 10,
                "description": "long",
            },
        ]
        kept, removals, _, counts = clean.apply_rules(
            ["ab", "abcdef", "abcdefghijkl"],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(kept, ["abcdef"])
        self.assertEqual(counts["drop_min_length"], 1)
        self.assertEqual(counts["drop_max_length"], 1)

    def test_language_signal_drop(self) -> None:
        rules = [
            {
                "id": "drop_english_signal",
                "type": "drop_language_signal",
                "enabled": True,
                "signals": ["english_signal"],
                "description": "en",
            }
        ]
        kept, removals, _, _ = clean.apply_rules(
            [
                "Mulungu ndi anthu kuti ndipo",
                "This is the best of the day and the night",
            ],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("Mulungu", kept[0])
        self.assertEqual(removals[0]["rule_id"], "drop_english_signal")
        self.assertIn("term_hits", removals[0]["metrics"])

    def test_dedupe_exact_keeps_first(self) -> None:
        rules = [
            {
                "id": "dedupe_exact",
                "type": "dedupe_exact",
                "enabled": True,
                "description": "dedupe",
            }
        ]
        kept, removals, _, counts = clean.apply_rules(
            ["same", "other", "same", "same"],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(kept, ["same", "other"])
        self.assertEqual(counts["dedupe_exact"], 2)
        self.assertEqual(removals[0]["line_number"], 3)
        self.assertEqual(removals[1]["line_number"], 4)

    def test_transform_strip_logged(self) -> None:
        rules = [
            {
                "id": "strip_edges",
                "type": "transform_strip",
                "enabled": True,
                "description": "strip",
            }
        ]
        kept, removals, transforms, counts = clean.apply_rules(
            ["  hello  ", "world"],
            rules,
            _base_config(),
            "bible",
        )
        self.assertEqual(kept, ["hello", "world"])
        self.assertEqual(len(removals), 0)
        self.assertEqual(len(transforms), 1)
        self.assertEqual(transforms[0]["line_number"], 1)
        self.assertIn("transform:strip_edges", counts)

    def test_first_matching_drop_wins(self) -> None:
        rules = [
            {
                "id": "drop_blank",
                "type": "drop_blank",
                "enabled": True,
                "description": "blank",
            },
            {
                "id": "drop_url",
                "type": "drop_url",
                "enabled": True,
                "description": "url",
            },
        ]
        # blank line should not also be logged as url even if empty
        _, removals, _, _ = clean.apply_rules(
            [""],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(removals[0]["rule_id"], "drop_blank")

    def test_disabled_rule_skipped(self) -> None:
        rules = [
            {
                "id": "drop_url",
                "type": "drop_url",
                "enabled": False,
                "description": "url",
            }
        ]
        kept, removals, _, _ = clean.apply_rules(
            ["https://x.com"],
            rules,
            _base_config(),
            "wikipedia",
        )
        self.assertEqual(kept, ["https://x.com"])
        self.assertEqual(removals, [])


class TestQualitySnapshot(unittest.TestCase):
    def test_before_after_metrics(self) -> None:
        cfg = _base_config()
        before = clean.quality_snapshot(
            ["hello", "", "Category:X", "see https://a.com"],
            cfg,
        )
        self.assertEqual(before["blank_lines"], 1)
        self.assertEqual(before["url_containing_lines"], 1)
        self.assertGreaterEqual(
            before["boilerplate_matching_lines"].get("category_prefix", 0), 1
        )


class TestEndToEnd(unittest.TestCase):
    def _fixture(self, root: Path) -> None:
        (root / "data/raw/bible").mkdir(parents=True)
        (root / "data/raw/wikipedia").mkdir(parents=True)
        (root / "configs/data").mkdir(parents=True)

        bible = "  Mulungu ndi anthu kuti.  \n\nSecond bible line.\n"
        wiki = (
            "Mu nkhani\n"
            "Category:Test\n"
            "Mulungu ndi anthu kuti ok.\n"
            "This is the best of the day and the night was here.\n"
            "Mulungu ndi anthu kuti ok.\n"
            "see https://example.com/page\n"
            "short\n"
            + ("Y" * 60)
            + "\n"
            "Ndipo mulungu ndi anthu yes.\n"
        )
        (root / "data/raw/bible/bible_clean.txt").write_text(bible, encoding="utf-8")
        (root / "data/raw/wikipedia/wiki_clean.txt").write_text(wiki, encoding="utf-8")

        cfg = _base_config(
            sources={
                "bible": {
                    "enabled": True,
                    "source_id": "bible",
                    "input_path": "data/raw/bible/bible_clean.txt",
                    "output_subdir": "bible",
                    "notes": "light",
                    "rules": [
                        {
                            "id": "drop_blank",
                            "type": "drop_blank",
                            "enabled": True,
                            "description": "blank",
                        },
                        {
                            "id": "strip_edges",
                            "type": "transform_strip",
                            "enabled": True,
                            "description": "strip",
                        },
                    ],
                },
                "wikipedia": {
                    "enabled": True,
                    "source_id": "wikipedia",
                    "input_path": "data/raw/wikipedia/wiki_clean.txt",
                    "output_subdir": "wikipedia",
                    "notes": "strong",
                    "rules": [
                        {
                            "id": "drop_blank",
                            "type": "drop_blank",
                            "enabled": True,
                            "description": "blank",
                        },
                        {
                            "id": "drop_category",
                            "type": "drop_regex",
                            "enabled": True,
                            "pattern": "Category\\s*:",
                            "flags": "i",
                            "description": "cat",
                        },
                        {
                            "id": "drop_mu_nkhani",
                            "type": "drop_regex",
                            "enabled": True,
                            "pattern": "Mu\\s+nkhani",
                            "flags": "i",
                            "description": "nav",
                        },
                        {
                            "id": "drop_url",
                            "type": "drop_url",
                            "enabled": True,
                            "description": "url",
                        },
                        {
                            "id": "drop_min_length",
                            "type": "drop_min_length",
                            "enabled": True,
                            "min_length": 10,
                            "description": "short",
                        },
                        {
                            "id": "drop_max_length",
                            "type": "drop_max_length",
                            "enabled": True,
                            "max_length": 40,
                            "description": "long",
                        },
                        {
                            "id": "drop_english_signal",
                            "type": "drop_language_signal",
                            "enabled": True,
                            "signals": ["english_signal"],
                            "description": "en",
                        },
                        {
                            "id": "dedupe_exact",
                            "type": "dedupe_exact",
                            "enabled": True,
                            "description": "dedupe",
                        },
                        {
                            "id": "strip_edges",
                            "type": "transform_strip",
                            "enabled": True,
                            "description": "strip",
                        },
                    ],
                },
            }
        )
        (root / "configs/data/cleaning.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def test_pipeline_writes_interim_only_raw_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            root = Path(tmp_s)
            self._fixture(root)
            bible_p = root / "data/raw/bible/bible_clean.txt"
            wiki_p = root / "data/raw/wikipedia/wiki_clean.txt"
            before = {
                "bible": (
                    bible_p.read_bytes(),
                    hashlib.sha256(bible_p.read_bytes()).hexdigest(),
                ),
                "wikipedia": (
                    wiki_p.read_bytes(),
                    hashlib.sha256(wiki_p.read_bytes()).hexdigest(),
                ),
            }

            rc = clean.main(
                [
                    "--config",
                    str(root / "configs/data/cleaning.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc, 0)

            for name, path in (
                ("bible", bible_p),
                ("wikipedia", wiki_p),
            ):
                data = path.read_bytes()
                self.assertEqual(data, before[name][0])
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(), before[name][1]
                )

            # Outputs only under interim
            interim = root / "data/interim/cleaning"
            self.assertTrue((interim / "bible" / "cleaned.txt").is_file())
            self.assertTrue((interim / "wikipedia" / "cleaned.txt").is_file())
            self.assertTrue((interim / "bible" / "removal_log.jsonl").is_file())
            self.assertTrue(
                (interim / "wikipedia" / "removal_log.jsonl").is_file()
            )
            self.assertTrue((interim / "summary.json").is_file())
            self.assertTrue((interim / "before_after_report.md").is_file())
            self.assertTrue((interim / "README.md").is_file())

            # No write into raw
            self.assertFalse((root / "data/raw/bible/cleaned.txt").exists())

            summary = json.loads(
                (interim / "summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(summary["raw_files_unchanged"])
            self.assertIn("bible", summary["sources"])
            self.assertIn("wikipedia", summary["sources"])

            # Bible blank removed + strip
            bible_clean = (
                interim / "bible" / "cleaned.txt"
            ).read_text(encoding="utf-8")
            self.assertIn("Mulungu ndi anthu kuti.", bible_clean)
            self.assertNotIn("\n\n", bible_clean)
            self.assertTrue(
                bible_clean.startswith("Mulungu")
            )  # stripped

            # Removal log valid JSONL with rule ids
            wiki_log = (
                interim / "wikipedia" / "removal_log.jsonl"
            ).read_text(encoding="utf-8")
            rules_seen = set()
            for line in wiki_log.splitlines():
                rec = json.loads(line)
                self.assertIn("rule_id", rec)
                self.assertIn("line_number", rec)
                self.assertIn("excerpt", rec)
                rules_seen.add(rec["rule_id"])
            self.assertIn("drop_category", rules_seen)
            self.assertIn("drop_url", rules_seen)
            self.assertIn("dedupe_exact", rules_seen)

            report = (interim / "before_after_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Before → after", report)
            self.assertIn("Raw files were not modified", report)

    def test_malformed_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            p = Path(tmp_s) / "bad.txt"
            p.write_bytes(b"\xff\xfe")
            with self.assertRaises(ValueError):
                clean.read_utf8_text(p)


if __name__ == "__main__":
    unittest.main()
