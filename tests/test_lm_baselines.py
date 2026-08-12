#!/usr/bin/env python3
"""Tests for controlled LM baseline pipeline."""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "models"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "tokenizers"))

import lm_common as lc  # noqa: E402


class TestCausalAndLoss(unittest.TestCase):
    @unittest.skipIf(
        __import__("importlib").util.find_spec("torch") is None, "torch not installed"
    )
    def test_causal_mask_and_shift_and_pad_ignore(self) -> None:
        import torch

        model = lc.build_gpt(
            vocab_size=32,
            n_layer=1,
            n_embd=32,
            n_head=4,
            n_inner=64,
            context_length=8,
            dropout=0.0,
            tie_embeddings=True,
        )
        model.eval()
        # fixed input
        x = torch.randint(0, 32, (2, 8))
        y = x.clone()
        y[:, :2] = 0  # pad id 0
        with torch.no_grad():
            logits, loss, nll, ntok = model(x, y, pad_id=0)
        self.assertEqual(logits.shape, (2, 8, 32))
        self.assertIsNotNone(loss)
        self.assertGreater(ntok, 0)
        # all pad targets → ntok 0 edge
        y2 = torch.zeros_like(x)
        logits2, loss2, nll2, ntok2 = model(x, y2, pad_id=0)
        self.assertEqual(ntok2, 0)

    def test_bpc_from_total_nll(self) -> None:
        # 10 nats over 5 chars
        bpc = lc.bits_per_character(10.0, 5)
        self.assertAlmostEqual(bpc, (10.0 / math.log(2)) / 5)
        bpb = lc.bits_per_byte(10.0, 10)
        self.assertAlmostEqual(bpb, (10.0 / math.log(2)) / 10)
        ppl = lc.token_perplexity_from_nll(math.log(4) * 3, 3)
        self.assertAlmostEqual(ppl, 4.0, places=5)


class TestPacking(unittest.TestCase):
    def test_deterministic_packing(self) -> None:
        # minimal fake tokenizer
        class T:
            pad_id = 0
            unk_id = 1
            bos_id = 2
            eos_id = 3
            vocab_size = 20

            def encode(self, text: str):
                return [min(ord(c) % 19 + 1, 19) for c in text][:10]

        lines = ["abc", "de", "fghi"]
        s1, m1, _, c1 = lc.pack_lines_to_sequences(lines, T(), context_length=8)
        s2, m2, _, c2 = lc.pack_lines_to_sequences(lines, T(), context_length=8)
        self.assertEqual(s1, s2)
        self.assertEqual(c1, c2)
        self.assertEqual(m1.n_characters_in_source_text, sum(len(x) for x in lines))
        self.assertTrue(all(len(s) == 8 for s in s1))
        self.assertEqual(len(c1), len(s1))


class TestParamCounting(unittest.TestCase):
    @unittest.skipIf(
        __import__("importlib").util.find_spec("torch") is None, "torch not installed"
    )
    def test_param_counts_and_matching(self) -> None:
        m_char = lc.build_gpt(
            vocab_size=915,
            n_layer=4,
            n_embd=256,
            n_head=4,
            n_inner=1024,
            context_length=256,
            dropout=0.1,
            tie_embeddings=True,
        )
        m_bpe = lc.build_gpt(
            vocab_size=8000,
            n_layer=4,
            n_embd=192,
            n_head=4,
            n_inner=768,
            context_length=256,
            dropout=0.1,
            tie_embeddings=True,
        )
        pc = m_char.count_parameters()
        pb = m_bpe.count_parameters()
        self.assertGreater(pc["embedding"], 0)
        self.assertEqual(pc["total"], pc["embedding"] + pc["non_embedding"])
        # parameter-matched should be closer than arch-matched 256/8000
        m_bpe_arch = lc.build_gpt(
            vocab_size=8000,
            n_layer=4,
            n_embd=256,
            n_head=4,
            n_inner=1024,
            context_length=256,
            dropout=0.1,
            tie_embeddings=True,
        )
        diff_matched = abs(pb["total"] - pc["total"]) / pc["total"]
        diff_arch = abs(m_bpe_arch.count_parameters()["total"] - pc["total"]) / pc["total"]
        self.assertLess(diff_matched, diff_arch)


class TestIntegrityHelpers(unittest.TestCase):
    def test_refuse_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "run"
            d.mkdir()
            (d / "x").write_text("1", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                lc.ensure_run_dir_free(d, force=False)

    def test_resolve_arch(self) -> None:
        cfg = {
            "architecture_matched": {
                "n_layer": 4,
                "n_embd": 256,
                "n_head": 4,
                "n_inner": 1024,
                "dropout": 0.1,
                "context_length": 256,
                "pre_ln": True,
                "tie_embeddings": True,
                "positional_encoding": "learned",
            },
            "parameter_matched": {
                "tolerance_fraction": 0.05,
                "overrides": {
                    "character": {
                        "n_layer": 4,
                        "n_embd": 256,
                        "n_head": 4,
                        "n_inner": 1024,
                    },
                    "bpe_8000": {
                        "n_layer": 4,
                        "n_embd": 192,
                        "n_head": 4,
                        "n_inner": 768,
                    },
                },
                "dropout": 0.1,
                "context_length": 256,
                "pre_ln": True,
                "tie_embeddings": True,
                "positional_encoding": "learned",
            },
        }
        a = lc.resolve_arch(cfg, "architecture_matched", "character")
        self.assertEqual(a["n_embd"], 256)
        b = lc.resolve_arch(cfg, "parameter_matched", "bpe_8000")
        self.assertEqual(b["n_embd"], 192)

    def test_memorization_helpers(self) -> None:
        train = "hello world this is a long bible verse about something important here"
        gen = "this is a long bible verse about"
        n = lc.longest_common_substring_len(gen, train)
        self.assertGreaterEqual(n, 10)
        ov = lc.ngram_overlap(gen, train, n=3)
        self.assertGreater(ov, 0.0)


class TestConfigPresence(unittest.TestCase):
    def test_config_and_hypotheses_locked(self) -> None:
        p = REPO_ROOT / "configs/models/lm_baselines_v0_1.json"
        self.assertTrue(p.is_file())
        cfg = json.loads(p.read_text(encoding="utf-8"))
        self.assertTrue(cfg["hypotheses"]["locked"])
        self.assertIn("H1_character", cfg["hypotheses"])
        self.assertEqual(cfg["budget"]["pilot"]["seeds"], [42])
        self.assertEqual(cfg["budget"]["final"]["seeds"], [42, 1337, 2026])


if __name__ == "__main__":
    unittest.main()
