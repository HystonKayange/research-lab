#!/usr/bin/env python3
"""Build a stratified 40-item pilot subset from the morphology development set.

Does not touch locked holdout. Does not invent human labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import load_json, utc_now_iso, write_json, write_jsonl, write_text  # noqa: E402

TOOL_NAME = "prepare_morphology_annotation_pilot"
TOOL_VERSION = "0.1.0"

# Pilot strata mapping from candidate_strata / automatic tags / surface heuristics
PILOT_BUCKETS = [
    "bpe_unigram_disagreement",
    "long_forms",
    "rare_forms",
    "unseen_like_forms",
    "apparent_prefix_patterns",
    "apparent_suffix_patterns",
    "noun_related_patterns",
    "verb_related_patterns",
    "contains_w_hat",
    "mixed_language_forms",
    "uncertain_automatic_candidates",
]


def refuse_locked(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked holdout path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def stable_rank(item_id: str, seed: str = "pilot_v0_1") -> str:
    return hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def assign_pilot_buckets(row: dict[str, Any]) -> list[str]:
    tags = set(row.get("candidate_strata") or []) | set(row.get("automatic_tags") or [])
    surface = row.get("surface_form") or ""
    buckets: list[str] = []
    if "bpe_unigram_disagreement" in tags or "bpe_unigram_disagree" in tags:
        buckets.append("bpe_unigram_disagreement")
    if "long_agglutinative_looking" in tags or len(surface) >= 12:
        buckets.append("long_forms")
    if "rare_word" in tags or int(row.get("frequency_train") or 0) <= 3:
        buckets.append("rare_forms")
    if "unseen_or_low_frequency" in tags or not row.get("frequency_train"):
        buckets.append("unseen_like_forms")
    if any(
        t.startswith("apparent_subject")
        or "prefix" in t
        or t == "apparent_negation"
        or t == "apparent_locative"
        for t in tags
    ):
        buckets.append("apparent_prefix_patterns")
    if "apparent_derivational_suffix" in tags or any("suffix" in t for t in tags):
        buckets.append("apparent_suffix_patterns")
    if "apparent_noun_class_contrast" in tags or "apparent_singular_plural_contrast" in tags:
        buckets.append("noun_related_patterns")
    # verb-ish surface: common TA/agreement + stem-ish or long verbal-looking
    if any(
        t in tags
        for t in (
            "apparent_subject_or_agreement_prefix",
            "apparent_tense_aspect",
            "apparent_object_marking",
            "apparent_derivational_suffix",
        )
    ):
        buckets.append("verb_related_patterns")
    if "contains_w_hat" in tags or "ŵ" in surface or "Ŵ" in surface:
        buckets.append("contains_w_hat")
    if "mixed_language_form" in tags or "mixed_orthography_heuristic" in tags:
        buckets.append("mixed_language_forms")
    # uncertain automatic: many strata, or no disagreement and few clear tags
    n_strata = len(row.get("candidate_strata") or [])
    if n_strata >= 6 or (
        "bpe_unigram_disagreement" not in buckets and n_strata >= 4 and len(surface) >= 8
    ):
        buckets.append("uncertain_automatic_candidates")
    if not buckets:
        buckets.append("uncertain_automatic_candidates")
    return buckets


def pick_stratified(rows: list[dict[str, Any]], n: int = 40) -> list[dict[str, Any]]:
    by_b: dict[str, list[dict[str, Any]]] = defaultdict(list)
    enriched = []
    for r in rows:
        b = assign_pilot_buckets(r)
        rr = dict(r)
        rr["pilot_buckets"] = b
        enriched.append(rr)
        for bucket in b:
            by_b[bucket].append(rr)
    for b in by_b:
        by_b[b].sort(key=lambda r: (stable_rank(r["item_id"]), r["item_id"]))

    per = max(2, n // max(len(PILOT_BUCKETS), 1))
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take(bucket: str, k: int) -> None:
        for r in by_b.get(bucket, []):
            if r["item_id"] in seen:
                continue
            # count how many already cover this bucket among chosen
            cover = sum(1 for c in chosen if bucket in c.get("pilot_buckets", []))
            if cover >= k:
                break
            seen.add(r["item_id"])
            chosen.append(r)

    for bucket in PILOT_BUCKETS:
        take(bucket, per)

    # fill to n deterministically
    rest = sorted(enriched, key=lambda r: (stable_rank(r["item_id"]), r["item_id"]))
    for r in rest:
        if len(chosen) >= n:
            break
        if r["item_id"] in seen:
            continue
        seen.add(r["item_id"])
        chosen.append(r)

    chosen = chosen[:n]
    chosen.sort(key=lambda r: r["item_id"])
    return chosen


ANNOTATION_CSV_FIELDS = [
    "item_id",
    "surface_form",
    "context",
    "source",
    "split",
    "bpe_tokens",
    "unigram_tokens",
    "automatic_tags",
    "candidate_strata",
    "pilot_buckets",
    "proposed_segmentation",
    "alternative_segmentation",
    "boundary_positions",
    "phenomenon_tags",
    "no_segmentation_required",
    "mixed_language",
    "spelling_or_ocr_issue",
    "insufficient_context",
    "uncertain",
    "confidence",
    "annotator_id",
    "notes",
]


def to_annotation_csv_row(item: dict[str, Any], annotator_id: str) -> dict[str, str]:
    return {
        "item_id": item["item_id"],
        "surface_form": item.get("surface_form") or "",
        "context": item.get("context") or "",
        "source": item.get("source") or "",
        "split": item.get("split") or "",
        "bpe_tokens": " ".join(item.get("bpe_tokens") or []),
        "unigram_tokens": " ".join(item.get("unigram_tokens") or []),
        "automatic_tags": "|".join(item.get("automatic_tags") or []),
        "candidate_strata": "|".join(item.get("candidate_strata") or []),
        "pilot_buckets": "|".join(item.get("pilot_buckets") or []),
        "proposed_segmentation": "",
        "alternative_segmentation": "",
        "boundary_positions": "",
        "phenomenon_tags": "",
        "no_segmentation_required": "",
        "mixed_language": "",
        "spelling_or_ocr_issue": "",
        "insufficient_context": "",
        "uncertain": "",
        "confidence": "",
        "annotator_id": annotator_id,
        "notes": "",
    }


def write_annotator_csv(path: Path, items: list[dict[str, Any]], annotator_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ANNOTATION_CSV_FIELDS)
        w.writeheader()
        for item in items:
            w.writerow(to_annotation_csv_row(item, annotator_id))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare morphology annotation pilot (40 items)")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--dev-jsonl",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotation_candidates.jsonl"
        ),
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/morphology_benchmark_v0.1/development"),
    )
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    dev_path = args.dev_jsonl if args.dev_jsonl.is_absolute() else root / args.dev_jsonl
    out_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    refuse_locked(dev_path)
    refuse_locked(out_dir)

    pilot_path = out_dir / "pilot_40.jsonl"
    if pilot_path.is_file() and not args.force:
        print(f"exists: {pilot_path} (use --force)")
        return 0

    rows = load_jsonl(dev_path)
    if len(rows) < args.n:
        raise SystemExit(f"development set too small: {len(rows)} < {args.n}")

    pilot = pick_stratified(rows, n=args.n)
    # ensure only development item_ids
    for r in pilot:
        if not str(r["item_id"]).startswith("morph_dev_"):
            raise SystemExit(f"non-dev item leaked into pilot: {r['item_id']}")
        # clear any human fields — pilot starts blank
        r["human_segments"] = None
        r["human_phenomenon_tags"] = None
        r["alternative_analysis"] = None
        r["uncertain"] = None
        r["confidence"] = None
        r["annotator_id"] = None
        r["reviewer_id"] = None
        r["adjudication_status"] = "pilot_unreviewed"
        r["notes"] = None
        r["pilot"] = True

    write_jsonl(pilot_path, pilot)
    write_annotator_csv(out_dir / "pilot_40_annotator_a.csv", pilot, "annotator_a")
    write_annotator_csv(out_dir / "pilot_40_annotator_b.csv", pilot, "annotator_b")

    # bucket coverage stats
    cov: dict[str, int] = {b: 0 for b in PILOT_BUCKETS}
    for r in pilot:
        for b in r.get("pilot_buckets") or []:
            if b in cov:
                cov[b] += 1

    man = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "n_pilot": len(pilot),
        "source_development_n": len(rows),
        "item_ids": [r["item_id"] for r in pilot],
        "bucket_coverage_counts": cov,
        "note": "Pilot is a subset of development; not the locked holdout.",
        "locked_holdout_used": False,
        "test_split_used": False,
        "human_labels_filled": False,
    }
    write_json(out_dir / "pilot_40_manifest.json", man)
    write_text(
        out_dir / "PILOT_README.md",
        "\n".join(
            [
                "# Morphology annotation pilot (40 items)",
                "",
                "Subset of the **development** set for the annotation pilot.",
                "**Not** the locked morphology holdout.",
                "",
                f"- Items: **{len(pilot)}**",
                "- Annotator templates: `pilot_40_annotator_a.csv`, `pilot_40_annotator_b.csv`",
                "- Guidelines: `docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md`",
                "",
                "Automatic tags are **hypotheses**. Do not copy them as gold.",
                "",
                "Bucket coverage (multi-label):",
                "",
            ]
            + [f"- `{k}`: {v}" for k, v in cov.items()]
            + ["", "Human labels start empty.", ""]
        ),
    )
    print(f"pilot={len(pilot)} wrote {pilot_path}")
    print("bucket_coverage", cov)
    return 0


if __name__ == "__main__":
    sys.exit(main())
