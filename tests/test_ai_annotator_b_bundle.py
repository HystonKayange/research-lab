#!/usr/bin/env python3
"""Tests for blinded AI Annotator B bundle (no annotation)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import validate_ai_annotator_b_bundle as val  # noqa: E402


class TestBundleIfPresent(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/ai_annotator_b_bundle"
        )

    def test_validate_script_passes(self) -> None:
        if not self.bundle.is_dir():
            self.skipTest("bundle not built")
        rc = val.main(["--repo-root", str(REPO)])
        self.assertEqual(rc, 0)

    def test_exactly_40_and_allowed_fields(self) -> None:
        p = self.bundle / "pilot_40_blinded.jsonl"
        if not p.is_file():
            self.skipTest("blinded file missing")
        rows = [
            json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        self.assertEqual(len(rows), 40)
        for r in rows:
            self.assertTrue(set(r.keys()).issubset(val.ALLOWED_FIELDS))
            self.assertTrue(str(r["item_id"]).startswith("morph_dev_"))
            self.assertFalse(str(r["item_id"]).startswith("morph_hold_"))
            for bad in ("bpe_tokens", "unigram_tokens", "proposed_segmentation", "automatic_tags"):
                self.assertNotIn(bad, r)

    def test_no_annotator_a_files_in_bundle(self) -> None:
        if not self.bundle.is_dir():
            self.skipTest("bundle not built")
        names = {p.name for p in self.bundle.rglob("*") if p.is_file()}
        self.assertNotIn("annotator_a_annotations.jsonl", names)
        self.assertNotIn("annotator_a_annotations.csv", names)
        self.assertNotIn("pilot_chat_state.json", names)

    def test_manifest_excludes_a(self) -> None:
        man = self.bundle / "bundle_manifest.json"
        if not man.is_file():
            self.skipTest("manifest missing")
        m = json.loads(man.read_text(encoding="utf-8"))
        self.assertTrue(m.get("annotator_a_outputs_excluded"))
        self.assertFalse(m.get("locked_holdout_included"))
        self.assertFalse(m.get("annotation_performed_at_bundle_creation"))
        self.assertEqual(m.get("item_count"), 40)


if __name__ == "__main__":
    unittest.main()
