#!/usr/bin/env python3
"""Tests for Phase A tokenizer failure audit (no training, no test split)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import audit_tokenizer_failures as audit  # noqa: E402


class TestSafety(unittest.TestCase):
    def test_refuse_test_path(self) -> None:
        with self.assertRaises(RuntimeError):
            audit.refuse_test_path(REPO / "data/splits/chichewa_corpus_v0.1/test/combined.txt")
        with self.assertRaises(RuntimeError):
            audit.refuse_test_path("data/splits/chichewa_corpus_v0.1/test/")
        # train/validation ok
        audit.refuse_test_path(REPO / "data/splits/chichewa_corpus_v0.1/train/combined.txt")
        audit.refuse_test_path(REPO / "data/splits/chichewa_corpus_v0.1/validation/bible.txt")

    def test_load_split_inventory_rejects_test(self) -> None:
        with self.assertRaises(ValueError):
            audit.load_split_inventory(REPO / "data/splits/chichewa_corpus_v0.1", "test")

    def test_script_never_implements_hybrid(self) -> None:
        src = (REPO / "scripts/tokenizers/audit_tokenizer_failures.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Does not implement a hybrid tokenizer", src)
        self.assertIn("Does not open the LM test split", src)
        self.assertNotIn("class Mthandizi", src)

    def test_blueprint_exists_and_is_cautious(self) -> None:
        p = REPO / "docs/tokenizers/MTHANDIZI_RESEARCH_BLUEPRINT.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("no assumed advantage", text.lower() or "no assumed" in text)
        self.assertIn("Do not", text)
        self.assertIn("test", text.lower())
        # banned hype without evidence framing
        self.assertIn("Avoid:", text)
        self.assertIn("state of the art", text)


class TestDiagnostics(unittest.TestCase):
    def test_bpe_unigram_disagree_tag(self) -> None:
        tags = audit.automatic_tags(
            word="ndimakukonda",
            split="train",
            source="bible",
            freq_train=10,
            seen_in_train=True,
            bpe8=["▁ndi", "maku", "konda"],
            uni8=["▁ndimakukonda"],
            all_enc={
                "bpe_1000": ["a"],
                "bpe_8000": ["▁ndi", "maku", "konda"],
                "unigram_1000": ["b"],
                "unigram_8000": ["▁ndimakukonda"],
            },
            stem="konda",
            family_inconsistent=True,
        )
        self.assertIn("bpe_unigram_disagree", tags)
        self.assertIn("family_stem_hit", tags)
        self.assertIn("family_segmentation_inconsistent", tags)
        self.assertIn("whole_word_single_token", tags)

    def test_unseen_validation_tag(self) -> None:
        tags = audit.automatic_tags(
            word="xyzzyform",
            split="validation",
            source="wikipedia",
            freq_train=0,
            seen_in_train=False,
            bpe8=["▁x", "y", "z"],
            uni8=["▁x", "y", "z"],
            all_enc={"bpe_8000": ["▁x", "y", "z"], "unigram_8000": ["▁x", "y", "z"]},
            stem=None,
            family_inconsistent=False,
        )
        self.assertIn("unseen_in_train", tags)
        self.assertNotIn("bpe_unigram_disagree", tags)

    def test_contains_w_hat(self) -> None:
        tags = audit.automatic_tags(
            word="Malaŵi",
            split="train",
            source="wikipedia",
            freq_train=100,
            seen_in_train=True,
            bpe8=["▁Malaŵi"],
            uni8=["▁Malaŵi"],
            all_enc={},
            stem=None,
            family_inconsistent=False,
        )
        self.assertIn("contains_w_hat", tags)
        self.assertIn("frequent_train", tags)

    def test_paired_priority_prefers_disagreement(self) -> None:
        high = audit.candidate_priority(
            ["bpe_unigram_disagree", "family_segmentation_inconsistent"],
            20,
            5,
            2,
        )
        low = audit.candidate_priority(["frequent_train"], 100, 1, 1)
        self.assertGreater(high, low)

    def test_candidate_schema_keys(self) -> None:
        required = {
            "candidate_id",
            "surface_form",
            "context",
            "source",
            "split",
            "frequency_train",
            "seen_in_train",
            "bpe_tokens",
            "unigram_tokens",
            "bpe_fertility",
            "unigram_fertility",
            "automatic_diagnostic_tags",
            "human_phenomenon_tags",
            "human_segments",
            "human_notes",
            "uncertain",
        }
        # synthetic record matching schema
        rec = {
            "candidate_id": "failure_000001",
            "surface_form": "testword",
            "context": "…",
            "source": "bible",
            "split": "train",
            "frequency_train": 0,
            "seen_in_train": True,
            "bpe_tokens": [],
            "unigram_tokens": [],
            "bpe_fertility": 0,
            "unigram_fertility": 0,
            "automatic_diagnostic_tags": [],
            "human_phenomenon_tags": None,
            "human_segments": None,
            "human_notes": None,
            "uncertain": None,
        }
        self.assertTrue(required.issubset(rec.keys()))
        self.assertIsNone(rec["human_segments"])


class TestMechanismMap(unittest.TestCase):
    def test_mechanism_map_covers_core_classes(self) -> None:
        stats = {
            "tag_counts": {
                "bpe_unigram_disagree": 10,
                "high_fragmentation": 5,
                "family_segmentation_inconsistent": 3,
            }
        }
        m = audit.mechanism_map_from_stats(stats)
        classes = {row["failure_class"] for row in m}
        self.assertIn("bpe_unigram_disagree", classes)
        self.assertIn("family_segmentation_inconsistent", classes)
        self.assertIn("high_fragmentation", classes)


class TestOutputsIfPresent(unittest.TestCase):
    def test_outputs_exclude_test_and_null_human(self) -> None:
        out = REPO / "data/reports/tokenizer_failure_audit_v0_1/failure_candidates.jsonl"
        if not out.is_file():
            self.skipTest("audit not run yet")
        n = 0
        for line in out.read_text(encoding="utf-8").splitlines()[:50]:
            c = json.loads(line)
            n += 1
            self.assertNotEqual(c.get("split"), "test")
            self.assertIsNone(c.get("human_segments"))
            self.assertIsNone(c.get("human_phenomenon_tags"))
            self.assertIn(c.get("source"), ("bible", "wikipedia"))
            self.assertTrue(str(c["candidate_id"]).startswith("failure_"))
        self.assertGreater(n, 0)

    def test_manifest_test_not_accessed(self) -> None:
        man = REPO / "data/reports/tokenizer_failure_audit_v0_1/audit_manifest.json"
        if not man.is_file():
            self.skipTest("audit not run yet")
        m = json.loads(man.read_text(encoding="utf-8"))
        self.assertFalse(m.get("test_split_accessed"))
        self.assertFalse(m.get("hybrid_tokenizer_implemented"))
        self.assertIn("bpe_8000", m.get("models_loaded") or [])
        self.assertIn("unigram_8000", m.get("models_loaded") or [])


class TestDryRun(unittest.TestCase):
    def test_dry_run_exits_zero(self) -> None:
        cfg = REPO / "configs/tokenizers/baselines_v0_1.json"
        if not cfg.is_file():
            self.skipTest("config missing")
        exp = REPO / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1"
        if not (exp / "bpe" / "vocab_8000" / "model.model").is_file():
            self.skipTest("tokenizers missing")
        rc = audit.main(
            [
                "--config",
                str(cfg),
                "--repo-root",
                str(REPO),
                "--dry-run",
            ]
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
