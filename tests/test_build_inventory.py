#!/usr/bin/env python3
"""Lightweight tests for scripts/data/build_inventory.py.

Uses the standard library unittest runner only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path so we can import the script module
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DATA = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS_DATA))

import build_inventory as bi  # noqa: E402


class TestSha256(unittest.TestCase):
    def test_sha256_file_matches_hashlib(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.txt"
            content = b"Chichewa test payload\nline two\n"
            p.write_bytes(content)
            expected = hashlib.sha256(content).hexdigest()
            self.assertEqual(bi.sha256_file(p), expected)

    def test_sha256_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.txt"
            p.write_bytes(b"")
            self.assertEqual(
                bi.sha256_file(p),
                hashlib.sha256(b"").hexdigest(),
            )


class TestDiscovery(unittest.TestCase):
    def test_recursive_file_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            (raw / "a").mkdir(parents=True)
            (raw / "b" / "nested").mkdir(parents=True)
            (raw / "a" / "one.txt").write_text("one\n", encoding="utf-8")
            (raw / "b" / "nested" / "two.txt").write_text("two\n", encoding="utf-8")
            (raw / "README.md").write_text("skip me\n", encoding="utf-8")
            (raw / ".hidden").write_text("skip\n", encoding="utf-8")

            found = bi.discover_files(raw)
            names = sorted(p.name for p in found)
            self.assertEqual(names, ["one.txt", "two.txt"])

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir()
            found = bi.discover_files(raw)
            self.assertEqual(found, [])

            inv = bi.build_inventory(raw, repo_root=Path(tmp))
            self.assertEqual(inv["file_count"], 0)
            self.assertEqual(inv["files"], [])
            self.assertEqual(inv["totals"]["size_bytes"], 0)

    def test_missing_directory_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist"
            with self.assertRaises(FileNotFoundError):
                bi.discover_files(missing)


class TestCounts(unittest.TestCase):
    def test_line_and_character_counts(self) -> None:
        # Three lines ending with newline → wc -l == 3
        raw = "alpha\nbeta\ngamma\n".encode("utf-8")
        line_count, char_count = bi.count_lines_and_chars(raw, "utf-8")
        self.assertEqual(line_count, 3)
        self.assertEqual(char_count, len("alpha\nbeta\ngamma\n"))

    def test_utf8_multibyte_characters(self) -> None:
        # ŵ is common in Chichewa orthography (U+0175)
        text = "mŵana\n"
        raw = text.encode("utf-8")
        self.assertGreater(len(raw), len(text))  # multi-byte
        line_count, char_count = bi.count_lines_and_chars(raw, "utf-8")
        self.assertEqual(line_count, 1)
        self.assertEqual(char_count, len(text))


class TestInventoryJson(unittest.TestCase):
    def test_valid_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "bible"
            raw.mkdir(parents=True)
            content = b"line1\nline2\n"
            f = raw / "sample.txt"
            f.write_bytes(content)

            inv = bi.build_inventory(root / "raw", repo_root=root)
            out = root / "inventory.json"
            bi.write_inventory(inv, out)

            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("files", loaded)
            self.assertIn("totals", loaded)
            self.assertIn("inventory_generated_at", loaded)
            self.assertEqual(loaded["file_count"], 1)

            rec = loaded["files"][0]
            for key in (
                "source_id",
                "relative_path",
                "filename",
                "size_bytes",
                "line_count",
                "character_count",
                "sha256",
                "encoding",
                "modification_timestamp",
            ):
                self.assertIn(key, rec)

            self.assertEqual(rec["source_id"], "bible")
            self.assertEqual(rec["filename"], "sample.txt")
            self.assertEqual(rec["size_bytes"], len(content))
            self.assertEqual(rec["line_count"], 2)
            self.assertEqual(rec["sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(rec["encoding"], "utf-8")
            self.assertEqual(loaded["totals"]["size_bytes"], len(content))

    def test_source_files_remain_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "raw" / "existing_corpus"
            raw_dir.mkdir(parents=True)
            target = raw_dir / "corpus.txt"
            original = b"immutable raw bytes\n\xff never mutate\n"
            # Use pure UTF-8 content so encoding detection is clean; still verify bytes
            original = "immutable raw bytes\nmŵana wanga\n".encode("utf-8")
            target.write_bytes(original)
            before_hash = hashlib.sha256(original).hexdigest()
            before_mtime = target.stat().st_mtime_ns

            inv = bi.build_inventory(root / "raw", repo_root=root)
            out = root / "meta" / "inventory.json"
            bi.write_inventory(inv, out)

            after = target.read_bytes()
            after_hash = hashlib.sha256(after).hexdigest()
            self.assertEqual(after, original)
            self.assertEqual(after_hash, before_hash)
            self.assertEqual(target.stat().st_mtime_ns, before_mtime)
            self.assertEqual(inv["files"][0]["sha256"], before_hash)

    def test_cli_main_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw" / "wikipedia"
            raw.mkdir(parents=True)
            (raw / "wiki.txt").write_bytes(b"wiki line\n")
            out = root / "inventory.json"
            rc = bi.main(
                [
                    "--raw-dir",
                    str(root / "raw"),
                    "--output",
                    str(out),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out.is_file())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["file_count"], 1)

    def test_cli_missing_raw_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc = bi.main(
                [
                    "--raw-dir",
                    str(root / "missing"),
                    "--output",
                    str(root / "out.json"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc, 1)


class TestEncodingDetection(unittest.TestCase):
    def test_utf8(self) -> None:
        self.assertEqual(bi.detect_encoding("hello\n".encode("utf-8")), "utf-8")

    def test_utf8_bom(self) -> None:
        raw = b"\xef\xbb\xbf" + "hello\n".encode("utf-8")
        self.assertEqual(bi.detect_encoding(raw), "utf-8-sig")


if __name__ == "__main__":
    unittest.main()
