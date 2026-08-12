#!/usr/bin/env python3
"""Tests for Chichewa tokenizer baseline laboratory."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts" / "tokenizers"
sys.path.insert(0, str(SCRIPTS))

import common as tc  # noqa: E402


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _write_json(p: Path, obj: object) -> None:
    _write(p, json.dumps(obj, indent=2) + "\n")


def _mini_split(root: Path) -> dict:
    split = root / "data/splits/chichewa_corpus_v0.1"
    for sp, n in (("train", 40), ("validation", 10), ("test", 10)):
        bible = [f"Mulungu anapanga {i} ŵanthu." for i in range(n // 2)]
        wiki = [f"Dziko la Malaŵi line {i}." for i in range(n - n // 2)]
        _write(split / sp / "bible.txt", "\n".join(bible) + "\n")
        _write(split / sp / "wikipedia.txt", "\n".join(wiki) + "\n")
        _write(split / sp / "combined.txt", "\n".join(bible + wiki) + "\n")
    # checksums for freeze verify
    checksums = {}
    for p in split.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(split)).replace("\\", "/")
            checksums[rel] = tc.sha256_file(p)
    _write_json(split / "metadata/checksums.json", checksums)
    _write_json(
        split / "metadata/FROZEN_SPLIT.json",
        {"frozen": True, "split_version": "v0.1", "corpus_version": "v0.1"},
    )
    return {
        "version": "0.1.0",
        "experiment_id": "baselines_v0.1",
        "corpus_version": "chichewa_corpus_v0.1",
        "split_version": "v0.1",
        "split_root": "data/splits/chichewa_corpus_v0.1",
        "output_root": "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1",
        "metadata_path": "data/metadata/tokenizer_baselines_v0_1.json",
        "report_path": "data/reports/tokenizer_baselines_v0_1.md",
        "examples_path": "data/reports/tokenizer_examples_v0_1.jsonl",
        "morphology_probe_path": "data/reports/chichewa_morphology_probe_v0_1.jsonl",
        "training_inputs": {
            "combined": "data/splits/chichewa_corpus_v0.1/train/combined.txt",
            "bible": "data/splits/chichewa_corpus_v0.1/train/bible.txt",
            "wikipedia": "data/splits/chichewa_corpus_v0.1/train/wikipedia.txt",
            "allowed_path_substrings": ["/train/"],
            "forbidden_path_substrings": ["/validation/", "/test/"],
        },
        "normalization": {
            "policy": "identity",
            "lowercase": False,
            "nfkc": False,
            "preserve_case": True,
            "preserve_unicode": True,
            "preserve_w_hat": True,
        },
        "special_tokens": {
            "pad": "<pad>",
            "unk": "<unk>",
            "bos": "<bos>",
            "eos": "<eos>",
            "roles": {},
        },
        "character": {
            "tokenizer_id": "character",
            "special_token_order": ["<pad>", "<unk>", "<bos>", "<eos>"],
            "unknown_behavior": "map_to_<unk>",
            "whitespace": "preserve_as_characters",
            "vocab_order": "specials_then_sorted_unicode_codepoints",
        },
        "sentencepiece": {
            "vocab_sizes": [100],
            "model_types": ["bpe"],
            "character_coverage": 1.0,
            "normalization_rule_name": "identity",
            "byte_fallback": False,
            "split_by_unicode_script": True,
            "split_by_number": True,
            "split_by_whitespace": True,
            "treat_whitespace_as_suffix": False,
            "allow_whitespace_only_pieces": False,
            "remove_extra_whitespaces": False,
            "add_dummy_prefix": True,
            "hard_vocab_limit": False,
            "input_sentence_size": 0,
            "shuffle_input_sentence": False,
            "seed": None,
            "num_threads": 1,
            "max_sentence_length": 4096,
            "pad_id": 0,
            "unk_id": 1,
            "bos_id": 2,
            "eos_id": 3,
            "pad_piece": "<pad>",
            "unk_piece": "<unk>",
            "bos_piece": "<bos>",
            "eos_piece": "<eos>",
            "unk_surface": "<unk>",
            "required_chars": "",
        },
        "selection_rubric": {"use_split": "validation", "forbid_test_for_selection": True},
        "morphology_probe": {"n_candidates": 10, "min_word_len": 4, "seed": 1},
        "example_texts": ["Mulungu anapanga.", "Malaŵi"],
    }


class TestCharacterTokenizer(unittest.TestCase):
    def test_vocab_from_train_only_and_unk(self) -> None:
        train = "abc ŵ"
        tok = tc.CharacterTokenizer.train_from_text(train)
        # z not in train
        res = tok.encode("az")
        self.assertIn(tok.unk_id, res.ids)
        self.assertEqual(res.tokens.count("<unk>"), 1)
        # ŵ preserved
        res2 = tok.encode("ŵ")
        self.assertNotIn(tok.unk_id, res2.ids)
        self.assertEqual(res2.tokens, ["ŵ"])

    def test_deterministic_vocab_order(self) -> None:
        t1 = tc.CharacterTokenizer.train_from_text("cba")
        t2 = tc.CharacterTokenizer.train_from_text("cba")
        self.assertEqual(t1.itos, t2.itos)
        # specials first
        self.assertEqual(t1.itos[:4], ["<pad>", "<unk>", "<bos>", "<eos>"])
        # chars sorted
        chars = [c for c in t1.itos[4:]]
        self.assertEqual(chars, sorted(chars, key=lambda c: (ord(c), c)))

    def test_unicode_preservation(self) -> None:
        tok = tc.CharacterTokenizer.train_from_text("Malaŵi")
        self.assertIn("ŵ", tok.stoi)
        enc = tok.encode("Malaŵi")
        self.assertEqual("".join(enc.tokens), "Malaŵi")

    def test_special_token_ids_stable(self) -> None:
        tok = tc.CharacterTokenizer.train_from_text("x")
        self.assertEqual(tok.stoi["<pad>"], 0)
        self.assertEqual(tok.stoi["<unk>"], 1)
        self.assertEqual(tok.stoi["<bos>"], 2)
        self.assertEqual(tok.stoi["<eos>"], 3)


class TestMetrics(unittest.TestCase):
    def test_fertility_and_sequence_stats(self) -> None:
        tok = tc.CharacterTokenizer.train_from_text("ab cd")
        units = [
            {
                "split": "validation",
                "source_id": "bible",
                "line_index": 0,
                "text": "ab cd",
                "n_chars": 5,
                "n_bytes": 5,
                "n_words": 2,
            }
        ]
        m = tc.evaluate_tokenizer_on_units(
            lambda t: tok.encode(t),
            units,
            tokenizer_id="character",
            vocab_size=len(tok.itos),
            unk_id=tok.unk_id,
        )
        self.assertEqual(m["sequence_efficiency"]["total_encoded_tokens"], 5)
        self.assertAlmostEqual(m["fertility"]["overall"], 5 / 2)
        self.assertIn("p50", m["sequence_efficiency"]["sequence_length_percentiles"])
        self.assertIn("bible", m["by_source"])


class TestFrozenSplitVerification(unittest.TestCase):
    def test_rejects_unfrozen_and_bad_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _mini_split(root)
            # OK
            tc.verify_frozen_split(root / cfg["split_root"], cfg)
            # unfrozen
            fr = root / cfg["split_root"] / "metadata/FROZEN_SPLIT.json"
            _write_json(fr, {"frozen": False})
            with self.assertRaises(ValueError):
                tc.verify_frozen_split(root / cfg["split_root"], cfg)
            _write_json(fr, {"frozen": True})
            # forbidden path
            bad = dict(cfg)
            bad["training_inputs"] = dict(cfg["training_inputs"])
            bad["training_inputs"]["combined"] = (
                "data/splits/chichewa_corpus_v0.1/validation/combined.txt"
            )
            with self.assertRaises(ValueError):
                tc.verify_frozen_split(root / cfg["split_root"], bad)

    def test_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _mini_split(root)
            # corrupt a file
            p = root / cfg["split_root"] / "train/bible.txt"
            p.write_text(p.read_text(encoding="utf-8") + "x", encoding="utf-8")
            with self.assertRaises(ValueError):
                tc.verify_frozen_split(root / cfg["split_root"], cfg)


class TestOverwriteRefusal(unittest.TestCase):
    def test_ensure_output_not_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "exp"
            d.mkdir()
            (d / "f").write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                tc.ensure_output_not_exists(d, force=False)


class TestSentencePieceOptional(unittest.TestCase):
    def test_missing_sentencepiece_message(self) -> None:
        # Wrapper raises ImportError-like if model missing; dependency message in train script
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                tc.SentencePieceWrapper(Path(td) / "nope.model", "x")

    @unittest.skipIf(tc.sentencepiece_version() is None, "sentencepiece not installed")
    def test_sentencepiece_train_tiny(self) -> None:
        import sentencepiece as spm

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _mini_split(root)
            train = root / cfg["training_inputs"]["combined"]
            # ensure enough chars for small vocab
            extra = "\n".join(f"anapanga {i} amakhala {i} ndimakukonda {i}" for i in range(50))
            train.write_text(train.read_text(encoding="utf-8") + extra + "\n", encoding="utf-8")
            # refresh checksums after edit
            split = root / cfg["split_root"]
            checksums = {
                str(p.relative_to(split)).replace("\\", "/"): tc.sha256_file(p)
                for p in split.rglob("*")
                if p.is_file() and "FROZEN" not in p.name and "checksums" not in p.name
            }
            # include all files
            checksums = {
                str(p.relative_to(split)).replace("\\", "/"): tc.sha256_file(p)
                for p in split.rglob("*")
                if p.is_file()
            }
            _write_json(split / "metadata/checksums.json", checksums)

            out = root / "sp_out"
            out.mkdir()
            prefix = out / "model"
            spm.SentencePieceTrainer.train(
                input=str(train),
                model_prefix=str(prefix),
                vocab_size=80,
                model_type="bpe",
                character_coverage=1.0,
                normalization_rule_name="identity",
                shuffle_input_sentence=False,
                num_threads=1,
                pad_id=0,
                unk_id=1,
                bos_id=2,
                eos_id=3,
                hard_vocab_limit=False,
            )
            wrap = tc.SentencePieceWrapper(out / "model.model", "bpe_80")
            self.assertEqual(wrap.sp.pad_id(), 0)
            self.assertEqual(wrap.sp.unk_id(), 1)
            enc = wrap.encode("Mulungu")
            self.assertGreater(len(enc.ids), 0)

    def test_no_validation_in_training_inputs_config(self) -> None:
        cfg_path = REPO_ROOT / "configs/tokenizers/baselines_v0_1.json"
        if not cfg_path.is_file():
            self.skipTest("config missing")
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        for key in ("combined", "bible", "wikipedia"):
            p = cfg["training_inputs"][key]
            self.assertIn("/train/", p)
            self.assertNotIn("/validation/", p)
            self.assertNotIn("/test/", p)


class TestNormalizationAudit(unittest.TestCase):
    def test_identity_audit(self) -> None:
        audit = tc.normalization_audit(["Malaŵi", "ABC"], "identity")
        self.assertEqual(audit["n_changed"], 0)
        self.assertTrue(all(s["unchanged"] for s in audit["samples"]))


class TestManifestShape(unittest.TestCase):
    def test_real_config_present(self) -> None:
        p = REPO_ROOT / "configs/tokenizers/baselines_v0_1.json"
        self.assertTrue(p.is_file())
        cfg = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(cfg["sentencepiece"]["vocab_sizes"], [1000, 2000, 4000, 8000])
        self.assertEqual(cfg["normalization"]["policy"], "identity")
        self.assertFalse(cfg["sentencepiece"]["byte_fallback"])


if __name__ == "__main__":
    unittest.main()
