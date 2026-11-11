"""Synthetic contract tests; no benchmark, tokenizer, or corpus inputs."""

from __future__ import annotations

import copy
import itertools
import unittest

from src.evaluation.morphology_boundaries_v0_1 import (
    EVALUATOR_ID, SegmentationError, aggregate_items, evaluate_item,
    scores_from_counts, validate_internal_boundaries,
)


class TestValidation(unittest.TestCase):
    def test_prediction_empty_pieces_removed_without_input_mutation(self):
        g, p = ["ab", "cd"], ["", "ab", "", "cd", ""]
        before = copy.deepcopy((g, p))
        r = evaluate_item("abcd", g, p)
        self.assertEqual(r["prediction_boundaries"], [2])
        self.assertEqual(r["n_empty_prediction_pieces_removed"], 3)
        self.assertTrue(r["exact_segmentation_match"])
        self.assertFalse(r["raw_piece_list_exact_match"])
        self.assertEqual((g, p), before)

    def test_bad_gold_rejected(self):
        for g in ([], ["", "ab"], ["a", "c"], "a+b", ["a", 1]):
            with self.subTest(gold=g), self.assertRaises(SegmentationError):
                evaluate_item("ab", g, ["ab"])

    def test_bad_prediction_rejected(self):
        for p in ([], [""], ["ac"], "ab", ["a", None]):
            with self.subTest(prediction=p), self.assertRaises(SegmentationError):
                evaluate_item("ab", ["ab"], p)

    def test_bad_surface_rejected(self):
        for surface in ("", None, 123):
            with self.subTest(surface=surface), self.assertRaises(SegmentationError):
                evaluate_item(surface, ["a"], ["a"])

    def test_unicode_case_apostrophe_and_whitespace_not_normalized(self):
        for word, wrong in [("ŵa", "w\u0302a"), ("M’na", "M'na"), ("Ndi", "ndi"), ("ab ", "ab")]:
            with self.subTest(surface=word), self.assertRaises(SegmentationError):
                evaluate_item(word, [word], [wrong])

    def test_unicode_codepoint_offsets(self):
        r = evaluate_item("M’nthaŵi", ["M’", "nthaŵi"], ["", "M’", "nthaŵi"])
        self.assertEqual(r["gold_boundaries"], [2])
        self.assertEqual(r["boundary_f1"], 1)

    def test_literal_word_start_marker_not_stripped(self):
        r = evaluate_item("▁ab", ["▁", "ab"], ["▁", "ab"])
        self.assertEqual(r["prediction_boundaries"], [1])
        with self.assertRaises(SegmentationError):
            evaluate_item("ab", ["ab"], ["▁ab"])

    def test_internal_offset_validation(self):
        for offsets in ([0], [4], [-1], [5], [True], [1.0], ["1"], [2, 2]):
            with self.subTest(offsets=offsets), self.assertRaises(SegmentationError):
                validate_internal_boundaries("abcd", offsets)
        self.assertEqual(validate_internal_boundaries("abcd", [3, 1]), frozenset({1, 3}))


class TestZeroCases(unittest.TestCase):
    def test_whole_word_correct(self):
        r = evaluate_item("ab", ["ab"], ["", "ab"])
        for key in ("boundary_precision", "boundary_recall", "boundary_f1", "boundary_jaccard"):
            self.assertEqual(r[key], 1)
        self.assertEqual(r["zero_boundary_case"], "both_empty")

    def test_gold_only_has_boundaries(self):
        r = evaluate_item("ab", ["a", "b"], ["ab"])
        self.assertEqual((r["tp"], r["fp"], r["fn"]), (0, 0, 1))
        self.assertEqual(r["boundary_precision"], 0)
        self.assertEqual(r["boundary_recall"], 0)
        self.assertEqual(r["boundary_f1"], 0)

    def test_prediction_only_has_boundaries(self):
        r = evaluate_item("ab", ["ab"], ["a", "b"])
        self.assertEqual((r["tp"], r["fp"], r["fn"]), (0, 1, 0))
        self.assertEqual(r["boundary_precision"], 0)
        self.assertEqual(r["boundary_recall"], 0)
        self.assertEqual(r["boundary_f1"], 0)

    def test_partial_overlap(self):
        r = evaluate_item("abcde", ["a", "b", "cde"], ["ab", "c", "de"])
        self.assertEqual((r["tp"], r["fp"], r["fn"]), (1, 1, 1))
        self.assertEqual(r["boundary_f1"], .5)

    def test_disjoint_nonempty_sets(self):
        self.assertEqual(evaluate_item("abc", ["a", "bc"], ["ab", "c"])["boundary_f1"], 0)

    def test_invalid_counts(self):
        for counts in ((-1, 0, 0), (0, True, 1), (1.0, 0, 0)):
            with self.subTest(counts=counts), self.assertRaises(SegmentationError):
                scores_from_counts(*counts)


class TestAggregation(unittest.TestCase):
    def test_empty_collection_is_not_perfect(self):
        out = aggregate_items([])
        self.assertEqual(out["n_items"], 0)
        self.assertIsNone(out["macro"]["boundary_f1"])
        self.assertIsNone(out["micro"]["boundary_f1"])
        self.assertIsNone(out["exact_match"]["rate"])

    def test_all_items_use_same_macro_denominator(self):
        rows = [evaluate_item("ab", ["a", "b"], ["ab"]), evaluate_item("cd", ["cd"], ["cd"])]
        out = aggregate_items(rows)
        self.assertTrue(all(n == 2 for n in out["metric_item_denominators"].values()))
        self.assertEqual(out["macro"]["boundary_f1"], .5)
        self.assertEqual(out["micro"]["boundary_f1"], 0)
        self.assertEqual(out["strata"]["gold_segmented"]["n_items"], 1)
        self.assertEqual(out["strata"]["gold_whole_word"]["n_items"], 1)

    def test_pooled_counts_not_mean_of_item_scores(self):
        rows = [evaluate_item("abcd", ["a", "b", "cd"], ["ab", "cd"]), evaluate_item("xy", ["x", "y"], ["x", "y"])]
        out = aggregate_items(rows)
        self.assertEqual(out["micro"]["tp"], 2)
        self.assertEqual(out["micro"]["fn"], 1)
        self.assertAlmostEqual(out["micro"]["boundary_f1"], .8)
        self.assertAlmostEqual(out["macro"]["boundary_f1"], (2/3 + 1)/2)

    def test_other_evaluator_results_rejected(self):
        r = evaluate_item("ab", ["ab"], ["ab"])
        r["evaluator_id"] = "legacy"
        with self.assertRaises(SegmentationError):
            aggregate_items([r])

    def test_all_whole_word_batch(self):
        out = aggregate_items([evaluate_item("a", ["a"], ["a"]), evaluate_item("b", ["b"], ["b"])])
        self.assertEqual(out["micro"]["boundary_f1"], 1)
        self.assertEqual(out["macro"]["boundary_f1"], 1)
        self.assertEqual(out["strata"]["gold_segmented"]["n_items"], 0)


class TestExhaustiveSmallPartitions(unittest.TestCase):
    def test_all_partitions_counts_symmetry_and_empty_invariance(self):
        word = "abcde"
        def pieces(cuts):
            points = [0, *cuts, len(word)]
            return [word[a:b] for a, b in zip(points, points[1:])]
        partitions = [pieces([i+1 for i, flag in enumerate(flags) if flag]) for flags in itertools.product([False, True], repeat=4)]
        for g in partitions:
            for p in partitions:
                r = evaluate_item(word, g, p)
                reverse = evaluate_item(word, p, g)
                self.assertEqual(r["tp"] + r["fn"], len(g)-1)
                self.assertEqual(r["tp"] + r["fp"], len(p)-1)
                self.assertEqual(r["boundary_f1"], reverse["boundary_f1"])
                self.assertEqual(r["exact_segmentation_match"], r["gold_boundaries"] == r["prediction_boundaries"])
                padded = evaluate_item(word, g, ["", *p, ""])
                for key in ("tp", "fp", "fn", "boundary_precision", "boundary_recall", "boundary_f1", "exact_segmentation_match"):
                    self.assertEqual(r[key], padded[key])
                self.assertEqual(r["evaluator_id"], EVALUATOR_ID)


if __name__ == "__main__":
    unittest.main()
