#!/usr/bin/env python3
"""Generate side-by-side tokenization examples and morphology probe candidates.

Does not fill human_morpheme_segments. Train-text only for probe word mining.
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
    CharacterTokenizer,
    SentencePieceWrapper,
    load_json,
    load_lines,
    sha256_file,
    verify_frozen_split,
    write_jsonl,
    write_text,
)
from evaluate_tokenizers import discover_models, get_encoder  # noqa: E402

TOOL_NAME = "inspect_tokenizations"
TOOL_VERSION = "0.1.0"


def stable_rng_pick(items: list[Any], k: int, seed: int) -> list[Any]:
    """Deterministic sample without Python hash randomization."""
    if not items:
        return []
    scored = []
    for i, item in enumerate(items):
        h = hashlib.sha256(f"{seed}:{i}:{item}".encode("utf-8")).hexdigest()
        scored.append((h, item))
    scored.sort(key=lambda x: x[0])
    # unique preserving order of sorted hash
    out: list[Any] = []
    seen = set()
    for _h, item in scored:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= k:
            break
    return out


def mine_morphology_probes(
    train_bible: Path,
    train_wiki: Path,
    *,
    n: int,
    seed: int,
    min_len: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    word_contexts: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for source, path in (("bible", train_bible), ("wikipedia", train_wiki)):
        for line in load_lines(path):
            words = re.findall(r"\S+", line)
            for w in words:
                core = w.strip(".,;:!?\"'()[]«»")
                if len(core) < min_len:
                    continue
                word_contexts[core].append((source, line[:200]))

    # candidate pools
    all_words = list(word_contexts.keys())
    with_what = [w for w in all_words if "ŵ" in w or "Ŵ" in w]
    long_words = [w for w in all_words if len(w) >= 12]
    # prefix families
    family_keys = [
        "konda",
        "panga",
        "khala",
        "chita",
        "funa",
        "pita",
        "nena",
        "gona",
        "dya",
        "mva",
        "ona",
        "bwera",
        "yamba",
        "tsata",
    ]
    family_words: list[str] = []
    for fk in family_keys:
        hits = [w for w in all_words if fk in w.lower() and len(w) >= min_len]
        family_words.extend(hits[:30])

    # frequent content words
    freq = Counter()
    for w, ctxs in word_contexts.items():
        freq[w] += len(ctxs)
    frequent = [w for w, _c in freq.most_common(500) if len(w) >= min_len]

    mixed = [
        w
        for w in all_words
        if re.search(r"[A-Za-z]{3,}", w)
        and re.search(r"[^\x00-\x7f]", w)
    ]

    pools = [
        ("w_hat", with_what, 12),
        ("long", long_words, 15),
        ("family", family_words, 25),
        ("frequent", frequent, 15),
        ("mixed", mixed, 8),
    ]
    chosen: list[str] = []
    seen: set[str] = set()
    for _name, pool, k in pools:
        for w in stable_rng_pick(pool, k, seed):
            if w not in seen:
                seen.add(w)
                chosen.append(w)
    # fill remaining
    for w in stable_rng_pick(all_words, n * 2, seed + 1):
        if len(chosen) >= n:
            break
        if w not in seen:
            seen.add(w)
            chosen.append(w)

    for i, w in enumerate(chosen[:n]):
        src, ctx = word_contexts[w][0]
        records.append(
            {
                "probe_id": f"probe_{i+1:04d}",
                "word": w,
                "source": src,
                "context": ctx,
                "human_morpheme_segments": None,
                "human_notes": None,
            }
        )
    return records


def collect_example_texts(config: dict[str, Any], split_root: Path) -> list[dict[str, str]]:
    texts: list[dict[str, str]] = []
    for t in config.get("example_texts") or []:
        texts.append({"text": t, "category": "configured"})
    # from splits (eval only for display — not for training)
    for split, cat in (("validation", "validation_sample"), ("train", "train_sample")):
        for sid in ("bible", "wikipedia"):
            p = split_root / split / f"{sid}.txt"
            if not p.is_file():
                continue
            lines = load_lines(p)
            # pick a few mid-length lines deterministically
            candidates = [L for L in lines if 40 <= len(L) <= 160]
            for L in stable_rng_pick(candidates, 3, 42 + len(sid)):
                texts.append({"text": L, "category": f"{cat}_{sid}"})
    return texts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect tokenizations and build morphology probes.")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    exp_root = root / config["output_root"]
    split_root = root / config["split_root"]

    try:
        verify_frozen_split(split_root, config)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    models = discover_models(exp_root)
    if not models:
        print("error: no models to inspect", file=sys.stderr)
        return 1

    # Morphology probes from TRAIN only
    train_bible = root / config["training_inputs"]["bible"]
    train_wiki = root / config["training_inputs"]["wikipedia"]
    for p in (train_bible, train_wiki):
        if "/train/" not in str(p).replace("\\", "/"):
            print(f"error: probe mining path not under train: {p}", file=sys.stderr)
            return 1

    probe_cfg = config.get("morphology_probe") or {}
    probes = mine_morphology_probes(
        train_bible,
        train_wiki,
        n=int(probe_cfg.get("n_candidates", 80)),
        seed=int(probe_cfg.get("seed", 0)),
        min_len=int(probe_cfg.get("min_word_len", 4)),
    )
    write_jsonl(root / config["morphology_probe_path"], probes)

    example_texts = collect_example_texts(config, split_root)
    # add morphology words
    for pr in probes[:25]:
        example_texts.append(
            {
                "text": pr["word"],
                "category": "morphology_probe_word",
                "probe_id": pr["probe_id"],
            }
        )
    # long/w_hat extras
    example_texts.append({"text": "Malaŵi", "category": "w_hat"})
    example_texts.append({"text": "ndimakukonda", "category": "agglutination_like"})

    rows: list[dict[str, Any]] = []
    for spec in models:
        encode, _vsz, _unk, tid = get_encoder(exp_root, spec)
        for ex in example_texts:
            text = ex["text"]
            res = encode(text)
            rows.append(
                {
                    "text": text,
                    "category": ex.get("category"),
                    "probe_id": ex.get("probe_id"),
                    "tokenizer_id": tid,
                    "tokens": res.tokens,
                    "token_ids": res.ids,
                    "token_count": len(res.ids),
                }
            )

    examples_path = root / config["examples_path"]
    write_jsonl(examples_path, rows)
    eval_examples = exp_root / "evaluation" / "examples.jsonl"
    write_jsonl(eval_examples, rows)

    # README for experiment root
    write_text(
        exp_root / "README.md",
        "# Tokenizer baselines v0.1\n\n"
        "Character + SentencePiece BPE/Unigram trained on frozen train split only.\n\n"
        f"Morphology probe (unlabeled): `{config['morphology_probe_path']}`\n"
        f"Examples: `{config['examples_path']}`\n"
        f"Report: `{config['report_path']}`\n",
    )

    print(f"Wrote {len(probes)} morphology probes → {config['morphology_probe_path']}")
    print(f"Wrote {len(rows)} example rows → {config['examples_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
