#!/usr/bin/env python3
"""Tests for morphology annotation pilot, IAA, adjudication, UI safety."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tokenizers"))

import prepare_morphology_annotation_pilot as pilot  # noqa: E402
import measure_morphology_annotation_agreement as iaa  # noqa: E402
import adjudicate_morphology_annotations as adj  # noqa: E402
import morphology_annotation_ui as ui  # noqa: E402


class TestPilot(unittest.TestCase):
    def test_pick_stratified_size_and_buckets(self) -> None:
        rows = []
        for i in range(80):
            rows.append(
                {
                    "item_id": f"morph_dev_{i+1:04d}",
                    "surface_form": f"word{i}ŵ" if i % 11 == 0 else f"ndimakonda{i}",
                    "frequency_train": 1 if i % 2 == 0 else 10,
                    "candidate_strata": [
                        "bpe_unigram_disagreement" if i % 3 == 0 else "rare_word",
                        "long_agglutinative_looking" if i % 5 == 0 else "rare_word",
                        "apparent_subject_or_agreement_prefix",
                        "apparent_derivational_suffix" if i % 4 == 0 else "rare_word",
                        "mixed_language_form" if i % 7 == 0 else "rare_word",
                    ],
                    "automatic_tags": [],
                    "bpe_tokens": ["a", "b"],
                    "unigram_tokens": ["ab"] if i % 3 == 0 else ["a", "b"],
                }
            )
        picked = pilot.pick_stratified(rows, n=40)
        self.assertEqual(len(picked), 40)
        ids = {r["item_id"] for r in picked}
        self.assertEqual(len(ids), 40)
        # all dev ids
        self.assertTrue(all(i.startswith("morph_dev_") for i in ids))
        buckets = set()
        for r in picked:
            buckets.update(r["pilot_buckets"])
        self.assertIn("bpe_unigram_disagreement", buckets)

    def test_pilot_files_if_present(self) -> None:
        p = REPO / "data/research/morphology_benchmark_v0.1/development/pilot_40.jsonl"
        if not p.is_file():
            self.skipTest("pilot not built")
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(rows), 40)
        for r in rows:
            self.assertTrue(r["item_id"].startswith("morph_dev_"))
            self.assertNotIn("morph_hold_", r["item_id"])
            self.assertIsNone(r.get("human_segments"))
        for name in (
            "pilot_40_annotator_a.csv",
            "pilot_40_annotator_b.csv",
        ):
            cp = p.parent / name
            self.assertTrue(cp.is_file(), name)
            with cp.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertIn("proposed_segmentation", reader.fieldnames or [])
                self.assertIn("annotator_id", reader.fieldnames or [])
                n = sum(1 for _ in reader)
            self.assertEqual(n, 40)


class TestIAA(unittest.TestCase):
    def test_exact_and_boundary_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            a = td_path / "a.jsonl"
            b = td_path / "b.jsonl"
            rows_a = [
                {
                    "item_id": "morph_dev_0001",
                    "proposed_segmentation": "ndi+ma+konda",
                    "phenomenon_tags": "apparent_prefix|apparent_stem_or_root",
                    "uncertain": False,
                    "annotator_id": "a",
                },
                {
                    "item_id": "morph_dev_0002",
                    "proposed_segmentation": "ab+cd",
                    "phenomenon_tags": "other",
                    "uncertain": True,
                    "annotator_id": "a",
                },
            ]
            rows_b = [
                {
                    "item_id": "morph_dev_0001",
                    "proposed_segmentation": "ndi+ma+konda",
                    "phenomenon_tags": "apparent_prefix|apparent_stem_or_root",
                    "uncertain": False,
                    "annotator_id": "b",
                },
                {
                    "item_id": "morph_dev_0002",
                    "proposed_segmentation": "a+b+cd",
                    "phenomenon_tags": "other|uncertain_segmentation",
                    "uncertain": True,
                    "annotator_id": "b",
                },
            ]
            a.write_text("\n".join(json.dumps(r) for r in rows_a) + "\n", encoding="utf-8")
            b.write_text("\n".join(json.dumps(r) for r in rows_b) + "\n", encoding="utf-8")
            result = iaa.measure(a, b)
            self.assertEqual(result["n_common"], 2)
            self.assertEqual(result["exact_segmentation_agreement"]["n_agree"], 1)
            self.assertEqual(result["adjudication"]["n_requiring_adjudication"], 1)
            self.assertFalse(result["cohens_kappa"]["reported"])
            self.assertIn("assumptions", result["cohens_kappa"]["reason"].lower())
            self.assertFalse(result["locked_holdout_used"])

    def test_refuse_locked(self) -> None:
        with self.assertRaises(RuntimeError):
            iaa.refuse_locked(
                REPO / "data/research/morphology_benchmark_v0.1/locked/holdout_manifest.json"
            )


class TestAdjudication(unittest.TestCase):
    def test_auto_merge_and_queue(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            a = td_path / "a.csv"
            b = td_path / "b.csv"
            # write minimal CSVs
            fields = [
                "item_id",
                "surface_form",
                "context",
                "proposed_segmentation",
                "phenomenon_tags",
                "uncertain",
                "annotator_id",
            ]
            with a.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerow(
                    {
                        "item_id": "morph_dev_0001",
                        "surface_form": "ndimakonda",
                        "context": "x",
                        "proposed_segmentation": "ndi+makonda",
                        "phenomenon_tags": "apparent_prefix",
                        "uncertain": "false",
                        "annotator_id": "a",
                    }
                )
                w.writerow(
                    {
                        "item_id": "morph_dev_0002",
                        "surface_form": "foo",
                        "context": "y",
                        "proposed_segmentation": "f+oo",
                        "phenomenon_tags": "other",
                        "uncertain": "true",
                        "annotator_id": "a",
                    }
                )
            with b.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerow(
                    {
                        "item_id": "morph_dev_0001",
                        "surface_form": "ndimakonda",
                        "context": "x",
                        "proposed_segmentation": "ndi+makonda",
                        "phenomenon_tags": "apparent_prefix",
                        "uncertain": "false",
                        "annotator_id": "b",
                    }
                )
                w.writerow(
                    {
                        "item_id": "morph_dev_0002",
                        "surface_form": "foo",
                        "context": "y",
                        "proposed_segmentation": "fo+o",
                        "phenomenon_tags": "other",
                        "uncertain": "false",
                        "annotator_id": "b",
                    }
                )
            out = td_path / "out"
            rc = adj.main(
                [
                    "--annotator-a",
                    str(a),
                    "--annotator-b",
                    str(b),
                    "--repo-root",
                    str(td_path),
                    "--output-dir",
                    str(out),
                ]
            )
            self.assertEqual(rc, 0)
            summary = json.loads((out / "adjudication_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["n_auto_agreed"], 1)
            self.assertEqual(summary["n_queued_for_human_adjudication"], 1)


class TestUISafety(unittest.TestCase):
    def test_refuse_locked_and_hold_ids(self) -> None:
        with self.assertRaises(RuntimeError):
            ui.refuse_locked("data/research/morphology_benchmark_v0.1/locked/x.jsonl")
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            items = td_path / "items.jsonl"
            items.write_text(
                json.dumps({"item_id": "morph_hold_0001", "surface_form": "x"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                ui.main(
                    [
                        "--items",
                        str(items),
                        "--annotator-id",
                        "annotator_a",
                        "--repo-root",
                        str(td_path),
                        "--port",
                        "9",
                    ]
                )


class TestDocsAndCriteria(unittest.TestCase):
    def test_guidelines_sections(self) -> None:
        text = (
            REPO / "docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md"
        ).read_text(encoding="utf-8")
        for s in (
            "## 1. Purpose",
            "## 4. Annotation fields",
            "## 5. Allowed phenomenon tags",
            "## 6. Segmentation conventions",
            "## 8. Independence",
            "## 9. Pilot procedure",
            "## 10. Adjudication",
            "no_meaningful_segmentation",
            "multiple_plausible_analyses",
            "unresolved_analysis",
        ):
            self.assertIn(s, text)

    def test_success_criteria_pending(self) -> None:
        cfg = json.loads(
            (
                REPO / "configs/research/mthandizi_tokenizer_success_criteria_v0_1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["approval_status"], "proposed_pending_human_approval")
        self.assertEqual(
            cfg["comparison_hierarchy"]["primary"]["track"], "parameter_matched"
        )
        self.assertEqual(
            cfg["comparison_hierarchy"]["primary"]["budget_policy"], "fixed_characters"
        )
        self.assertEqual(
            cfg["comparison_hierarchy"]["primary"]["primary_baseline"], "unigram_8000"
        )
        self.assertEqual(cfg["comparison_hierarchy"]["primary"]["seeds"], [42, 1337, 2026])
        for key, block in cfg["criteria"].items():
            self.assertEqual(
                block["status"],
                "proposed_pending_human_approval",
                key,
            )
        self.assertIsNone(cfg["approved_by"])

    def test_prior_art_ingestion_template(self) -> None:
        text = (
            REPO / "docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_PLAN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Verified-reference ingestion", text)
        self.assertIn("doi_or_authoritative_url", text)
        self.assertIn("Do not fabricate", text)
        tpl = REPO / "data/research/prior_art/verified_references_template.csv"
        self.assertTrue(tpl.is_file())


if __name__ == "__main__":
    unittest.main()
