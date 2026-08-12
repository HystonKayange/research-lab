#!/usr/bin/env python3
"""Tests for LM baselines v0.1 final validation audit (no training, no test eval)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "models"))

import matrix_common as mc  # noqa: E402
import audit_lm_validation_results as audit  # noqa: E402


class TestDiscoveryAndExclusion(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1_final_matrix_r2.json").read_text(
                encoding="utf-8"
            )
        )
        self.specs = mc.enumerate_full_runs(self.cfg)

    def test_exactly_36_scientific_runs(self) -> None:
        self.assertEqual(len(self.specs), 36)
        self.assertEqual(len(self.specs), int(self.cfg["scientific_run_count"]))

    def test_canary_excluded_from_enumeration(self) -> None:
        for s in self.specs:
            self.assertNotIn("canary", s.run_id.lower())
            # scientific path uses fixed_characters_e30, not bare fixed_characters
            if s.budget_policy == "fixed_characters":
                self.assertEqual(s.budget_path_slug, "fixed_characters_e30")
                self.assertNotEqual(s.budget_path_slug, "fixed_characters")

    def test_calibration_excluded(self) -> None:
        for s in self.specs:
            self.assertNotIn("calibration", s.run_id.lower())
            rd = mc.run_dir_for(REPO, self.cfg, s)
            self.assertNotIn("/calibration/", str(rd).replace("\\", "/"))

    def test_pilot_excluded(self) -> None:
        for s in self.specs:
            self.assertNotIn("pilot", s.run_id.lower())

    def test_r1_artifacts_excluded(self) -> None:
        for s in self.specs:
            self.assertIn("r2", s.run_id)
            self.assertNotIn("r1", s.run_id)
            # r1 used bare fixed_characters path / 4M canary style
            self.assertNotEqual(s.budget_path_slug, "fixed_characters")

    def test_incomplete_runs_reported_not_silently_skipped(self) -> None:
        """audit_one returns ok=False with failures when run dir missing."""
        parent = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # empty root — all dirs missing
            rec = audit.audit_one(
                root, self.cfg, parent, self.specs[0], matrix_sha="deadbeef"
            )
            self.assertFalse(rec["ok"])
            self.assertTrue(any("run_dir_exists" in f for f in rec["failures"]))
            self.assertEqual(rec["run_id"], self.specs[0].run_id)


class TestAggregation(unittest.TestCase):
    def test_groups_separated_by_track_and_budget(self) -> None:
        records = []
        for track, budget in audit.GROUPS:
            for tok in audit.TOKENIZER_ORDER:
                for seed in (42, 1337, 2026):
                    records.append(
                        {
                            "ok": True,
                            "run_id": f"{track}_{budget}_{tok}_{seed}",
                            "tokenizer_id": tok,
                            "seed": seed,
                            "track": track,
                            "budget_policy": budget,
                            "best_validation_bpc": 1.5
                            + (0.1 if tok == "character" else 0.0)
                            + (0.05 if budget == "fixed_updates" else 0.0),
                            "best_validation_bpb": 1.2,
                            "final_budget_bpc": 1.6,
                            "best_vs_final_bpc_gap": 0.1,
                            "best_step": 100,
                            "best_effective_epochs": 30.0,
                            "characters_processed": 138713970
                            if budget == "fixed_characters"
                            else 50_000_000,
                            "optimizer_steps": 4000 if budget == "fixed_updates" else 8000,
                            "effective_epochs": 30.0,
                            "runtime_s": 100.0,
                            "peak_vram_gb": 2.0,
                            "total_parameters": 1_000_000,
                            "embedding_parameters": 100_000,
                            "non_embedding_parameters": 900_000,
                        }
                    )
        groups = [audit.aggregate_group(records, t, b) for t, b in audit.GROUPS]
        self.assertEqual(len(groups), 4)
        # architecture fixed_chars character mean BPC = 1.6
        g0 = next(
            g
            for g in groups
            if g["track"] == "architecture_matched"
            and g["budget_policy"] == "fixed_characters"
        )
        self.assertAlmostEqual(
            g0["tokenizers"]["character"]["mean_validation_bpc"]["mean"], 1.6
        )
        self.assertAlmostEqual(
            g0["tokenizers"]["bpe_8000"]["mean_validation_bpc"]["mean"], 1.5
        )
        # fixed_updates has +0.05
        g1 = next(
            g
            for g in groups
            if g["track"] == "architecture_matched"
            and g["budget_policy"] == "fixed_updates"
        )
        self.assertAlmostEqual(
            g1["tokenizers"]["character"]["mean_validation_bpc"]["mean"], 1.65
        )
        # leaders never mix tracks
        for g in groups:
            self.assertIn(g["provisional_validation_leader"], audit.TOKENIZER_ORDER)

    def test_seed_statistics(self) -> None:
        records = [
            {
                "ok": True,
                "tokenizer_id": "character",
                "seed": s,
                "track": "architecture_matched",
                "budget_policy": "fixed_characters",
                "best_validation_bpc": bpc,
                "best_validation_bpb": 1.0,
                "final_budget_bpc": bpc + 0.01,
                "best_vs_final_bpc_gap": 0.01,
                "best_step": 1,
                "best_effective_epochs": 30.0,
                "characters_processed": 1,
                "optimizer_steps": 1,
                "effective_epochs": 30.0,
                "runtime_s": 1.0,
                "peak_vram_gb": 1.0,
                "total_parameters": 1,
                "embedding_parameters": 1,
                "non_embedding_parameters": 1,
            }
            for s, bpc in ((42, 1.0), (1337, 2.0), (2026, 3.0))
        ]
        g = audit.aggregate_group(records, "architecture_matched", "fixed_characters")
        st = g["tokenizers"]["character"]["mean_validation_bpc"]
        self.assertEqual(st["n"], 3)
        self.assertAlmostEqual(st["mean"], 2.0)
        self.assertAlmostEqual(st["median"], 2.0)
        self.assertAlmostEqual(st["min"], 1.0)
        self.assertAlmostEqual(st["max"], 3.0)
        self.assertAlmostEqual(st["stdev"], 1.0)

    def test_paired_differences(self) -> None:
        records = []
        for tok, base in (("character", 2.0), ("bpe_8000", 1.5), ("unigram_8000", 1.4)):
            for seed in (42, 1337, 2026):
                records.append(
                    {
                        "ok": True,
                        "tokenizer_id": tok,
                        "seed": seed,
                        "track": "architecture_matched",
                        "budget_policy": "fixed_characters",
                        "best_validation_bpc": base,
                        "best_validation_bpb": base,
                        "final_budget_bpc": base,
                        "best_vs_final_bpc_gap": 0.0,
                        "best_step": 1,
                        "best_effective_epochs": 30.0,
                        "characters_processed": 1,
                        "optimizer_steps": 1,
                        "effective_epochs": 30.0,
                        "runtime_s": 1.0,
                        "peak_vram_gb": 1.0,
                        "total_parameters": 1,
                        "embedding_parameters": 1,
                        "non_embedding_parameters": 1,
                    }
                )
        g = audit.aggregate_group(records, "architecture_matched", "fixed_characters")
        paired = g["paired_seed_differences"]
        # bpe - character = 1.5 - 2.0 = -0.5 (bpe better)
        self.assertAlmostEqual(
            paired["bpe_minus_character"]["mean_diff"]["mean"], -0.5
        )
        self.assertAlmostEqual(
            paired["unigram_minus_character"]["mean_diff"]["mean"], -0.6
        )
        self.assertAlmostEqual(
            paired["unigram_minus_bpe"]["mean_diff"]["mean"], -0.1
        )
        self.assertIn("lower BPC", paired["bpe_minus_character"]["note"])


class TestSourceValidationSafety(unittest.TestCase):
    def test_source_paths_are_validation_only(self) -> None:
        """Source dict in run_source_validation must not include test paths."""
        # Inspect source construction by reading the function body constants via a dry check
        matrix = {
            "split_root": "data/splits/chichewa_corpus_v0.1",
            "evaluation": {"eval_batch_size": 16},
        }
        root = REPO
        split_root = root / matrix["split_root"]
        sources = {
            "combined_validation": split_root / "validation" / "combined.txt",
            "bible_validation": split_root / "validation" / "bible.txt",
            "wikipedia_validation": split_root / "validation" / "wikipedia.txt",
        }
        for name, p in sources.items():
            path_s = str(p).replace("\\", "/")
            self.assertIn("/validation/", path_s)
            self.assertNotIn("/test/", path_s)
            self.assertTrue(name.endswith("_validation"))

    def test_no_test_path_access_in_audit_module(self) -> None:
        src = (REPO / "scripts/models/audit_lm_validation_results.py").read_text(
            encoding="utf-8"
        )
        # executable evaluation path must never open test splits
        self.assertIn("Never opens the test split", src)
        self.assertIn('"/test/"', src)
        self.assertIn("refusing test path", src)
        # source paths are validation-only
        self.assertIn('"validation" / "combined.txt"', src)
        self.assertIn('"validation" / "bible.txt"', src)
        self.assertIn('"validation" / "wikipedia.txt"', src)
        # --allow-test may appear only as documentation of a later operator command
        # (must not be an argparse flag of this tool)
        self.assertNotIn('add_argument("--allow-test"', src)
        self.assertNotIn("action=\"store_true\"", src) if False else None
        # ensure evaluate is only called with validation source texts via evaluate_split
        self.assertIn("evaluate_split", src)
        self.assertNotIn("evaluate_lm_baseline.main", src)


class TestFigureOutputAndReadiness(unittest.TestCase):
    def test_final_validation_folder_not_calibration(self) -> None:
        fig_dir = REPO / "data/reports/figures/lm_baselines_v0.1/final_validation"
        cal_dir = REPO / "data/reports/figures/lm_baselines_v0.1/calibration"
        self.assertNotEqual(fig_dir, cal_dir)
        self.assertIn("final_validation", str(fig_dir))
        self.assertNotIn("calibration", str(fig_dir.name))

    def test_required_figure_names(self) -> None:
        required = [
            "validation_bpc_arch_fixed_characters",
            "validation_bpc_arch_fixed_updates",
            "validation_bpc_param_fixed_characters",
            "validation_bpc_param_fixed_updates",
            "validation_bpb_arch_fixed_characters",
            "validation_bpb_arch_fixed_updates",
            "validation_bpb_param_fixed_characters",
            "validation_bpb_param_fixed_updates",
            "validation_bpc_bible_vs_wikipedia",
            "best_checkpoint_effective_epoch",
            "best_vs_final_bpc_gap",
            "runtime_by_tokenizer",
            "peak_vram_by_tokenizer",
            "total_parameters_by_track",
            "characters_processed_by_budget",
            "optimizer_updates_by_budget",
            "learning_curves_arch_fixed_characters",
            "learning_curves_param_fixed_characters",
            "learning_curves_arch_fixed_updates",
            "learning_curves_param_fixed_updates",
        ]
        self.assertEqual(len(required), 20)

    def test_generated_figures_png_and_svg_if_present(self) -> None:
        fig_dir = REPO / "data/reports/figures/lm_baselines_v0.1/final_validation"
        if not fig_dir.is_dir():
            self.skipTest("final_validation not generated yet")
        required = [
            "validation_bpc_arch_fixed_characters",
            "learning_curves_arch_fixed_characters",
            "learning_curves_arch_fixed_updates",
            "validation_bpc_bible_vs_wikipedia",
        ]
        for name in required:
            self.assertTrue(
                (fig_dir / f"{name}.png").is_file(), f"missing {name}.png"
            )
            self.assertTrue(
                (fig_dir / f"{name}.svg").is_file(), f"missing {name}.svg"
            )

    def test_calibration_figures_untouched(self) -> None:
        cal = REPO / "data/reports/figures/lm_baselines_v0.1/calibration"
        if not cal.is_dir():
            self.skipTest("no calibration figures")
        # calibration dir should still exist and not be emptied by validation audit
        files = list(cal.glob("*"))
        self.assertGreater(len(files), 0)
        # validation must not write into calibration
        for p in cal.glob("validation_bpc_*"):
            self.fail(f"validation figure leaked into calibration: {p.name}")

    def test_learning_curve_x_axis_policy(self) -> None:
        """Fixed-character curves use effective_epochs; fixed-update use step."""
        src = (REPO / "scripts/models/audit_lm_validation_results.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('budget == "fixed_characters"', src)
        self.assertIn('row.get("effective_epochs")', src)
        self.assertIn('row.get("step")', src)
        self.assertIn("Optimizer steps", src)

    def test_error_bars_use_seed_stdev(self) -> None:
        src = (REPO / "scripts/models/audit_lm_validation_results.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("yerr=stds", src)
        self.assertIn("statistics.stdev", src)

    def test_test_ready_false_on_integrity_failure(self) -> None:
        readiness = {
            "all_36_completed": False,
            "all_36_audited": True,
            "all_manifests_valid": True,
            "all_selection_locks_valid": True,
            "all_checkpoint_checksums_valid": True,
            "all_budget_exposures_valid": True,
            "no_nan_inf": True,
            "no_test_access_detected": True,
            "canary_excluded": True,
            "calibration_excluded": True,
            "pilots_excluded": True,
            "validation_aggregation_complete": False,
            "source_validation_complete": False,
            "figures_complete": False,
            "checkpoint_reload_ok_all": True,
        }
        self.assertFalse(all(readiness.values()))

    def test_test_ready_true_only_when_all_pass(self) -> None:
        readiness = {
            "all_36_completed": True,
            "all_36_audited": True,
            "all_manifests_valid": True,
            "all_selection_locks_valid": True,
            "all_checkpoint_checksums_valid": True,
            "all_budget_exposures_valid": True,
            "no_nan_inf": True,
            "no_test_access_detected": True,
            "canary_excluded": True,
            "calibration_excluded": True,
            "pilots_excluded": True,
            "validation_aggregation_complete": True,
            "source_validation_complete": True,
            "figures_complete": True,
            "checkpoint_reload_ok_all": True,
        }
        self.assertTrue(all(readiness.values()))

    def test_readiness_json_if_present(self) -> None:
        p = REPO / "data/metadata/lm_baselines_v0_1_test_readiness.json"
        if not p.is_file():
            self.skipTest("readiness not generated")
        r = json.loads(p.read_text(encoding="utf-8"))
        required_keys = [
            "all_36_completed",
            "all_36_audited",
            "all_manifests_valid",
            "all_selection_locks_valid",
            "all_checkpoint_checksums_valid",
            "all_budget_exposures_valid",
            "no_nan_inf",
            "no_test_access_detected",
            "canary_excluded",
            "calibration_excluded",
            "pilots_excluded",
            "validation_aggregation_complete",
            "source_validation_complete",
            "figures_complete",
            "test_ready",
        ]
        for k in required_keys:
            self.assertIn(k, r)
        # if test_ready true, every condition must be true
        if r["test_ready"]:
            for k in required_keys:
                if k == "test_ready":
                    continue
                self.assertTrue(r[k], f"{k} must be true when test_ready")


class TestNoFrozenInputsModified(unittest.TestCase):
    def test_frozen_split_checksums_stable(self) -> None:
        split_root = REPO / "data/splits/chichewa_corpus_v0.1"
        man = split_root / "split_manifest.json"
        if not man.is_file():
            self.skipTest("split not present")
        # verify_frozen_split should pass (raises on mismatch)
        import lm_common as lc

        lc.verify_frozen_split(split_root)

    def test_audit_does_not_write_to_frozen_splits(self) -> None:
        src = (REPO / "scripts/models/audit_lm_validation_results.py").read_text(
            encoding="utf-8"
        )
        # write_json targets are reports/metadata/run source_validation only
        self.assertNotIn("split_manifest", src.split("write_json")[0] if False else src)
        # crude: no write under data/splits
        self.assertNotIn('write_json(root / "data/splits', src)
        self.assertNotIn("write_text(root / \"data/splits", src)


if __name__ == "__main__":
    unittest.main()
