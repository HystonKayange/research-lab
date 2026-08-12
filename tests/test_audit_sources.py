#!/usr/bin/env python3
"""Unit tests for scripts/data/audit_sources.py (stdlib unittest)."""

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

import audit_sources as audit  # noqa: E402


def _minimal_config(**overrides) -> dict:
    cfg = {
        "version": "test",
        "short_line_threshold": 10,
        "long_line_threshold": 40,
        "sample_count": 3,
        "excerpt_length": 40,
        "random_seed": 7,
        "max_examples_per_category": 5,
        "max_repeated_lines_report": 5,
        "case_fold_comparison": True,
        "percentiles": [50, 90, 95, 99],
        "chichewa_chars": ["ŵ", "Ŵ"],
        "unusual_codepoint_min": 256,
        "max_unusual_codepoints_report": 20,
        "replacement_char": "\ufffd",
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
        "shingles": {
            "mode": "token",
            "window_size": 3,
            "stride": 1,
            "min_tokens_in_unit": 3,
        },
    }
    cfg.update(overrides)
    return cfg


class TestExcerptAndSample(unittest.TestCase):
    def test_excerpt_truncation(self) -> None:
        text = "a" * 100
        out = audit.excerpt(text, 20)
        self.assertEqual(len(out), 20)
        self.assertTrue(out.endswith("..."))

    def test_excerpt_short(self) -> None:
        self.assertEqual(audit.excerpt("hello", 20), "hello")

    def test_deterministic_sampling(self) -> None:
        items = list(range(50))
        a = audit.deterministic_sample(items, 5, seed=42, salt="x")
        b = audit.deterministic_sample(items, 5, seed=42, salt="x")
        c = audit.deterministic_sample(items, 5, seed=99, salt="x")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(a, sorted(a))  # indices sorted → stable order


class TestStructuralMetrics(unittest.TestCase):
    def test_structural_and_duplicates(self) -> None:
        text = "aaa\nbbb\naaa\n\nccc\n"
        st = audit.structural_stats(text, _minimal_config())
        self.assertEqual(st["total_lines"], 5)
        self.assertEqual(st["blank_lines"], 1)
        self.assertEqual(st["non_empty_lines"], 4)
        self.assertEqual(st["unique_exact_lines"], 3)
        self.assertEqual(st["lines_appearing_more_than_once"], 2)  # two aaa
        self.assertGreater(st["duplicate_line_percentage"], 0)

    def test_empty_file_stats(self) -> None:
        st = audit.structural_stats("", _minimal_config())
        self.assertEqual(st["total_lines"], 0)
        self.assertEqual(st["non_empty_lines"], 0)
        self.assertIsNone(st["min_line_length"])

    def test_url_and_short_long(self) -> None:
        text = "short\n" + ("x" * 50) + "\nsee https://example.com/a\n"
        st = audit.structural_stats(text, _minimal_config(short_line_threshold=10, long_line_threshold=40))
        self.assertEqual(st["very_short_lines"], 1)
        self.assertEqual(st["very_long_lines"], 1)
        self.assertEqual(st["lines_containing_urls"], 1)


class TestOverlapMath(unittest.TestCase):
    def test_jaccard(self) -> None:
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        self.assertAlmostEqual(audit.jaccard(a, b), 2 / 4)

    def test_jaccard_empty(self) -> None:
        self.assertEqual(audit.jaccard(set(), set()), 1.0)

    def test_coverage_asymmetric(self) -> None:
        a = {"1", "2", "3", "4"}
        b = {"1", "2"}
        self.assertAlmostEqual(audit.coverage(a, b), 0.5)
        self.assertAlmostEqual(audit.coverage(b, a), 1.0)

    def test_whitespace_normalized_keys(self) -> None:
        self.assertEqual(
            audit.key_ws_normalized("  foo   bar\t"),
            "foo bar",
        )
        self.assertEqual(
            audit.key_casefold_ws("  Foo   BAR "),
            "foo bar",
        )

    def test_overlap_pair_shared(self) -> None:
        cfg = _minimal_config()
        ua = ["hello world", "unique a", "shared line"]
        ub = ["shared line", "unique b", "  shared   line  "]
        # exact
        exact = audit.overlap_pair(
            "a", ua, "b", ub, audit.key_exact, "exact", cfg
        )
        self.assertEqual(exact["shared_units"], 1)
        # whitespace normalized merges spacing variants
        ws = audit.overlap_pair(
            "a", ua, "b", ub, audit.key_ws_normalized, "whitespace_normalized", cfg
        )
        self.assertGreaterEqual(ws["shared_units"], 1)
        self.assertGreater(ws["coverage_a_by_b"], 0)


class TestLanguageSignal(unittest.TestCase):
    def test_categorization(self) -> None:
        cfg = _minimal_config()
        ny = audit.build_term_pattern(cfg["chichewa_signal_terms"])
        en = audit.build_term_pattern(cfg["english_signal_terms"])
        de = audit.build_term_pattern(cfg["german_signal_terms"])
        min_m = 2

        cat, hits = audit.classify_language_signal(
            "Mulungu ndi anthu kuti",
            ny, en, de, min_m,
        )
        self.assertEqual(cat, "chichewa_signal")
        self.assertGreaterEqual(hits["chichewa"], 2)

        cat, _ = audit.classify_language_signal(
            "This is the best of the day and the night",
            ny, en, de, min_m,
        )
        self.assertEqual(cat, "english_signal")

        cat, _ = audit.classify_language_signal(
            "Der und die und das ist von",
            ny, en, de, min_m,
        )
        self.assertEqual(cat, "german_signal")

        cat, _ = audit.classify_language_signal(
            "xyz",
            ny, en, de, min_m,
        )
        self.assertEqual(cat, "insufficient_signal")


class TestBoilerplate(unittest.TestCase):
    def test_pattern_matching(self) -> None:
        cfg = _minimal_config()
        compiled = audit.compile_boilerplate(cfg["boilerplate_patterns"])
        lines = [
            "normal text",
            "Category:Lincoln, Nebraska",
            "visit https://example.org/x",
        ]
        res = audit.boilerplate_audit(lines, compiled, cfg, "test")
        self.assertEqual(res["category_prefix"]["matching_lines"], 1)
        self.assertEqual(res["url_http"]["matching_lines"], 1)
        self.assertGreaterEqual(res["url_http"]["total_occurrences"], 1)


class TestShinglesAndParagraphs(unittest.TestCase):
    def test_paragraphs(self) -> None:
        lines = ["a", "b", "", "c", "", "", "d", "e"]
        paras = audit.extract_paragraphs(lines)
        self.assertEqual(paras, ["a b", "c", "d e"])

    def test_token_shingles(self) -> None:
        s = audit.shingles_from_text(
            "one two three four five",
            window=3,
            stride=1,
            min_tokens=3,
            mode="token",
        )
        self.assertEqual(
            s,
            ["one two three", "two three four", "three four five"],
        )


class TestRawUnchangedAndIO(unittest.TestCase):
    def _fixture_repo(self, tmp: Path) -> Path:
        raw = tmp / "data" / "raw"
        (raw / "bible").mkdir(parents=True)
        (raw / "wikipedia").mkdir(parents=True)
        (raw / "existing_corpus").mkdir(parents=True)

        bible = (
            "Mulungu ndi anthu kuti dziko.\n"
            "Ndipo Mulungu anati kuti.\n"
            "Shared exact line for overlap.\n"
        )
        wiki = (
            "Mu nkhani\n"
            "Category:Test\n"
            "This is the best of the article and the page.\n"
            "Shared exact line for overlap.\n"
            "see https://example.com/wiki\n"
        )
        corpus = (
            "Der und die und das ist von Berlin.\n"
            "Shared exact line for overlap.\n"
            "Mulungu ndi anthu kuti.\n"
            "  Shared   exact   line   for   overlap.  \n"
        )
        (raw / "bible" / "bible_clean.txt").write_text(bible, encoding="utf-8")
        (raw / "wikipedia" / "wiki_clean.txt").write_text(wiki, encoding="utf-8")
        (raw / "existing_corpus" / "chichewa_corpus.txt").write_text(
            corpus, encoding="utf-8"
        )

        meta = tmp / "data" / "metadata"
        meta.mkdir(parents=True)
        sources = [
            {
                "source_id": "bible",
                "file_path": "data/raw/bible/bible_clean.txt",
                "source_name": "Bible",
            },
            {
                "source_id": "wikipedia",
                "file_path": "data/raw/wikipedia/wiki_clean.txt",
                "source_name": "Wiki",
            },
            {
                "source_id": "existing_corpus",
                "file_path": "data/raw/existing_corpus/chichewa_corpus.txt",
                "source_name": "Corpus",
            },
        ]
        with (meta / "sources.jsonl").open("w", encoding="utf-8") as f:
            for s in sources:
                f.write(json.dumps(s) + "\n")

        cfg_path = tmp / "configs" / "data" / "source_audit.json"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text(json.dumps(_minimal_config()), encoding="utf-8")
        return tmp

    def test_end_to_end_outputs_and_raw_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            tmp = Path(tmp_s)
            self._fixture_repo(tmp)

            paths = {
                "bible": tmp / "data/raw/bible/bible_clean.txt",
                "wikipedia": tmp / "data/raw/wikipedia/wiki_clean.txt",
                "existing_corpus": tmp
                / "data/raw/existing_corpus/chichewa_corpus.txt",
            }
            before = {
                k: (p.read_bytes(), hashlib.sha256(p.read_bytes()).hexdigest())
                for k, p in paths.items()
            }

            rc = audit.main(
                [
                    "--raw-dir",
                    str(tmp / "data/raw"),
                    "--sources",
                    str(tmp / "data/metadata/sources.jsonl"),
                    "--config",
                    str(tmp / "configs/data/source_audit.json"),
                    "--json-output",
                    str(tmp / "data/metadata/source_audit.json"),
                    "--report-output",
                    str(tmp / "data/reports/source_audit.md"),
                    "--samples-output",
                    str(tmp / "data/reports/source_audit_samples.jsonl"),
                    "--eligibility-output",
                    str(tmp / "data/reports/training_eligibility_review.md"),
                    "--repo-root",
                    str(tmp),
                ]
            )
            self.assertEqual(rc, 0)

            for k, p in paths.items():
                after_bytes = p.read_bytes()
                self.assertEqual(after_bytes, before[k][0])
                self.assertEqual(
                    hashlib.sha256(after_bytes).hexdigest(),
                    before[k][1],
                )

            inv = json.loads(
                (tmp / "data/metadata/source_audit.json").read_text(encoding="utf-8")
            )
            self.assertTrue(inv["raw_files_unchanged"])
            self.assertEqual(len(inv["sources"]), 3)
            self.assertIn("bible__vs__existing_corpus", inv["pairwise_overlap"])
            self.assertIn("bible__vs__wikipedia", inv["pairwise_overlap"])
            self.assertIn(
                "existing_corpus__vs__wikipedia", inv["pairwise_overlap"]
            )

            # Shared exact line should appear in overlap
            pair = inv["pairwise_overlap"]["bible__vs__wikipedia"]
            shared = pair["units"]["nonempty_lines"]["exact"]["shared_units"]
            self.assertGreaterEqual(shared, 1)

            # JSONL valid
            samples_path = tmp / "data/reports/source_audit_samples.jsonl"
            self.assertTrue(samples_path.is_file())
            for line in samples_path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                self.assertIn("source_id", rec)
                self.assertIn("reason", rec)
                self.assertIn("excerpt", rec)
                self.assertLessEqual(len(rec["excerpt"]), 40 + 0)  # limit 40

            report = (tmp / "data/reports/source_audit.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("No source content was modified", report)
            self.assertIn("Executive summary", report)

            elig = (
                tmp / "data/reports/training_eligibility_review.md"
            ).read_text(encoding="utf-8")
            self.assertIn("pending human review", elig)

    def test_malformed_utf8_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            tmp = Path(tmp_s)
            p = tmp / "bad.txt"
            p.write_bytes(b"hello \xff world\n")
            with self.assertRaises(ValueError) as ctx:
                audit.read_utf8_text(p)
            self.assertIn("Malformed UTF-8", str(ctx.exception))

    def test_cli_missing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_s:
            tmp = Path(tmp_s)
            rc = audit.main(
                [
                    "--sources",
                    str(tmp / "missing.jsonl"),
                    "--config",
                    str(tmp / "c.json"),
                    "--repo-root",
                    str(tmp),
                ]
            )
            self.assertEqual(rc, 1)


class TestWithinDup(unittest.TestCase):
    def test_within_source(self) -> None:
        lines = ["a", "b", "a", "A"]
        cfg = _minimal_config()
        d = audit.within_source_duplication(lines, ["a b", "a b"], cfg)
        self.assertEqual(d["repeated_exact_lines"], 1)  # "a" repeats
        self.assertGreaterEqual(d["repeated_casefold_lines"], 1)


if __name__ == "__main__":
    unittest.main()
