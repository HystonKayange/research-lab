#!/usr/bin/env python3
"""Tests for cleaning review sample build and summary."""

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

import build_cleaning_review_sample as build  # noqa: E402
import summarize_cleaning_review as summarize  # noqa: E402


def _cfg(**overrides) -> dict:
    cfg = {
        "version": "test",
        "source_id": "wikipedia",
        "random_seed": 7,
        "excerpt_length": 40,
        "include_uncertain_in_precision": False,
        "paths": {
            "raw": "data/raw/wikipedia/wiki_clean.txt",
            "cleaned": "data/interim/cleaning/wikipedia/cleaned.txt",
            "removal_log": "data/interim/cleaning/wikipedia/removal_log.jsonl",
            "sample_output": "data/reports/cleaning_review_sample.jsonl",
            "instructions_output": "data/reports/cleaning_review_instructions.md",
            "validation_json": "data/metadata/cleaning_validation.json",
            "validation_report": "data/reports/cleaning_validation_report.md",
        },
        "priority_rule_samples": {
            "drop_min_length": 2,
            "drop_english_signal": 2,
            "drop_mixed_signal": 1,
            "drop_max_length": 1,
        },
        "other_rule_samples": {
            "drop_category": 2,
            "drop_url": 1,
            "drop_digit_only": 1,
            "dedupe_exact": 1,
            "drop_blank": 1,
        },
        "kept_sample_size": 3,
        "allowed_labels": [
            "valid_chichewa",
            "useful_mixed_chichewa",
            "boilerplate_or_noise",
            "foreign_language",
            "duplicate",
            "uncertain",
        ],
        "false_removal_labels": ["valid_chichewa", "useful_mixed_chichewa"],
        "correct_removal_labels": [
            "boilerplate_or_noise",
            "foreign_language",
            "duplicate",
        ],
        "useful_kept_labels": ["valid_chichewa", "useful_mixed_chichewa"],
        "noise_kept_labels": ["boilerplate_or_noise", "duplicate"],
        "foreign_kept_labels": ["foreign_language"],
        "boilerplate_kept_labels": ["boilerplate_or_noise"],
    }
    cfg.update(overrides)
    return cfg


class TestReviewIdAndHash(unittest.TestCase):
    def test_stable_review_id(self) -> None:
        h = build.text_sha256("hello")
        a = build.make_review_id("wikipedia", "removed", "drop_url", 5, h)
        b = build.make_review_id("wikipedia", "removed", "drop_url", 5, h)
        c = build.make_review_id("wikipedia", "removed", "drop_url", 6, h)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 16)

    def test_text_sha256(self) -> None:
        self.assertEqual(
            build.text_sha256("abc"),
            hashlib.sha256(b"abc").hexdigest(),
        )


class TestSampling(unittest.TestCase):
    def test_deterministic_removed_by_rule(self) -> None:
        raw_lines = [f"line {i}" for i in range(1, 21)]
        removals = []
        for i in range(1, 11):
            removals.append(
                {
                    "line_number": i,
                    "rule_id": "drop_min_length",
                    "rule_type": "drop_min_length",
                    "rule_description": "short",
                    "metrics": {},
                }
            )
        for i in range(11, 16):
            removals.append(
                {
                    "line_number": i,
                    "rule_id": "drop_category",
                    "rule_type": "drop_regex",
                    "rule_description": "cat",
                    "metrics": {},
                }
            )
        cfg = _cfg()
        s1, st1 = build.build_removed_samples(
            removals, raw_lines, {"drop_min_length": 3, "drop_category": 2}, cfg
        )
        s2, st2 = build.build_removed_samples(
            removals, raw_lines, {"drop_min_length": 3, "drop_category": 2}, cfg
        )
        self.assertEqual(
            [r["review_id"] for r in s1],
            [r["review_id"] for r in s2],
        )
        self.assertEqual(st1["sampled_by_rule"]["drop_min_length"], 3)
        self.assertEqual(st1["sampled_by_rule"]["drop_category"], 2)
        for r in s1:
            self.assertEqual(r["decision"], "removed")
            self.assertIsNone(r["review_label"])
            self.assertEqual(r["source_id"], "wikipedia")
            # full text hash matches raw line
            full = raw_lines[r["original_line_number"] - 1]
            self.assertEqual(r["text_sha256"], build.text_sha256(full))

    def test_kept_excludes_removed_line_numbers(self) -> None:
        raw_lines = ["a", "b", "c", "d", "e"]
        removed = {1, 3, 5}
        cleaned = ["b", "d"]
        samples, stats = build.build_kept_samples(
            raw_lines, removed, cleaned, n_kept=10, config=_cfg()
        )
        nums = {s["original_line_number"] for s in samples}
        self.assertTrue(nums.isdisjoint(removed))
        self.assertEqual(stats["kept_population_nonblank"], 2)
        self.assertEqual(stats["sampled"], 2)
        for s in samples:
            self.assertEqual(s["decision"], "kept")
            self.assertIsNone(s["rule_id"])


class TestSummaryMetrics(unittest.TestCase):
    def test_removal_precision_and_false_rate(self) -> None:
        records = [
            {
                "review_id": "1",
                "decision": "removed",
                "rule_id": "drop_min_length",
                "review_label": "boilerplate_or_noise",
            },
            {
                "review_id": "2",
                "decision": "removed",
                "rule_id": "drop_min_length",
                "review_label": "valid_chichewa",
            },
            {
                "review_id": "3",
                "decision": "removed",
                "rule_id": "drop_english_signal",
                "review_label": "foreign_language",
            },
            {
                "review_id": "4",
                "decision": "removed",
                "rule_id": "drop_english_signal",
                "review_label": "uncertain",
            },
            {
                "review_id": "5",
                "decision": "kept",
                "rule_id": None,
                "review_label": "valid_chichewa",
            },
            {
                "review_id": "6",
                "decision": "kept",
                "rule_id": None,
                "review_label": "boilerplate_or_noise",
            },
            {
                "review_id": "7",
                "decision": "kept",
                "rule_id": None,
                "review_label": "foreign_language",
            },
            {
                "review_id": "8",
                "decision": "kept",
                "rule_id": None,
                "review_label": None,
            },
        ]
        summary = summarize.summarize(records, _cfg())
        ro = summary["removed"]["overall"]
        # decisive removed: boilerplate, valid_chichewa, foreign (uncertain excluded)
        # correct=2, false=1, precision=2/3, frr=1/3
        self.assertEqual(ro["n_correct_removal"], 2)
        self.assertEqual(ro["n_false_removal"], 1)
        self.assertAlmostEqual(ro["removal_precision"], 2 / 3, places=5)
        self.assertAlmostEqual(ro["false_removal_rate"], 1 / 3, places=5)

        rule_min = summary["removed"]["by_rule"]["drop_min_length"]
        self.assertEqual(rule_min["n_false_removal"], 1)
        self.assertEqual(rule_min["n_correct_removal"], 1)

        ko = summary["kept"]
        # decisive kept: valid, boilerplate, foreign (1 unlabeled)
        self.assertEqual(ko["n_useful"], 1)
        self.assertEqual(ko["n_noise"], 1)
        self.assertEqual(ko["n_foreign"], 1)
        self.assertAlmostEqual(ko["useful_text_rate"], 1 / 3, places=5)
        self.assertAlmostEqual(ko["kept_noise_rate"], 1 / 3, places=5)
        self.assertAlmostEqual(ko["foreign_language_leakage"], 1 / 3, places=5)
        self.assertAlmostEqual(ko["boilerplate_leakage"], 1 / 3, places=5)
        self.assertEqual(summary["annotation_status"], "partial")

    def test_pending_when_unlabeled(self) -> None:
        records = [
            {
                "review_id": "a",
                "decision": "removed",
                "rule_id": "drop_url",
                "review_label": None,
            }
        ]
        summary = summarize.summarize(records, _cfg())
        self.assertEqual(summary["annotation_status"], "pending_human_labels")
        self.assertIsNone(summary["removed"]["overall"]["removal_precision"])


class TestEndToEnd(unittest.TestCase):
    def test_build_and_summarize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            root = Path(tmp_s)
            raw_dir = root / "data/raw/wikipedia"
            interim = root / "data/interim/cleaning/wikipedia"
            raw_dir.mkdir(parents=True)
            interim.mkdir(parents=True)
            (root / "configs/data").mkdir(parents=True)
            (root / "data/reports").mkdir(parents=True)
            (root / "data/metadata").mkdir(parents=True)

            # 10 raw lines
            raw_lines = [
                "keep one chichewa text here",
                "Category:Foo",
                "xx",  # short
                "see https://example.com",
                "keep two chichewa text here",
                "42",
                "Category:Bar",
                "keep three chichewa text here",
                "English the and of to is was line",
                "keep four chichewa text here",
            ]
            (raw_dir / "wiki_clean.txt").write_text(
                "\n".join(raw_lines) + "\n", encoding="utf-8"
            )
            # removals: 2,3,4,6,7,9
            removals = [
                {"line_number": 2, "rule_id": "drop_category", "rule_type": "drop_regex", "rule_description": "c", "metrics": {}},
                {"line_number": 3, "rule_id": "drop_min_length", "rule_type": "drop_min_length", "rule_description": "s", "metrics": {}},
                {"line_number": 4, "rule_id": "drop_url", "rule_type": "drop_url", "rule_description": "u", "metrics": {}},
                {"line_number": 6, "rule_id": "drop_digit_only", "rule_type": "drop_digit_only", "rule_description": "d", "metrics": {}},
                {"line_number": 7, "rule_id": "drop_category", "rule_type": "drop_regex", "rule_description": "c", "metrics": {}},
                {"line_number": 9, "rule_id": "drop_english_signal", "rule_type": "drop_language_signal", "rule_description": "e", "metrics": {}},
            ]
            with (interim / "removal_log.jsonl").open("w", encoding="utf-8") as f:
                for r in removals:
                    f.write(json.dumps(r) + "\n")
            cleaned = [
                raw_lines[0],
                raw_lines[4],
                raw_lines[7],
                raw_lines[9],
            ]
            (interim / "cleaned.txt").write_text(
                "\n".join(cleaned) + "\n", encoding="utf-8"
            )

            cfg = _cfg(
                priority_rule_samples={
                    "drop_min_length": 1,
                    "drop_english_signal": 1,
                    "drop_mixed_signal": 1,
                    "drop_max_length": 1,
                },
                other_rule_samples={
                    "drop_category": 2,
                    "drop_url": 1,
                    "drop_digit_only": 1,
                    "dedupe_exact": 1,
                },
                kept_sample_size=3,
            )
            (root / "configs/data/cleaning_review.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )

            raw_before = (raw_dir / "wiki_clean.txt").read_bytes()
            cleaned_before = (interim / "cleaned.txt").read_bytes()
            log_before = (interim / "removal_log.jsonl").read_bytes()

            rc = build.main(
                [
                    "--config",
                    str(root / "configs/data/cleaning_review.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc, 0)

            # Inputs unchanged
            self.assertEqual(
                (raw_dir / "wiki_clean.txt").read_bytes(), raw_before
            )
            self.assertEqual(
                (interim / "cleaned.txt").read_bytes(), cleaned_before
            )
            self.assertEqual(
                (interim / "removal_log.jsonl").read_bytes(), log_before
            )

            sample_path = root / "data/reports/cleaning_review_sample.jsonl"
            self.assertTrue(sample_path.is_file())
            records = [
                json.loads(line)
                for line in sample_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreater(len(records), 0)
            for rec in records:
                for key in (
                    "review_id",
                    "source_id",
                    "original_line_number",
                    "decision",
                    "excerpt",
                    "text_sha256",
                    "review_label",
                    "review_notes",
                ):
                    self.assertIn(key, rec)
                self.assertIsNone(rec["review_label"])

            # Determinism
            rc2 = build.main(
                [
                    "--config",
                    str(root / "configs/data/cleaning_review.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc2, 0)
            records2 = [
                json.loads(line)
                for line in sample_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(
                [r["review_id"] for r in records],
                [r["review_id"] for r in records2],
            )

            # Summarize unlabeled
            rc3 = summarize.main(
                [
                    "--config",
                    str(root / "configs/data/cleaning_review.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc3, 0)
            val = json.loads(
                (root / "data/metadata/cleaning_validation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(val["annotation_status"], "pending_human_labels")
            report = (
                root / "data/reports/cleaning_validation_report.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Annotation status", report)

            # Label all and re-summarize
            for rec in records:
                if rec["decision"] == "removed":
                    rec["review_label"] = "boilerplate_or_noise"
                else:
                    rec["review_label"] = "valid_chichewa"
            with sample_path.open("w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec) + "\n")
            rc4 = summarize.main(
                [
                    "--config",
                    str(root / "configs/data/cleaning_review.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc4, 0)
            val2 = json.loads(
                (root / "data/metadata/cleaning_validation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(val2["annotation_status"], "complete")
            self.assertEqual(
                val2["removed"]["overall"]["false_removal_rate"], 0.0
            )
            self.assertEqual(val2["kept"]["useful_text_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
