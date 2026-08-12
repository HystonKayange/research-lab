#!/usr/bin/env python3
"""Tests for cleaning policy v2 rules and frozen evaluation."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS))

import clean_sources as clean  # noqa: E402
import evaluate_cleaning_policy as ev  # noqa: E402


def _cfg(**overrides) -> dict:
    base = {
        "version": "2-test",
        "excerpt_length": 80,
        "short_line_threshold": 20,
        "language_signal": {
            "min_matches_for_signal": 2,
            "min_english_hits": 3,
            "min_german_hits": 2,
            "max_chichewa_hits": 0,
            "dominance_margin": 3,
        },
        "chichewa_signal_terms": ["ndi", "ndipo", "kuti", "mulungu", "anthu", "anali"],
        "english_signal_terms": ["the", "and", "of", "to", "in", "is", "was", "for", "with"],
        "german_signal_terms": ["der", "die", "das", "und", "ist", "von"],
    }
    base.update(overrides)
    return base


def _apply(lines: list[str], rules: list[dict], cfg: dict | None = None):
    return clean.apply_rules(lines, rules, cfg or _cfg(), "wikipedia")


class TestV2ShortLines(unittest.TestCase):
    def test_short_valid_chichewa_retained(self) -> None:
        rules = [
            {
                "id": "drop_short_conditional",
                "type": "drop_short_conditional",
                "enabled": True,
                "max_length": 20,
                "boilerplate_patterns": [],
            }
        ]
        kept, removals, _, _ = _apply(["Mzuzu", "Hoseya", "Songwe"], rules)
        self.assertIn("Mzuzu", kept)
        self.assertIn("Hoseya", kept)
        self.assertIn("Songwe", kept)
        # Bare "Link" is treated as short metadata chrome under conditional rules
        kept2, rem2, _, _ = _apply(["Link"], rules)
        self.assertEqual(kept2, [])
        self.assertTrue(any(r["rule_id"] == "drop_short_conditional" for r in rem2))

    def test_short_boilerplate_removed(self) -> None:
        rules = [
            {
                "id": "drop_short_conditional",
                "type": "drop_short_conditional",
                "enabled": True,
                "max_length": 20,
                "boilerplate_patterns": [{"pattern": "^thumb\\b", "flags": "i"}],
            },
            {"id": "drop_digit_only", "type": "drop_digit_only", "enabled": True},
        ]
        kept, removals, _, counts = _apply(
            ["thumb", "12345", "Mzuzu"], rules
        )
        self.assertEqual(kept, ["Mzuzu"])
        self.assertEqual(counts.get("drop_short_conditional", 0) + counts.get("drop_digit_only", 0), 2)


class TestV2MixedAndForeign(unittest.TestCase):
    def test_useful_mixed_retained(self) -> None:
        rules = [
            {
                "id": "drop_high_confidence_foreign",
                "type": "drop_high_confidence_foreign",
                "enabled": True,
                "min_english_hits": 3,
                "max_chichewa_hits": 0,
                "dominance_margin": 3,
            }
        ]
        line = "Anaphunzira zamalamulo ku University of Fort Hare asanagwire ntchito."
        kept, _, _, _ = _apply([line], rules)
        self.assertEqual(kept, [line])

    def test_english_institutional_high_conf_dropped(self) -> None:
        rules = [
            {
                "id": "drop_high_confidence_foreign",
                "type": "drop_high_confidence_foreign",
                "enabled": True,
                "min_english_hits": 3,
                "max_chichewa_hits": 0,
                "dominance_margin": 3,
            }
        ]
        line = "This is the best of the day and the night for the team"
        kept, removals, _, _ = _apply([line], rules)
        self.assertEqual(kept, [])
        self.assertEqual(removals[0]["rule_id"], "drop_high_confidence_foreign")


class TestV2URL(unittest.TestCase):
    def test_url_stripped_text_remains(self) -> None:
        rules = [
            {
                "id": "strip_urls",
                "type": "transform_strip_urls",
                "enabled": True,
            },
            {"id": "drop_url_only", "type": "drop_url_only", "enabled": True},
        ]
        line = "George Washington ndi mtsogoleri https://example.com/x"
        kept, removals, transforms, _ = _apply([line], rules)
        self.assertEqual(len(kept), 1)
        self.assertNotIn("https://", kept[0])
        self.assertIn("George Washington", kept[0])
        self.assertEqual(len(removals), 0)
        self.assertTrue(any(t["rule_id"] == "strip_urls" for t in transforms))

    def test_url_only_removed(self) -> None:
        rules = [
            {"id": "strip_urls", "type": "transform_strip_urls", "enabled": True},
            {"id": "drop_url_only", "type": "drop_url_only", "enabled": True},
        ]
        # After strip, empty → blank after transform OR drop_url_only before strip
        kept, removals, _, _ = _apply(["https://example.com/only"], rules)
        self.assertEqual(kept, [])
        self.assertTrue(len(removals) >= 1)


class TestV2LongAndBoilerplate(unittest.TestCase):
    def test_valid_long_line_retained(self) -> None:
        rules = [
            {
                "id": "drop_long_table_dump",
                "type": "drop_long_table_dump",
                "enabled": True,
                "min_length": 100,
            }
        ]
        long_ok = ("Anthu ambiri ochoka ku mayikao a ku Malawi " * 8).strip()
        self.assertGreater(len(long_ok), 100)
        kept, _, _, _ = _apply([long_ok], rules)
        self.assertEqual(kept, [long_ok])

    def test_known_boilerplate_still_removed(self) -> None:
        rules = [
            {
                "id": "drop_category",
                "type": "drop_regex",
                "enabled": True,
                "pattern": "Category\\s*:",
                "flags": "i",
            },
            {
                "id": "drop_blank",
                "type": "drop_blank",
                "enabled": True,
            },
        ]
        kept, removals, _, _ = _apply(
            ["Category:Zambia", "Mulungu ndi anthu kuti", ""], rules
        )
        self.assertEqual(kept, ["Mulungu ndi anthu kuti"])
        ids = {r["rule_id"] for r in removals}
        self.assertIn("drop_category", ids)
        self.assertIn("drop_blank", ids)


class TestV1Compatibility(unittest.TestCase):
    def test_v1_url_still_drops_whole_line(self) -> None:
        rules = [
            {"id": "drop_url", "type": "drop_url", "enabled": True},
        ]
        kept, removals, _, _ = _apply(
            ["see https://example.com ok"], rules
        )
        self.assertEqual(kept, [])
        self.assertEqual(removals[0]["rule_id"], "drop_url")


class TestEvaluation(unittest.TestCase):
    def test_deterministic_and_labels_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            root = Path(tmp_s)
            raw = root / "data/raw/wikipedia"
            raw.mkdir(parents=True)
            (root / "configs/data").mkdir(parents=True)
            (root / "data/reports").mkdir(parents=True)
            (root / "data/metadata").mkdir(parents=True)

            lines = [
                "Category:Test",
                "Mzuzu",
                "This is the best of the day and the night",
                "Mulungu ndi anthu kuti ndipo",
            ]
            (raw / "wiki_clean.txt").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
            before_sha = hashlib.sha256(
                (raw / "wiki_clean.txt").read_bytes()
            ).hexdigest()

            sample = [
                {
                    "review_id": "a1",
                    "source_id": "wikipedia",
                    "original_line_number": 1,
                    "decision": "removed",
                    "rule_id": "drop_category",
                    "excerpt": "Category:Test",
                    "text_sha256": "a" * 64,
                    "review_label": "boilerplate_or_noise",
                    "review_notes": None,
                },
                {
                    "review_id": "a2",
                    "source_id": "wikipedia",
                    "original_line_number": 2,
                    "decision": "removed",
                    "rule_id": "drop_min_length",
                    "excerpt": "Mzuzu",
                    "text_sha256": "b" * 64,
                    "review_label": "valid_chichewa",
                    "review_notes": None,
                },
                {
                    "review_id": "a3",
                    "source_id": "wikipedia",
                    "original_line_number": 3,
                    "decision": "removed",
                    "rule_id": "drop_english_signal",
                    "excerpt": "english",
                    "text_sha256": "c" * 64,
                    "review_label": "foreign_language",
                    "review_notes": None,
                },
                {
                    "review_id": "a4",
                    "source_id": "wikipedia",
                    "original_line_number": 4,
                    "decision": "kept",
                    "rule_id": None,
                    "excerpt": "mulungu",
                    "text_sha256": "d" * 64,
                    "review_label": "valid_chichewa",
                    "review_notes": None,
                },
            ]
            sp = root / "data/reports/cleaning_review_sample.jsonl"
            with sp.open("w", encoding="utf-8") as f:
                for r in sample:
                    f.write(json.dumps(r) + "\n")
            labels_before = {r["review_id"]: r["review_label"] for r in sample}

            cfg = _cfg(
                sources={
                    "wikipedia": {
                        "enabled": True,
                        "source_id": "wikipedia",
                        "input_path": "data/raw/wikipedia/wiki_clean.txt",
                        "output_subdir": "wikipedia",
                        "rules": [
                            {
                                "id": "drop_category",
                                "type": "drop_regex",
                                "enabled": True,
                                "pattern": "Category\\s*:",
                                "flags": "i",
                            },
                            {
                                "id": "drop_high_confidence_foreign",
                                "type": "drop_high_confidence_foreign",
                                "enabled": True,
                                "min_english_hits": 3,
                                "max_chichewa_hits": 0,
                                "dominance_margin": 3,
                            },
                        ],
                    }
                }
            )
            cp = root / "configs/data/cleaning_v2.json"
            cp.write_text(json.dumps(cfg), encoding="utf-8")

            rc = ev.main(
                [
                    "--config",
                    str(cp),
                    "--sample",
                    str(sp),
                    "--json-output",
                    str(root / "data/metadata/out.json"),
                    "--report-output",
                    str(root / "data/reports/out.md"),
                    "--repo-root",
                    str(root),
                    "--policy-name",
                    "test_v2",
                ]
            )
            self.assertEqual(rc, 0)
            after_sha = hashlib.sha256(
                (raw / "wiki_clean.txt").read_bytes()
            ).hexdigest()
            self.assertEqual(before_sha, after_sha)

            # labels immutable
            reloaded = [
                json.loads(l)
                for l in sp.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
            for r in reloaded:
                self.assertEqual(r["review_label"], labels_before[r["review_id"]])

            out = json.loads(
                (root / "data/metadata/out.json").read_text(encoding="utf-8")
            )
            self.assertIn("metrics", out)
            # re-run deterministic
            rc2 = ev.main(
                [
                    "--config",
                    str(cp),
                    "--sample",
                    str(sp),
                    "--json-output",
                    str(root / "data/metadata/out2.json"),
                    "--report-output",
                    str(root / "data/reports/out2.md"),
                    "--repo-root",
                    str(root),
                    "--policy-name",
                    "test_v2",
                ]
            )
            self.assertEqual(rc2, 0)
            out2 = json.loads(
                (root / "data/metadata/out2.json").read_text(encoding="utf-8")
            )
            self.assertEqual(out["metrics"], out2["metrics"])


if __name__ == "__main__":
    unittest.main()
