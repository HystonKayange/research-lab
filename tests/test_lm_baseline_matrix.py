#!/usr/bin/env python3
"""Tests for final LM baseline matrix launcher (no real training)."""

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
from matrix_common import (  # noqa: E402
    FileLock,
    canary_acceptance_valid,
    enumerate_canary_runs,
    enumerate_full_runs,
    enumerate_stage,
    filter_specs,
    is_run_completed_valid,
    make_run_id,
)


class TestMatrixEnumeration(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1_final_matrix.json").read_text(
                encoding="utf-8"
            )
        )

    def test_exactly_36_runs(self) -> None:
        runs = enumerate_full_runs(self.cfg)
        self.assertEqual(len(runs), 36)
        self.assertEqual(len(runs), int(self.cfg["expected_run_count"]))

    def test_stable_run_ids(self) -> None:
        a = enumerate_full_runs(self.cfg)
        b = enumerate_full_runs(self.cfg)
        self.assertEqual([r.run_id for r in a], [r.run_id for r in b])
        ids = [r.run_id for r in a]
        self.assertEqual(len(ids), len(set(ids)))

    def test_canary_exactly_one(self) -> None:
        c = enumerate_canary_runs(self.cfg)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].tokenizer, "bpe_8000")
        self.assertEqual(c[0].seed, 42)
        self.assertEqual(c[0].track, "architecture_matched")
        self.assertEqual(c[0].budget_policy, "fixed_characters")

    def test_full_blocked_without_canary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acc.json"
            self.assertFalse(canary_acceptance_valid(p))
            write = {"accepted": True}
            p.write_text(json.dumps(write), encoding="utf-8")
            self.assertTrue(canary_acceptance_valid(p))

    def test_filter_specs(self) -> None:
        runs = enumerate_full_runs(self.cfg)
        f = filter_specs(runs, tokenizer="character", seed=42)
        self.assertEqual(len(f), 4)  # 2 tracks × 2 budgets

    def test_completed_run_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertFalse(is_run_completed_valid(d))
            (d / "best.pt").write_bytes(b"abc")
            import hashlib

            h = hashlib.sha256(b"abc").hexdigest()
            (d / "manifest.json").write_text(
                json.dumps({"status": "completed"}), encoding="utf-8"
            )
            (d / "selection_lock.json").write_text(
                json.dumps(
                    {
                        "selected_checkpoint": "best.pt",
                        "checkpoint_sha256": h,
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(is_run_completed_valid(d))

    def test_file_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lp = Path(td) / "lock"
            a = FileLock(lp)
            self.assertTrue(a.acquire())
            b = FileLock(lp)
            self.assertFalse(b.acquire())
            a.release()
            self.assertTrue(b.acquire())
            b.release()

    def test_make_run_id_stable(self) -> None:
        a = make_run_id("bpe_8000", 42, "architecture_matched", "fixed_characters")
        b = make_run_id("bpe_8000", 42, "architecture_matched", "fixed_characters")
        self.assertEqual(a, b)
        self.assertIn("bpe_8000", a)
        self.assertIn("seed42", a)


class TestMatrixLauncherDryRun(unittest.TestCase):
    def test_dry_run_launches_nothing(self) -> None:
        import run_lm_baseline_matrix as launcher

        with mock.patch("subprocess.run") as sp:
            rc = launcher.main(
                [
                    "--config",
                    str(REPO / "configs/models/lm_baselines_v0_1_final_matrix.json"),
                    "--stage",
                    "canary",
                    "--dry-run",
                    "--repo-root",
                    str(REPO),
                ]
            )
            self.assertEqual(rc, 0)
            sp.assert_not_called()

    def test_full_blocked_without_acceptance(self) -> None:
        import run_lm_baseline_matrix as launcher

        # ensure acceptance file absent or false
        acc = REPO / "data/metadata/lm_baselines_v0_1_canary_acceptance.json"
        backup = None
        if acc.is_file():
            backup = acc.read_text(encoding="utf-8")
            acc.unlink()
        try:
            with mock.patch("subprocess.run") as sp:
                rc = launcher.main(
                    [
                        "--config",
                        str(REPO / "configs/models/lm_baselines_v0_1_final_matrix.json"),
                        "--stage",
                        "full",
                        "--repo-root",
                        str(REPO),
                        "--yes",
                    ]
                )
                self.assertEqual(rc, 2)
                sp.assert_not_called()
        finally:
            if backup is not None:
                acc.write_text(backup, encoding="utf-8")


class TestTrainDryPlan(unittest.TestCase):
    def test_dry_run_plan_no_train(self) -> None:
        import train_lm_baseline as train

        with mock.patch("torch.cuda.is_available", return_value=False):
            rc = train.main(
                [
                    "--config",
                    str(REPO / "configs/models/lm_baselines_v0_1.json"),
                    "--matrix-config",
                    str(REPO / "configs/models/lm_baselines_v0_1_final_matrix.json"),
                    "--phase",
                    "final",
                    "--tokenizer",
                    "bpe_8000",
                    "--seed",
                    "42",
                    "--track",
                    "architecture_matched",
                    "--budget-policy",
                    "fixed_characters",
                    "--dry-run-plan",
                    "--repo-root",
                    str(REPO),
                ]
            )
            self.assertEqual(rc, 0)


class TestPilotExclusionNote(unittest.TestCase):
    def test_matrix_flags_pilot_excluded(self) -> None:
        cfg = json.loads(
            (REPO / "configs/models/lm_baselines_v0_1_final_matrix.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(cfg["launcher"]["pilot_excluded_from_final_aggregation"])
        self.assertTrue(cfg["launcher"]["require_canary_acceptance_for_full"])


if __name__ == "__main__":
    unittest.main()
