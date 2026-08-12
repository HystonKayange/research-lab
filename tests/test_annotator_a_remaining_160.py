#!/usr/bin/env python3
"""Tests for remaining-160 prep, full merge, self-review (no auto annotation)."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import merge_annotator_a_full_200 as merge  # noqa: E402
import measure_annotation_self_consistency as sc  # noqa: E402


class TestRemainingPrep(unittest.TestCase):
    def test_remaining_160_excludes_pilot(self) -> None:
        dev = REPO / "data/research/morphology_benchmark_v0.1/development"
        rem_p = dev / "remaining_160.jsonl"
        pilot_p = dev / "pilot_40.jsonl"
        if not rem_p.is_file() or not pilot_p.is_file():
            self.skipTest("not prepared")
        rem = [
            json.loads(l)
            for l in rem_p.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        pilot = {
            json.loads(l)["item_id"]
            for l in pilot_p.read_text(encoding="utf-8").splitlines()
            if l.strip()
        }
        self.assertEqual(len(rem), 160)
        for r in rem:
            self.assertNotIn(r["item_id"], pilot)
            self.assertTrue(str(r["item_id"]).startswith("morph_dev_"))

    def test_remaining_csv_no_tokenizer_columns(self) -> None:
        p = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/annotations"
            / "annotator_a_remaining_160.csv"
        )
        if not p.is_file():
            self.skipTest("csv missing")
        with p.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            self.assertNotIn("bpe_tokens", fields)
            self.assertNotIn("unigram_tokens", fields)
            self.assertIn("proposed_segmentation", fields)
            n = sum(1 for _ in reader)
        self.assertEqual(n, 160)

    def test_pilot_annotations_not_cleared(self) -> None:
        p = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/annotations"
            / "annotator_a_annotations.jsonl"
        )
        if not p.is_file():
            self.skipTest("pilot ann missing")
        rows = [
            json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        self.assertEqual(len(rows), 40)
        filled = sum(1 for r in rows if r.get("proposed_segmentation"))
        self.assertEqual(filled, 40)

    def test_full_200_unique(self) -> None:
        p = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/annotations"
            / "annotator_a_full_200.jsonl"
        )
        if not p.is_file():
            self.skipTest("full 200 missing")
        rows = [
            json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        self.assertEqual(len(rows), 200)
        self.assertEqual(len({r["item_id"] for r in rows}), 200)

    def test_reconstruction_helper(self) -> None:
        self.assertTrue(merge.reconstruction_ok("abc", "a+b+c"))
        self.assertFalse(merge.reconstruction_ok("abc", "a+bx"))
        self.assertTrue(merge.reconstruction_ok("abc", None))

    def test_self_review_blinded(self) -> None:
        p = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development"
            / "self_review_25_blinded.jsonl"
        )
        if not p.is_file():
            self.skipTest("self review missing")
        rows = [
            json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        self.assertEqual(len(rows), 25)
        for r in rows:
            self.assertIn("item_id", r)
            self.assertIn("surface_form", r)
            self.assertIn("context", r)
            self.assertNotIn("proposed_segmentation", r)
            self.assertNotIn("bpe_tokens", r)
            self.assertFalse(str(r["item_id"]).startswith("morph_hold_"))

    def test_self_consistency_awaits_pass2(self) -> None:
        rc = sc.main(["--repo-root", str(REPO)])
        self.assertEqual(rc, 0)
        rep = json.loads(
            (
                REPO / "data/reports/morphology_single_annotator_quality_v0_1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(rep["status"], "awaiting_pass2_reannotation")
        self.assertFalse(rep["comparison_run"])
        self.assertEqual(rep["framing"]["annotator_count"], 1)
        self.assertFalse(rep["framing"]["human_human_iaa_claim"])


if __name__ == "__main__":
    unittest.main()
