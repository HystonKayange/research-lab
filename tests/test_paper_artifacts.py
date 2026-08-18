"""Regression locks for paper-facing anatomy numbers.

Uses the frozen oracle JSON only. Does not open holdout, LM test, or train models.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tokenizers.statbound.nbest_oracle import classify_oracle_change, gold_miss_zone_counts

ORACLE = REPO / "data/reports/unigram_nbest_oracle_v0_1.json"
ARTIFACTS = REPO / "data/reports/paper_artifacts_v0_1.json"


@unittest.skipUnless(ORACLE.is_file(), "oracle report not present")
class TestPaperAnatomy(unittest.TestCase):
    def test_location_and_change_counts(self) -> None:
        data = json.loads(ORACLE.read_text(encoding="utf-8"))
        uni = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
        ora = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
        changes = {"unchanged": 0, "clean_prefix": 0, "mixed_gold": 0, "junk_fp": 0}
        for item in data["items"]:
            word = item["surface_form"]
            gold = item["gold_segmentation"].split("+")
            u = item["unigram"]["pieces"]
            o = item["f1_oracle"]["pieces"]
            um = gold_miss_zone_counts(word, gold, u)
            om = gold_miss_zone_counts(word, gold, o)
            for key in uni:
                uni[key] += um[key]
                ora[key] += om[key]
            changes[classify_oracle_change(word, gold, u, o)] += 1
        self.assertEqual(uni, {"left_edge": 129, "right_edge": 93, "internal": 70, "total": 292})
        self.assertEqual(ora, {"left_edge": 2, "right_edge": 71, "internal": 41, "total": 114})
        self.assertEqual(changes["clean_prefix"], 66)
        self.assertEqual(changes["mixed_gold"], 28)
        self.assertEqual(changes["junk_fp"], 31)
        self.assertEqual(changes["unchanged"], 37)


@unittest.skipUnless(ARTIFACTS.is_file(), "paper artifacts not generated")
class TestPaperArtifactFile(unittest.TestCase):
    def test_artifacts_record_no_unlock(self) -> None:
        art = json.loads(ARTIFACTS.read_text(encoding="utf-8"))
        self.assertFalse(art["restricted"]["morphology_holdout_accessed"])
        self.assertFalse(art["restricted"]["lm_test_accessed"])
        self.assertFalse(art["restricted"]["new_training"])
        self.assertEqual(art["T2_statbound_v1"]["sc1"], "FAIL")
        self.assertEqual(art["T2_statbound_v1"]["sc4"], "FAIL")


if __name__ == "__main__":
    unittest.main()
