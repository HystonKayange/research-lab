"""Synthetic tests for offline archived-path auditing; no corpus/model reads."""

import copy
import unittest

from scripts.evaluation.audit_morphology_evaluator_v0_1 import (
    audit_path, difference, indexed, legacy_missing_value_scores, legacy_summary,
    raw_boundaries, research_boundaries, same_score,
)
from src.evaluation.morphology_boundaries_v0_1 import SegmentationError


class TestAuditConventions(unittest.TestCase):
    def test_session_incident_not_erased_by_runner_scope(self):
        incident = {"morphology_holdout_metadata_accessed": True,
                    "holdout_payload_decoded": False, "holdout_evaluation_run": False,
                    "holdout_released": False, "lm_test_accessed": False, "lm_bpc_accessed": False}
        result = research_boundaries(incident)
        self.assertTrue(result["morphology_holdout_accessed"])
        self.assertFalse(result["holdout_payload_decoded"])
        self.assertFalse(result["audit_runner_scope"]["morphology_holdout_metadata_or_payload_accessed"])
        self.assertNotEqual(result["morphology_holdout_status"], "LOCKED / UNTOUCHED")
        for key, value in [("morphology_holdout_metadata_accessed", False),
                           ("holdout_payload_decoded", True), ("holdout_evaluation_run", True),
                           ("holdout_released", True), ("lm_test_accessed", True), ("lm_bpc_accessed", True)]:
            with self.subTest(key=key), self.assertRaises(SegmentationError):
                research_boundaries({**incident, key: value})

    def test_legacy_nulls_are_not_strict_zero_scores(self):
        scores = legacy_missing_value_scores(0, 0, 2)
        self.assertIsNone(scores["boundary_precision"])
        self.assertEqual(scores["boundary_recall"], 0)
        self.assertIsNone(scores["boundary_f1"])
        self.assertIsNone(legacy_missing_value_scores(0, 0, 0)["boundary_jaccard"])

    def test_missing_value_denominators_are_explicit(self):
        rows = [{**legacy_missing_value_scores(1, 0, 1), "exact": False},
                {**legacy_missing_value_scores(0, 0, 1), "exact": False}]
        s = legacy_summary(rows)
        self.assertEqual(s["metric_item_denominators"]["boundary_precision"], 1)
        self.assertEqual(s["metric_item_denominators"]["boundary_recall"], 2)
        self.assertEqual(s["macro"]["boundary_recall"], .25)
        self.assertEqual(legacy_summary([])["exact_match"]["rate"], None)

    def test_raw_offsets_expose_endpoint_artifacts(self):
        self.assertEqual(raw_boundaries(["", "ab", "c", ""]), {0, 2, 3})

    def test_duplicate_ids_fail(self):
        with self.assertRaises(SegmentationError):
            indexed([{"item_id": "x"}, {"item_id": "x"}], "fixture")

    def test_roundoff_is_not_a_semantic_change(self):
        self.assertTrue(same_score(2 / 7, 2 * (1 / 2) * (1 / 5) / ((1 / 2) + (1 / 5))))
        self.assertTrue(same_score(None, None))
        self.assertFalse(same_score(None, 0))
        self.assertIsNone(difference(None, .2))
        self.assertAlmostEqual(difference(.3, .2), .1)


class TestFixedPathAudit(unittest.TestCase):
    def setUp(self):
        self.gold = {
            "a": {"surface_form": "abc", "final_segmentation": "a+bc", "source": "synthetic"},
            "b": {"surface_form": "def", "final_segmentation": "def", "source": "synthetic"},
            "c": {"surface_form": "ghi", "final_segmentation": "g+hi", "source": "synthetic"},
        }
        self.predictions = {
            "a": {"pieces": ["", "a", "bc"], "boundary_precision": .5,
                  "boundary_recall": 1., "boundary_f1": 2 / 3, "exact": False},
            "b": {"pieces": ["", "def"], "boundary_precision": 0.,
                  "boundary_recall": None, "boundary_f1": None, "exact": False},
            "c": {"pieces": ["ghi"], "boundary_precision": None,
                  "boundary_recall": 0., "boundary_f1": None, "exact": False},
        }
        self.archived = {"macro": {"boundary_precision": .25, "boundary_recall": .5,
                                   "boundary_f1": 2 / 3, "boundary_jaccard": 1 / 6,
                                   "exact_match_rate": 0.}}

    def test_cleanup_denominator_effects_and_exact_changes(self):
        before = copy.deepcopy((self.gold, self.predictions, self.archived))
        r = audit_path(self.gold, self.predictions, self.archived, "synthetic fixed paths")
        self.assertEqual((self.gold, self.predictions, self.archived), before)
        self.assertEqual(r["normalization_only_legacy_nulls"]["macro"]["boundary_f1"], 1)
        self.assertAlmostEqual(r["strict"]["macro"]["boundary_f1"], 2 / 3)
        self.assertEqual(r["strict"]["metric_item_denominators"]["boundary_f1"], 3)
        self.assertEqual(r["strict"]["exact_match"]["count"], 2)
        self.assertEqual(r["items"][0]["noninternal_legacy_offsets_removed"], [0])
        self.assertFalse(r["selection_changed"])

    def test_id_mismatch_rejected(self):
        del self.predictions["b"]
        with self.assertRaises(SegmentationError):
            audit_path(self.gold, self.predictions, self.archived, "missing ID")

    def test_corrupted_archive_rejected(self):
        self.predictions["a"]["boundary_f1"] = .9
        with self.assertRaises(SegmentationError):
            audit_path(self.gold, self.predictions, self.archived, "bad metric")

    def test_corrupted_aggregate_rejected(self):
        self.archived["macro"]["boundary_f1"] = .9
        with self.assertRaises(SegmentationError):
            audit_path(self.gold, self.predictions, self.archived, "bad aggregate")

    def test_invalid_reconstruction_not_silently_dropped(self):
        self.predictions["a"]["pieces"] = ["ab"]
        with self.assertRaises(SegmentationError):
            audit_path(self.gold, self.predictions, self.archived, "bad reconstruction")


if __name__ == "__main__":
    unittest.main()
