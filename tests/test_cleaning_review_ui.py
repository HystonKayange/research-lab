#!/usr/bin/env python3
"""Tests for scripts/data/run_cleaning_review.py (data integrity + session)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DATA = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS_DATA))

import run_cleaning_review as ui  # noqa: E402


def _rec(
    rid: str,
    *,
    decision: str = "removed",
    rule_id: str | None = "drop_min_length",
    line: int = 1,
    excerpt: str = "mŵana wanga",
    label=None,
    notes=None,
) -> dict:
    return {
        "review_id": rid,
        "source_id": "wikipedia",
        "original_line_number": line,
        "decision": decision,
        "rule_id": rule_id if decision == "removed" else None,
        "rule_type": "drop_min_length" if decision == "removed" else None,
        "rule_description": "short",
        "excerpt": excerpt,
        "text_sha256": "a" * 64,
        "metrics": {"length": len(excerpt)},
        "review_label": label,
        "review_notes": notes,
    }


def _write_sample(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestLoadValidate(unittest.TestCase):
    def test_valid_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            _write_sample(
                p,
                [
                    _rec("id1", line=1, excerpt="ndi anthu"),
                    _rec("id2", line=2, decision="kept", rule_id=None, excerpt="mulungu"),
                ],
            )
            recs = ui.load_sample(p)
            self.assertEqual(len(recs), 2)
            self.assertEqual(recs[0]["excerpt"], "ndi anthu")

    def test_malformed_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.jsonl"
            p.write_text("{not json\n", encoding="utf-8")
            with self.assertRaises(ui.ReviewError) as ctx:
                ui.load_sample(p)
            self.assertIn("Malformed JSONL", str(ctx.exception))

    def test_invalid_label_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            r = _rec("x", label="not_a_real_label")
            _write_sample(p, [r])
            with self.assertRaises(ui.ReviewError):
                ui.load_sample(p)

    def test_unicode_chichewa_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            text = "Mŵana wanga ndi wabwino"
            _write_sample(p, [_rec("u1", excerpt=text)])
            recs = ui.load_sample(p)
            self.assertEqual(recs[0]["excerpt"], text)


class TestMutationAndSave(unittest.TestCase):
    def test_only_label_and_notes_change(self) -> None:
        recs = [_rec("a", line=10, excerpt="hello")]
        snap = ui.snapshot_immutable(recs)
        ui.apply_annotation(recs, snap, 0, "valid_chichewa", "ok note")
        self.assertEqual(recs[0]["review_label"], "valid_chichewa")
        self.assertEqual(recs[0]["review_notes"], "ok note")
        self.assertEqual(recs[0]["excerpt"], "hello")
        self.assertEqual(recs[0]["original_line_number"], 10)

    def test_invalid_label_rejected(self) -> None:
        recs = [_rec("a")]
        snap = ui.snapshot_immutable(recs)
        with self.assertRaises(ui.ReviewError):
            ui.apply_annotation(recs, snap, 0, "definitely_not", None)

    def test_immutable_tampering_detected(self) -> None:
        recs = [_rec("a", excerpt="orig")]
        snap = ui.snapshot_immutable(recs)
        recs[0]["excerpt"] = "TAMPERED"
        with self.assertRaises(ui.ReviewError) as ctx:
            ui.assert_immutable_intact(snap, recs)
        self.assertIn("excerpt", str(ctx.exception))

    def test_atomic_save_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.jsonl"
            backup_dir = root / "backups"
            records = [
                _rec("r1", line=1, excerpt="one"),
                _rec("r2", line=2, excerpt="two"),
            ]
            _write_sample(sample, records)
            loaded = ui.load_sample(sample)
            snap = ui.snapshot_immutable(loaded)
            ui.apply_annotation(loaded, snap, 0, "boilerplate_or_noise", None)
            result = ui.atomic_save(
                sample, loaded, snap, backup_dir, create_backup=True
            )
            self.assertTrue(sample.is_file())
            self.assertIsNotNone(result["backup_path"])
            self.assertTrue(Path(result["backup_path"]).is_file())

            # Order preserved
            again = ui.load_sample(sample)
            self.assertEqual([r["review_id"] for r in again], ["r1", "r2"])
            self.assertEqual(again[0]["review_label"], "boilerplate_or_noise")
            # Backup has original unlabeled
            bak = [
                json.loads(l)
                for l in Path(result["backup_path"]).read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
            self.assertIsNone(bak[0]["review_label"])

    def test_failed_save_does_not_destroy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.jsonl"
            backup_dir = root / "backups"
            original = [_rec("keep", excerpt="safe")]
            _write_sample(sample, original)
            before = sample.read_bytes()

            loaded = ui.load_sample(sample)
            snap = ui.snapshot_immutable(loaded)
            # Tamper after snapshot → save must fail validation
            loaded[0]["text_sha256"] = "b" * 64
            with self.assertRaises(ui.ReviewError):
                ui.atomic_save(
                    sample, loaded, snap, backup_dir, create_backup=True
                )
            # Original file intact
            self.assertEqual(sample.read_bytes(), before)

    def test_unwritable_output_safe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.jsonl"
            _write_sample(sample, [_rec("x")])
            loaded = ui.load_sample(sample)
            snap = ui.snapshot_immutable(loaded)
            ui.apply_annotation(loaded, snap, 0, "uncertain", None)
            # Point save path to a directory (cannot write as file replace cleanly)
            # Use a non-existent parent that we make into a file to block mkdir... 
            # Better: make backup_dir a file so mkdir fails after validation
            # Actually atomic_save creates parent dirs. Use read-only directory.
            ro = root / "ro"
            ro.mkdir()
            target = ro / "out.jsonl"
            # Write initial target then chmod directory read-only
            _write_sample(target, [_rec("x")])
            import os
            os.chmod(ro, 0o555)
            try:
                with self.assertRaises(OSError):
                    ui.atomic_save(
                        target,
                        loaded,
                        snap,
                        root / "backups",
                        create_backup=False,
                    )
                # original still readable with original content
                self.assertTrue(target.is_file())
            finally:
                os.chmod(ro, 0o755)


class TestSession(unittest.TestCase):
    def test_resume_partial_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "s.jsonl"
            records = [
                _rec("a", line=1, rule_id="drop_url", label="foreign_language"),
                _rec("b", line=2, rule_id="drop_min_length", label=None),
                _rec("c", line=3, decision="kept", rule_id=None, label=None),
                _rec("d", line=4, rule_id="drop_min_length", label="uncertain"),
            ]
            _write_sample(sample, records)
            session = ui.ReviewSession(
                sample_path=sample,
                backup_dir=root / "bak",
                autosave_every=100,
            )
            counts = session.counts()
            self.assertEqual(counts["total"], 4)
            self.assertEqual(counts["labeled"], 2)
            self.assertEqual(counts["unlabeled"], 2)
            self.assertEqual(counts["uncertain"], 1)
            # Starts at first unlabeled
            ri = session.current_record_index()
            self.assertEqual(session.records[ri]["review_id"], "b")

            # Unlabeled filter
            session.set_filters(unlabeled_only=True)
            ids = [
                session.records[i]["review_id"] for i in session.filtered_indices()
            ]
            self.assertEqual(ids, ["b", "c"])

            # Rule filter
            session.set_filters(unlabeled_only=False, rule_id="drop_min_length")
            ids = [
                session.records[i]["review_id"] for i in session.filtered_indices()
            ]
            self.assertEqual(ids, ["b", "d"])

            # Decision filter
            session.set_filters(rule_id="", decision="kept")
            ids = [
                session.records[i]["review_id"] for i in session.filtered_indices()
            ]
            self.assertEqual(ids, ["c"])

            # Progress counts
            self.assertEqual(session.state_dict()["counts"]["unlabeled"], 2)

    def test_label_and_save_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "s.jsonl"
            _write_sample(
                sample,
                [
                    _rec("a", line=1, label=None, excerpt="mŵana"),
                    _rec("b", line=2, label=None),
                ],
            )
            session = ui.ReviewSession(sample, root / "bak", autosave_every=50)
            session.set_label("valid_chichewa", "note ŵ")
            self.assertTrue(session.dirty)
            session.save(create_backup=True)
            self.assertFalse(session.dirty)
            reloaded = ui.load_sample(sample)
            self.assertEqual(reloaded[0]["review_label"], "valid_chichewa")
            self.assertEqual(reloaded[0]["review_notes"], "note ŵ")
            self.assertEqual(reloaded[0]["excerpt"], "mŵana")
            # backup exists
            backups = list((root / "bak").glob("*.jsonl"))
            self.assertGreaterEqual(len(backups), 1)

    def test_order_preserved_after_many_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "s.jsonl"
            recs = [_rec(f"id{i}", line=i, excerpt=f"line {i}") for i in range(5)]
            _write_sample(sample, recs)
            session = ui.ReviewSession(sample, root / "bak", autosave_every=1000)
            for _ in range(5):
                session.set_label("duplicate", None)
                session.navigate("next")
            session.save(create_backup=True)
            again = ui.load_sample(sample)
            self.assertEqual(
                [r["review_id"] for r in again],
                [f"id{i}" for i in range(5)],
            )


if __name__ == "__main__":
    unittest.main()
