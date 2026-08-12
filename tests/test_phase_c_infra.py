"""Synthetic infrastructure tests for Phase C harness + boundary_stats verify.

Does NOT touch active-195, self-review, holdout, or LM scientific paths.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tokenizers.statbound.metrics import (  # noqa: E402
    aggregate_boundary_metrics,
    boundary_metrics,
    efficiency_metrics_from_encodings,
    select_lambda_star,
)
from src.tokenizers.statbound.phase_c_harness import (  # noqa: E402
    PhaseCGateError,
    assert_path_allowed_for_phase_c,
    build_lambda_selection_table,
    evaluate_morphology_pairs,
    filter_active_rows,
)
from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402
from src.tokenizers.statbound.unigram_adapter import UnigramAdapter  # noqa: E402
from src.tokenizers.statbound.boundary_stats import (  # noqa: E402
    BoundaryDiscoveryConfig,
    learn_boundary_stats,
    save_boundary_stats,
)
import hashlib

BASE_MODEL = (
    REPO
    / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
)
PROTOCOL = REPO / "configs/tokenizers/statbound_unigram_v1_eval_protocol.json"
EXISTING_STATS = (
    REPO
    / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
)


class TestBoundaryMetricsSynthetic(unittest.TestCase):
    def test_perfect_match(self) -> None:
        m = boundary_metrics(["ab", "cd"], ["ab", "cd"])
        self.assertEqual(m["boundary_precision"], 1.0)
        self.assertEqual(m["boundary_recall"], 1.0)
        self.assertEqual(m["boundary_f1"], 1.0)
        self.assertEqual(m["boundary_jaccard"], 1.0)
        self.assertTrue(m["exact_segmentation_match"])

    def test_no_boundary_both_whole(self) -> None:
        m = boundary_metrics(["abcd"], ["abcd"])
        self.assertTrue(m["exact_segmentation_match"])
        # no internal boundaries → empty sets → jaccard 1.0
        self.assertEqual(m["boundary_jaccard"], 1.0)
        self.assertIsNone(m["boundary_precision"])  # no tp/fp
        self.assertIsNone(m["boundary_recall"])

    def test_partial_overlap(self) -> None:
        # gold: a|b|cd  bounds {1,2}
        # pred: ab|cd   bounds {2}
        m = boundary_metrics(["a", "b", "cd"], ["ab", "cd"])
        self.assertAlmostEqual(m["boundary_precision"], 1.0)
        self.assertAlmostEqual(m["boundary_recall"], 0.5)
        self.assertFalse(m["exact_segmentation_match"])
        self.assertGreater(m["boundary_jaccard"], 0.0)
        self.assertLess(m["boundary_jaccard"], 1.0)

    def test_aggregate_schema(self) -> None:
        items = [
            boundary_metrics(["a", "bc"], ["a", "bc"]),
            boundary_metrics(["ab", "c"], ["a", "b", "c"]),
        ]
        agg = aggregate_boundary_metrics(items)
        self.assertEqual(agg["n_items"], 2)
        self.assertIn("boundary_f1", agg)
        self.assertEqual(agg["exact_match_count"], 1)


class TestEfficiencySynthetic(unittest.TestCase):
    def test_efficiency_metrics(self) -> None:
        words = ["abc", "de"]
        pieces = [["a", "b", "c"], ["de"]]
        m = efficiency_metrics_from_encodings(words, pieces)
        self.assertEqual(m["n_words"], 2)
        self.assertEqual(m["n_chars"], 5)
        self.assertEqual(m["n_tokens"], 4)
        self.assertAlmostEqual(m["tokens_per_character"], 4 / 5)
        self.assertAlmostEqual(m["word_fertility"], 2.0)
        self.assertAlmostEqual(m["single_character_fragment_rate"], 3 / 4)
        self.assertAlmostEqual(m["whole_word_rate"], 0.5)


class TestLambdaSelection(unittest.TestCase):
    def test_efficiency_gate_then_max_f1(self) -> None:
        cands = [
            {"lambda": 0.0, "boundary_f1": 0.99, "tokens_per_character": 0.4},
            {"lambda": 0.25, "boundary_f1": 0.55, "tokens_per_character": 0.42},
            {"lambda": 0.5, "boundary_f1": 0.60, "tokens_per_character": 0.43},
            {"lambda": 1.0, "boundary_f1": 0.62, "tokens_per_character": 0.50},  # > 1.1*0.4=0.44
            {"lambda": 2.0, "boundary_f1": 0.70, "tokens_per_character": 0.80},
        ]
        # unigram tpc 0.40 → threshold 0.44; eligible 0.25 and 0.5; max F1 = 0.5
        sel = select_lambda_star(cands, unigram_tpc=0.40, max_relative_tpc=1.10)
        self.assertEqual(sel["lambda_star"], 0.5)
        self.assertFalse(sel["sc5_failed_all_nonzero"])
        self.assertFalse(sel["selection_used_lm_bpc"])

    def test_lambda0_never_selected(self) -> None:
        cands = [
            {"lambda": 0.0, "boundary_f1": 1.0, "tokens_per_character": 0.4},
            {"lambda": 0.25, "boundary_f1": 0.1, "tokens_per_character": 0.4},
        ]
        sel = select_lambda_star(cands, unigram_tpc=0.4)
        self.assertNotEqual(sel["lambda_star"], 0.0)

    def test_all_fail_efficiency_still_picks_max_f1(self) -> None:
        cands = [
            {"lambda": 0.25, "boundary_f1": 0.5, "tokens_per_character": 1.0},
            {"lambda": 0.5, "boundary_f1": 0.7, "tokens_per_character": 1.2},
            {"lambda": 1.0, "boundary_f1": 0.6, "tokens_per_character": 1.1},
        ]
        sel = select_lambda_star(cands, unigram_tpc=0.5, max_relative_tpc=1.10)
        # threshold 0.55; all fail; pick max F1 = 0.5
        self.assertTrue(sel["sc5_failed_all_nonzero"])
        self.assertEqual(sel["lambda_star"], 0.5)

    def test_tie_lower_tpc_then_smaller_lambda(self) -> None:
        cands = [
            {"lambda": 1.0, "boundary_f1": 0.6, "tokens_per_character": 0.45},
            {"lambda": 0.5, "boundary_f1": 0.6, "tokens_per_character": 0.45},
            {"lambda": 0.25, "boundary_f1": 0.6, "tokens_per_character": 0.46},
        ]
        sel = select_lambda_star(cands, unigram_tpc=0.5)
        # same F1, lower tpc is 0.45 for both 0.5 and 1.0 → smaller lambda 0.5
        self.assertEqual(sel["lambda_star"], 0.5)

    def test_bpc_flag_refused(self) -> None:
        cands = [
            {
                "lambda": 0.25,
                "boundary_f1": 0.5,
                "tokens_per_character": 0.4,
                "use_bpc_for_selection": True,
            }
        ]
        with self.assertRaises(ValueError):
            select_lambda_star(cands, unigram_tpc=0.4)

    def test_build_table_schema(self) -> None:
        systems = {
            "unigram_8000": {
                "morphology": {"aggregate": {"boundary_f1": 0.5}},
                "efficiency": {"tokens_per_character": 0.5},
            },
            "statbound_lambda_0_0": {
                "morphology": {"aggregate": {"boundary_f1": 0.5}},
                "efficiency": {"tokens_per_character": 0.5},
            },
            "statbound_lambda_0_25": {
                "morphology": {"aggregate": {"boundary_f1": 0.55}},
                "efficiency": {"tokens_per_character": 0.52},
            },
        }
        sel = build_lambda_selection_table(systems)
        self.assertEqual(sel["schema_version"], "phase_c_lambda_selection_v0_1")
        self.assertEqual(sel["lambda_star"], 0.25)


class TestExcludedRows(unittest.TestCase):
    def test_filter_excluded(self) -> None:
        rows = [
            {"item_id": "a", "excluded": False, "proposed_segmentation": "x+y"},
            {"item_id": "b", "excluded": True, "proposed_segmentation": "z"},
            {
                "item_id": "c",
                "human_review": {"excluded": True, "human_review_decision": "EXCLUDE"},
            },
            {"item_id": "d", "adjudication_status": "excluded_by_human_review"},
        ]
        active = filter_active_rows(rows)
        self.assertEqual([r["item_id"] for r in active], ["a"])


class TestPathGates(unittest.TestCase):
    def test_holdout_blocked(self) -> None:
        with self.assertRaises(PhaseCGateError):
            assert_path_allowed_for_phase_c(
                REPO / "data/research/morphology_benchmark_v0.1/locked/foo.jsonl"
            )

    def test_lm_test_blocked(self) -> None:
        with self.assertRaises(PhaseCGateError):
            assert_path_allowed_for_phase_c(
                REPO / "data/splits/chichewa_corpus_v0.1/test/combined.txt"
            )

    def test_active_morph_blocked_by_default(self) -> None:
        with self.assertRaises(PhaseCGateError):
            assert_path_allowed_for_phase_c(
                REPO
                / "data/research/morphology_benchmark_v0.1/development/annotations/"
                "annotator_a_active_195_v0_1.jsonl"
            )

    def test_validation_blocked_by_default(self) -> None:
        with self.assertRaises(PhaseCGateError):
            assert_path_allowed_for_phase_c(
                REPO / "data/splits/chichewa_corpus_v0.1/validation/combined.txt"
            )


@unittest.skipUnless(BASE_MODEL.is_file(), "Unigram model missing")
class TestLambda0Unigram(unittest.TestCase):
    def test_lambda0_equals_unigram(self) -> None:
        empty = {"words": {}}
        adapter = UnigramAdapter(BASE_MODEL)
        tok = StatBoundUnigramTokenizer(
            adapter=adapter, stats=empty, lambda_bias=0.0, nbest_size=16
        )
        for w in ["ndimakonda", "kugona", "anthu", "42", "ŵanthu"]:
            self.assertEqual(tok.encode_word(w), adapter.encode_as_pieces(w))


class TestBoundaryStatsHashInfra(unittest.TestCase):
    def test_protocol_expected_sha_present_and_unchanged_field(self) -> None:
        proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        expected = proto["reproducibility_snapshot"]["artifacts"]["boundary_stats"][
            "sha256"
        ]
        self.assertEqual(
            expected,
            "4744460d14bd30b8941c0e92d753cbdc54ead8471f43bb78dead922941bd721f",
        )

    def test_existing_on_disk_matches_expected_if_present(self) -> None:
        if not EXISTING_STATS.is_file():
            self.skipTest("on-disk boundary_stats missing (gitignored)")
        proto = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        expected = proto["reproducibility_snapshot"]["artifacts"]["boundary_stats"][
            "sha256"
        ]
        h = hashlib.sha256(EXISTING_STATS.read_bytes()).hexdigest()
        self.assertEqual(h, expected)

    def test_regeneration_is_deterministic_on_toy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            train = tmp / "train" / "t.txt"
            train.parent.mkdir(parents=True)
            train.write_text("kugona kuseka kuyenda " * 50 + "\n", encoding="utf-8")
            cfg = BoundaryDiscoveryConfig(min_type_support=2, min_productivity=2)
            a = learn_boundary_stats(train, cfg)
            b = learn_boundary_stats(train, cfg)
            pa = tmp / "a.json"
            pb = tmp / "b.json"
            save_boundary_stats(a, pa)
            save_boundary_stats(b, pb)
            self.assertEqual(
                hashlib.sha256(pa.read_bytes()).hexdigest(),
                hashlib.sha256(pb.read_bytes()).hexdigest(),
            )


class TestMorphologyPairsSchema(unittest.TestCase):
    def test_evaluate_pairs_schema(self) -> None:
        r = evaluate_morphology_pairs(
            [
                (["a", "b"], ["a", "b"]),
                (["ab"], ["a", "b"]),
            ]
        )
        self.assertEqual(r["schema_version"], "phase_c_morphology_v0_1")
        self.assertEqual(r["aggregate"]["n_items"], 2)


if __name__ == "__main__":
    unittest.main()
