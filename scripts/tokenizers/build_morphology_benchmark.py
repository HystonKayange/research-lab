#!/usr/bin/env python3
"""Build morphology annotation benchmark: development set + locked holdout scaffolding.

Development set: released for human review (~160–240 items, train-primary).
Locked holdout: sealed; ordinary access refused; no release in this task.

Does not invent gold morphology. Does not open LM test split.
"""

from __future__ import annotations

import argparse
import csv
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
    sha256_text,
    utc_now_iso,
    verify_frozen_split,
    write_json,
    write_jsonl,
    write_text,
)
from evaluate_tokenizers import get_encoder  # noqa: E402

TOOL_NAME = "build_morphology_benchmark"
TOOL_VERSION = "0.1.0"
WORD_RE = re.compile(r"\S+")
PUNCT_STRIP = ".,;:!?\"'()[]«»“”‘’…—–-"

# Candidate stratification buckets (labels are hypotheses for human check)
STRATA = [
    "apparent_subject_or_agreement_prefix",
    "apparent_tense_aspect",
    "apparent_object_marking",
    "apparent_negation",
    "apparent_noun_class_contrast",
    "apparent_singular_plural_contrast",
    "apparent_derivational_suffix",
    "apparent_locative",
    "long_agglutinative_looking",
    "frequent_word_family",
    "rare_word",
    "unseen_or_low_frequency",
    "contains_w_hat",
    "mixed_language_form",
    "bpe_unigram_disagreement",
    "apparent_whole_word_memorization",
]

# Surface heuristics only — not gold morphology
AGREE_PREF = ("ndi", "ti", "a", "wa", "mu", "u", "i", "zi", "li", "chi", "ka", "ta")
TA_MARK = ("na", "da", "dza", "ma", "nga", "ka")  # loose
OBJ_MARK = ("ndi", "ku", "mu", "wa", "zi", "chi", "li", "ka")  # highly ambiguous
NEG = ("si", "sa", "osati")
LOC = ("ku", "pa", "mu", "kwa")
DERIV_SUF = ("ira", "era", "itsa", "etsa", "ika", "eka", "idwa", "edwa", "ana")
NC_PAIR_HINTS = (
    ("mu", "a"),
    ("chi", "zi"),
    ("li", "ma"),
    ("ka", "ti"),
)
STEMS = (
    "konda",
    "panga",
    "khala",
    "chita",
    "funa",
    "pita",
    "nena",
    "lemba",
    "werenga",
    "phunzira",
    "tenga",
    "yenda",
    "bwera",
)


def refuse_test(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def strip_punct(w: str) -> str:
    return w.strip(PUNCT_STRIP)


def stable_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def encode_word(fn, w: str) -> list[str]:
    return list(fn(w).tokens)


def load_words(split_root: Path, split: str) -> tuple[Counter[str], dict[str, dict[str, Any]]]:
    refuse_test(split_root / split)
    freq: Counter[str] = Counter()
    info: dict[str, dict[str, Any]] = {}
    for source in ("bible", "wikipedia"):
        path = split_root / split / f"{source}.txt"
        refuse_test(path)
        for li, line in enumerate(load_lines(path)):
            for wi, raw in enumerate(WORD_RE.findall(line)):
                core = strip_punct(raw)
                if len(core) < 2:
                    continue
                freq[core] += 1
                if core not in info:
                    info[core] = {
                        "source": source,
                        "split": split,
                        "line_index": li,
                        "word_index": wi,
                        "context": line[:200],
                        "raw": raw,
                    }
    return freq, info


def assign_strata(
    word: str,
    *,
    train_freq: int,
    seen_train: bool,
    bpe: list[str],
    uni: list[str],
) -> list[str]:
    wl = word.lower()
    hits: list[str] = []
    if any(wl.startswith(p) and len(wl) > len(p) + 2 for p in AGREE_PREF):
        hits.append("apparent_subject_or_agreement_prefix")
    if any(f"na{s}" in wl or wl.startswith(s) for s in TA_MARK) and len(wl) >= 6:
        hits.append("apparent_tense_aspect")
    if any(m in wl[1:6] for m in OBJ_MARK) and len(wl) >= 8:
        hits.append("apparent_object_marking")
    if any(wl.startswith(n) for n in NEG):
        hits.append("apparent_negation")
    for a, b in NC_PAIR_HINTS:
        if wl.startswith(a) or wl.startswith(b):
            hits.append("apparent_noun_class_contrast")
            break
    if wl.endswith("i") or wl.endswith("a") or "ana" in wl:
        # weak plural/sg heuristic — candidate only
        if len(wl) >= 5:
            hits.append("apparent_singular_plural_contrast")
    if any(wl.endswith(s) for s in DERIV_SUF):
        hits.append("apparent_derivational_suffix")
    if any(wl.startswith(x) for x in LOC) and len(wl) >= 5:
        hits.append("apparent_locative")
    if len(word) >= 14 or (len(word) >= 10 and (len(bpe) >= 4 or len(uni) >= 4)):
        hits.append("long_agglutinative_looking")
    if any(s in wl for s in STEMS) and train_freq >= 5:
        hits.append("frequent_word_family")
    if seen_train and train_freq <= 3:
        hits.append("rare_word")
    if (not seen_train) or train_freq <= 2:
        hits.append("unseen_or_low_frequency")
    if "ŵ" in word or "Ŵ" in word:
        hits.append("contains_w_hat")
    if re.search(r"[A-Za-z]{3,}", word) and re.search(r"[^\x00-\x7f]", word):
        hits.append("mixed_language_form")
    if bpe != uni:
        hits.append("bpe_unigram_disagreement")
    if (len(bpe) == 1 and bpe[0].lstrip("▁") == word) or (
        len(uni) == 1 and uni[0].lstrip("▁") == word
    ):
        hits.append("apparent_whole_word_memorization")
    return hits or ["unseen_or_low_frequency"]


def pick_stratified(
    pool: list[dict[str, Any]],
    *,
    n_target: int,
    seed: str,
    prefer_split: str | None,
) -> list[dict[str, Any]]:
    """Greedy stratified sample with deterministic hash order."""
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pool:
        if prefer_split and item["split"] != prefer_split:
            # still allow but lower priority via later sort
            pass
        for st in item["candidate_strata"]:
            by_stratum[st].append(item)

    for st in by_stratum:
        by_stratum[st].sort(
            key=lambda r: stable_hash(f"{seed}:{st}:{r['surface_form']}")
        )

    per_stratum = max(4, n_target // max(len(STRATA), 1))
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take(st: str, k: int) -> None:
        for r in by_stratum.get(st, []):
            if len([c for c in chosen if st in c["candidate_strata"]]) >= k:
                break
            if r["surface_form"] in seen:
                continue
            if prefer_split and r["split"] != prefer_split and st not in (
                "unseen_or_low_frequency",
                "contains_w_hat",
            ):
                continue
            seen.add(r["surface_form"])
            chosen.append(r)

    for st in STRATA:
        take(st, per_stratum)

    # fill
    all_sorted = sorted(pool, key=lambda r: stable_hash(f"{seed}:fill:{r['surface_form']}"))
    for r in all_sorted:
        if len(chosen) >= n_target:
            break
        if r["surface_form"] in seen:
            continue
        if prefer_split and r["split"] != prefer_split:
            continue
        seen.add(r["surface_form"])
        chosen.append(r)

    # if still short (prefer_split too strict), fill without split filter
    for r in all_sorted:
        if len(chosen) >= n_target:
            break
        if r["surface_form"] in seen:
            continue
        seen.add(r["surface_form"])
        chosen.append(r)

    return chosen[:n_target]


def make_dev_record(item: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "item_id": f"morph_dev_{idx:04d}",
        "surface_form": item["surface_form"],
        "context": item["context"],
        "source": item["source"],
        "split": item["split"],
        "line_ref": item["line_ref"],
        "frequency_train": item["frequency_train"],
        "bpe_tokens": item["bpe_tokens"],
        "unigram_tokens": item["unigram_tokens"],
        "automatic_tags": item["automatic_tags"],
        "candidate_strata": item["candidate_strata"],
        "strata_note": (
            "candidate_strata are automatic hypotheses for human verification; "
            "do not treat as gold morphology."
        ),
        "human_segments": None,
        "human_phenomenon_tags": None,
        "alternative_analysis": None,
        "uncertain": None,
        "confidence": None,
        "annotator_id": None,
        "reviewer_id": None,
        "adjudication_status": "unreviewed",
        "notes": None,
    }


def make_holdout_payload_item(item: dict[str, Any], idx: int) -> dict[str, Any]:
    """Full content sealed; not printed in development reports."""
    return {
        "item_id": f"morph_hold_{idx:04d}",
        "surface_form": item["surface_form"],
        "context": item["context"],
        "source": item["source"],
        "split": item["split"],
        "line_ref": item["line_ref"],
        "frequency_train": item["frequency_train"],
        "bpe_tokens": item["bpe_tokens"],
        "unigram_tokens": item["unigram_tokens"],
        "automatic_tags": item["automatic_tags"],
        "candidate_strata": item["candidate_strata"],
        "human_segments": None,
        "human_phenomenon_tags": None,
        "alternative_analysis": None,
        "uncertain": None,
        "confidence": None,
        "annotator_id": None,
        "reviewer_id": None,
        "adjudication_status": "locked_unreleased",
        "notes": None,
    }


def seal_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    blob = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "format": "mthandizi_morphology_holdout_seal_v1",
        "sha256": sha256_text(blob),
        "n_items": len(items),
        "payload_b64": __import__("base64").b64encode(blob.encode("utf-8")).decode("ascii"),
        "access": "blocked_until_method_freeze",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build morphology benchmark scaffolding")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument(
        "--research-config",
        type=Path,
        default=Path("configs/research/mthandizi_tokenizer_research_v0_1.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--dev-size", type=int, default=200)
    p.add_argument("--holdout-size", type=int, default=80)
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    tok_cfg = load_json(
        args.config if args.config.is_absolute() else root / args.config
    )
    research_cfg_path = (
        args.research_config
        if args.research_config.is_absolute()
        else root / args.research_config
    )
    research_cfg = load_json(research_cfg_path) if research_cfg_path.is_file() else {}

    split_root = root / tok_cfg["split_root"]
    exp_root = root / tok_cfg["output_root"]
    bench_root = root / "data/research/morphology_benchmark_v0.1"
    dev_dir = bench_root / "development"
    locked_dir = bench_root / "locked"
    meta_dir = bench_root / "metadata"

    if (dev_dir / "annotation_candidates.jsonl").is_file() and not args.force:
        print("Benchmark exists; use --force to rebuild.")
        return 0

    verify_frozen_split(split_root, tok_cfg)
    encode_bpe, _, _, _ = get_encoder(exp_root, {"kind": "bpe", "vocab_size": 8000})
    encode_uni, _, _, _ = get_encoder(exp_root, {"kind": "unigram", "vocab_size": 8000})

    train_freq, train_info = load_words(split_root, "train")
    val_freq, val_info = load_words(split_root, "validation")

    pool: list[dict[str, Any]] = []
    # train-primary pool
    for w, fr in train_freq.items():
        if len(w) < 3:
            continue
        bpe = encode_word(encode_bpe, w)
        uni = encode_word(encode_uni, w)
        info = train_info[w]
        strata = assign_strata(w, train_freq=fr, seen_train=True, bpe=bpe, uni=uni)
        pool.append(
            {
                "surface_form": w,
                "context": info["context"],
                "source": info["source"],
                "split": "train",
                "frequency_train": fr,
                "bpe_tokens": bpe,
                "unigram_tokens": uni,
                "automatic_tags": strata
                + (["bpe_unigram_disagree"] if bpe != uni else []),
                "candidate_strata": strata,
                "line_ref": {
                    "split": "train",
                    "source": info["source"],
                    "line_index": info["line_index"],
                    "word_index": info["word_index"],
                },
            }
        )
    # validation-derived for holdout preference
    val_pool: list[dict[str, Any]] = []
    for w, fr in val_freq.items():
        if len(w) < 3:
            continue
        tf = int(train_freq.get(w, 0))
        bpe = encode_word(encode_bpe, w)
        uni = encode_word(encode_uni, w)
        info = val_info[w]
        strata = assign_strata(
            w, train_freq=tf, seen_train=w in train_freq, bpe=bpe, uni=uni
        )
        row = {
            "surface_form": w,
            "context": info["context"],
            "source": info["source"],
            "split": "validation",
            "frequency_train": tf,
            "bpe_tokens": bpe,
            "unigram_tokens": uni,
            "automatic_tags": strata
            + (["bpe_unigram_disagree"] if bpe != uni else []),
            "candidate_strata": strata,
            "line_ref": {
                "split": "validation",
                "source": info["source"],
                "line_index": info["line_index"],
                "word_index": info["word_index"],
            },
        }
        val_pool.append(row)

    n_dev = int(research_cfg.get("benchmark", {}).get("development_size", args.dev_size))
    n_hold = int(research_cfg.get("benchmark", {}).get("holdout_size", args.holdout_size))
    n_dev = max(160, min(240, n_dev))
    n_hold = max(40, min(120, n_hold))

    # prefer disagreements and diverse strata in pool ranking
    def interest(r: dict[str, Any]) -> float:
        s = float(len(r["candidate_strata"]))
        if "bpe_unigram_disagreement" in r["candidate_strata"]:
            s += 3
        if "contains_w_hat" in r["candidate_strata"]:
            s += 2
        if "long_agglutinative_looking" in r["candidate_strata"]:
            s += 1.5
        return s

    pool.sort(key=lambda r: (-interest(r), stable_hash(r["surface_form"])))
    val_pool.sort(key=lambda r: (-interest(r), stable_hash(r["surface_form"])))

    # holdout first from val unseen/low-freq so they are not in dev
    holdout_src = [
        r
        for r in val_pool
        if "unseen_or_low_frequency" in r["candidate_strata"]
        or r["frequency_train"] <= 2
    ]
    if len(holdout_src) < n_hold:
        holdout_src = val_pool
    holdout_items_raw = pick_stratified(
        holdout_src, n_target=n_hold, seed="holdout_v0_1", prefer_split="validation"
    )
    holdout_surfaces = {r["surface_form"] for r in holdout_items_raw}

    dev_pool = [r for r in pool if r["surface_form"] not in holdout_surfaces]
    # allow some val into dev only if needed for ŵ etc. — keep train primary
    dev_items_raw = pick_stratified(
        dev_pool, n_target=n_dev, seed="dev_v0_1", prefer_split="train"
    )

    dev_records = [make_dev_record(r, i + 1) for i, r in enumerate(dev_items_raw)]
    hold_payload = [
        make_holdout_payload_item(r, i + 1) for i, r in enumerate(holdout_items_raw)
    ]
    sealed = seal_payload(hold_payload)

    # category distributions without revealing labels
    def dist(records: list[dict[str, Any]], key: str = "candidate_strata") -> dict[str, int]:
        c: Counter[str] = Counter()
        for r in records:
            for st in r.get(key) or []:
                c[st] += 1
        return dict(c.most_common())

    dev_dist = dist(dev_records)
    hold_dist = dist(hold_payload)

    # write development
    dev_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(dev_dir / "annotation_candidates.jsonl", dev_records)

    # CSV template for annotators
    csv_path = dev_dir / "annotation_template.csv"
    fields = [
        "item_id",
        "surface_form",
        "context",
        "source",
        "automatic_tags",
        "candidate_strata",
        "human_segments",
        "human_phenomenon_tags",
        "alternative_analysis",
        "uncertain",
        "confidence",
        "annotator_id",
        "reviewer_id",
        "adjudication_status",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in dev_records:
            row = dict(r)
            row["automatic_tags"] = "|".join(r.get("automatic_tags") or [])
            row["candidate_strata"] = "|".join(r.get("candidate_strata") or [])
            w.writerow(row)

    write_text(
        dev_dir / "README.md",
        "\n".join(
            [
                "# Morphology benchmark v0.1 — development annotation set",
                "",
                "This set is **released for human review**.",
                "",
                "## Important",
                "",
                "- `human_*` fields are **null** until annotated.",
                "- `candidate_strata` / `automatic_tags` are **hypotheses**, not gold morphology.",
                "- Do **not** treat recurring strings as morphemes without annotator confirmation.",
                "- Support **disagreement** and `alternative_analysis`.",
                "- The locked holdout is **not** included here.",
                "",
                f"- Items: **{len(dev_records)}**",
                f"- Primary source split: **train**",
                "",
                "## Files",
                "",
                "- `annotation_candidates.jsonl` — full machine-readable records",
                "- `annotation_template.csv` — spreadsheet-friendly template",
                "",
                "## Annotation fields",
                "",
                "| field | meaning |",
                "|-------|---------|",
                "| human_segments | space- or `+`-separated segments (annotator) |",
                "| human_phenomenon_tags | verified phenomenon tags |",
                "| alternative_analysis | competing segmentation if disagreement |",
                "| uncertain | true if annotator unsure |",
                "| confidence | 1–5 optional |",
                "| adjudication_status | unreviewed / annotated / adjudicated |",
                "",
                "## Category distribution (candidate strata counts; multi-label)",
                "",
            ]
            + [f"- `{k}`: {v}" for k, v in dev_dist.items()]
            + [
                "",
                "## Safety",
                "",
                "- LM test split not used",
                "- No fake gold morphology",
                "",
            ]
        ),
    )

    # locked holdout
    locked_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        locked_dir / "holdout_manifest.json",
        {
            "status": "LOCKED",
            "release_blocked": True,
            "n_items": len(hold_payload),
            "split_preference": "validation_unseen_or_low_frequency",
            "category_distribution_candidate_strata": hold_dist,
            "source_counts": dict(Counter(r["source"] for r in hold_payload)),
            "split_counts": dict(Counter(r["split"] for r in hold_payload)),
            "payload_sha256": sealed["sha256"],
            "payload_file": "holdout_payload.sealed.json",
            "access_policy": (
                "Refuse ordinary access. Release only via "
                "scripts/tokenizers/release_morphology_holdout.py "
                "with --confirm-method-freeze after method freeze."
            ),
            "item_ids": [r["item_id"] for r in hold_payload],
            "line_refs_only": [
                {
                    "item_id": r["item_id"],
                    "line_ref": r["line_ref"],
                    "surface_sha256": sha256_text(r["surface_form"]),
                    "context_sha256": sha256_text(r["context"]),
                }
                for r in hold_payload
            ],
            "note": "Surface forms intentionally omitted from this manifest.",
        },
    )
    write_json(
        locked_dir / "holdout_checksums.json",
        {
            "payload_sha256": sealed["sha256"],
            "n_items": len(hold_payload),
            "item_surface_sha256": {
                r["item_id"]: sha256_text(r["surface_form"]) for r in hold_payload
            },
            "generated_at": utc_now_iso(),
        },
    )
    write_json(locked_dir / "holdout_payload.sealed.json", sealed)
    write_text(
        locked_dir / "RELEASE_BLOCKED",
        "MORPHOLOGY HOLDOUT LOCKED\n"
        "Do not open holdout_payload.sealed.json for method design.\n"
        "Release only after method freeze via release_morphology_holdout.py "
        "--confirm-method-freeze\n",
    )
    write_text(
        locked_dir / "README.md",
        "# Locked morphology holdout\n\n"
        f"- n_items: **{len(hold_payload)}**\n"
        "- Full text: sealed; not for method design\n"
        "- Category distribution: see holdout_manifest.json "
        "(candidate strata only; no human labels)\n"
        "- Status: RELEASE_BLOCKED\n",
    )

    meta_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "benchmark_version": "morphology_benchmark_v0.1",
        "development": {
            "n_items": len(dev_records),
            "path": "data/research/morphology_benchmark_v0.1/development/",
            "strata_distribution": dev_dist,
            "split_counts": dict(Counter(r["split"] for r in dev_records)),
            "source_counts": dict(Counter(r["source"] for r in dev_records)),
            "human_labels_present": False,
        },
        "locked_holdout": {
            "n_items": len(hold_payload),
            "released": False,
            "path": "data/research/morphology_benchmark_v0.1/locked/",
            "strata_distribution": hold_dist,
            "payload_sha256": sealed["sha256"],
        },
        "overlap_dev_holdout_surfaces": 0,
        "test_split_accessed": False,
        "fake_gold_morphology": False,
        "research_config": str(research_cfg_path.relative_to(root))
        if research_cfg_path.is_relative_to(root)
        else str(research_cfg_path),
    }
    # verify no overlap
    dev_set = {r["surface_form"] for r in dev_records}
    hold_set = {r["surface_form"] for r in hold_payload}
    manifest["overlap_dev_holdout_surfaces"] = len(dev_set & hold_set)
    write_json(meta_dir / "benchmark_manifest.json", manifest)
    write_json(root / "data/metadata/morphology_benchmark_v0_1.json", manifest)

    print(
        f"dev={len(dev_records)} holdout={len(hold_payload)} "
        f"overlap={manifest['overlap_dev_holdout_surfaces']} locked=True"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
