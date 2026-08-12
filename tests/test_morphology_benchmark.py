#!/usr/bin/env python3
"""Tests for morphology benchmark scaffolding and holdout lock."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import build_morphology_benchmark as build  # noqa: E402
import release_morphology_holdout as rel  # noqa: E402
import evaluate_morphology_boundaries as ev  # noqa: E402


class TestStrataAndSchema(unittest.TestCase):
    def test_assign_strata_multi_label(self) -> None:
        tags = build.assign_strata(
            "sindimakukonda",
            train_freq=5,
            seen_train=True,
            bpe=["▁si", "ndi", "maku", "konda"],
            uni=["▁sindimakukonda"],
        )
        self.assertIn("apparent_negation", tags)
        self.assertIn("bpe_unigram_disagreement", tags)
        self.assertIn("apparent_whole_word_memorization", tags)

    def test_dev_record_schema(self) -> None:
        item = {
            "surface_form": "mufuna",
            "context": "…",
            "source": "bible",
            "split": "train",
            "frequency_train": 10,
            "bpe_tokens": ["▁mu", "funa"],
            "unigram_tokens": ["▁mufuna"],
            "automatic_tags": ["x"],
            "candidate_strata": ["frequent_word_family"],
            "line_ref": {"split": "train", "source": "bible", "line_index": 0, "word_index": 0},
        }
        rec = build.make_dev_record(item, 1)
        self.assertEqual(rec["item_id"], "morph_dev_0001")
        self.assertIsNone(rec["human_segments"])
        self.assertIsNone(rec["human_phenomenon_tags"])
        self.assertEqual(rec["adjudication_status"], "unreviewed")
        self.assertIn("alternative_analysis", rec)

    def test_seal_roundtrip_checksum(self) -> None:
        items = [{"item_id": "morph_hold_0001", "surface_form": "abc", "context": "c"}]
        sealed = build.seal_payload(items)
        self.assertEqual(sealed["n_items"], 1)
        self.assertEqual(sealed["access"], "blocked_until_method_freeze")
        # release loader checks checksum
        import base64
        from common import sha256_text

        raw = base64.b64decode(sealed["payload_b64"]).decode("utf-8")
        self.assertEqual(sha256_text(raw), sealed["sha256"])


class TestHoldoutLock(unittest.TestCase):
    def test_release_refused_without_flags(self) -> None:
        rc = rel.main(["--repo-root", str(REPO), "--status-only"])
        # status-only ok even if missing
        self.assertIn(rc, (0, 1))
        rc2 = rel.main(["--repo-root", str(REPO)])
        self.assertEqual(rc2, 2)

    def test_locked_manifest_hides_surfaces_if_present(self) -> None:
        man = REPO / "data/research/morphology_benchmark_v0.1/locked/holdout_manifest.json"
        if not man.is_file():
            self.skipTest("benchmark not built")
        m = json.loads(man.read_text(encoding="utf-8"))
        self.assertTrue(m.get("release_blocked"))
        self.assertIn("n_items", m)
        self.assertIn("category_distribution_candidate_strata", m)
        # no surface_form list
        self.assertNotIn("surface_forms", m)
        for ref in m.get("line_refs_only") or []:
            self.assertIn("surface_sha256", ref)
            self.assertNotIn("surface_form", ref)

    def test_dev_size_and_null_gold_if_present(self) -> None:
        path = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/annotation_candidates.jsonl"
        )
        if not path.is_file():
            self.skipTest("dev set not built")
        rows = [
            json.loads(l)
            for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        self.assertGreaterEqual(len(rows), 160)
        self.assertLessEqual(len(rows), 240)
        for r in rows[:20]:
            self.assertIsNone(r.get("human_segments"))
            self.assertNotEqual(r.get("split"), "test")
            self.assertTrue(str(r["item_id"]).startswith("morph_dev_"))

    def test_release_blocked_file(self) -> None:
        p = REPO / "data/research/morphology_benchmark_v0.1/locked/RELEASE_BLOCKED"
        if not p.is_file():
            self.skipTest("not built")
        text = p.read_text(encoding="utf-8")
        self.assertIn("LOCKED", text.upper())


class TestBoundaryEval(unittest.TestCase):
    def test_boundary_scores_exact(self) -> None:
        sc = ev.boundary_scores(["ndi", "ma", "konda"], ["ndi", "ma", "konda"])
        self.assertTrue(sc["exact_segmentation"])
        self.assertEqual(sc["boundary_f1"], 1.0)

    def test_boundary_over_under(self) -> None:
        over = ev.boundary_scores(["ab", "cd"], ["a", "b", "cd"])
        self.assertTrue(over["over_segmentation"])
        under = ev.boundary_scores(["a", "b", "cd"], ["ab", "cd"])
        self.assertTrue(under["under_segmentation"])

    def test_refuse_locked_path(self) -> None:
        rc = ev.main(
            [
                "--repo-root",
                str(REPO),
                "--annotations",
                "data/research/morphology_benchmark_v0.1/locked/holdout_payload.sealed.json",
            ]
        )
        # sealed is not jsonl — may return 1 or 2; locked path should refuse if jsonl under locked without released
        rc2 = ev.main(
            [
                "--repo-root",
                str(REPO),
                "--annotations",
                "data/research/morphology_benchmark_v0.1/locked/foo.jsonl",
            ]
        )
        self.assertEqual(rc2, 2)

    def test_no_fake_gold_in_evaluate_doc(self) -> None:
        src = (REPO / "scripts/tokenizers/evaluate_morphology_boundaries.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Does not invent gold labels", src)


class TestDocsAndConfig(unittest.TestCase):
    def test_research_files_exist(self) -> None:
        for rel in (
            "docs/research/MTHANDIZI_TOKENIZER_RESEARCH_BLUEPRINT_v0_1.md",
            "docs/research/MTHANDIZI_TOKENIZER_DECISION_LOG.md",
            "docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_PLAN.md",
            "configs/research/mthandizi_tokenizer_research_v0_1.json",
        ):
            self.assertTrue((REPO / rel).is_file(), rel)

    def test_config_safety_flags(self) -> None:
        cfg = json.loads(
            (REPO / "configs/research/mthandizi_tokenizer_research_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(cfg["implementation_executed"])
        self.assertFalse(cfg["safety"]["lm_test_evaluations_allowed"])
        self.assertFalse(cfg["safety"]["morphology_holdout_release_allowed"])
        self.assertEqual(cfg["success_criteria_status"], "proposed_pending_human_approval")

    def test_prior_art_table_empty_not_fabricated(self) -> None:
        text = (
            REPO / "docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_PLAN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Do **not** fabricate", text)
        self.assertIn("empty until filled", text.lower())

    def test_blueprint_design_families(self) -> None:
        text = (
            REPO / "docs/research/MTHANDIZI_TOKENIZER_RESEARCH_BLUEPRINT_v0_1.md"
        ).read_text(encoding="utf-8")
        for name in (
            "Morphology-aware pre-segmentation",
            "Boundary-biased Unigram",
            "Morphology-constrained BPE",
            "Hybrid affix/stem vocabulary",
            "Statistical affix discovery",
            "Vocabulary regularization",
            "Word-family-consistency",
            "Stochastic segmentation",
            "Character or byte fallback",
        ):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
