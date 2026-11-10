"""Check the distinction between a selected path and the candidate union."""

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts/publication/build_publication_snapshot.py"
SPEC = importlib.util.spec_from_file_location("publication_snapshot", PATH)
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


def row():
    metrics = {"boundary_precision": 1.0, "boundary_recall": .5, "boundary_f1": 2/3}
    return {
        "surface_form": "abc", "gold_segmentation": "a+b+c",
        "unigram": {"pieces": ["abc"], "boundary_precision": None, "boundary_recall": 0.0, "boundary_f1": None},
        "f1_oracle": {"pieces": ["a", "bc"], **metrics},
        "compat_oracle": {"pieces": ["a", "bc"], **metrics},
        "candidates": [{"pieces": ["abc"]}, {"pieces": ["a", "bc"]}, {"pieces": ["ab", "c"]}],
    }


class PublicationSnapshotTest(unittest.TestCase):
    def test_oracle_miss_can_be_available_in_another_candidate(self):
        result = publication.summarize_candidates([row()])
        self.assertEqual(result["misses"]["selected_oracle"]["left_edge"], 1)
        self.assertEqual(result["misses"]["absent_from_union"]["left_edge"], 0)

    def test_defined_denominators_are_kept_separate(self):
        result = publication.summarize_candidates([row()])
        counts = result["macro_defined_item_counts"]
        self.assertEqual(counts["unigram"]["boundary_precision"], 0)
        self.assertEqual(counts["unigram"]["boundary_recall"], 1)
        self.assertEqual(counts["f1_oracle"]["boundary_f1"], 1)
        self.assertEqual(result["changed_item_f1_status"], {"undefined_comparison": 1})

    def test_left_edge_bin_takes_precedence(self):
        self.assertEqual(publication.zone("abcde", 3), "left_edge")
        self.assertEqual(publication.zone("abcdefgh", 6), "right_edge")

    def test_piece_count_does_not_prove_only_additions(self):
        x = row()
        x["unigram"] = {"pieces": ["ab", "c"], "boundary_precision": .5, "boundary_recall": .5, "boundary_f1": .5}
        result = publication.summarize_candidates([x])
        self.assertEqual(result["changed_items_only_add_boundaries"], 0)


if __name__ == "__main__":
    unittest.main()
