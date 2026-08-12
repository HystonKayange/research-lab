#!/usr/bin/env python3
"""Unit tests for scripts/data/analyze_residual_corpus.py."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DATA = REPO_ROOT / "scripts" / "data"
sys.path.insert(0, str(SCRIPTS_DATA))

import analyze_residual_corpus as residual  # noqa: E402
from audit_sources import key_casefold_ws, key_exact, key_ws_normalized  # noqa: E402


def _cfg(**overrides) -> dict:
    base = {
        "version": "test",
        "subtraction_comparison_mode": "whitespace_normalized",
        "case_fold_diagnostic": True,
        "use_casefold_for_residual": False,
        "short_line_threshold": 10,
        "long_line_threshold": 40,
        "sample_count": 3,
        "max_examples_per_category": 5,
        "excerpt_length": 50,
        "random_seed": 11,
        "max_repeated_lines_report": 5,
        "percentiles": [50, 90, 95, 99],
        "chichewa_chars": ["ŵ", "Ŵ"],
        "unusual_codepoint_min": 256,
        "max_unusual_codepoints_report": 10,
        "replacement_char": "\ufffd",
        "write_candidate_file": False,
        "language_signal": {"min_matches_for_signal": 2},
        "chichewa_signal_terms": ["ndi", "ndipo", "kuti", "mulungu", "anthu"],
        "english_signal_terms": ["the", "and", "of", "to", "in", "is", "was"],
        "german_signal_terms": ["der", "die", "das", "und", "ist", "von"],
        "boilerplate_patterns": [
            {
                "id": "category_prefix",
                "description": "Category",
                "pattern": "Category\\s*:",
                "flags": "i",
            },
            {
                "id": "url_http",
                "description": "URL",
                "pattern": "https?://",
                "flags": "i",
            },
        ],
        "source_paths": {
            "bible": "data/raw/bible/bible_clean.txt",
            "wikipedia": "data/raw/wikipedia/wiki_clean.txt",
            "existing_corpus": "data/raw/existing_corpus/chichewa_corpus.txt",
        },
        "candidate_file_header": ["# HEADER", ""],
        "term_list_disclaimer": "test disclaimer",
    }
    base.update(overrides)
    return base


class TestExactSubtraction(unittest.TestCase):
    def test_exact_classification(self) -> None:
        bible = ["Bible line one", "Shared both"]
        wiki = ["Wiki line one", "Shared both"]
        corpus = [
            "Bible line one",
            "Wiki line one",
            "Shared both",
            "Unique residual",
            "",
            "  spaced unique  ",
        ]
        summary = residual.subtraction_summary(
            corpus, bible, wiki, "exact"
        )
        counts = summary["category_counts"]
        self.assertEqual(counts["duplicate_of_bible"], 1)
        self.assertEqual(counts["duplicate_of_wikipedia"], 1)
        self.assertEqual(counts["duplicate_of_both"], 1)
        self.assertEqual(counts["blank"], 1)
        # "Unique residual" + "  spaced unique  " (exact differs from nothing)
        self.assertEqual(counts["unique_candidate"], 2)
        self.assertEqual(counts["unresolved"], 0)


class TestWhitespaceSubtraction(unittest.TestCase):
    def test_whitespace_normalized_matches(self) -> None:
        bible = ["foo   bar"]
        wiki = ["wiki only"]
        corpus = [
            "  foo bar  ",
            "wiki   only",
            "totally unique",
        ]
        summary = residual.subtraction_summary(
            corpus, bible, wiki, "whitespace_normalized"
        )
        c = summary["category_counts"]
        self.assertEqual(c["duplicate_of_bible"], 1)
        self.assertEqual(c["duplicate_of_wikipedia"], 1)
        self.assertEqual(c["unique_candidate"], 1)


class TestCasefoldDiagnostic(unittest.TestCase):
    def test_casefold_matches_where_exact_does_not(self) -> None:
        bible = ["Hello World"]
        wiki = []
        corpus = ["hello world", "HELLO WORLD", "other"]
        exact = residual.subtraction_summary(corpus, bible, wiki, "exact")
        cf = residual.subtraction_summary(
            corpus, bible, wiki, "casefold_whitespace_normalized"
        )
        self.assertEqual(exact["category_counts"]["unique_candidate"], 3)
        self.assertEqual(cf["category_counts"]["duplicate_of_bible"], 2)
        self.assertEqual(cf["category_counts"]["unique_candidate"], 1)


class TestOverlapBoth(unittest.TestCase):
    def test_duplicate_of_both(self) -> None:
        bible = ["common line"]
        wiki = ["common line"]
        corpus = ["common line", "only residual"]
        summary = residual.subtraction_summary(
            corpus, bible, wiki, "exact"
        )
        recs = {r["line_number"]: r["category"] for r in summary["records"]}
        self.assertEqual(recs[1], "duplicate_of_both")
        self.assertEqual(recs[2], "unique_candidate")


class TestLineNumberPreservation(unittest.TestCase):
    def test_line_numbers_1based(self) -> None:
        bible = ["a"]
        wiki = ["b"]
        corpus = ["x", "a", "", "b", "y"]
        summary = residual.subtraction_summary(
            corpus, bible, wiki, "exact"
        )
        numbers = [r["line_number"] for r in summary["records"]]
        self.assertEqual(numbers, [1, 2, 3, 4, 5])
        cats = [r["category"] for r in summary["records"]]
        self.assertEqual(
            cats,
            [
                "unique_candidate",
                "duplicate_of_bible",
                "blank",
                "duplicate_of_wikipedia",
                "unique_candidate",
            ],
        )


class TestEmptyFiles(unittest.TestCase):
    def test_empty_corpus(self) -> None:
        summary = residual.subtraction_summary([], ["a"], ["b"], "exact")
        self.assertEqual(summary["total_lines"], 0)
        self.assertEqual(summary["unique_candidate_lines"], 0)
        self.assertEqual(summary["unique_candidate_percentage_of_total"], 0.0)

    def test_empty_subtractors(self) -> None:
        summary = residual.subtraction_summary(
            ["only line", ""], [], [], "exact"
        )
        self.assertEqual(summary["category_counts"]["unique_candidate"], 1)
        self.assertEqual(summary["category_counts"]["blank"], 1)


class TestUnicodeAndMalformed(unittest.TestCase):
    def test_unicode_keys(self) -> None:
        bible = ["mŵana wanga"]
        wiki = []
        corpus = ["mŵana wanga", "ŵ unique"]
        summary = residual.subtraction_summary(
            corpus, bible, wiki, "exact"
        )
        self.assertEqual(summary["category_counts"]["duplicate_of_bible"], 1)
        self.assertEqual(summary["category_counts"]["unique_candidate"], 1)

    def test_malformed_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            p = Path(tmp_s) / "bad.txt"
            p.write_bytes(b"ok\n\xff\n")
            with self.assertRaises(ValueError) as ctx:
                residual.read_utf8_text(p)
            self.assertIn("Malformed UTF-8", str(ctx.exception))


class TestDeterminismAndIO(unittest.TestCase):
    def _write_fixture(self, root: Path) -> None:
        (root / "data/raw/bible").mkdir(parents=True)
        (root / "data/raw/wikipedia").mkdir(parents=True)
        (root / "data/raw/existing_corpus").mkdir(parents=True)
        (root / "configs/data").mkdir(parents=True)

        bible = "Mulungu ndi anthu kuti.\nShared both lines.\n"
        wiki = "This is the page and the article.\nShared both lines.\nCategory:Test\n"
        corpus = (
            "Mulungu ndi anthu kuti.\n"
            "This is the page and the article.\n"
            "Shared both lines.\n"
            "Unique residual with mulungu ndi anthu kuti more.\n"
            "  Unique residual with mulungu ndi anthu kuti more.  \n"
            "Der und die und das ist von.\n"
            "Category:Residual\n"
            "see https://example.com/x\n"
            "\n"
            "short\n"
            + ("Z" * 50)
            + "\n"
        )
        (root / "data/raw/bible/bible_clean.txt").write_text(
            bible, encoding="utf-8"
        )
        (root / "data/raw/wikipedia/wiki_clean.txt").write_text(
            wiki, encoding="utf-8"
        )
        (root / "data/raw/existing_corpus/chichewa_corpus.txt").write_text(
            corpus, encoding="utf-8"
        )
        cfg = _cfg(
            write_candidate_file=True,
            candidate_output_path="data/interim/existing_corpus/residual_candidates.txt",
        )
        (root / "configs/data/residual_analysis.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def test_end_to_end_raw_unchanged_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            root = Path(tmp_s)
            self._write_fixture(root)

            paths = {
                "bible": root / "data/raw/bible/bible_clean.txt",
                "wikipedia": root / "data/raw/wikipedia/wiki_clean.txt",
                "existing_corpus": root
                / "data/raw/existing_corpus/chichewa_corpus.txt",
            }
            before = {
                k: (p.read_bytes(), hashlib.sha256(p.read_bytes()).hexdigest())
                for k, p in paths.items()
            }

            rc1 = residual.main(
                [
                    "--config",
                    str(root / "configs/data/residual_analysis.json"),
                    "--json-output",
                    str(root / "data/metadata/residual_analysis.json"),
                    "--report-output",
                    str(root / "data/reports/residual_analysis.md"),
                    "--samples-output",
                    str(root / "data/reports/residual_samples.jsonl"),
                    "--repo-root",
                    str(root),
                ]
            )
            self.assertEqual(rc1, 0)

            # Deterministic second run on samples content
            samples1 = (
                root / "data/reports/residual_samples.jsonl"
            ).read_text(encoding="utf-8")
            rc2 = residual.main(
                [
                    "--config",
                    str(root / "configs/data/residual_analysis.json"),
                    "--json-output",
                    str(root / "data/metadata/residual_analysis2.json"),
                    "--report-output",
                    str(root / "data/reports/residual_analysis2.md"),
                    "--samples-output",
                    str(root / "data/reports/residual_samples2.jsonl"),
                    "--repo-root",
                    str(root),
                    "--no-candidate-file",
                ]
            )
            self.assertEqual(rc2, 0)
            samples2 = (
                root / "data/reports/residual_samples2.jsonl"
            ).read_text(encoding="utf-8")
            self.assertEqual(samples1, samples2)

            for k, p in paths.items():
                data = p.read_bytes()
                self.assertEqual(data, before[k][0])
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(), before[k][1]
                )

            result = json.loads(
                (root / "data/metadata/residual_analysis.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(result["raw_files_unchanged"])
            self.assertIn("exact", result["decompositions"])
            self.assertIn(
                "whitespace_normalized", result["decompositions"]
            )
            self.assertIn(
                "casefold_whitespace_normalized", result["decompositions"]
            )
            self.assertIn(
                result["recommendation"]["option"],
                result["recommendation"]["allowed_options"],
            )

            # JSONL validity
            for line in samples1.splitlines():
                rec = json.loads(line)
                for key in (
                    "source_id",
                    "line_number",
                    "residual_category",
                    "reason",
                    "excerpt",
                    "metrics",
                ):
                    self.assertIn(key, rec)
                self.assertEqual(rec["residual_category"], "unique_candidate")

            report = (
                root / "data/reports/residual_analysis.md"
            ).read_text(encoding="utf-8")
            self.assertIn("No raw files were modified", report)
            self.assertIn("not approved training data", report.lower())

            cand = (
                root
                / "data/interim/existing_corpus/residual_candidates.txt"
            )
            self.assertTrue(cand.is_file())
            head = cand.read_text(encoding="utf-8")
            self.assertTrue(head.startswith("# HEADER"))

    def test_keys_helpers_used(self) -> None:
        self.assertEqual(key_ws_normalized(" a  b "), "a b")
        self.assertEqual(key_casefold_ws(" Ab "), "ab")
        self.assertEqual(key_exact("x"), "x")


class TestQualityAndRecommendation(unittest.TestCase):
    def test_quality_metrics_on_residual(self) -> None:
        residual_lines = [
            (1, "Mulungu ndi anthu kuti ndipo"),
            (2, "This is the best of the day and the night"),
            (3, "Category:Foo"),
            (4, "same"),
            (5, "same"),
        ]
        q = residual.residual_quality_metrics(residual_lines, _cfg())
        self.assertEqual(q["total_residual_lines"], 5)
        self.assertGreater(q["estimated_word_token_count"], 0)
        self.assertEqual(q["exact_duplicate_line_occurrences"], 2)
        self.assertGreaterEqual(
            q["language_signals"]["counts"]["chichewa_signal"], 1
        )
        self.assertGreaterEqual(
            q["language_signals"]["counts"]["english_signal"], 1
        )
        self.assertGreaterEqual(q["boilerplate_matching_any_pattern"], 1)
        # private fields present for sampling
        self.assertIn("_line_meta", q)

    def test_recommendation_empty(self) -> None:
        primary = {
            "total_lines": 10,
            "unique_candidate_lines": 0,
            "unique_candidate_percentage_of_total": 0.0,
        }
        quality = {
            "language_signals": {
                "counts": {
                    "chichewa_signal": 0,
                    "english_signal": 0,
                    "german_signal": 0,
                    "mixed_signal": 0,
                    "insufficient_signal": 0,
                }
            },
            "boilerplate_matching_any_pattern": 0,
            "url_containing_lines": 0,
            "very_short_lines": 0,
        }
        rec = residual.evidence_based_recommendation(primary, quality)
        self.assertEqual(rec["option"], "discard residual")


if __name__ == "__main__":
    unittest.main()
