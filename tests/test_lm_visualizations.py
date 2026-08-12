#!/usr/bin/env python3
"""Tests for epoch accounting, calibration config, and plotting (no GPU training)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "models"))

import lm_common as lc  # noqa: E402
import plot_lm_learning_curves as plc  # noqa: E402
import plot_lm_comparisons as pcmp  # noqa: E402
import train_lm_baseline as train  # noqa: E402


class TestEffectiveEpochs(unittest.TestCase):
    def test_formula(self) -> None:
        # canary-like: 4009607 / 4623799 ≈ 0.867
        e = lc.effective_epochs(4_009_607, 4_623_799)
        self.assertIsNotNone(e)
        assert e is not None
        self.assertAlmostEqual(e, 4_009_607 / 4_623_799, places=6)
        self.assertLess(e, 1.0)
        self.assertGreater(e, 0.8)

    def test_frozen_char_count_matches_line_sum(self) -> None:
        text = "abc\ndefg\n"
        # lines "abc", "defg" → 3+4=7
        self.assertEqual(lc.frozen_train_character_count(text), 7)
        # real split if present
        p = REPO / "data/splits/chichewa_corpus_v0.1/train/combined.txt"
        if p.is_file():
            t = p.read_text(encoding="utf-8")
            self.assertEqual(lc.frozen_train_character_count(t), 4_623_799)


class TestCalibrationConfig(unittest.TestCase):
    def test_config_checkpoints_and_early_stop(self) -> None:
        cfg = json.loads(
            (REPO / "configs/models/lm_budget_calibration_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cfg["run"]["tokenizer"], "bpe_8000")
        self.assertEqual(cfg["run"]["seed"], 42)
        self.assertEqual(cfg["budget"]["train_characters_max"], 185_000_000)
        epochs = cfg["budget"]["validation_effective_epoch_checkpoints"]
        self.assertEqual(epochs, [1, 2, 5, 10, 15, 20, 30, 40])
        es = cfg["early_stopping"]
        self.assertTrue(es["enabled"])
        self.assertEqual(es["primary_metric"], "validation_bpc")
        self.assertGreaterEqual(es["patience_evaluations"], 3)
        self.assertTrue(es["restore_best_checkpoint"])
        self.assertFalse(cfg["evaluation"]["test_access"])
        self.assertTrue(cfg["safety"]["do_not_auto_run_calibration"])

    def test_resolve_budget_derives_character_checkpoints(self) -> None:
        calib = json.loads(
            (REPO / "configs/models/lm_budget_calibration_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        parent = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1.json").read_text(encoding="utf-8")
        )
        b = train.resolve_budget(
            parent,
            "calibration",
            "fixed_characters",
            None,
            calib,
            frozen_chars=4_623_799,
        )
        self.assertEqual(b["policy"], "fixed_characters")
        self.assertEqual(b["train_characters"], 185_000_000)
        # 1 epoch → 4623799 chars
        self.assertEqual(b["validation_character_checkpoints"][0], 4_623_799)
        self.assertEqual(b["validation_character_checkpoints"][-1], 40 * 4_623_799)
        self.assertTrue(b["early_stopping"]["enabled"])


class TestPlotLearningCurves(unittest.TestCase):
    def test_generate_plots_from_synthetic_logs(self) -> None:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / "run"
            rd.mkdir()
            # synthetic curve
            rows = []
            for i, ep in enumerate([1, 2, 5, 10]):
                rows.append(
                    {
                        "step": (i + 1) * 100,
                        "characters_processed": ep * 4_623_799,
                        "effective_epochs": ep,
                        "bits_per_character": 3.0 - 0.1 * i,
                        "bits_per_byte": 2.9 - 0.1 * i,
                        "tokens_processed": (i + 1) * 10000,
                        "characters_per_second": 1e5,
                        "tokens_per_second": 5e4,
                        "learning_rate": 3e-4,
                    }
                )
            (rd / "learning_curve.jsonl").write_text(
                "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
            )
            logs = [
                {"step": s, "train_loss": 2.0 - 0.01 * s, "lr": 3e-4, "grad_norm": 1.0}
                for s in range(1, 21)
            ]
            (rd / "train_log.jsonl").write_text(
                "\n".join(json.dumps(r) for r in logs) + "\n", encoding="utf-8"
            )
            (rd / "manifest.json").write_text(
                json.dumps(
                    {
                        "tokenizer_id": "bpe_8000",
                        "seed": 42,
                        "exposure": {
                            "frozen_training_corpus_character_count": 4_623_799
                        },
                    }
                ),
                encoding="utf-8",
            )
            out = Path(td) / "figs"
            paths = plc.generate_plots(rd, out, frozen_chars=4_623_799)
            self.assertGreater(len(paths), 0)
            # expected pair of png+svg for multiple plots
            pngs = list(out.glob("*.png"))
            svgs = list(out.glob("*.svg"))
            self.assertGreaterEqual(len(pngs), 5)
            self.assertEqual(len(pngs), len(svgs))
            self.assertTrue((out / "plot_manifest.json").is_file())


class TestPlotComparisons(unittest.TestCase):
    def test_comparison_without_fabricating_seeds(self) -> None:
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib not installed")
        with tempfile.TemporaryDirectory() as td:
            runs = []
            for tok, bpc in [("bpe_8000", 2.5), ("character", 3.1)]:
                rd = Path(td) / tok
                rd.mkdir()
                (rd / "manifest.json").write_text(
                    json.dumps(
                        {
                            "tokenizer_id": tok,
                            "seed": 42,
                            "track": "architecture_matched",
                            "budget_policy": "fixed_characters",
                            "phase": "final",
                            "pilot_label": False,
                            "best_checkpoint": {"validation_bpc": bpc},
                            "parameter_counts": {"total": 1_000_000},
                            "runtime": {"wall_clock_s": 10.0, "peak_gpu_memory_gb": 1.0},
                        }
                    ),
                    encoding="utf-8",
                )
                runs.append(pcmp.load_run(rd))
            out = Path(td) / "cmp"
            summary = pcmp.generate_comparisons(
                [r for r in runs if r], out, exclude_pilot=True
            )
            self.assertEqual(summary["n_runs_loaded"], 2)
            self.assertTrue((out / "comparison_summary.json").is_file())


class TestCalibrationDryPlan(unittest.TestCase):
    def test_calibration_dry_run_plan(self) -> None:
        rc = train.main(
            [
                "--config",
                str(REPO / "configs/models/lm_baselines_v0_1.json"),
                "--calibration-config",
                str(REPO / "configs/models/lm_budget_calibration_v0_1.json"),
                "--dry-run-plan",
                "--repo-root",
                str(REPO),
            ]
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
