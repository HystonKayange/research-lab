#!/usr/bin/env python3
"""Tests for blind cleaning holdout sampling and metrics."""

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

import build_cleaning_holdout_sample as build  # noqa: E402
import summarize_cleaning_holdout as summary  # noqa: E402


def _minimal_config(**overrides) -> dict:
    cfg = {
        "version": "test",
        "source_id": "wikipedia",
        "dataset_role": "blind_holdout",
        "development_set_path": "data/reports/cleaning_review_sample.jsonl",
        "development_set_role": "development_validation",
        "random_seed": 99,
        "excerpt_length": 80,
        "include_uncertain_in_precision": False,
        "paths": {
            "raw": "data/raw/wikipedia/wiki_clean.txt",
            "cleaned": "data/interim/cleaning_v2/wikipedia/cleaned.txt",
            "removal_log": "data/interim/cleaning_v2/wikipedia/removal_log.jsonl",
            "transform_log": "data/interim/cleaning_v2/wikipedia/transform_log.jsonl",
            "cleaning_config": "configs/data/cleaning_v2.json",
            "sample_output": "data/reports/cleaning_holdout_sample.jsonl",
            "instructions_output": "data/reports/cleaning_holdout_instructions.md",
            "manifest_output": "data/reports/cleaning_holdout_manifest.json",
            "validation_json": "data/metadata/cleaning_holdout_validation.json",
            "validation_report": "data/reports/cleaning_holdout_validation_report.md",
            "backup_dir": "data/reports/cleaning_holdout_backups",
        },
        "targets": {"removed_total": 10, "kept_total": 10},
        "removed_strata_quotas": {
            "drop_category": 3,
            "drop_high_confidence_foreign": 2,
            "drop_short_conditional": 2,
            "drop_url_only": 1,
            "drop_blank": 1,
            "drop_digit_only": 1,
        },
        "removed_rule_aliases": {},
        "kept_strata_quotas": {
            "chichewa_signal": 3,
            "mixed_signal": 2,
            "insufficient_signal": 2,
            "short_retained": 1,
            "long_retained": 1,
            "url_stripped_retained": 0,
            "english_names_institutions": 1,
            "near_threshold": 0,
        },
        "short_line_threshold": 20,
        "long_line_threshold": 100,
        "near_threshold_short_min": 15,
        "near_threshold_short_max": 25,
        "near_threshold_long_min": 90,
        "near_threshold_long_max": 110,
        "language_signal": {"min_matches_for_signal": 2},
        "chichewa_signal_terms": ["ndi", "ndipo", "kuti", "mulungu", "anthu"],
        "english_signal_terms": ["the", "and", "of", "to", "in", "is", "was"],
        "german_signal_terms": ["der", "die", "das", "und"],
        "institution_name_patterns": ["University", "Ministry"],
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
        "wilson_z": 1.96,
        "generalization_targets": {
            "removal_precision_ge": 0.9,
            "false_removal_rate_le": 0.1,
            "useful_text_retention_ge": 0.9,
        },
    }
    cfg.update(overrides)
    return cfg


class TestExclusionAndIds(unittest.TestCase):
    def test_exclusion_by_hash_and_line(self) -> None:
        dev = [
            {
                "review_id": "dev1",
                "original_line_number": 5,
                "text_sha256": build.text_sha256("hello"),
                "excerpt": "hello",
            }
        ]
        h, lines, ids, lh = build.development_exclusion_sets(dev)
        self.assertTrue(
            build.is_excluded(
                5, "hello", dev_hashes=h, dev_lines=lines, dev_line_hash=lh
            )
        )
        self.assertTrue(
            build.is_excluded(
                99, "hello", dev_hashes=h, dev_lines=lines, dev_line_hash=lh
            )
        )
        self.assertFalse(
            build.is_excluded(
                6, "other", dev_hashes=h, dev_lines=lines, dev_line_hash=lh
            )
        )

    def test_stable_review_id(self) -> None:
        h = build.text_sha256("x")
        a = build.make_review_id("wikipedia", "removed", "drop_category", 1, h)
        b = build.make_review_id("wikipedia", "removed", "drop_category", 1, h)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)


class TestWilsonAndMetrics(unittest.TestCase):
    def test_wilson_interval(self) -> None:
        ci = summary.wilson_interval(9, 10, z=1.96)
        self.assertIsNotNone(ci["low"])
        self.assertIsNotNone(ci["high"])
        self.assertLessEqual(ci["low"], ci["p"])
        self.assertGreaterEqual(ci["high"], ci["p"])
        self.assertEqual(ci["n"], 10)

    def test_metric_calculations(self) -> None:
        records = [
            {
                "v2_decision": "removed",
                "v2_rule_id": "drop_category",
                "review_label": "boilerplate_or_noise",
            },
            {
                "v2_decision": "removed",
                "v2_rule_id": "drop_category",
                "review_label": "valid_chichewa",
            },
            {
                "v2_decision": "kept",
                "v2_rule_id": None,
                "review_label": "valid_chichewa",
            },
            {
                "v2_decision": "kept",
                "v2_rule_id": None,
                "review_label": "foreign_language",
            },
            {
                "v2_decision": "removed",
                "v2_rule_id": "drop_url_only",
                "review_label": "uncertain",
            },
        ]
        s = summary.summarize(records, _minimal_config())
        # removed decisive: 1 correct + 1 false → prec 0.5 frr 0.5
        self.assertAlmostEqual(s["metrics"]["removal_precision"], 0.5)
        self.assertAlmostEqual(s["metrics"]["false_removal_rate"], 0.5)
        # useful: 2 total (one removed FP, one kept) → retention 0.5
        self.assertAlmostEqual(s["metrics"]["useful_text_retention"], 0.5)
        self.assertEqual(s["annotation_status"], "complete")


class TestEndToEndHoldout(unittest.TestCase):
    def test_build_excludes_dev_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            root = Path(tmp_s)
            raw = root / "data/raw/wikipedia"
            interim = root / "data/interim/cleaning_v2/wikipedia"
            raw.mkdir(parents=True)
            interim.mkdir(parents=True)
            (root / "configs/data").mkdir(parents=True)
            (root / "data/reports").mkdir(parents=True)
            (root / "data/metadata").mkdir(parents=True)

            # 40 raw lines
            lines = []
            for i in range(1, 41):
                if i <= 5:
                    lines.append(f"Category:Test{i}")
                elif i <= 10:
                    lines.append(f"This is the best of the day and night {i}")
                elif i <= 12:
                    lines.append(str(i))
                elif i <= 15:
                    lines.append(f"https://example.com/{i}")
                elif i == 16:
                    lines.append("")
                else:
                    lines.append(
                        f"Mulungu ndi anthu kuti line number {i} ndipo more words here."
                    )
            raw_text = "\n".join(lines) + "\n"
            (raw / "wiki_clean.txt").write_text(raw_text, encoding="utf-8")
            raw_sha = hashlib.sha256(raw_text.encode()).hexdigest()

            # removal log for first 16-ish
            rem = []
            for i in range(1, 6):
                rem.append(
                    {
                        "line_number": i,
                        "rule_id": "drop_category",
                        "rule_type": "drop_regex",
                    }
                )
            for i in range(6, 11):
                rem.append(
                    {
                        "line_number": i,
                        "rule_id": "drop_high_confidence_foreign",
                        "rule_type": "drop_high_confidence_foreign",
                    }
                )
            for i in range(11, 13):
                rem.append(
                    {
                        "line_number": i,
                        "rule_id": "drop_digit_only",
                        "rule_type": "drop_digit_only",
                    }
                )
            for i in range(13, 16):
                rem.append(
                    {
                        "line_number": i,
                        "rule_id": "drop_url_only",
                        "rule_type": "drop_url_only",
                    }
                )
            rem.append(
                {
                    "line_number": 16,
                    "rule_id": "drop_blank",
                    "rule_type": "drop_blank",
                }
            )
            with (interim / "removal_log.jsonl").open("w", encoding="utf-8") as f:
                for r in rem:
                    f.write(json.dumps(r) + "\n")
            (interim / "transform_log.jsonl").write_text("", encoding="utf-8")
            (interim / "cleaned.txt").write_text(
                "\n".join(lines[16:]) + "\n", encoding="utf-8"
            )

            # development set: exclude lines 17 and 18
            dev = []
            for ln in (17, 18):
                t = lines[ln - 1]
                dev.append(
                    {
                        "review_id": f"dev{ln}",
                        "source_id": "wikipedia",
                        "original_line_number": ln,
                        "decision": "kept",
                        "rule_id": None,
                        "excerpt": t,
                        "text_sha256": build.text_sha256(t),
                        "review_label": "valid_chichewa",
                        "review_notes": None,
                    }
                )
            dev_path = root / "data/reports/cleaning_review_sample.jsonl"
            with dev_path.open("w", encoding="utf-8") as f:
                for r in dev:
                    f.write(json.dumps(r) + "\n")
            dev_sha = hashlib.sha256(dev_path.read_bytes()).hexdigest()

            cfg = _minimal_config(
                development_set_path="data/reports/cleaning_review_sample.jsonl"
            )
            # fix long threshold so some long retained exist
            cfg["long_line_threshold"] = 40
            cp = root / "configs/data/cleaning_holdout.json"
            cp.write_text(json.dumps(cfg), encoding="utf-8")
            (root / "configs/data/cleaning_v2.json").write_text("{}", encoding="utf-8")

            rc = build.main(
                ["--config", str(cp), "--repo-root", str(root)]
            )
            self.assertEqual(rc, 0)

            # raw + dev unchanged
            self.assertEqual(
                hashlib.sha256((raw / "wiki_clean.txt").read_bytes()).hexdigest(),
                raw_sha,
            )
            self.assertEqual(
                hashlib.sha256(dev_path.read_bytes()).hexdigest(),
                dev_sha,
            )

            holdout = [
                json.loads(l)
                for l in (
                    root / "data/reports/cleaning_holdout_sample.jsonl"
                )
                .read_text(encoding="utf-8")
                .splitlines()
                if l.strip()
            ]
            self.assertGreater(len(holdout), 0)
            dev_hashes = {r["text_sha256"] for r in dev}
            dev_lines = {r["original_line_number"] for r in dev}
            ho_hashes = {r["text_sha256"] for r in holdout}
            ho_lines = {r["original_line_number"] for r in holdout}
            self.assertEqual(len(ho_hashes & dev_hashes), 0)
            self.assertEqual(len(ho_lines & dev_lines), 0)
            self.assertNotIn(17, ho_lines)
            self.assertNotIn(18, ho_lines)

            for r in holdout:
                self.assertIsNone(r["review_label"])
                self.assertIn(r["v2_decision"], ("removed", "kept"))
                self.assertEqual(len(r["text_sha256"]), 64)
                # Unicode path: Chichewa lines present
            # deterministic second run
            rc2 = build.main(
                ["--config", str(cp), "--repo-root", str(root)]
            )
            self.assertEqual(rc2, 0)
            holdout2 = [
                json.loads(l)
                for l in (
                    root / "data/reports/cleaning_holdout_sample.jsonl"
                )
                .read_text(encoding="utf-8")
                .splitlines()
                if l.strip()
            ]
            self.assertEqual(
                [r["review_id"] for r in holdout],
                [r["review_id"] for r in holdout2],
            )

            # label and summarize
            for r in holdout2:
                if r["v2_decision"] == "removed":
                    r["review_label"] = "boilerplate_or_noise"
                else:
                    r["review_label"] = "valid_chichewa"
            sp = root / "data/reports/cleaning_holdout_sample.jsonl"
            with sp.open("w", encoding="utf-8") as f:
                for r in holdout2:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            rc3 = summary.main(
                [
                    "--config",
                    str(cp),
                    "--sample",
                    str(sp),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc3, 0)
            val = json.loads(
                (root / "data/metadata/cleaning_holdout_validation.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(val["annotation_status"], "complete")
            self.assertIn("confidence_intervals", val)
            self.assertIsNotNone(val["confidence_intervals"]["removal_precision"]["low"])


class TestUnicode(unittest.TestCase):
    def test_unicode_sha_and_excerpt(self) -> None:
        t = "mŵana wanga"
        h = build.text_sha256(t)
        self.assertEqual(h, hashlib.sha256(t.encode("utf-8")).hexdigest())
        rec = build.build_candidate_record(
            source_id="wikipedia",
            line_number=1,
            text=t,
            decision="kept",
            rule_id=None,
            excerpt_len=50,
            strata=["chichewa_signal"],
        )
        self.assertIn("ŵ", rec["excerpt"])


if __name__ == "__main__":
    unittest.main()
