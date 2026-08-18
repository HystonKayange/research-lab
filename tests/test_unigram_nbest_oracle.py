"""Unit tests for the analysis-only Unigram n-best oracle.

Does not open morphology holdout, LM test, or train a tokenizer.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tokenizers.statbound.metrics import boundary_metrics
from src.tokenizers.statbound.nbest_oracle import (
    ScoredCandidate,
    assign_unigram_ranks,
    classify_oracle_change,
    compare_f1,
    cut_zone,
    defined_correlations,
    family_decision,
    gold_miss_zone_counts,
    micro_boundary_metrics,
    oracle_sort_key,
    pearson,
    pick_compat_oracle,
    pick_oracle,
    restricted_rank_oracle,
    selection_f1,
    spearman,
)


def cand(
    pieces: list[str],
    gold: list[str],
    *,
    unigram_score: float,
    unigram_rank: int,
    is_s0: bool,
    compat: float | None,
) -> ScoredCandidate:
    return ScoredCandidate(
        pieces=tuple(pieces),
        raw_pieces=tuple(pieces),
        unigram_score=unigram_score,
        unigram_rank=unigram_rank,
        is_s0=is_s0,
        compat=compat,
        metrics=boundary_metrics(gold, pieces),
    )


class TestSelectionF1(unittest.TestCase):
    def test_exact_whole_word_counts_as_one(self) -> None:
        m = boundary_metrics(["abcd"], ["abcd"])
        self.assertIsNone(m["boundary_f1"])
        self.assertTrue(m["exact_segmentation_match"])
        self.assertEqual(selection_f1(m), 1.0)

    def test_undefined_non_exact_is_worst(self) -> None:
        m = boundary_metrics(["abcd"], ["a", "bcd"])
        self.assertIsNone(m["boundary_f1"])
        self.assertFalse(m["exact_segmentation_match"])
        self.assertEqual(selection_f1(m), -1.0)

    def test_numeric_f1_preserved(self) -> None:
        m = boundary_metrics(["a", "b", "cd"], ["ab", "cd"])
        self.assertAlmostEqual(selection_f1(m), m["boundary_f1"])


class TestOraclePick(unittest.TestCase):
    def test_higher_f1_wins(self) -> None:
        gold = ["a", "b", "cd"]
        s0 = cand(["abcd"], gold, unigram_score=0.0, unigram_rank=1, is_s0=True, compat=0.0)
        better = cand(["a", "bcd"], gold, unigram_score=-5.0, unigram_rank=4, is_s0=False, compat=0.2)
        best = cand(["a", "b", "cd"], gold, unigram_score=-8.0, unigram_rank=8, is_s0=False, compat=-0.1)
        chosen = pick_oracle([s0, better, best])
        self.assertEqual(list(chosen.pieces), gold)

    def test_f1_tie_prefers_s0(self) -> None:
        gold = ["ab", "cd"]
        s0 = cand(["ab", "cd"], gold, unigram_score=-1.0, unigram_rank=1, is_s0=True, compat=0.1)
        alt = cand(["ab", "cd"], gold, unigram_score=-1.0, unigram_rank=2, is_s0=False, compat=0.9)
        chosen = pick_oracle([alt, s0])
        self.assertTrue(chosen.is_s0)

    def test_f1_tie_then_better_rank(self) -> None:
        gold = ["a", "bcd"]
        a = cand(["a", "bcd"], gold, unigram_score=-3.0, unigram_rank=5, is_s0=False, compat=0.0)
        b = cand(["a", "bcd"], gold, unigram_score=-4.0, unigram_rank=3, is_s0=False, compat=0.0)
        chosen = pick_oracle([a, b])
        self.assertEqual(chosen.unigram_rank, 3)

    def test_compat_oracle_ignores_f1(self) -> None:
        gold = ["a", "b", "cd"]
        s0 = cand(["abcd"], gold, unigram_score=0.0, unigram_rank=1, is_s0=True, compat=0.1)
        high_compat = cand(["ab", "cd"], gold, unigram_score=-2.0, unigram_rank=2, is_s0=False, compat=0.8)
        gold_cand = cand(["a", "b", "cd"], gold, unigram_score=-6.0, unigram_rank=6, is_s0=False, compat=0.2)
        chosen = pick_compat_oracle([s0, high_compat, gold_cand])
        self.assertEqual(list(chosen.pieces), ["ab", "cd"])

    def test_compat_tie_prefers_s0(self) -> None:
        gold = ["a", "bcd"]
        s0 = cand(["a", "bcd"], gold, unigram_score=-1.0, unigram_rank=1, is_s0=True, compat=0.4)
        alt = cand(["ab", "cd"], gold, unigram_score=-1.1, unigram_rank=2, is_s0=False, compat=0.4)
        chosen = pick_compat_oracle([alt, s0])
        self.assertTrue(chosen.is_s0)

    def test_restricted_rank_cannot_use_deep_gold(self) -> None:
        gold = ["a", "b", "cd"]
        s0 = cand(["abcd"], gold, unigram_score=0.0, unigram_rank=1, is_s0=True, compat=0.0)
        mid = cand(["a", "bcd"], gold, unigram_score=-2.0, unigram_rank=3, is_s0=False, compat=0.0)
        deep = cand(["a", "b", "cd"], gold, unigram_score=-9.0, unigram_rank=10, is_s0=False, compat=0.0)
        chosen = restricted_rank_oracle([s0, mid, deep], max_rank=4)
        self.assertEqual(list(chosen.pieces), ["a", "bcd"])
        deep_ok = restricted_rank_oracle([s0, mid, deep], max_rank=16)
        self.assertEqual(list(deep_ok.pieces), gold)


class TestRanksAndStats(unittest.TestCase):
    def test_s0_wins_score_tie_for_rank_one(self) -> None:
        ranks = assign_unigram_ranks(
            [
                (("a", "b"), -1.0, False),
                (("ab",), -1.0, True),
                (("a", "bc"), -2.0, False),
            ]
        )
        self.assertEqual(ranks, [2, 1, 3])

    def test_micro_f1(self) -> None:
        # item1 gold {1,2} pred {2}; item2 gold {3} pred {3}
        pairs = [(["a", "b", "cd"], ["ab", "cd"]), (["abc", "d"], ["abc", "d"])]
        m = micro_boundary_metrics(pairs)
        self.assertEqual(m["tp"], 2)
        self.assertEqual(m["fp"], 0)
        self.assertEqual(m["fn"], 1)
        self.assertAlmostEqual(m["boundary_precision"], 1.0)
        self.assertAlmostEqual(m["boundary_recall"], 2.0 / 3.0)

    def test_pearson_perfect(self) -> None:
        self.assertAlmostEqual(pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]), 1.0)
        self.assertIsNone(pearson([1.0, 1.0, 1.0], [2.0, 3.0, 4.0]))

    def test_spearman_monotonic(self) -> None:
        rho = spearman([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 40.0, 80.0])
        self.assertIsNotNone(rho)
        self.assertGreater(rho, 0.99)

    def test_defined_correlations_skips_undefined_f1(self) -> None:
        gold = ["abcd"]
        cands = [
            cand(["abcd"], gold, unigram_score=0.0, unigram_rank=1, is_s0=True, compat=0.0),
            cand(["a", "bcd"], gold, unigram_score=-1.0, unigram_rank=2, is_s0=False, compat=0.5),
        ]
        out = defined_correlations(cands)
        self.assertEqual(out["n_pairs"], 0)

    def test_compare_f1(self) -> None:
        self.assertEqual(compare_f1(0.8, 0.5), "better")
        self.assertEqual(compare_f1(0.2, 0.2), "tied")
        self.assertEqual(compare_f1(None, 0.5), "undefined")


class TestFamilyDecision(unittest.TestCase):
    def test_ceiling_too_low(self) -> None:
        d = family_decision(
            oracle_delta_macro_f1=0.02,
            n_strictly_better_f1=80,
            n_better_with_pos_compat=70,
        )
        self.assertEqual(d["code"], "abandon_reranking_generator_ceiling")
        self.assertFalse(d["chooses_alpha"])

    def test_wrong_signal(self) -> None:
        d = family_decision(
            oracle_delta_macro_f1=0.08,
            n_strictly_better_f1=100,
            n_better_with_pos_compat=20,
        )
        self.assertEqual(d["code"], "do_not_calibrate_wrong_signal")

    def test_relbound_warranted(self) -> None:
        d = family_decision(
            oracle_delta_macro_f1=0.08,
            n_strictly_better_f1=100,
            n_better_with_pos_compat=60,
        )
        self.assertEqual(d["code"], "relbound_v2_warranted")
        self.assertFalse(d["uses_gold_as_training_signal"])

    def test_cut_zone_edges(self) -> None:
        self.assertEqual(cut_zone(10, 1), "left_edge")
        self.assertEqual(cut_zone(10, 4), "left_edge")
        self.assertEqual(cut_zone(10, 8), "right_edge")
        self.assertEqual(cut_zone(10, 9), "right_edge")
        self.assertEqual(cut_zone(10, 5), "internal")

    def test_gold_miss_zones(self) -> None:
        # gold A|na|li|gaw|a bounds {1,3,5,8}; Unigram Anali|gawa has {5}
        counts = gold_miss_zone_counts(
            "Analigawa",
            ["A", "na", "li", "gaw", "a"],
            ["Anali", "gawa"],
        )
        self.assertEqual(counts["left_edge"], 2)  # 1, 3
        self.assertEqual(counts["right_edge"], 1)  # 8
        self.assertEqual(counts["internal"], 0)
        self.assertEqual(counts["total"], 3)

    def test_classify_clean_prefix(self) -> None:
        label = classify_oracle_change(
            "Analigawa",
            ["A", "na", "li", "gaw", "a"],
            ["Anali", "gawa"],
            ["A", "na", "li", "gawa"],
        )
        self.assertEqual(label, "clean_prefix")

    def test_classify_junk_fp(self) -> None:
        label = classify_oracle_change(
            "nditenga",
            ["ndi", "teng", "a"],
            ["ndi", "tenga"],
            ["ndi", "te", "ng", "a"],
        )
        self.assertEqual(label, "junk_fp")

    def test_oracle_sort_key_is_total_order(self) -> None:
        gold = ["a", "b"]
        a = cand(["a", "b"], gold, unigram_score=-1.0, unigram_rank=2, is_s0=False, compat=0.0)
        b = cand(["ab"], gold, unigram_score=0.0, unigram_rank=1, is_s0=True, compat=0.0)
        self.assertNotEqual(oracle_sort_key(a), oracle_sort_key(b))


if __name__ == "__main__":
    unittest.main()
