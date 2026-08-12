#!/usr/bin/env python3
"""Tests for baseline morphology failure analysis (no LM test, no hybrid train)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import analyze_baseline_morphology_failures as ana  # noqa: E402


class TestSafety(unittest.TestCase):
    def test_refuse_test_path(self) -> None:
        with self.assertRaises(RuntimeError):
            ana.refuse_test_path(REPO / "data/splits/chichewa_corpus_v0.1/test/combined.txt")

    def test_load_inventory_rejects_test_split_name(self) -> None:
        with self.assertRaises(ValueError):
            ana.load_inventory(REPO / "data/splits/chichewa_corpus_v0.1", "test")

    def test_no_morpheme_claim_in_module_doc(self) -> None:
        src = (REPO / "scripts/tokenizers/analyze_baseline_morphology_failures.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Does not call recurring character strings", src)
        self.assertIn("requires_human_review", src)


class TestDiagnosticsHelpers(unittest.TestCase):
    def test_pearson_perfect(self) -> None:
        r = ana.pearson([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])
        self.assertIsNotNone(r)
        assert r is not None
        self.assertAlmostEqual(r, 1.0, places=6)

    def test_whole_word_and_single_char(self) -> None:
        self.assertTrue(ana.is_whole_word_token(["▁hello"], "hello"))
        self.assertFalse(ana.is_whole_word_token(["▁he", "llo"], "hello"))
        self.assertTrue(ana.is_single_char_frag("▁a"))
        self.assertFalse(ana.is_single_char_frag("▁ab"))

    def test_tag_candidate_disagreement(self) -> None:
        tags = ana.tag_candidate(
            "ndimakukonda",
            train_freq=10,
            seen=True,
            bpe=["▁ndi", "maku", "konda"],
            uni=["▁ndimakukonda"],
        )
        self.assertIn("bpe_unigram_disagree", tags)
        self.assertIn("orthographic_surface_form", tags)

    def test_evidence_taxonomy_keys_in_summary_schema(self) -> None:
        # structural expectation for report JSON
        required = {
            "token_count_per_word",
            "characters_per_token",
            "whole_word_token_rate",
            "single_character_fragment_rate",
            "segmentation_disagreement_rate",
            "validation_unseen_form_fragmentation",
            "recurring_initial_string_consistency",
            "recurring_final_string_consistency",
            "automatic_word_family_consistency",
            "vocabulary_utilization_proxy",
            "frequency_sensitivity",
            "source_sensitivity",
            "correlation_log_frequency_vs_fertility",
            "correlation_word_length_vs_fertility",
        }
        # if summary exists, check
        p = REPO / "data/reports/tokenizer_morphology_failure_summary_v0_1.json"
        if not p.is_file():
            self.skipTest("summary not generated yet")
        s = json.loads(p.read_text(encoding="utf-8"))
        self.assertFalse(s.get("test_split_accessed"))
        self.assertTrue(required.issubset(s["diagnostics"].keys()))
        self.assertIn("orthographic", s["evidence_taxonomy"])
        self.assertIn("statistical", s["evidence_taxonomy"])
        self.assertIn(
            "linguistic_interpretation_requires_human_review", s["evidence_taxonomy"]
        )


class TestDryRun(unittest.TestCase):
    def test_dry_run(self) -> None:
        cfg = REPO / "configs/tokenizers/baselines_v0_1.json"
        if not (REPO / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/bpe/vocab_8000/model.model").is_file():
            self.skipTest("tokenizers missing")
        rc = ana.main(["--repo-root", str(REPO), "--config", str(cfg), "--dry-run"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
