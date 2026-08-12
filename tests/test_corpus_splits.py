#!/usr/bin/env python3
"""Tests for leakage-safe corpus split builder and validator."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS))

import build_corpus_splits as splitmod  # noqa: E402
import validate_corpus_splits as valmod  # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _write_json(p: Path, obj: object) -> None:
    _write(p, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _make_processed(
    root: Path,
    *,
    bible_lines: list[str],
    wiki_lines: list[str],
) -> Path:
    corpus = root / "data" / "processed" / "chichewa_corpus_v0.1"
    (corpus / "corpus").mkdir(parents=True)
    (corpus / "metadata").mkdir(parents=True)
    bible_body = "\n".join(bible_lines) + ("\n" if bible_lines else "")
    wiki_body = "\n".join(wiki_lines) + ("\n" if wiki_lines else "")
    _write(corpus / "corpus" / "bible.txt", bible_body)
    _write(corpus / "corpus" / "wikipedia.txt", wiki_body)
    docs = []
    for sid, lines in (("bible", bible_lines), ("wikipedia", wiki_lines)):
        for i, t in enumerate(lines):
            docs.append(
                {
                    "doc_id": f"{sid}:{i}",
                    "source_id": sid,
                    "line_index": i,
                    "text_sha256": splitmod.sha256_text(t),
                    "n_chars": len(t),
                }
            )
    with (corpus / "metadata" / "documents.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    _write_json(
        corpus / "metadata" / "sources.json",
        {"sources": {"bible": {}, "wikipedia": {}}, "excluded": ["existing_corpus"]},
    )
    _write_json(
        corpus / "metadata" / "build_manifest.json",
        {"corpus_version": "v0.1", "tool": {"name": "fixture"}},
    )
    checksums = {
        "corpus/bible.txt": _sha(bible_body.encode("utf-8")),
        "corpus/wikipedia.txt": _sha(wiki_body.encode("utf-8")),
    }
    _write_json(corpus / "metadata" / "checksums.json", checksums)
    return corpus


def _base_config(root: Path, *, target_chars: int = 40) -> dict:
    return {
        "version": "0.1.0",
        "split_version": "v0.1",
        "corpus_name": "chichewa_corpus",
        "corpus_version": "v0.1",
        "processed_corpus_root": "data/processed/chichewa_corpus_v0.1",
        "output_root": "data/splits/chichewa_corpus_v0.1",
        "report_path": "data/reports/split_v0_1_report.md",
        "manifest_path": "data/metadata/split_v0_1_manifest.json",
        "proportions": {"train": 0.80, "validation": 0.10, "test": 0.10},
        "assignment": {
            "method": "sha256_group_hash",
            "salt": "test_salt_v0_1",
            "bucket_modulus": 10000,
        },
        "grouping": {
            "strategy": "contiguous_char_blocks",
            "target_group_characters": target_chars,
            "sources": {
                "bible": {
                    "preferred": "book_or_chapter",
                    "available": "contiguous_char_blocks",
                    "limitation": "fixture",
                },
                "wikipedia": {
                    "preferred": "article_document",
                    "available": "contiguous_char_blocks",
                    "limitation": "fixture",
                },
            },
        },
        "sources": ["bible", "wikipedia"],
        "combined_source_order": ["bible", "wikipedia"],
        "leakage": {
            "forbid_exact_cross_split": True,
            "forbid_normalized_cross_split": True,
            "normalization": "unicode_nfc_whitespace_collapse_strip",
            "on_conflict": "reassign_non_train_groups_to_train",
            "optional_shingle_diagnostics": {
                "enabled": True,
                "shingle_size": 5,
                "max_report_pairs": 5,
            },
        },
        "tokenizer_policy": {
            "train_tokenizer_on": ["train"],
            "forbid_tokenizer_on": ["validation", "test"],
        },
        "frozen": True,
    }


class TestGroupingAndAssignment(unittest.TestCase):
    def test_contiguous_blocks_and_sha256_stable(self) -> None:
        lines = [
            splitmod.LineRecord("bible", i, f"line {i} xxxx", f"bible:{i}", "h", 12)
            for i in range(10)
        ]
        groups = splitmod.form_contiguous_char_blocks(
            lines, target_chars=30, source_id="bible"
        )
        self.assertGreaterEqual(len(groups), 2)
        # contiguous coverage
        covered = []
        for g in groups:
            covered.extend(range(g.start_line, g.end_line))
        self.assertEqual(covered, list(range(10)))

        thr = splitmod.bucket_thresholds(
            {"train": 0.8, "validation": 0.1, "test": 0.1}, 10000
        )
        a1 = splitmod.assign_split_sha256(
            "bible:block:000000-000003", salt="s", modulus=10000, thresholds=thr
        )
        a2 = splitmod.assign_split_sha256(
            "bible:block:000000-000003", salt="s", modulus=10000, thresholds=thr
        )
        self.assertEqual(a1, a2)
        # digest is full SHA-256 hex
        self.assertEqual(len(a1[2]), 64)
        self.assertRegex(a1[2], r"^[0-9a-f]{64}$")
        # different salt → different bucket path material (digest changes)
        a3 = splitmod.assign_split_sha256(
            "bible:block:000000-000003", salt="other", modulus=10000, thresholds=thr
        )
        self.assertNotEqual(a1[2], a3[2])

    def test_deterministic_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"Bible verse number {i} content pad" for i in range(40)]
            wiki = [f"Wiki article line {i} content pad" for i in range(30)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=50)
            cfg_path = root / "configs" / "data" / "split_v0_1.json"
            _write_json(cfg_path, cfg)
            r1 = splitmod.run_build(
                config=cfg, config_path=cfg_path, repo_root=root
            )
            # Capture stable artifacts (exclude README timestamps)
            def stable_checksums(base: Path) -> dict[str, str]:
                c = json.loads(
                    (base / "metadata/checksums.json").read_text(encoding="utf-8")
                )
                return {k: v for k, v in c.items() if k != "README.md"}

            def assignments_bytes(base: Path) -> bytes:
                return (base / "metadata/split_assignments.jsonl").read_bytes()

            base = root / "data/splits/chichewa_corpus_v0.1"
            c1 = stable_checksums(base)
            a1 = assignments_bytes(base)
            shutil.rmtree(base)
            (root / "data/metadata").mkdir(exist_ok=True)
            r2 = splitmod.run_build(
                config=cfg, config_path=cfg_path, repo_root=root, force_new_version=True
            )
            c2 = stable_checksums(base)
            a2 = assignments_bytes(base)
            self.assertEqual(c1, c2)
            self.assertEqual(a1, a2)
            self.assertEqual(
                r1["stats"]["train"]["totals"]["lines"],
                r2["stats"]["train"]["totals"]["lines"],
            )

    def test_group_integrity_no_multi_split(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i} " + ("word " * 5) for i in range(25)]
            wiki = [f"w{i} " + ("word " * 5) for i in range(25)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=40)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            assigns = [
                json.loads(L)
                for L in (root / "data/splits/chichewa_corpus_v0.1/metadata/split_assignments.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if L.strip()
            ]
            seen: dict[str, str] = {}
            for a in assigns:
                if a["group_id"] in seen:
                    self.assertEqual(seen[a["group_id"]], a["split"])
                seen[a["group_id"]] = a["split"]

    def test_no_exact_or_normalized_cross_split(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Include a normalized duplicate that would leak if groups split differently
            shared = "  Same   LINE  "
            bible = [f"bible unique {i} pad pad" for i in range(20)] + [shared.strip()]
            wiki = [f"wiki unique {i} pad pad" for i in range(20)] + [shared]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=35)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            result = valmod.validate(config=cfg, repo_root=root, include_shingles=False)
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["exact_cross_split_count"], 0)
            self.assertEqual(result["normalized_cross_split_count"], 0)

    def test_source_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"B{i}" for i in range(15)]
            wiki = [f"W{i}" for i in range(12)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=10)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            total_b = 0
            total_w = 0
            for s in ("train", "validation", "test"):
                total_b += len(
                    (root / f"data/splits/chichewa_corpus_v0.1/{s}/bible.txt")
                    .read_text(encoding="utf-8")
                    .splitlines()
                )
                total_w += len(
                    (root / f"data/splits/chichewa_corpus_v0.1/{s}/wikipedia.txt")
                    .read_text(encoding="utf-8")
                    .splitlines()
                )
            self.assertEqual(total_b, 15)
            self.assertEqual(total_w, 12)

    def test_approximate_ratio_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Many small groups → ratio closer to target
            bible = [f"bible line {i:04d} " + ("x" * 20) for i in range(200)]
            wiki = [f"wiki line {i:04d} " + ("y" * 20) for i in range(200)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=30)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            res = splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            total = sum(res["stats"][s]["totals"]["characters"] for s in splitmod.SPLITS)
            train_f = res["stats"]["train"]["totals"]["characters"] / total
            # Allow wide band: hash assignment is approximate
            self.assertGreater(train_f, 0.55)
            self.assertLess(train_f, 0.95)

    def test_small_source_handling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = ["only one bible line here"]
            wiki = ["w0", "w1", "w2"]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=1000)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            res = splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            self.assertEqual(
                sum(res["stats"][s]["totals"]["lines"] for s in splitmod.SPLITS), 4
            )

    def test_unicode_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = ["Malaŵi ndi dziko la ŵanthu.", "Chichewa ŵ"]
            wiki = ["Zambia ndi ŵabale"]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=5)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            text = ""
            for s in splitmod.SPLITS:
                p = root / f"data/splits/chichewa_corpus_v0.1/{s}/bible.txt"
                if p.is_file():
                    text += p.read_text(encoding="utf-8")
            self.assertIn("ŵ", text)
            self.assertIn("Malaŵi", text)

    def test_source_specific_and_combined_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i}" for i in range(10)]
            wiki = [f"w{i}" for i in range(10)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=8)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            for s in splitmod.SPLITS:
                b = (root / f"data/splits/chichewa_corpus_v0.1/{s}/bible.txt").read_text(
                    encoding="utf-8"
                ).splitlines()
                w = (
                    root / f"data/splits/chichewa_corpus_v0.1/{s}/wikipedia.txt"
                ).read_text(encoding="utf-8").splitlines()
                c = (
                    root / f"data/splits/chichewa_corpus_v0.1/{s}/combined.txt"
                ).read_text(encoding="utf-8").splitlines()
                self.assertEqual(c, b + w)

    def test_immutable_processed_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i}" for i in range(8)]
            wiki = [f"w{i}" for i in range(8)]
            corpus = _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            before = (corpus / "corpus" / "bible.txt").read_bytes()
            cfg = _base_config(root, target_chars=10)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            after = (corpus / "corpus" / "bible.txt").read_bytes()
            self.assertEqual(before, after)

    def test_refuse_overwrite_frozen_split(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i}" for i in range(12)]
            wiki = [f"w{i}" for i in range(12)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=15)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            with self.assertRaises(FileExistsError):
                splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)

    def test_manifest_validity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i} pad" for i in range(20)]
            wiki = [f"w{i} pad" for i in range(20)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=25)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            res = splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            man = res["manifest"]
            self.assertTrue(man["frozen"])
            self.assertEqual(man["input_line_total"], man["output_line_total"])
            self.assertIn("config_sha256", man)
            self.assertIn("processed_build_manifest_sha256", man)
            self.assertEqual(man["leakage"]["exact_cross_split_count"], 0)

    def test_malformed_document_metadata_handling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"b{i}" for i in range(6)]
            wiki = [f"w{i}" for i in range(6)]
            corpus = _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            # Corrupt documents.jsonl with bad lines; builder should still work
            with (corpus / "metadata" / "documents.jsonl").open("a", encoding="utf-8") as f:
                f.write("{not json\n")
                f.write(json.dumps({"source_id": "bible"}) + "\n")  # missing line_index
            cfg = _base_config(root, target_chars=8)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            res = splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            self.assertEqual(res["manifest"]["output_line_total"], 12)

    def test_fallback_when_document_boundaries_unavailable(self) -> None:
        """Line-level docs only → contiguous blocks; group_id encodes line range."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bible = [f"verse {i} text content here" for i in range(30)]
            wiki = [f"para {i} text content here" for i in range(30)]
            _make_processed(root, bible_lines=bible, wiki_lines=wiki)
            cfg = _base_config(root, target_chars=50)
            cfg_path = root / "cfg.json"
            _write_json(cfg_path, cfg)
            splitmod.run_build(config=cfg, config_path=cfg_path, repo_root=root)
            assigns = [
                json.loads(L)
                for L in (
                    root
                    / "data/splits/chichewa_corpus_v0.1/metadata/split_assignments.jsonl"
                )
                .read_text(encoding="utf-8")
                .splitlines()
                if L.strip()
            ]
            self.assertTrue(all(":block:" in a["group_id"] for a in assigns))
            self.assertTrue(
                all(a["source_document_id"] == a["group_id"] for a in assigns)
            )
            self.assertTrue(
                all(a["assignment_method"] == "sha256_group_hash" for a in assigns)
            )


class TestRealCorpusReadiness(unittest.TestCase):
    def test_real_config_paths_exist(self) -> None:
        cfg_path = REPO_ROOT / "configs/data/split_v0_1.json"
        self.assertTrue(cfg_path.is_file())
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(cfg["proportions"]["train"], 0.8)
        corpus = REPO_ROOT / cfg["processed_corpus_root"]
        self.assertTrue((corpus / "corpus/bible.txt").is_file())
        self.assertTrue((corpus / "corpus/wikipedia.txt").is_file())


if __name__ == "__main__":
    unittest.main()
