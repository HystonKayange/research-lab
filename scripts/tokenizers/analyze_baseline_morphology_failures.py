#!/usr/bin/env python3
"""Automatic baseline tokenizer failure / disagreement diagnostics (Phase A).

Train + validation only. No LM test. No hybrid tokenizer. No human gold labels.

Distinguishes:
  - orthographic evidence
  - statistical evidence
  - linguistic interpretation (requires human review; not asserted)

Does not call recurring character strings "morphemes".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import (  # noqa: E402
    load_json,
    load_lines,
    sha256_file,
    utc_now_iso,
    verify_frozen_split,
    write_json,
    write_jsonl,
    write_text,
)
from evaluate_tokenizers import discover_models, get_encoder  # noqa: E402

TOOL_NAME = "analyze_baseline_morphology_failures"
TOOL_VERSION = "0.1.0"
WORD_RE = re.compile(r"\S+")
PUNCT_STRIP = ".,;:!?\"'()[]«»“”‘’…—–-"

# Surface pattern anchors only — NOT claimed morphemes.
APPARENT_PREFIX_PATTERNS = (
    "si",
    "sa",
    "si-",
    "ndi",
    "ti",
    "ta",
    "a",
    "ana",
    "wa",
    "mu",
    "ku",
    "chi",
    "zi",
    "ma",
    "li",
    "pa",
    "ka",
    "u",
    "i",
    "o",
)
APPARENT_SUFFIX_PATTERNS = (
    "ira",
    "era",
    "itsa",
    "etsa",
    "ika",
    "eka",
    "ana",
    "idwa",
    "edwa",
    "ndi",
    "nso",
    "be",
    "tu",
    "ko",
    "mo",
    "po",
)
APPARENT_NEG = ("si", "sa", "osati", "sizinthu")
APPARENT_LOC = ("ku", "ku-", "pa", "mu", "kwa")


def refuse_test_path(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/test/" in s or s.rstrip("/").endswith("/test"):
        raise RuntimeError(f"refusing test path: {path}")


def strip_punct(w: str) -> str:
    return w.strip(PUNCT_STRIP)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def encode_word(encode_fn, word: str) -> list[str]:
    return list(encode_fn(word).tokens)


def pieces_surface(pieces: list[str]) -> list[str]:
    return [p.lstrip("▁") for p in pieces]


def is_single_char_frag(piece: str) -> bool:
    s = piece.lstrip("▁")
    return len(s) == 1


def is_whole_word_token(pieces: list[str], word: str) -> bool:
    if len(pieces) != 1:
        return False
    return pieces[0].lstrip("▁") == word


def load_inventory(split_root: Path, split: str) -> tuple[Counter[str], dict[str, list[dict[str, Any]]]]:
    if split not in ("train", "validation"):
        raise ValueError("only train|validation")
    refuse_test_path(split_root / split)
    freq: Counter[str] = Counter()
    meta: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in ("bible", "wikipedia"):
        path = split_root / split / f"{source}.txt"
        refuse_test_path(path)
        if not path.is_file():
            continue
        for li, line in enumerate(load_lines(path)):
            for wi, raw in enumerate(WORD_RE.findall(line)):
                core = strip_punct(raw)
                if not core:
                    continue
                freq[core] += 1
                if len(meta[core]) < 2:
                    meta[core].append(
                        {
                            "source": source,
                            "split": split,
                            "line_index": li,
                            "word_index": wi,
                            "context": line[:180],
                        }
                    )
    return freq, meta


def prefix_consistency(words: list[str], encodings: dict[str, list[str]], k: int = 3) -> dict[str, Any]:
    """Statistical consistency of recurring initial strings vs first piece(s)."""
    by_pref: dict[str, list[str]] = defaultdict(list)
    for w in words:
        if len(w) >= k + 2:
            by_pref[w[:k].lower()].append(w)
    scores = []
    examples = []
    for pref, members in by_pref.items():
        if len(members) < 5:
            continue
        first_pieces = []
        for w in members[:40]:
            pcs = encodings.get(w) or []
            if pcs:
                first_pieces.append(pcs[0].lstrip("▁").lower())
        if len(first_pieces) < 5:
            continue
        mode, cnt = Counter(first_pieces).most_common(1)[0]
        rate = cnt / len(first_pieces)
        scores.append(rate)
        if rate < 0.7:
            examples.append(
                {
                    "initial_string": pref,
                    "n_members_sampled": len(first_pieces),
                    "mode_first_piece": mode,
                    "mode_rate": rate,
                    "evidence_type": "statistical",
                    "note": "Not a morpheme label; recurring initial string only.",
                }
            )
    return {
        "n_prefix_groups": len(scores),
        "mean_mode_rate": sum(scores) / len(scores) if scores else None,
        "low_consistency_examples": examples[:30],
        "evidence_type": "statistical",
        "linguistic_interpretation": "requires_human_review",
    }


def suffix_consistency(words: list[str], encodings: dict[str, list[str]], k: int = 3) -> dict[str, Any]:
    by_suf: dict[str, list[str]] = defaultdict(list)
    for w in words:
        if len(w) >= k + 2:
            by_suf[w[-k:].lower()].append(w)
    scores = []
    examples = []
    for suf, members in by_suf.items():
        if len(members) < 5:
            continue
        last_pieces = []
        for w in members[:40]:
            pcs = encodings.get(w) or []
            if pcs:
                last_pieces.append(pcs[-1].lstrip("▁").lower())
        if len(last_pieces) < 5:
            continue
        mode, cnt = Counter(last_pieces).most_common(1)[0]
        rate = cnt / len(last_pieces)
        scores.append(rate)
        if rate < 0.7:
            examples.append(
                {
                    "final_string": suf,
                    "n_members_sampled": len(last_pieces),
                    "mode_last_piece": mode,
                    "mode_rate": rate,
                    "evidence_type": "statistical",
                    "note": "Not a morpheme label; recurring final string only.",
                }
            )
    return {
        "n_suffix_groups": len(scores),
        "mean_mode_rate": sum(scores) / len(scores) if scores else None,
        "low_consistency_examples": examples[:30],
        "evidence_type": "statistical",
        "linguistic_interpretation": "requires_human_review",
    }


def family_consistency(
    words: list[str],
    encodings: dict[str, list[str]],
    stems: tuple[str, ...],
) -> dict[str, Any]:
    """Automatically discovered families via stem substring after short prefix — surface only."""
    prefixes = ("", "ku", "a", "ana", "wa", "mu", "chi", "zi", "ma", "ti", "ndi", "si", "sa", "li", "pa", "ka", "u", "i", "o")
    by_stem: dict[str, list[str]] = defaultdict(list)
    for w in words:
        wl = w.lower()
        for stem in stems:
            if len(stem) < 4:
                continue
            for pref in prefixes:
                if wl.startswith(pref + stem) and len(wl) > len(pref) + len(stem):
                    by_stem[stem].append(w)
                    break
    family_rows = []
    for stem, members in by_stem.items():
        members = sorted(set(members))
        if len(members) < 4:
            continue
        share = 0
        sample = members[:30]
        for w in sample:
            pcs = encodings.get(w) or []
            joined = "".join(pieces_surface(pcs)).lower()
            piece_hit = any(stem in p.lstrip("▁").lower() for p in pcs)
            if piece_hit and stem in joined:
                share += 1
        rate = share / len(sample)
        family_rows.append(
            {
                "surface_family_key": stem,
                "n_members": len(members),
                "n_sampled": len(sample),
                "stem_as_single_piece_rate": rate,
                "evidence_type": "statistical",
                "note": "surface_family_key is not a verified morpheme",
            }
        )
    family_rows.sort(key=lambda r: r["stem_as_single_piece_rate"])
    return {
        "n_families": len(family_rows),
        "mean_stem_piece_rate": (
            sum(r["stem_as_single_piece_rate"] for r in family_rows) / len(family_rows)
            if family_rows
            else None
        ),
        "lowest_consistency_families": family_rows[:20],
        "evidence_type": "statistical",
        "linguistic_interpretation": "requires_human_review",
    }


def vocab_utilization(encode_fn, words: list[str], vocab_size: int) -> dict[str, Any]:
    seen: set[str] = set()
    for w in words:
        for p in encode_word(encode_fn, w):
            seen.add(p)
    return {
        "vocab_size": vocab_size,
        "pieces_observed_on_sample": len(seen),
        "utilization_proxy": len(seen) / vocab_size if vocab_size else None,
        "evidence_type": "statistical",
        "note": "Proxy from word sample, not full corpus encode.",
    }


def tag_candidate(word: str, train_freq: int, seen: bool, bpe: list[str], uni: list[str]) -> list[str]:
    tags = []
    if bpe != uni:
        tags.append("bpe_unigram_disagree")
    if len(bpe) >= 4 or len(uni) >= 4:
        tags.append("high_fragmentation")
    if is_whole_word_token(bpe, word) or is_whole_word_token(uni, word):
        tags.append("whole_word_single_token")
    if any(is_single_char_frag(p) for p in bpe + uni):
        tags.append("single_character_fragment")
    if "ŵ" in word or "Ŵ" in word:
        tags.append("contains_w_hat")
    if not seen:
        tags.append("unseen_in_train")
    if train_freq <= 3 and seen:
        tags.append("rare_train")
    if train_freq >= 50:
        tags.append("frequent_train")
    if len(word) >= 12:
        tags.append("long_word")
    if re.search(r"[A-Za-z]{3,}", word) and re.search(r"[^\x00-\x7f]", word):
        tags.append("mixed_orthography_heuristic")
    wl = word.lower()
    for p in APPARENT_PREFIX_PATTERNS:
        if wl.startswith(p) and len(word) > len(p) + 2:
            tags.append("candidate_apparent_prefix")
            break
    for s in APPARENT_SUFFIX_PATTERNS:
        if wl.endswith(s) and len(word) > len(s) + 2:
            tags.append("candidate_apparent_suffix")
            break
    if any(wl.startswith(n) for n in APPARENT_NEG):
        tags.append("candidate_apparent_negation")
    if any(wl.startswith(n) for n in APPARENT_LOC) and len(word) > 4:
        tags.append("candidate_apparent_locative")
    tags.append("orthographic_surface_form")
    return tags


STEMS = (
    "konda",
    "panga",
    "khala",
    "chita",
    "funa",
    "pita",
    "nena",
    "gona",
    "bwera",
    "yamba",
    "tsata",
    "gula",
    "lemba",
    "werenga",
    "phunzira",
    "thamanga",
    "pereka",
    "tenga",
    "yenda",
    "seka",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baseline morphology-oriented tokenizer failure analysis")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--max-words", type=int, default=15000)
    p.add_argument("--max-disagreement-export", type=int, default=3000)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    split_root = root / config["split_root"]
    exp_root = root / config["output_root"]

    refuse_test_path(split_root / "train")
    refuse_test_path(split_root / "validation")
    freeze = verify_frozen_split(split_root, config)

    models = discover_models(exp_root)
    encoders: dict[str, Any] = {}
    vocab_sizes: dict[str, int] = {}
    for spec in models:
        encode_fn, vs, _u, tid = get_encoder(exp_root, spec)
        encoders[tid] = encode_fn
        vocab_sizes[tid] = vs
    for need in ("bpe_8000", "unigram_8000", "character"):
        if need not in encoders:
            raise FileNotFoundError(need)

    if args.dry_run:
        print("dry-run ok", sorted(encoders))
        return 0

    train_freq, train_meta = load_inventory(split_root, "train")
    val_freq, val_meta = load_inventory(split_root, "validation")

    # build analysis word list: train types + val types, capped
    all_words = set(train_freq) | set(val_freq)
    # prioritize
    priority = []
    rest = []
    for w in all_words:
        if len(w) < 2:
            continue
        if (
            "ŵ" in w
            or "Ŵ" in w
            or w not in train_freq
            or len(w) >= 12
            or train_freq.get(w, 0) <= 3
        ):
            priority.append(w)
        else:
            rest.append(w)
    rest.sort(key=lambda w: hashlib.sha256(w.encode()).hexdigest())
    priority.sort()
    words = (priority + rest)[: args.max_words]
    print(f"Analyzing {len(words)} words…")

    bpe_enc: dict[str, list[str]] = {}
    uni_enc: dict[str, list[str]] = {}
    per_word: list[dict[str, Any]] = []

    # aggregate counters
    n = 0
    n_disagree = 0
    bpe_tok_counts = []
    uni_tok_counts = []
    bpe_cpt = []  # chars per token
    uni_cpt = []
    bpe_whole = 0
    uni_whole = 0
    bpe_sc_frags = 0
    uni_sc_frags = 0
    bpe_total_pieces = 0
    uni_total_pieces = 0
    bpe_rare_frags = 0  # piece length 1-2 non-space
    uni_rare_frags = 0
    piece_freq_bpe: Counter[str] = Counter()
    piece_freq_uni: Counter[str] = Counter()
    unseen_frag_bpe = []
    unseen_frag_uni = []
    freq_list = []
    len_list = []
    fert_bpe_list = []
    fert_uni_list = []
    by_source_bpe_fert: dict[str, list[float]] = defaultdict(list)
    by_freq_band: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for i, w in enumerate(words):
        if i and i % 3000 == 0:
            print(f"  …{i}/{len(words)}")
        bpe = encode_word(encoders["bpe_8000"], w)
        uni = encode_word(encoders["unigram_8000"], w)
        bpe_enc[w] = bpe
        uni_enc[w] = uni
        n += 1
        disagree = bpe != uni
        if disagree:
            n_disagree += 1
        bf, uf = len(bpe), len(uni)
        bpe_tok_counts.append(bf)
        uni_tok_counts.append(uf)
        bpe_cpt.append(len(w) / bf if bf else None)
        uni_cpt.append(len(w) / uf if uf else None)
        if is_whole_word_token(bpe, w):
            bpe_whole += 1
        if is_whole_word_token(uni, w):
            uni_whole += 1
        for p in bpe:
            bpe_total_pieces += 1
            piece_freq_bpe[p] += 1
            if is_single_char_frag(p):
                bpe_sc_frags += 1
            if 1 <= len(p.lstrip("▁")) <= 2:
                bpe_rare_frags += 1
        for p in uni:
            uni_total_pieces += 1
            piece_freq_uni[p] += 1
            if is_single_char_frag(p):
                uni_sc_frags += 1
            if 1 <= len(p.lstrip("▁")) <= 2:
                uni_rare_frags += 1

        seen = w in train_freq
        tf = int(train_freq.get(w, 0))
        if not seen:
            unseen_frag_bpe.append(bf)
            unseen_frag_uni.append(uf)

        freq_list.append(float(tf + 1))  # log later
        len_list.append(float(len(w)))
        fert_bpe_list.append(float(bf))
        fert_uni_list.append(float(uf))

        # source: prefer train meta else val
        src = "unknown"
        if w in train_meta and train_meta[w]:
            src = train_meta[w][0]["source"]
        elif w in val_meta and val_meta[w]:
            src = val_meta[w][0]["source"]
        by_source_bpe_fert[src].append(float(bf))

        if tf == 0:
            band = "unseen"
        elif tf <= 3:
            band = "rare_1_3"
        elif tf <= 20:
            band = "mid_4_20"
        elif tf <= 100:
            band = "common_21_100"
        else:
            band = "frequent_100p"
        by_freq_band[band].append((float(bf), float(uf)))

        tags = tag_candidate(w, tf, seen, bpe, uni)
        if disagree or any(
            t
            in tags
            for t in (
                "high_fragmentation",
                "contains_w_hat",
                "unseen_in_train",
                "whole_word_single_token",
                "mixed_orthography_heuristic",
            )
        ):
            ctx_info = (val_meta.get(w) or train_meta.get(w) or [{}])[0]
            per_word.append(
                {
                    "surface_form": w,
                    "split": "validation" if w in val_freq and w not in train_freq else (
                        "validation" if w in val_freq else "train"
                    ),
                    "source": ctx_info.get("source", src),
                    "context": ctx_info.get("context", ""),
                    "frequency_train": tf,
                    "seen_in_train": seen,
                    "bpe_tokens": bpe,
                    "unigram_tokens": uni,
                    "bpe_fertility": bf,
                    "unigram_fertility": uf,
                    "bpe_chars_per_token": len(w) / bf if bf else None,
                    "unigram_chars_per_token": len(w) / uf if uf else None,
                    "automatic_tags": tags,
                    "evidence_layers": {
                        "orthographic": ["surface_form_recorded", "unicode_codepoint_intact"],
                        "statistical": ["fertility", "disagreement", "frequency_band"],
                        "linguistic_interpretation": "requires_human_review",
                    },
                    "line_ref": {
                        "split": ctx_info.get("split"),
                        "source": ctx_info.get("source"),
                        "line_index": ctx_info.get("line_index"),
                        "word_index": ctx_info.get("word_index"),
                    },
                }
            )

    # rare fragment rate: pieces with global count == 1 among observed
    bpe_singleton_pieces = sum(1 for p, c in piece_freq_bpe.items() if c == 1)
    uni_singleton_pieces = sum(1 for p, c in piece_freq_uni.items() if c == 1)

    log_freq = [math.log(f) for f in freq_list]
    corr_freq_bpe = pearson(log_freq, fert_bpe_list)
    corr_freq_uni = pearson(log_freq, fert_uni_list)
    corr_len_bpe = pearson(len_list, fert_bpe_list)
    corr_len_uni = pearson(len_list, fert_uni_list)

    def mean(xs: list[float]) -> float | None:
        return sum(xs) / len(xs) if xs else None

    pref_bpe = prefix_consistency(words, bpe_enc)
    pref_uni = prefix_consistency(words, uni_enc)
    suf_bpe = suffix_consistency(words, bpe_enc)
    suf_uni = suffix_consistency(words, uni_enc)
    fam_bpe = family_consistency(words, bpe_enc, STEMS)
    fam_uni = family_consistency(words, uni_enc, STEMS)
    util_bpe = vocab_utilization(encoders["bpe_8000"], words[:5000], vocab_sizes["bpe_8000"])
    util_uni = vocab_utilization(encoders["unigram_8000"], words[:5000], vocab_sizes["unigram_8000"])

    freq_sensitivity = {
        band: {
            "n": len(vals),
            "mean_bpe_fertility": mean([a for a, _b in vals]),
            "mean_unigram_fertility": mean([b for _a, b in vals]),
        }
        for band, vals in sorted(by_freq_band.items())
    }
    source_sensitivity = {
        src: {"n": len(vs), "mean_bpe_fertility": mean(vs)}
        for src, vs in sorted(by_source_bpe_fert.items())
    }

    summary = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "frozen_split_verified": bool(freeze.get("frozen")),
        "test_split_accessed": False,
        "n_words_analyzed": n,
        "n_bpe_unigram_disagree": n_disagree,
        "segmentation_disagreement_rate": n_disagree / n if n else None,
        "diagnostics": {
            "token_count_per_word": {
                "bpe_8000_mean": mean([float(x) for x in bpe_tok_counts]),
                "unigram_8000_mean": mean([float(x) for x in uni_tok_counts]),
                "evidence_type": "statistical",
            },
            "characters_per_token": {
                "bpe_8000_mean": mean([x for x in bpe_cpt if x is not None]),
                "unigram_8000_mean": mean([x for x in uni_cpt if x is not None]),
                "evidence_type": "statistical",
            },
            "whole_word_token_rate": {
                "bpe_8000": bpe_whole / n if n else None,
                "unigram_8000": uni_whole / n if n else None,
                "evidence_type": "statistical",
            },
            "single_character_fragment_rate": {
                "bpe_8000": bpe_sc_frags / bpe_total_pieces if bpe_total_pieces else None,
                "unigram_8000": uni_sc_frags / uni_total_pieces if uni_total_pieces else None,
                "evidence_type": "statistical",
            },
            "short_fragment_rate_len_le_2": {
                "bpe_8000": bpe_rare_frags / bpe_total_pieces if bpe_total_pieces else None,
                "unigram_8000": uni_rare_frags / uni_total_pieces if uni_total_pieces else None,
                "evidence_type": "statistical",
            },
            "rare_fragment_rate_singleton_piece_types": {
                "bpe_8000_singleton_types": bpe_singleton_pieces,
                "unigram_8000_singleton_types": uni_singleton_pieces,
                "bpe_8000_fraction_of_types": bpe_singleton_pieces / len(piece_freq_bpe)
                if piece_freq_bpe
                else None,
                "unigram_8000_fraction_of_types": uni_singleton_pieces / len(piece_freq_uni)
                if piece_freq_uni
                else None,
                "evidence_type": "statistical",
            },
            "segmentation_disagreement_rate": {
                "rate": n_disagree / n if n else None,
                "count": n_disagree,
                "n": n,
                "evidence_type": "statistical",
            },
            "validation_unseen_form_fragmentation": {
                "n_unseen_in_sample": len(unseen_frag_bpe),
                "mean_bpe_fertility": mean([float(x) for x in unseen_frag_bpe]),
                "mean_unigram_fertility": mean([float(x) for x in unseen_frag_uni]),
                "evidence_type": "statistical",
            },
            "recurring_initial_string_consistency": {
                "bpe_8000": pref_bpe,
                "unigram_8000": pref_uni,
            },
            "recurring_final_string_consistency": {
                "bpe_8000": suf_bpe,
                "unigram_8000": suf_uni,
            },
            "automatic_word_family_consistency": {
                "bpe_8000": fam_bpe,
                "unigram_8000": fam_uni,
                "caution": "surface_family_key is not a verified morpheme",
            },
            "vocabulary_utilization_proxy": {
                "bpe_8000": util_bpe,
                "unigram_8000": util_uni,
            },
            "frequency_sensitivity": {
                "bands": freq_sensitivity,
                "evidence_type": "statistical",
            },
            "source_sensitivity": {
                "by_source": source_sensitivity,
                "evidence_type": "statistical",
            },
            "correlation_log_frequency_vs_fertility": {
                "bpe_8000_pearson": corr_freq_bpe,
                "unigram_8000_pearson": corr_freq_uni,
                "evidence_type": "statistical",
            },
            "correlation_word_length_vs_fertility": {
                "bpe_8000_pearson": corr_len_bpe,
                "unigram_8000_pearson": corr_len_uni,
                "evidence_type": "statistical",
            },
        },
        "evidence_taxonomy": {
            "orthographic": [
                "Unicode surface forms as written in corpus",
                "Presence of ŵ / mixed scripts",
                "Word length in characters",
            ],
            "statistical": [
                "Fertility, disagreement rates, correlations, consistency rates",
                "Frequency bands and source aggregates",
            ],
            "linguistic_interpretation_requires_human_review": [
                "Whether a prefix/suffix string is a morpheme",
                "Whether disagreement is morphologically meaningful",
                "Noun-class, tense/aspect, object marking claims",
            ],
        },
        "dominant_automatic_patterns": [],
        "lm_test_evaluations_executed": 0,
        "mthandizi_implementation_executed": False,
    }

    # dominant patterns
    patterns = []
    if summary["diagnostics"]["segmentation_disagreement_rate"]["rate"]:
        patterns.append(
            {
                "pattern": "high_bpe_unigram_disagreement_on_prioritized_sample",
                "rate": summary["diagnostics"]["segmentation_disagreement_rate"]["rate"],
                "evidence_type": "statistical",
            }
        )
    patterns.append(
        {
            "pattern": "fertility_increases_for_unseen_and_rare_bands",
            "detail": freq_sensitivity,
            "evidence_type": "statistical",
        }
    )
    if fam_bpe.get("mean_stem_piece_rate") is not None:
        patterns.append(
            {
                "pattern": "incomplete_stem_piece_sharing_in_surface_families",
                "bpe_mean_stem_piece_rate": fam_bpe["mean_stem_piece_rate"],
                "unigram_mean_stem_piece_rate": fam_uni["mean_stem_piece_rate"],
                "evidence_type": "statistical",
                "linguistic_interpretation": "requires_human_review",
            }
        )
    summary["dominant_automatic_patterns"] = patterns

    # sort disagreement candidates
    disagreements = [r for r in per_word if "bpe_unigram_disagree" in r["automatic_tags"]]
    disagreements.sort(
        key=lambda r: (
            -abs(r["bpe_fertility"] - r["unigram_fertility"]),
            -r["bpe_fertility"],
            r["surface_form"],
        )
    )
    disagreements = disagreements[: args.max_disagreement_export]

    out_report = root / "data/reports/tokenizer_morphology_failure_audit_v0_1.md"
    out_sum = root / "data/reports/tokenizer_morphology_failure_summary_v0_1.json"
    out_dis = root / "data/reports/tokenizer_disagreement_candidates_v0_1.jsonl"
    write_json(out_sum, summary)
    write_jsonl(out_dis, disagreements)

    md = [
        "# Tokenizer morphology-oriented failure audit v0.1",
        "",
        f"_Generated {summary['generated_at']} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "## Safety",
        "",
        "- Splits: train + validation only",
        "- LM test split: **not accessed**",
        "- Human gold morphology: **not generated**",
        "- Recurring strings are **not** called morphemes without human validation",
        "",
        "## Evidence taxonomy",
        "",
        "### Orthographic evidence",
        "",
    ]
    for x in summary["evidence_taxonomy"]["orthographic"]:
        md.append(f"- {x}")
    md += ["", "### Statistical evidence", ""]
    for x in summary["evidence_taxonomy"]["statistical"]:
        md.append(f"- {x}")
    md += ["", "### Linguistic interpretation (human review required)", ""]
    for x in summary["evidence_taxonomy"]["linguistic_interpretation_requires_human_review"]:
        md.append(f"- {x}")

    d = summary["diagnostics"]
    md += [
        "",
        "## Aggregate diagnostics",
        "",
        f"- Words analyzed: **{n}**",
        f"- BPE≠Unigram (8000) count: **{n_disagree}** "
        f"(rate={d['segmentation_disagreement_rate']['rate']})",
        f"- Mean tokens/word BPE: {d['token_count_per_word']['bpe_8000_mean']}",
        f"- Mean tokens/word Unigram: {d['token_count_per_word']['unigram_8000_mean']}",
        f"- Mean chars/token BPE: {d['characters_per_token']['bpe_8000_mean']}",
        f"- Mean chars/token Unigram: {d['characters_per_token']['unigram_8000_mean']}",
        f"- Whole-word token rate BPE: {d['whole_word_token_rate']['bpe_8000']}",
        f"- Whole-word token rate Unigram: {d['whole_word_token_rate']['unigram_8000']}",
        f"- Single-char fragment rate BPE: {d['single_character_fragment_rate']['bpe_8000']}",
        f"- Single-char fragment rate Unigram: {d['single_character_fragment_rate']['unigram_8000']}",
        f"- Unseen-form mean fertility BPE: {d['validation_unseen_form_fragmentation']['mean_bpe_fertility']}",
        f"- Unseen-form mean fertility Unigram: {d['validation_unseen_form_fragmentation']['mean_unigram_fertility']}",
        f"- Corr(log freq, fertility) BPE: {d['correlation_log_frequency_vs_fertility']['bpe_8000_pearson']}",
        f"- Corr(log freq, fertility) Unigram: {d['correlation_log_frequency_vs_fertility']['unigram_8000_pearson']}",
        f"- Corr(length, fertility) BPE: {d['correlation_word_length_vs_fertility']['bpe_8000_pearson']}",
        f"- Corr(length, fertility) Unigram: {d['correlation_word_length_vs_fertility']['unigram_8000_pearson']}",
        "",
        "### Frequency sensitivity",
        "",
        "```json",
        json.dumps(freq_sensitivity, indent=2),
        "```",
        "",
        "### Source sensitivity",
        "",
        "```json",
        json.dumps(source_sensitivity, indent=2),
        "```",
        "",
        "### Surface family consistency (not morphemes)",
        "",
        f"- BPE mean stem-as-piece rate: {fam_bpe.get('mean_stem_piece_rate')}",
        f"- Unigram mean stem-as-piece rate: {fam_uni.get('mean_stem_piece_rate')}",
        "",
        "## Dominant automatic patterns",
        "",
    ]
    for ptn in patterns:
        md.append(f"- `{ptn.get('pattern')}` ({ptn.get('evidence_type')})")
    md += [
        "",
        f"Disagreement export: `{out_dis.relative_to(root)}` (n={len(disagreements)})",
        "",
        "## What this report does not claim",
        "",
        "- Morphological correctness of any tokenization",
        "- That BPE or Unigram is linguistically superior",
        "- That a hybrid method will improve LM test BPC",
        "",
    ]
    write_text(out_report, "\n".join(md))
    print(f"words={n} disagree={n_disagree} exported={len(disagreements)}")
    print(f"wrote {out_sum}")
    print(f"wrote {out_dis}")
    print(f"wrote {out_report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
