#!/usr/bin/env python3
"""Phase A — baseline tokenization failure audit for Chichewa (train+validation only).

Mines BPE/Unigram disagreements and automatic diagnostic tags.
Does not implement a hybrid tokenizer. Does not open the LM test split.
Does not invent human morphology labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

TOOL_NAME = "audit_tokenizer_failures"
TOOL_VERSION = "0.1.0"

WORD_RE = re.compile(r"\S+")
PUNCT_STRIP = ".,;:!?\"'()[]«»“”‘’…—–-"

# High-frequency Chichewa verbal/nominal stems used only as **surface** family keys
# (not claimed morpheme gold).
DEFAULT_STEMS = (
    "konda",
    "panga",
    "khala",
    "chita",
    "funa",
    "pita",
    "nena",
    "gona",
    "ona",
    "bwera",
    "yamba",
    "tsata",
    "mva",
    "dya",
    "gula",
    "lemba",
    "werenga",
    "phunzira",
    "thamanga",
    "seka",
    "lira",
    "ima",
    "yenda",
    "tenga",
    "pereka",
)

THRESH = {
    "high_fragmentation": 4,  # subword pieces for a single word
    "rare_train": 3,
    "frequent_train": 50,
    "long_word": 12,
    "fertility_asymmetric": 2,
    "max_candidates": 2500,
    "context_chars": 180,
}


def strip_punct(w: str) -> str:
    return w.strip(PUNCT_STRIP)


def refuse_test_path(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/test/" in s or s.rstrip("/").endswith("/test"):
        raise RuntimeError(f"refusing test path: {path}")


def surface_pieces(tokens: list[str]) -> list[str]:
    """Normalize SP pieces for word-level comparison (keep ▁ markers)."""
    return list(tokens)


def piece_fertility(tokens: list[str]) -> int:
    return len(tokens)


def encode_word(encode_fn, word: str) -> list[str]:
    """Encode an isolated word surface (SP dummy prefix applies as in training)."""
    res = encode_fn(word)
    return list(res.tokens)


def load_split_inventory(
    split_root: Path, split: str
) -> tuple[Counter[str], dict[str, list[tuple[str, str]]]]:
    """Return frequency of cores and contexts (source, line preview). Never test."""
    if split not in ("train", "validation"):
        raise ValueError(f"only train|validation allowed, got {split}")
    refuse_test_path(split_root / split)
    freq: Counter[str] = Counter()
    contexts: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source in ("bible", "wikipedia"):
        path = split_root / split / f"{source}.txt"
        refuse_test_path(path)
        if not path.is_file():
            continue
        for line in load_lines(path):
            for raw in WORD_RE.findall(line):
                core = strip_punct(raw)
                if not core:
                    continue
                freq[core] += 1
                if len(contexts[core]) < 3:
                    contexts[core].append(
                        (source, line[: THRESH["context_chars"]])
                    )
    return freq, contexts


def mixed_orthography_heuristic(word: str) -> bool:
    has_ascii = bool(re.search(r"[A-Za-z]{3,}", word))
    has_non_ascii = bool(re.search(r"[^\x00-\x7f]", word))
    return has_ascii and has_non_ascii


# Common surface prefixes used only as matching anchors (not gold morphology).
_STEM_PREFIXES = (
    "",
    "ku",
    "kwa",
    "ko",
    "ka",
    "ti",
    "ta",
    "ndi",
    "si",
    "sa",
    "wa",
    "wo",
    "wu",
    "mu",
    "mo",
    "mi",
    "ma",
    "chi",
    "cha",
    "zi",
    "za",
    "li",
    "la",
    "lo",
    "a",
    "ana",
    "an",
    "ama",
    "aka",
    "uku",
    "u",
    "i",
    "o",
    "e",
    "pa",
    "po",
    "ya",
    "yo",
    "ye",
    "nga",
    "nka",
    "mka",
    "dza",
    "dzo",
)


def family_stem(word: str, stems: tuple[str, ...]) -> str | None:
    """Heuristic family key: stem after a short surface prefix, not arbitrary substring.

    Avoids false hits like English 'Manager' matching stem 'ima'.
    """
    wl = word.lower()
    if len(wl) < 4:
        return None
    # skip heavily mixed Latin+digit product-name style tokens for stem families
    if mixed_orthography_heuristic(word) and sum(ch.isupper() for ch in word) >= 2:
        return None
    best: str | None = None
    for stem in sorted(stems, key=len, reverse=True):
        if len(stem) < 3:
            continue
        for pref in _STEM_PREFIXES:
            if not wl.startswith(pref + stem):
                continue
            # require some residual material (affix/extension) beyond stem
            if len(wl) >= len(pref) + len(stem) + 1:
                if best is None or len(stem) > len(best):
                    best = stem
                break
    return best


def pieces_share_stem_surface(pieces: list[str], stem: str) -> bool:
    joined = "".join(p.lstrip("▁") for p in pieces).lower()
    if stem not in joined:
        return False
    # any single piece contains full stem
    for p in pieces:
        if stem in p.lstrip("▁").lower():
            return True
    return False


def vocab_size_sensitive(
    encodings: dict[str, list[str]], model: str
) -> bool:
    """True if 1k/2k/4k/8k piece sequences are not all equal for model."""
    seqs = []
    for vs in (1000, 2000, 4000, 8000):
        key = f"{model}_{vs}"
        if key in encodings:
            seqs.append(tuple(encodings[key]))
    if len(seqs) < 2:
        return False
    return len(set(seqs)) > 1


def automatic_tags(
    *,
    word: str,
    split: str,
    source: str,
    freq_train: int,
    seen_in_train: bool,
    bpe8: list[str],
    uni8: list[str],
    all_enc: dict[str, list[str]],
    stem: str | None,
    family_inconsistent: bool,
) -> list[str]:
    tags: list[str] = []
    if bpe8 != uni8:
        tags.append("bpe_unigram_disagree")
    bf = piece_fertility(bpe8)
    uf = piece_fertility(uni8)
    if bf >= THRESH["high_fragmentation"] or uf >= THRESH["high_fragmentation"]:
        tags.append("high_fragmentation")
    if bf == 1 or uf == 1:
        tags.append("whole_word_single_token")
    if "ŵ" in word or "Ŵ" in word:
        tags.append("contains_w_hat")
    if split == "validation" and not seen_in_train:
        tags.append("unseen_in_train")
    if seen_in_train and freq_train <= THRESH["rare_train"]:
        tags.append("rare_train")
    if freq_train >= THRESH["frequent_train"]:
        tags.append("frequent_train")
    if len(word) >= THRESH["long_word"]:
        tags.append("long_word")
    if mixed_orthography_heuristic(word):
        tags.append("mixed_orthography_heuristic")
    if stem:
        tags.append("family_stem_hit")
        tags.append(f"stem:{stem}")
    if family_inconsistent:
        tags.append("family_segmentation_inconsistent")
    if abs(bf - uf) >= THRESH["fertility_asymmetric"]:
        tags.append("fertility_asymmetric")
    if vocab_size_sensitive(all_enc, "bpe") or vocab_size_sensitive(all_enc, "unigram"):
        tags.append("vocab_size_sensitive")
    tags.append(f"source_{source}")
    tags.append(f"split_{split}")
    return tags


def candidate_priority(tags: list[str], freq_train: int, bpe_f: int, uni_f: int) -> float:
    """Higher = more interesting for the candidate bank."""
    score = 0.0
    weights = {
        "bpe_unigram_disagree": 5.0,
        "family_segmentation_inconsistent": 4.0,
        "high_fragmentation": 3.0,
        "unseen_in_train": 3.0,
        "contains_w_hat": 2.5,
        "fertility_asymmetric": 2.0,
        "mixed_orthography_heuristic": 2.0,
        "long_word": 1.5,
        "vocab_size_sensitive": 1.5,
        "rare_train": 1.5,
        "whole_word_single_token": 1.0,
        "family_stem_hit": 1.0,
        "frequent_train": 0.5,
    }
    for t in tags:
        if t in weights:
            score += weights[t]
        elif t.startswith("stem:"):
            score += 0.2
    score += min(abs(bpe_f - uni_f), 8) * 0.5
    # slight boost for mid-frequency (paradigms)
    if 5 <= freq_train <= 200:
        score += 0.5
    return score


def stable_id(word: str, split: str, source: str) -> str:
    h = hashlib.sha256(f"{split}:{source}:{word}".encode("utf-8")).hexdigest()[:10]
    return h


def build_family_inconsistency(
    word_list: list[str],
    encode_bpe,
    encode_uni,
    stems: tuple[str, ...],
) -> set[str]:
    """Words whose family does not share a stem piece under BPE-8000 or Unigram-8000."""
    by_stem: dict[str, list[str]] = defaultdict(list)
    for w in word_list:
        st = family_stem(w, stems)
        if st:
            by_stem[st].append(w)

    inconsistent: set[str] = set()
    for stem, members in by_stem.items():
        if len(members) < 3:
            continue
        # sample up to 40 members by length diversity
        members = sorted(set(members), key=lambda x: (-len(x), x))[:40]
        bpe_share = []
        uni_share = []
        for w in members:
            bp = encode_word(encode_bpe, w)
            up = encode_word(encode_uni, w)
            bpe_share.append(pieces_share_stem_surface(bp, stem))
            uni_share.append(pieces_share_stem_surface(up, stem))
        # inconsistent if some share and some don't
        if any(bpe_share) and not all(bpe_share):
            for w, ok in zip(members, bpe_share):
                if not ok:
                    inconsistent.add(w)
        if any(uni_share) and not all(uni_share):
            for w, ok in zip(members, uni_share):
                if not ok:
                    inconsistent.add(w)
    return inconsistent


def select_pool(
    train_freq: Counter[str],
    val_freq: Counter[str],
    train_ctx: dict[str, list[tuple[str, str]]],
    val_ctx: dict[str, list[tuple[str, str]]],
    stems: tuple[str, ...],
) -> list[tuple[str, str, str]]:
    """Return list of (word, split, source) prioritized pools merged."""
    pool: dict[str, tuple[str, str]] = {}  # word -> (split, source) preferred val if both

    def add(word: str, split: str, ctx_map: dict) -> None:
        if word not in ctx_map or not ctx_map[word]:
            return
        source, _ = ctx_map[word][0]
        # prefer validation for unseen analysis
        if word in pool and pool[word][0] == "validation":
            return
        if split == "validation" or word not in pool:
            pool[word] = (split, source)

    # priority cohorts
    val_unseen = [w for w in val_freq if w not in train_freq and len(w) >= 4]
    what = [w for w in list(train_freq) + list(val_freq) if "ŵ" in w or "Ŵ" in w]
    long_w = [w for w, c in train_freq.most_common() if len(w) >= THRESH["long_word"]][:8000]
    rare = [w for w, c in train_freq.items() if c <= THRESH["rare_train"] and len(w) >= 5]
    frequent = [w for w, c in train_freq.most_common(3000) if len(w) >= 4]
    family = [w for w in train_freq if family_stem(w, stems)]
    mixed = [w for w in train_freq if mixed_orthography_heuristic(w)]
    val_all = [w for w in val_freq if len(w) >= 4]

    for w in val_unseen:
        add(w, "validation", val_ctx)
    for w in what:
        if w in val_freq:
            add(w, "validation", val_ctx)
        else:
            add(w, "train", train_ctx)
    for cohort in (long_w[:5000], rare[:5000], frequent, family[:8000], mixed[:2000], val_all[:8000]):
        for w in cohort:
            if w in val_freq:
                add(w, "validation", val_ctx)
            else:
                add(w, "train", train_ctx)

    return [(w, split, src) for w, (split, src) in pool.items()]


def load_lm_validation_summary(root: Path) -> dict[str, Any] | None:
    p = root / "data/reports/lm_baselines_v0_1_validation_summary.json"
    if p.is_file():
        return load_json(p)
    return None


def load_morphology_probes(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rel = config.get("morphology_probe_path") or "data/reports/chichewa_morphology_probe_v0_1.jsonl"
    p = root / rel
    if not p.is_file():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def aggregate_stats(candidates: list[dict[str, Any]], n_compared: int) -> dict[str, Any]:
    tag_counts: Counter[str] = Counter()
    for c in candidates:
        for t in c.get("automatic_diagnostic_tags") or []:
            if not t.startswith("stem:") and not t.startswith("source_") and not t.startswith("split_"):
                tag_counts[t] += 1
            elif t.startswith("source_") or t.startswith("split_"):
                tag_counts[t] += 1

    disagree = [c for c in candidates if "bpe_unigram_disagree" in c["automatic_diagnostic_tags"]]
    return {
        "n_words_compared": n_compared,
        "n_candidates_emitted": len(candidates),
        "n_bpe_unigram_disagree_in_bank": len(disagree),
        "tag_counts": dict(tag_counts.most_common()),
        "mean_bpe_fertility_bank": (
            sum(c["bpe_fertility"] for c in candidates) / len(candidates) if candidates else None
        ),
        "mean_unigram_fertility_bank": (
            sum(c["unigram_fertility"] for c in candidates) / len(candidates) if candidates else None
        ),
        "split_counts": dict(Counter(c["split"] for c in candidates)),
        "source_counts": dict(Counter(c["source"] for c in candidates)),
        "caution": (
            "Automatic tags are not morphological gold labels. "
            "human_phenomenon_tags remain null until annotation."
        ),
    }


def mechanism_map_from_stats(stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Link measured automatic failure classes to proposed (unimplemented) mechanisms."""
    tags = stats.get("tag_counts") or {}
    rows = [
        {
            "failure_class": "bpe_unigram_disagree",
            "count_in_candidate_bank": tags.get("bpe_unigram_disagree", 0),
            "interpretation": (
                "Surface evidence that two strong unsupervised methods choose different "
                "segmentations; morphology is one possible explanation among several."
            ),
            "proposed_mechanism": (
                "Hybrid constraints: prefer inventory-backed boundaries when annotation "
                "supports them; otherwise keep Unigram/BPE backbone."
            ),
            "evaluation": "Family agreement and human boundary F1 on annotated sample; val BPC.",
        },
        {
            "failure_class": "family_segmentation_inconsistent",
            "count_in_candidate_bank": tags.get("family_segmentation_inconsistent", 0),
            "interpretation": (
                "Within surface stem families, stem string is not consistently realized as a piece."
            ),
            "proposed_mechanism": "Shared stem piece inventory with optional forced merges.",
            "evaluation": "Per-family shared-piece rate; no large fertility regression.",
        },
        {
            "failure_class": "high_fragmentation",
            "count_in_candidate_bank": tags.get("high_fragmentation", 0),
            "interpretation": "Many pieces per word — sequence cost and weaker type sharing risk.",
            "proposed_mechanism": "Productive affix/stem pieces instead of character-like shatter.",
            "evaluation": "Fertility on rare/unseen-validation; LM val BPC under fixed updates.",
        },
        {
            "failure_class": "whole_word_single_token",
            "count_in_candidate_bank": tags.get("whole_word_single_token", 0),
            "interpretation": "Opaque whole-word tokens may hurt generalization to unseen forms.",
            "proposed_mechanism": "Discourage low-count whole-word pieces; favour composition.",
            "evaluation": "Unseen-validation fertility; paradigm completion diagnostics.",
        },
        {
            "failure_class": "unseen_in_train",
            "count_in_candidate_bank": tags.get("unseen_in_train", 0),
            "interpretation": "Validation-only types stress compositional generalization.",
            "proposed_mechanism": "Composition-first segmentation for OOV types.",
            "evaluation": "Val OOV subset BPC (validation only); never test for design.",
        },
        {
            "failure_class": "contains_w_hat",
            "count_in_candidate_bank": tags.get("contains_w_hat", 0),
            "interpretation": "Orthographic edge case; may be representation, not morphology.",
            "proposed_mechanism": "Preserve identity normalization; retain ŵ in inventory.",
            "evaluation": "No fertility regression on ŵ subset vs Unigram-8000.",
        },
        {
            "failure_class": "mixed_orthography_heuristic",
            "count_in_candidate_bank": tags.get("mixed_orthography_heuristic", 0),
            "interpretation": "Heuristic mixed orthography / loan-like surfaces (not language ID).",
            "proposed_mechanism": "Fallback to backbone; optional bilingual piece seeds if justified.",
            "evaluation": "Domain-stratified val metrics; avoid English-centric vocab bloat.",
        },
    ]
    return rows


def render_report(
    *,
    meta: dict[str, Any],
    stats: dict[str, Any],
    mechanisms: list[dict[str, Any]],
    lm_snippet: dict[str, Any] | None,
    examples: list[dict[str, Any]],
) -> str:
    lines = [
        "# Tokenizer failure audit v0.1 (Phase A)",
        "",
        f"_Generated {meta.get('generated_at')} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "## Scope",
        "",
        "- Splits used: **train**, **validation** only",
        "- LM **test** split: **not accessed**",
        "- Hybrid tokenizer implementation: **not in this phase**",
        "- Human morphology labels: **not invented** (`human_*` fields null)",
        "",
        "## Inputs",
        "",
        f"- Config: `{meta.get('config')}`",
        f"- Experiment root: `{meta.get('experiment_root')}`",
        f"- Frozen split verified: `{meta.get('frozen_split_verified')}`",
        f"- Models loaded: {meta.get('models_loaded')}",
        f"- Morphology probes incorporated: {meta.get('n_morphology_probes')}",
        "",
        "## Aggregate diagnostics (candidate bank)",
        "",
        f"- Words compared (pool): **{stats.get('n_words_compared')}**",
        f"- Candidates emitted: **{stats.get('n_candidates_emitted')}**",
        f"- BPE≠Unigram (8000) in bank: **{stats.get('n_bpe_unigram_disagree_in_bank')}**",
        f"- Mean BPE-8000 fertility (bank): {stats.get('mean_bpe_fertility_bank')}",
        f"- Mean Unigram-8000 fertility (bank): {stats.get('mean_unigram_fertility_bank')}",
        f"- Split counts: `{stats.get('split_counts')}`",
        f"- Source counts: `{stats.get('source_counts')}`",
        "",
        "### Tag counts",
        "",
    ]
    for tag, n in (stats.get("tag_counts") or {}).items():
        lines.append(f"- `{tag}`: {n}")
    lines.extend(
        [
            "",
            f"**Caution:** {stats.get('caution')}",
            "",
            "## Link to LM validation (existing r2; test not run)",
            "",
        ]
    )
    if lm_snippet:
        lines.append("Provisional validation leaders (from prior audit):")
        lines.append("")
        for g in lm_snippet.get("groups") or []:
            lines.append(
                f"- {g.get('track')} × {g.get('budget_policy')}: "
                f"**{g.get('provisional_validation_leader')}** "
                f"(mean BPC={g.get('provisional_validation_leader_mean_bpc')})"
            )
        lines.append("")
        lines.append(
            "These LM results motivate studying why Unigram performed better on "
            "validation under these budgets; they do **not** by themselves prove "
            "morphological adequacy of Unigram pieces."
        )
    else:
        lines.append("_LM validation summary not found; skip linkage._")

    lines.extend(
        [
            "",
            "## Failure class → proposed mechanism map (design only)",
            "",
            "| failure_class | count | proposed_mechanism |",
            "|---------------|------:|--------------------|",
        ]
    )
    for m in mechanisms:
        lines.append(
            f"| {m['failure_class']} | {m['count_in_candidate_bank']} | {m['proposed_mechanism'][:80]}… |"
            if len(m["proposed_mechanism"]) > 80
            else f"| {m['failure_class']} | {m['count_in_candidate_bank']} | {m['proposed_mechanism']} |"
        )

    lines.extend(
        [
            "",
            "Full mechanism notes are in `mechanism_map.json` and "
            "`docs/tokenizers/MTHANDIZI_RESEARCH_BLUEPRINT.md`.",
            "",
            "## Example disagreements (sample)",
            "",
        ]
    )
    for c in examples[:25]:
        lines.append(
            f"- `{c['surface_form']}` ({c['split']}/{c['source']}, "
            f"freq_train={c['frequency_train']}): "
            f"BPE={c['bpe_tokens']} Unigram={c['unigram_tokens']} "
            f"tags={c['automatic_diagnostic_tags']}"
        )

    lines.extend(
        [
            "",
            "## What this audit does **not** claim",
            "",
            "- That automatic tags equal morphological truth",
            "- That Unigram or BPE is morphologically correct",
            "- That a hybrid tokenizer will improve LM test BPC",
            "- That results transfer to all Bantu languages",
            "",
            "## Next phases",
            "",
            "1. Stratified human annotation of a fixed sample (`human_*` fields)",
            "2. Estimate how often disagreements are genuinely morphological",
            "3. Only then implement hybrid mechanisms that map to measured classes",
            "4. Validate under the same four LM comparison groups; keep test locked",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase A tokenizer failure audit (no test).")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/tokenizers/baselines_v0_1.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/reports/tokenizer_failure_audit_v0_1"),
    )
    p.add_argument("--max-candidates", type=int, default=THRESH["max_candidates"])
    p.add_argument("--max-compare", type=int, default=12000, help="Max words to encode fully")
    p.add_argument("--dry-run", action="store_true", help="Load models and inventory only")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    split_root = root / config["split_root"]
    exp_root = root / config["output_root"]
    out_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir

    # safety: never configure test
    for key in ("combined", "bible", "wikipedia"):
        if key in (config.get("training_inputs") or {}):
            refuse_test_path(config["training_inputs"][key])
    refuse_test_path(split_root / "train")
    refuse_test_path(split_root / "validation")

    freeze_info = verify_frozen_split(split_root, config)

    models = discover_models(exp_root)
    encoders: dict[str, Any] = {}
    for spec in models:
        encode_fn, vocab_size, _unk, tid = get_encoder(exp_root, spec)
        encoders[tid] = encode_fn
    required = ["character", "bpe_8000", "unigram_8000"]
    for r in required:
        if r not in encoders:
            raise FileNotFoundError(f"required tokenizer missing: {r}")

    if args.dry_run:
        print(f"dry-run ok: models={list(encoders)} freeze={freeze_info.get('frozen')}")
        return 0

    train_freq, train_ctx = load_split_inventory(split_root, "train")
    val_freq, val_ctx = load_split_inventory(split_root, "validation")

    stems = DEFAULT_STEMS
    pool = select_pool(train_freq, val_freq, train_ctx, val_ctx, stems)
    # deterministic order
    pool.sort(key=lambda x: (x[1], x[2], x[0]))
    if len(pool) > args.max_compare:
        # keep all ŵ and unseen val, then fill by hash
        priority = []
        rest = []
        for item in pool:
            w, split, src = item
            if "ŵ" in w or "Ŵ" in w or (split == "validation" and w not in train_freq):
                priority.append(item)
            else:
                rest.append(item)
        rest.sort(
            key=lambda it: hashlib.sha256(it[0].encode()).hexdigest()
        )
        pool = (priority + rest)[: args.max_compare]

    print(f"Comparing {len(pool)} word surfaces…")

    # family inconsistency on a broader train member set
    family_words = [w for w in train_freq if family_stem(w, stems) and len(w) >= 5]
    family_words = sorted(family_words, key=lambda w: (-train_freq[w], w))[:4000]
    family_inconsistent = build_family_inconsistency(
        family_words, encoders["bpe_8000"], encoders["unigram_8000"], stems
    )
    print(f"Family-inconsistent surfaces (heuristic): {len(family_inconsistent)}")

    # include morphology probe words
    probes = load_morphology_probes(root, config)
    probe_words: list[str] = []
    pool_words = {x[0] for x in pool}
    for pr in probes:
        w = strip_punct(pr.get("word") or "")
        if not w:
            continue
        probe_words.append(w)
        if w in pool_words:
            continue
        if w in val_freq:
            split = "validation"
        elif w in train_freq:
            split = "train"
        else:
            # probe word not in inventories (stripped/punct edge): keep as train diagnostic
            split = "train"
        src = pr.get("source") if pr.get("source") in ("bible", "wikipedia") else "wikipedia"
        pool.append((w, split, src))
        pool_words.add(w)

    # re-unique pool
    seen_w: set[str] = set()
    uniq_pool: list[tuple[str, str, str]] = []
    for w, split, src in pool:
        if w in seen_w:
            continue
        seen_w.add(w)
        uniq_pool.append((w, split, src))
    pool = uniq_pool

    subword_ids = [
        tid
        for tid in encoders
        if tid.startswith("bpe_") or tid.startswith("unigram_")
    ]

    scored: list[tuple[float, dict[str, Any]]] = []
    n_disagree_8000 = 0
    for idx, (word, split, source) in enumerate(pool):
        if idx and idx % 2000 == 0:
            print(f"  …{idx}/{len(pool)}")
        all_enc: dict[str, list[str]] = {}
        for tid in subword_ids + ["character"]:
            try:
                all_enc[tid] = encode_word(encoders[tid], word)
            except Exception:
                all_enc[tid] = []
        bpe8 = all_enc.get("bpe_8000") or []
        uni8 = all_enc.get("unigram_8000") or []
        if bpe8 != uni8:
            n_disagree_8000 += 1

        freq_tr = int(train_freq.get(word, 0))
        seen = word in train_freq
        stem = family_stem(word, stems)
        fam_inc = word in family_inconsistent
        tags = automatic_tags(
            word=word,
            split=split,
            source=source,
            freq_train=freq_tr,
            seen_in_train=seen,
            bpe8=bpe8,
            uni8=uni8,
            all_enc=all_enc,
            stem=stem,
            family_inconsistent=fam_inc,
        )
        # only emit if interesting
        interesting = any(
            t in tags
            for t in (
                "bpe_unigram_disagree",
                "high_fragmentation",
                "family_segmentation_inconsistent",
                "contains_w_hat",
                "unseen_in_train",
                "fertility_asymmetric",
                "mixed_orthography_heuristic",
                "vocab_size_sensitive",
            )
        )
        if not interesting and word not in probe_words:
            continue

        ctx_map = val_ctx if split == "validation" else train_ctx
        ctx = ""
        if word in ctx_map and ctx_map[word]:
            source = ctx_map[word][0][0]
            ctx = ctx_map[word][0][1]
        # probe context override
        for pr in probes:
            if strip_punct(pr.get("word") or "") == word and pr.get("context"):
                ctx = str(pr["context"])[: THRESH["context_chars"]]
                if pr.get("source") in ("bible", "wikipedia"):
                    source = pr["source"]
                break

        rec = {
            "candidate_id": f"failure_{stable_id(word, split, source)}",
            "surface_form": word,
            "context": ctx,
            "source": source,
            "split": split,
            "frequency_train": freq_tr,
            "seen_in_train": seen,
            "bpe_tokens": bpe8,
            "unigram_tokens": uni8,
            "bpe_fertility": piece_fertility(bpe8),
            "unigram_fertility": piece_fertility(uni8),
            "encodings_by_tokenizer": {tid: all_enc[tid] for tid in sorted(all_enc)},
            "character_tokens": all_enc.get("character"),
            "automatic_diagnostic_tags": tags,
            "human_phenomenon_tags": None,
            "human_segments": None,
            "human_notes": None,
            "uncertain": None,
            "probe_overlap": word in set(probe_words),
        }
        score = candidate_priority(
            tags, freq_tr, rec["bpe_fertility"], rec["unigram_fertility"]
        )
        scored.append((score, rec))

    scored.sort(key=lambda x: (-x[0], x[1]["surface_form"]))
    max_c = int(args.max_candidates)
    candidates = []
    for i, (score, rec) in enumerate(scored[:max_c], start=1):
        rec = dict(rec)
        rec["candidate_id"] = f"failure_{i:06d}"
        rec["priority_rank"] = i
        rec["priority_score"] = score
        candidates.append(rec)

    stats = aggregate_stats(candidates, n_compared=len(pool))
    stats["n_bpe_unigram_disagree_in_pool"] = n_disagree_8000
    stats["n_family_inconsistent_heuristic"] = len(family_inconsistent)
    mechanisms = mechanism_map_from_stats(stats)

    lm_sum = load_lm_validation_summary(root)
    lm_snippet = None
    if lm_sum:
        lm_snippet = {
            "matrix_id": lm_sum.get("matrix_id"),
            "number_of_valid_runs": lm_sum.get("number_of_valid_runs"),
            "groups": [
                {
                    "track": g.get("track"),
                    "budget_policy": g.get("budget_policy"),
                    "provisional_validation_leader": g.get("provisional_validation_leader"),
                    "provisional_validation_leader_mean_bpc": g.get(
                        "provisional_validation_leader_mean_bpc"
                    ),
                    "tokenizer_mean_bpc": {
                        tok: (g.get("tokenizers") or {}).get(tok, {})
                        .get("mean_validation_bpc", {})
                        .get("mean")
                        for tok in ("character", "bpe_8000", "unigram_8000")
                    },
                }
                for g in lm_sum.get("groups") or []
            ],
        }

    meta = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "config": str(config_path.relative_to(root)) if config_path.is_relative_to(root) else str(config_path),
        "config_sha256": sha256_file(config_path),
        "experiment_root": str(Path(config["output_root"])),
        "split_root": str(Path(config["split_root"])),
        "frozen_split_verified": bool(freeze_info.get("frozen")),
        "models_loaded": sorted(encoders.keys()),
        "n_morphology_probes": len(probes),
        "thresholds": THRESH,
        "stems_surface_keys": list(stems),
        "test_split_accessed": False,
        "hybrid_tokenizer_implemented": False,
        "lm_validation_linkage": lm_snippet,
        "stats": stats,
        "outputs": {
            "failure_candidates": "failure_candidates.jsonl",
            "aggregate": "aggregate_diagnostics.json",
            "mechanism_map": "mechanism_map.json",
            "report": "FAILURE_AUDIT_REPORT.md",
        },
        "research_blueprint": "docs/tokenizers/MTHANDIZI_RESEARCH_BLUEPRINT.md",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "failure_candidates.jsonl", candidates)
    write_json(out_dir / "aggregate_diagnostics.json", {"meta": meta, "stats": stats})
    write_json(out_dir / "mechanism_map.json", {"mechanisms": mechanisms, "caution": stats["caution"]})
    write_json(out_dir / "audit_manifest.json", meta)
    report = render_report(
        meta=meta,
        stats=stats,
        mechanisms=mechanisms,
        lm_snippet=lm_snippet,
        examples=[c for c in candidates if "bpe_unigram_disagree" in c["automatic_diagnostic_tags"]],
    )
    write_text(out_dir / "FAILURE_AUDIT_REPORT.md", report)
    # also copy-level pointer in data/reports
    write_text(root / "data/reports/tokenizer_failure_audit_v0_1.md", report)
    write_json(
        root / "data/metadata/tokenizer_failure_audit_v0_1.json",
        {
            "tool": meta["tool"],
            "generated_at": meta["generated_at"],
            "output_dir": str(out_dir.relative_to(root)) if out_dir.is_relative_to(root) else str(out_dir),
            "n_candidates": len(candidates),
            "test_split_accessed": False,
            "stats_summary": {
                "n_words_compared": stats["n_words_compared"],
                "n_bpe_unigram_disagree_in_pool": stats.get("n_bpe_unigram_disagree_in_pool"),
                "n_candidates_emitted": stats["n_candidates_emitted"],
                "tag_counts": stats.get("tag_counts"),
            },
        },
    )

    print(
        f"Done. candidates={len(candidates)} "
        f"disagree_pool={n_disagree_8000} out={out_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
