#!/usr/bin/env python3
"""Tests for calibrated final matrix r2 (no training)."""

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
import train_lm_baseline as train  # noqa: E402
import compare_lm_baselines as cmp  # noqa: E402


class TestR2Budget(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1_final_matrix_r2.json").read_text(
                encoding="utf-8"
            )
        )

    def test_fixed_characters_exactly_30_epochs(self) -> None:
        fc = self.cfg["budgets"]["fixed_characters"]
        corpus = self.cfg["corpus"]["frozen_training_corpus_character_count"]
        self.assertEqual(corpus, 4_623_799)
        self.assertEqual(fc["effective_epoch_target"], 30)
        self.assertEqual(fc["train_characters"], 30 * 4_623_799)
        self.assertEqual(fc["train_characters"], 138_713_970)

    def test_validation_checkpoints_exact(self) -> None:
        fc = self.cfg["budgets"]["fixed_characters"]
        epochs = fc["validation_effective_epoch_checkpoints"]
        chars = fc["validation_character_checkpoints"]
        corpus = 4_623_799
        self.assertEqual(epochs, [1, 2, 5, 10, 15, 20, 22, 24, 26, 28, 30])
        self.assertEqual(chars, [e * corpus for e in epochs])
        self.assertEqual(chars[-1], fc["train_characters"])

    def test_early_stop_disabled_for_fixed_characters(self) -> None:
        es = self.cfg["budgets"]["fixed_characters"]["early_stopping"]
        self.assertFalse(es["enabled"])

    def test_exactly_36_scientific_runs(self) -> None:
        runs = mc.enumerate_full_runs(self.cfg)
        self.assertEqual(len(runs), 36)
        self.assertEqual(len(runs), int(self.cfg["scientific_run_count"]))
        ids = [r.run_id for r in runs]
        self.assertEqual(len(ids), len(set(ids)))
        # fresh bpe seed42 arch fixed chars e30 present
        hits = [
            r
            for r in runs
            if r.tokenizer == "bpe_8000"
            and r.seed == 42
            and r.track == "architecture_matched"
            and r.budget_policy == "fixed_characters"
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].budget_path_slug, "fixed_characters_e30")
        self.assertIn("chars_e30", hits[0].run_id)
        self.assertIn("r2", hits[0].run_id)

    def test_canary_not_launchable_in_r2(self) -> None:
        self.assertEqual(int(self.cfg["canary_run_count"]), 0)
        self.assertEqual(mc.enumerate_canary_runs(self.cfg), [])
        self.assertTrue(self.cfg["canary"]["excluded_from_final_statistics"])
        self.assertTrue(self.cfg["calibration"]["excluded_from_final_statistics"])

    def test_resolve_budget_no_patience_early_stop(self) -> None:
        parent = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1.json").read_text(encoding="utf-8")
        )
        b = train.resolve_budget(
            parent,
            "final",
            "fixed_characters",
            self.cfg,
            frozen_chars=4_623_799,
        )
        self.assertEqual(b["train_characters"], 138_713_970)
        self.assertFalse(b["early_stopping"]["enabled"])
        self.assertEqual(
            b["validation_character_checkpoints"],
            [e * 4_623_799 for e in [1, 2, 5, 10, 15, 20, 22, 24, 26, 28, 30]],
        )

    def test_fixed_update_revised_to_4000(self) -> None:
        fu = self.cfg["budgets"]["fixed_updates"]
        self.assertEqual(fu["optimizer_updates"], 4000)
        self.assertEqual(fu["previous_optimizer_updates"], 2000)

    def test_canary_excluded_from_collect_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # fake canary path structure
            canary = (
                root
                / "data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"
                / "architecture_matched/bpe_8000/seed_42/final/fixed_characters"
            )
            canary.mkdir(parents=True)
            (canary / "manifest.json").write_text(
                json.dumps(
                    {
                        "phase": "final",
                        "pilot_label": False,
                        "tokenizer_id": "bpe_8000",
                        "seed": 42,
                        "track": "architecture_matched",
                        "budget_policy": "fixed_characters",
                        "budget": {"train_characters": 4_000_000},
                        "best_checkpoint": {"validation_bpc": 2.9},
                    }
                ),
                encoding="utf-8",
            )
            # fake scientific e30 run
            sci = (
                root
                / "data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"
                / "architecture_matched/bpe_8000/seed_42/final/fixed_characters_e30"
            )
            sci.mkdir(parents=True)
            (sci / "manifest.json").write_text(
                json.dumps(
                    {
                        "phase": "final",
                        "pilot_label": False,
                        "tokenizer_id": "bpe_8000",
                        "seed": 42,
                        "track": "architecture_matched",
                        "budget_policy": "fixed_characters",
                        "budget": {"train_characters": 138_713_970},
                        "best_checkpoint": {"validation_bpc": 1.5},
                    }
                ),
                encoding="utf-8",
            )
            # calibration
            cal = (
                root
                / "data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"
                / "architecture_matched/bpe_8000/seed_42/calibration/fixed_characters"
            )
            cal.mkdir(parents=True)
            (cal / "manifest.json").write_text(
                json.dumps({"phase": "calibration", "best_checkpoint": {"validation_bpc": 1.4}}),
                encoding="utf-8",
            )
            cfg = {
                "output_root": "data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"
            }
            runs = cmp.collect_runs(root, cfg, "architecture_matched", "final")
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["best_checkpoint"]["validation_bpc"], 1.5)

    def test_dry_run_no_train(self) -> None:
        import run_lm_baseline_matrix as launcher

        with mock.patch("subprocess.run") as sp:
            rc = launcher.main(
                [
                    "--config",
                    str(REPO / "configs/models/lm_baselines_v0_1_final_matrix_r2.json"),
                    "--stage",
                    "full",
                    "--dry-run",
                    "--repo-root",
                    str(REPO),
                ]
            )
            self.assertEqual(rc, 0)
            sp.assert_not_called()

    def test_migration_preserves_backup(self) -> None:
        import migrate_matrix_status_r2 as mig

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # minimal parent config files
            (root / "configs/models").mkdir(parents=True)
            shutil_copy = REPO / "configs/models/lm_baselines_v0_1_final_matrix_r2.json"
            import shutil

            shutil.copy(
                shutil_copy,
                root / "configs/models/lm_baselines_v0_1_final_matrix_r2.json",
            )
            (root / "data/metadata").mkdir(parents=True)
            old = {
                "matrix_id": "lm_baselines_v0_1_final_matrix",
                "canary_accepted": True,
                "runs": {
                    "lm_baselines_v0_1_final_matrix__final__arch__bpe_8000__seed42__chars": {
                        "status": "completed"
                    }
                },
                "failure_history": [{"x": 1}],
            }
            old_path = root / "data/metadata/lm_baselines_v0_1_matrix_status.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            # fake canary acceptance
            acc = root / "data/metadata/lm_baselines_v0_1_canary_acceptance.json"
            acc.write_text(json.dumps({"accepted": True}), encoding="utf-8")
            rc = mig.main(
                [
                    "--matrix-config",
                    "configs/models/lm_baselines_v0_1_final_matrix_r2.json",
                    "--repo-root",
                    str(root),
                    "--old-status",
                    "data/metadata/lm_baselines_v0_1_matrix_status.json",
                ]
            )
            self.assertEqual(rc, 0)
            backups = list((root / "data/metadata").glob("*pre_r2_migration_*.json"))
            self.assertTrue(backups)
            new = json.loads(
                (root / "data/metadata/lm_baselines_v0_1_matrix_r2_status.json").read_text()
            )
            self.assertEqual(new["matrix_id"], "lm_baselines_v0_1_final_matrix_r2")
            self.assertEqual(len(new["runs"]), 36)
            self.assertTrue(all(r["status"] == "pending" for r in new["runs"].values()))
            self.assertEqual(new["completed_scientific_runs"], 0)
            self.assertTrue(new["canary_accepted"])
            self.assertEqual(new["failure_history"], [{"x": 1}])


if __name__ == "__main__":
    unittest.main()
