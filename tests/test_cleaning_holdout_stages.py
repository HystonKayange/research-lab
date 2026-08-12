#!/usr/bin/env python3
"""Tests for sequential holdout stage builder and stopping logic."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS))

import build_cleaning_holdout_stages as stages  # noqa: E402
import summarize_cleaning_holdout_stage as stage_sum  # noqa: E402


def _parent_records(n_rm: int = 50, n_kp: int = 50) -> list[dict]:
    recs = []
    rules = [
        "drop_high_confidence_foreign",
        "drop_short_conditional",
        "drop_url_only",
        "drop_wikimedia_chrome",
        "drop_long_table_dump",
        "drop_category",
        "drop_blank",
        "drop_digit_only",
    ]
    for i in range(n_rm):
        rid = rules[i % len(rules)]
        recs.append(
            {
                "review_id": f"rm{i}",
                "source_id": "wikipedia",
                "original_line_number": i + 1,
                "v2_decision": "removed",
                "v2_rule_id": rid,
                "excerpt": f"removed text {i} mŵana" if i % 3 == 0 else f"rm {i}",
                "text_sha256": f"{i:064d}"[:64],
                "review_label": None,
                "review_notes": None,
                "holdout_strata": [rid],
            }
        )
    strata = [
        "mixed_signal",
        "insufficient_signal",
        "english_names_institutions",
        "near_threshold",
        "short_retained",
        "long_retained",
        "chichewa_signal",
        "url_stripped_retained",
    ]
    for i in range(n_kp):
        s = strata[i % len(strata)]
        recs.append(
            {
                "review_id": f"kp{i}",
                "source_id": "wikipedia",
                "original_line_number": 1000 + i,
                "v2_decision": "kept",
                "v2_rule_id": None,
                "excerpt": f"kept text {i}",
                "text_sha256": f"{1000+i:064d}"[:64],
                "review_label": None,
                "review_notes": None,
                "holdout_strata": [s, "chichewa_signal"],
            }
        )
    return recs


class TestStageSelection(unittest.TestCase):
    def test_stage1_size_and_exclusion(self) -> None:
        parent = _parent_records(60, 60)
        config = {
            "random_seed": 7,
            "stage1": {
                "removed_total": 40,
                "kept_total": 40,
                "removed_priority_quotas": {
                    "drop_high_confidence_foreign": 12,
                    "drop_short_conditional": 10,
                    "drop_url_only": 8,
                    "drop_wikimedia_chrome": 5,
                    "drop_long_table_dump": 2,
                    "drop_category": 3,
                },
                "removed_exclude_rules": ["drop_blank", "drop_digit_only"],
                "kept_priority_quotas": {
                    "mixed_signal": 10,
                    "insufficient_signal": 8,
                    "english_names_institutions": 6,
                    "near_threshold": 5,
                    "short_retained": 4,
                    "long_retained": 3,
                    "url_stripped_retained": 2,
                    "chichewa_signal": 2,
                },
            },
        }
        stage, extension, stats = stages.select_stage1(parent, config)
        self.assertEqual(len(stage), 80)
        self.assertEqual(stats["stage1_counts"]["removed"], 40)
        self.assertEqual(stats["stage1_counts"]["kept"], 40)
        self.assertEqual(len(stage) + len(extension), len(parent))
        stage_ids = {r["review_id"] for r in stage}
        ext_ids = {r["review_id"] for r in extension}
        self.assertEqual(len(stage_ids & ext_ids), 0)
        # excluded rules not in stage1 removed
        for r in stage:
            if r["v2_decision"] == "removed":
                self.assertNotIn(r["v2_rule_id"], {"drop_blank", "drop_digit_only"})

    def test_deterministic(self) -> None:
        parent = _parent_records(50, 50)
        config = {
            "random_seed": 7,
            "stage1": {
                "removed_total": 40,
                "kept_total": 40,
                "removed_priority_quotas": {
                    "drop_high_confidence_foreign": 12,
                    "drop_short_conditional": 10,
                    "drop_url_only": 8,
                    "drop_wikimedia_chrome": 5,
                    "drop_long_table_dump": 2,
                    "drop_category": 3,
                },
                "removed_exclude_rules": ["drop_blank", "drop_digit_only"],
                "kept_priority_quotas": {
                    "mixed_signal": 10,
                    "insufficient_signal": 8,
                    "english_names_institutions": 6,
                    "near_threshold": 5,
                    "short_retained": 4,
                    "long_retained": 3,
                    "url_stripped_retained": 2,
                    "chichewa_signal": 2,
                },
            },
        }
        a, _, _ = stages.select_stage1(parent, config)
        b, _, _ = stages.select_stage1(parent, config)
        self.assertEqual(
            [r["review_id"] for r in a],
            [r["review_id"] for r in b],
        )


class TestStoppingLogic(unittest.TestCase):
    def test_stop_when_clear(self) -> None:
        metrics = {
            "removal_precision": 0.95,
            "false_removal_rate": 0.05,
            "useful_text_retention": 0.96,
        }
        intervals = {
            "removal_precision": {"low": 0.85, "high": 0.99},
            "false_removal_rate": {"low": 0.01, "high": 0.12},
            "useful_text_retention": {"low": 0.88, "high": 0.99},
        }
        # tighten: need ci_high_le 0.2 for frr — 0.12 ok; ci_low_ge 0.8 for prec — 0.85 ok
        stopping = {
            "stop_if_all": [
                {"metric": "removal_precision", "op": "ge", "value": 0.9, "ci_low_ge": 0.8},
                {"metric": "false_removal_rate", "op": "le", "value": 0.1, "ci_high_le": 0.2},
                {"metric": "useful_text_retention", "op": "ge", "value": 0.9, "ci_low_ge": 0.8},
            ],
            "chunk_size": 40,
        }
        rec = stage_sum.apply_stopping_logic(metrics, intervals, stopping)
        self.assertEqual(rec["decision"], "stop")

    def test_release_when_missed(self) -> None:
        metrics = {
            "removal_precision": 0.7,
            "false_removal_rate": 0.3,
            "useful_text_retention": 0.95,
        }
        intervals = {
            "removal_precision": {"low": 0.55, "high": 0.82},
            "false_removal_rate": {"low": 0.18, "high": 0.45},
            "useful_text_retention": {"low": 0.88, "high": 0.99},
        }
        stopping = {
            "stop_if_all": [
                {"metric": "removal_precision", "op": "ge", "value": 0.9, "ci_low_ge": 0.8},
                {"metric": "false_removal_rate", "op": "le", "value": 0.1, "ci_high_le": 0.2},
                {"metric": "useful_text_retention", "op": "ge", "value": 0.9, "ci_low_ge": 0.8},
            ],
            "chunk_size": 40,
        }
        rec = stage_sum.apply_stopping_logic(metrics, intervals, stopping)
        self.assertEqual(rec["decision"], "release_next_chunk")


def _ext_record(i: int) -> dict:
    return {
        "review_id": f"ext{i:03d}",
        "source_id": "wikipedia",
        "original_line_number": 5000 + i,
        "v2_decision": "removed" if i % 2 == 0 else "kept",
        "v2_rule_id": "drop_url_only" if i % 2 == 0 else None,
        "excerpt": f"extension text {i}",
        "text_sha256": f"{5000 + i:064d}"[:64],
        "review_label": None,
        "review_notes": None,
        "sequential_role": "extension_locked",
        "evaluation_stage": None,
        "holdout_strata": ["mixed_signal"],
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _label_all(path: Path, label: str = "boilerplate_or_noise") -> None:
    recs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        r["review_label"] = label
        recs.append(r)
    _write_jsonl(path, recs)


def _file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestSequentialStageRelease(unittest.TestCase):
    """Part A: immutable sequential stage numbering and release safety."""

    def _seed_stages_1_2(
        self, reports: Path, ext_path: Path, n_ext: int = 20
    ) -> None:
        stage1 = [
            {
                "review_id": f"s1_{i}",
                "source_id": "wikipedia",
                "original_line_number": i,
                "v2_decision": "removed",
                "v2_rule_id": "drop_url_only",
                "excerpt": f"s1 {i}",
                "text_sha256": f"{i:064d}"[:64],
                "review_label": "boilerplate_or_noise",
                "review_notes": None,
                "evaluation_stage": 1,
                "sequential_role": "stage1_active",
            }
            for i in range(5)
        ]
        stage2 = [
            {
                "review_id": f"s2_{i}",
                "source_id": "wikipedia",
                "original_line_number": 100 + i,
                "v2_decision": "kept",
                "v2_rule_id": None,
                "excerpt": f"s2 {i}",
                "text_sha256": f"{100 + i:064d}"[:64],
                "review_label": "valid_chichewa",
                "review_notes": None,
                "evaluation_stage": 2,
                "sequential_role": "stage2_active",
            }
            for i in range(5)
        ]
        _write_jsonl(reports / "cleaning_holdout_stage1_sample.jsonl", stage1)
        _write_jsonl(reports / "cleaning_holdout_stage2_sample.jsonl", stage2)
        _write_jsonl(ext_path, [_ext_record(i) for i in range(n_ext)])

    def test_stage3_created_after_stages_1_and_2(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            backups = root / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=15)
            info = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=5,
                backup_dir=backups,
            )
            self.assertEqual(info["stage_number"], 3)
            stage3 = reports / "cleaning_holdout_stage3_sample.jsonl"
            self.assertTrue(stage3.is_file())
            self.assertEqual(info["stage_sample"], str(stage3))
            self.assertFalse(
                (reports / "cleaning_holdout_stage4_sample.jsonl").exists()
            )

    def test_no_overwrite_of_stage2(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            backups = root / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=10)
            stage2 = reports / "cleaning_holdout_stage2_sample.jsonl"
            sha_before = _file_sha256(stage2)
            content_before = stage2.read_text(encoding="utf-8")
            stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=3,
                backup_dir=backups,
            )
            self.assertEqual(stage2.read_text(encoding="utf-8"), content_before)
            self.assertEqual(_file_sha256(stage2), sha_before)

    def test_prior_stage_checksums_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=12)
            s1 = reports / "cleaning_holdout_stage1_sample.jsonl"
            s2 = reports / "cleaning_holdout_stage2_sample.jsonl"
            sha1, sha2 = _file_sha256(s1), _file_sha256(s2)
            stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=4,
                backup_dir=backups,
            )
            self.assertEqual(_file_sha256(s1), sha1)
            self.assertEqual(_file_sha256(s2), sha2)

    def test_partially_labeled_previous_stage_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=8)
            # Unlabel one stage-2 record
            s2 = reports / "cleaning_holdout_stage2_sample.jsonl"
            recs = [json.loads(line) for line in s2.read_text().splitlines() if line.strip()]
            recs[0]["review_label"] = None
            _write_jsonl(s2, recs)
            with self.assertRaises(ValueError) as ctx:
                stage_sum.release_next_chunk(
                    extension_path=ext,
                    reports_dir=reports,
                    chunk_size=3,
                    backup_dir=backups,
                    allow_partial_prior=False,
                )
            self.assertIn("not fully labeled", str(ctx.exception).lower())
            # Override allowed
            info = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=3,
                backup_dir=backups,
                allow_partial_prior=True,
            )
            self.assertEqual(info["stage_number"], 3)

    def test_deterministic_record_selection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            pool = [_ext_record(i) for i in range(10)]
            self._seed_stages_1_2(reports, ext, n_ext=0)
            _write_jsonl(ext, pool)
            info_a = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=4,
                backup_dir=backups,
            )
            # Rebuild identical world for second run
            reports2 = Path(td) / "reports2"
            backups2 = Path(td) / "backups2"
            ext2 = reports2 / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports2, ext2, n_ext=0)
            _write_jsonl(ext2, pool)
            info_b = stage_sum.release_next_chunk(
                extension_path=ext2,
                reports_dir=reports2,
                chunk_size=4,
                backup_dir=backups2,
            )
            self.assertEqual(info_a["review_ids"], info_b["review_ids"])
            self.assertEqual(
                info_a["review_ids"],
                [f"ext{i:03d}" for i in range(4)],
            )

    def test_extension_pool_count_decreases(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=17)
            info = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=5,
                backup_dir=backups,
            )
            remaining = [
                line
                for line in ext.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(remaining), 12)
            self.assertEqual(info["extension_remaining"], 12)
            self.assertEqual(info["released"], 5)

    def test_no_duplicate_record_across_stages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=10)
            stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=4,
                backup_dir=backups,
            )
            ids: list[str] = []
            for n in (1, 2, 3):
                p = reports / f"cleaning_holdout_stage{n}_sample.jsonl"
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        ids.append(json.loads(line)["review_id"])
            self.assertEqual(len(ids), len(set(ids)))

    def test_atomic_failure_safety_no_stage_on_empty_pool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=0)
            _write_jsonl(ext, [])
            with self.assertRaises(ValueError) as ctx:
                stage_sum.release_next_chunk(
                    extension_path=ext,
                    reports_dir=reports,
                    chunk_size=5,
                    backup_dir=backups,
                )
            self.assertIn("empty", str(ctx.exception).lower())
            self.assertFalse(
                (reports / "cleaning_holdout_stage3_sample.jsonl").exists()
            )

    def test_empty_extension_pool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=0)
            # empty file
            ext.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                stage_sum.release_next_chunk(
                    extension_path=ext,
                    reports_dir=reports,
                    chunk_size=5,
                    backup_dir=backups,
                )

    def test_manifest_correctness(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=9)
            info = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=3,
                backup_dir=backups,
            )
            man_path = Path(info["manifest_path"])
            self.assertTrue(man_path.is_file())
            man = json.loads(man_path.read_text(encoding="utf-8"))
            self.assertEqual(man["stage_number"], 3)
            self.assertEqual(man["n_records"], 3)
            self.assertEqual(man["parent_holdout_ids"], info["review_ids"])
            self.assertEqual(man["immutable_prior_stages"], [1, 2])
            self.assertEqual(man["extension_remaining"], 6)
            self.assertEqual(man["annotation_status"], "pending_human_labels")
            self.assertIsNotNone(man.get("extension_backup"))
            self.assertTrue(Path(man["extension_backup"]).is_file())

    def test_next_stage_number_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td)
            self.assertEqual(stage_sum.next_stage_number(reports), 1)
            (reports / "cleaning_holdout_stage1_sample.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            (reports / "cleaning_holdout_stage2_sample.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            self.assertEqual(stage_sum.discover_existing_stages(reports), [1, 2])
            self.assertEqual(stage_sum.next_stage_number(reports), 3)

    def test_refuse_overwrite_existing_next_stage_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td) / "reports"
            backups = Path(td) / "backups"
            ext = reports / "cleaning_holdout_extension_pool.jsonl"
            self._seed_stages_1_2(reports, ext, n_ext=5)
            # Pre-create fully labeled stage3 so next free stage is 4
            stage3 = reports / "cleaning_holdout_stage3_sample.jsonl"
            stage3.write_text(
                json.dumps(
                    {
                        "review_id": "preexisting",
                        "review_label": "boilerplate_or_noise",
                        "text_sha256": "a" * 64,
                        "original_line_number": 1,
                        "v2_decision": "removed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            sha3 = _file_sha256(stage3)
            info = stage_sum.release_next_chunk(
                extension_path=ext,
                reports_dir=reports,
                chunk_size=2,
                backup_dir=backups,
            )
            self.assertEqual(info["stage_number"], 4)
            self.assertTrue(
                (reports / "cleaning_holdout_stage4_sample.jsonl").is_file()
            )
            # preexisting stage3 unchanged (no overwrite)
            self.assertEqual(_file_sha256(stage3), sha3)
            self.assertIn("preexisting", stage3.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
