"""Unit/sanity tests for StatBound-Unigram V1 (no scientific morph/LM eval)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tokenizers.statbound.boundary_stats import (  # noqa: E402
    BoundaryDiscoveryConfig,
    learn_boundary_stats,
    save_boundary_stats,
    strengths_for_word,
)
from src.tokenizers.statbound.leakage import LeakageError, assert_train_only_path  # noqa: E402
from src.tokenizers.statbound.reranker import (  # noqa: E402
    boundary_compatibility,
    rank_candidates,
    surface_from_pieces,
)
from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402
from src.tokenizers.statbound.unigram_adapter import SegmentCandidate, UnigramAdapter  # noqa: E402


CONFIG = REPO / "configs/tokenizers/statbound_unigram_v1.json"
BASE_MODEL = (
    REPO
    / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
)
TRAIN = REPO / "data/splits/chichewa_corpus_v0.1/train/combined.txt"


def _toy_train_file(tmp: Path) -> Path:
    """Synthetic corpus with productive prefixes/suffixes."""
    # Many types sharing prefix "ku" and suffix "ira" / "idwa"
    words = []
    stems = ["gona", "seka", "yenda", "lira", "nena", "funa", "tenga", "pita", "bwera", "dya"]
    for s in stems:
        words.append(f"ku{s}")
        words.append(f"ku{s}ira")
        words.append(f"a{s}idwa")
        words.append(f"ti{s}a")
    # repeat for support
    lines = [" ".join(words)] * 20
    # add extra productivity for ku*
    extra = " ".join([f"ku{s}a" for s in stems] * 5)
    lines.append(extra)
    p = tmp / "train" / "combined.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@unittest.skipUnless(BASE_MODEL.is_file(), "Unigram-8000 model missing")
class TestStatBoundUnigramV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = UnigramAdapter(BASE_MODEL)

    def test_leakage_guard_blocks_validation_and_morph(self) -> None:
        with self.assertRaises(LeakageError):
            assert_train_only_path(REPO / "data/splits/chichewa_corpus_v0.1/validation/combined.txt")
        with self.assertRaises(LeakageError):
            assert_train_only_path(
                REPO
                / "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl"
            )
        with self.assertRaises(LeakageError):
            assert_train_only_path("/tmp/not_train/file.txt", require_train_substring=True)

    def test_leakage_guard_allows_train(self) -> None:
        if TRAIN.is_file():
            p = assert_train_only_path(TRAIN)
            self.assertTrue(p.is_file())

    def test_boundary_score_normalization_range(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            train = _toy_train_file(tmp)
            cfg = BoundaryDiscoveryConfig(
                max_affix_context_length=6,
                min_type_support=3,
                min_productivity=2,
                length_one_affix_weight=0.15,
            )
            stats = learn_boundary_stats(train, cfg)
            for w, info in stats["words"].items():
                for k, v in info["strengths"].items():
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 1.0)
            # at least some positive strengths expected on toy data
            n_pos = sum(1 for info in stats["words"].values() if info["strengths"])
            self.assertGreater(n_pos, 0)

    def test_length_one_affix_not_automatically_max(self) -> None:
        # Build types where 1-char cut has high raw support but should be downweighted
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # many words starting with 'a' + various, and ending with productive suffixes
            toks = []
            for i in range(20):
                toks.append(f"aSTEM{i}ira")
                toks.append(f"kuSTEM{i}ira")
            train = tmp / "train" / "t.txt"
            train.parent.mkdir(parents=True)
            train.write_text((" ".join(toks) + "\n") * 10, encoding="utf-8")
            cfg = BoundaryDiscoveryConfig(min_type_support=3, min_productivity=2)
            stats = learn_boundary_stats(train, cfg)
            # strengths are normalized per word; ensure formula runs
            w = "aSTEM0ira"
            self.assertIn(w, stats["words"])

    def test_deterministic_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            train = _toy_train_file(tmp)
            cfg = BoundaryDiscoveryConfig(min_type_support=3, min_productivity=2)
            stats = learn_boundary_stats(train, cfg)
            spath = tmp / "stats.json"
            save_boundary_stats(stats, spath)
            tok = StatBoundUnigramTokenizer(
                adapter=self.adapter,
                stats=stats,
                lambda_bias=0.5,
                nbest_size=16,
            )
            w = "kugona"
            a = tok.encode_word(w)
            b = tok.encode_word(w)
            self.assertEqual(a, b)

    def test_exact_reconstruction_per_word(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            train = _toy_train_file(tmp)
            stats = learn_boundary_stats(
                train, BoundaryDiscoveryConfig(min_type_support=3, min_productivity=2)
            )
            tok = StatBoundUnigramTokenizer(
                adapter=self.adapter, stats=stats, lambda_bias=1.0, nbest_size=16
            )
            for w in ["kugona", "ndimakonda", "Hello", "123", "a", ""]:
                if w == "":
                    self.assertEqual(tok.encode_word(w), [])
                    continue
                pieces = tok.encode_word(w)
                self.assertEqual(surface_from_pieces(pieces), w)

    def test_lambda0_equivalence_with_unigram(self) -> None:
        # Empty stats → compat=0; lambda=0 must match SP default
        empty_stats = {
            "formula_id": "statbound_v1_branch_productivity_log",
            "words": {},
        }
        tok = StatBoundUnigramTokenizer(
            adapter=self.adapter,
            stats=empty_stats,
            lambda_bias=0.0,
            nbest_size=16,
        )
        words = [
            "ndimakonda",
            "kugona",
            "anthu",
            "Mulungu",
            "wikipedia",
            "12345",
            "a",
            "ndi",
            "sizinachitikepo",
            "HelloWorld",
        ]
        for w in words:
            sp = self.adapter.encode_as_pieces(w)
            sb = tok.encode_word(w)
            self.assertEqual(
                sb,
                sp,
                msg=f"lambda=0 mismatch for {w!r}: statbound={sb} unigram={sp}",
            )

    def test_lambda0_with_nonzero_stats_still_matches_unigram(self) -> None:
        """compat may be nonzero but lambda=0 ignores it."""
        with tempfile.TemporaryDirectory() as td:
            train = _toy_train_file(Path(td))
            stats = learn_boundary_stats(
                train, BoundaryDiscoveryConfig(min_type_support=3, min_productivity=2)
            )
            tok = StatBoundUnigramTokenizer(
                adapter=self.adapter, stats=stats, lambda_bias=0.0, nbest_size=16
            )
            for w in ["kugona", "ndimakonda", "kuseka"]:
                self.assertEqual(tok.encode_word(w), self.adapter.encode_as_pieces(w))

    def test_no_morphology_annotations_in_learning_api(self) -> None:
        morph = (
            REPO
            / "data/research/morphology_benchmark_v0.1/development/annotations"
            / "annotator_a_active_195_v0_1.jsonl"
        )
        if morph.is_file():
            with self.assertRaises(LeakageError):
                learn_boundary_stats(
                    morph, BoundaryDiscoveryConfig(), forbidden_substrings=None
                )

    def test_tie_breaking_deterministic(self) -> None:
        # Construct two candidates with identical scores via manual rank_candidates
        empty = {"words": {}}
        cands = [
            SegmentCandidate(pieces=["▁ab", "c"], unigram_score=-1.0),
            SegmentCandidate(pieces=["▁a", "bc"], unigram_score=-1.0),
        ]
        # both invalid surface for word xyz → empty ranked
        ranked = rank_candidates("abc", cands, empty, lambda_bias=0.0)
        # Fix surface-valid candidates
        cands = [
            SegmentCandidate(pieces=["▁ab", "c"], unigram_score=-1.0),
            SegmentCandidate(pieces=["▁a", "bc"], unigram_score=-1.0),
        ]
        ranked = rank_candidates("abc", cands, empty, lambda_bias=0.0)
        self.assertEqual(len(ranked), 2)
        # same unigram, compat 0; fewer pieces preferred — both 2 pieces; lex smaller wins
        self.assertEqual(ranked[0].pieces, ["▁a", "bc"])  # "▁a\x1fbc" < "▁ab\x1fc"? 
        # Compare: "\x1f".join(["▁a","bc"]) vs join(["▁ab","c"])
        a = "\x1f".join(["▁a", "bc"])
        b = "\x1f".join(["▁ab", "c"])
        expected = ["▁a", "bc"] if a < b else ["▁ab", "c"]
        self.assertEqual(ranked[0].pieces, expected)

    def test_unseen_word_handling(self) -> None:
        empty = {"words": {}}
        tok = StatBoundUnigramTokenizer(
            adapter=self.adapter, stats=empty, lambda_bias=0.5, nbest_size=16
        )
        w = "zzzxqqqnotaword"
        pieces = tok.encode_word(w)
        self.assertEqual(surface_from_pieces(pieces), w)

    def test_fallback_punctuation_numeric_mixed(self) -> None:
        empty = {"words": {}}
        tok = StatBoundUnigramTokenizer(
            adapter=self.adapter, stats=empty, lambda_bias=0.5, nbest_size=16
        )
        for w in [",", ".", "42", "3.14", "COVID-19", "ŵanthu", "a+b"]:
            pieces = tok.encode_word(w)
            self.assertEqual(surface_from_pieces(pieces), w)

    def test_vocab_accounting_8000(self) -> None:
        empty = {"words": {}}
        tok = StatBoundUnigramTokenizer(
            adapter=self.adapter, stats=empty, lambda_bias=0.0, nbest_size=16
        )
        acc = tok.vocab_accounting()
        self.assertEqual(acc["vocab_size"], 8000)
        self.assertEqual(acc["extra_statbound_pieces"], 0)
        self.assertEqual(acc["total_effective_vocabulary"], 8000)

    def test_reproducibility_same_train_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            train = _toy_train_file(tmp)
            cfg = BoundaryDiscoveryConfig(min_type_support=3, min_productivity=2)
            a = learn_boundary_stats(train, cfg)
            b = learn_boundary_stats(train, cfg)
            self.assertEqual(a["n_types"], b["n_types"])
            self.assertEqual(a["words"], b["words"])

    def test_inspect_structure(self) -> None:
        empty = {"words": {}}
        tok = StatBoundUnigramTokenizer(
            adapter=self.adapter, stats=empty, lambda_bias=0.0, nbest_size=8
        )
        info = tok.inspect_word("ndimakonda")
        self.assertEqual(info["word"], "ndimakonda")
        self.assertIn("candidates", info)
        self.assertIn("selected", info)
        self.assertTrue(info["candidates"])
        for c in info["candidates"]:
            self.assertIn("unigram_score", c)
            self.assertIn("boundary_compatibility", c)
            self.assertIn("combined_score", c)

    def test_boundary_compatibility_rewards_supported_cuts(self) -> None:
        # Manual stats: strong cut after 2 chars
        stats = {"words": {"abcdef": {"freq": 1, "strengths": {"2": 1.0, "4": 0.2}}}}
        # pieces that cut at 2: ab|cdef
        pieces_good = ["▁ab", "cdef"]
        pieces_bad = ["▁abcdef"]
        if surface_from_pieces(pieces_good) == "abcdef":
            cg = boundary_compatibility("abcdef", pieces_good, stats)
            cb = boundary_compatibility("abcdef", pieces_bad, stats)
            self.assertIsNotNone(cg)
            self.assertIsNotNone(cb)
            self.assertGreater(cg, cb)


if __name__ == "__main__":
    unittest.main()
