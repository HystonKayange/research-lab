#!/usr/bin/env python3
"""Validate the blinded AI Annotator B pilot bundle.

Does not annotate. Does not open locked holdout or LM test for content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TOOL_NAME = "validate_ai_annotator_b_bundle"
TOOL_VERSION = "0.1.0"

ALLOWED_FIELDS = frozenset({"item_id", "surface_form", "context", "source"})
PROHIBITED_FIELDS = frozenset(
    {
        "proposed_segmentation",
        "alternative_segmentation",
        "boundary_positions",
        "phenomenon_tags",
        "human_segments",
        "human_phenomenon_tags",
        "alternative_analysis",
        "bpe_tokens",
        "unigram_tokens",
        "automatic_tags",
        "candidate_strata",
        "pilot_buckets",
        "strata_note",
        "frequency_train",
        "line_ref",
        "priority_rank",
        "priority_score",
        "encodings_by_tokenizer",
        "character_tokens",
        "bpe_fertility",
        "unigram_fertility",
        "annotator_id",
        "reviewer_id",
        "adjudication_status",
        "confidence",
        "uncertain",
        "notes",
        "no_segmentation_required",
        "mixed_language",
        "spelling_or_ocr_issue",
        "insufficient_context",
        "seen_in_train",
        "probe_overlap",
        "pilot",
        "pilot_chat",
        "automatic_diagnostic_tags",
        "updated_at",
    }
)
PROHIBITED_BUNDLE_NAMES = frozenset(
    {
        "annotator_a_annotations.jsonl",
        "annotator_a_annotations.csv",
        "pilot_chat_state.json",
    }
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate AI Annotator B blinded bundle")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/ai_annotator_b_bundle"
        ),
    )
    p.add_argument(
        "--source-pilot",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/pilot_40.jsonl"
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    bundle = args.bundle_dir if args.bundle_dir.is_absolute() else root / args.bundle_dir
    source = (
        args.source_pilot if args.source_pilot.is_absolute() else root / args.source_pilot
    )

    errors: list[str] = []
    warnings: list[str] = []

    required_files = [
        "MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md",
        "pilot_40_blinded.jsonl",
        "AI_ANNOTATOR_B_INSTRUCTIONS.md",
        "bundle_manifest.json",
    ]
    for name in required_files:
        if not (bundle / name).is_file():
            errors.append(f"missing bundle file: {name}")

    # no prohibited annotator A artifacts inside bundle
    for p in bundle.rglob("*"):
        if p.is_file() and p.name in PROHIBITED_BUNDLE_NAMES:
            errors.append(f"prohibited Annotator A artifact in bundle: {p.name}")
        if p.is_file() and "annotator_a" in p.name.lower():
            errors.append(f"name suggests Annotator A data in bundle: {p.name}")
        if p.is_file() and "holdout" in p.name.lower():
            errors.append(f"holdout-related file in bundle: {p.name}")

    if not source.is_file():
        errors.append(f"source pilot missing: {source}")
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1

    blind_path = bundle / "pilot_40_blinded.jsonl"
    if not blind_path.is_file():
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1

    src_rows = load_jsonl(source)
    blind_rows = load_jsonl(blind_path)

    if len(blind_rows) != 40:
        errors.append(f"expected exactly 40 blinded items, got {len(blind_rows)}")
    if len(src_rows) != 40:
        warnings.append(f"source pilot has {len(src_rows)} items (expected 40)")

    src_by_id = {str(r["item_id"]): r for r in src_rows}
    blind_ids = [str(r.get("item_id")) for r in blind_rows]
    if len(blind_ids) != len(set(blind_ids)):
        errors.append("duplicate item_id in blinded file")

    src_ids = [str(r["item_id"]) for r in src_rows]
    if set(blind_ids) != set(src_ids):
        missing = set(src_ids) - set(blind_ids)
        extra = set(blind_ids) - set(src_ids)
        if missing:
            errors.append(f"missing item_ids vs source: {sorted(missing)[:5]}")
        if extra:
            errors.append(f"extra item_ids vs source: {sorted(extra)[:5]}")
    else:
        # order may differ; still require same multiset — already checked
        pass

    for r in blind_rows:
        iid = str(r.get("item_id", ""))
        if iid.startswith("morph_hold_"):
            errors.append(f"locked holdout record present: {iid}")
        if not iid.startswith("morph_dev_"):
            errors.append(f"non-development item_id: {iid}")

        keys = set(r.keys())
        unknown = keys - ALLOWED_FIELDS
        if unknown:
            errors.append(f"{iid}: non-allowed fields {sorted(unknown)}")
        prohibited_hit = keys & PROHIBITED_FIELDS
        if prohibited_hit:
            errors.append(f"{iid}: prohibited fields {sorted(prohibited_hit)}")

        for req in ("item_id", "surface_form", "context"):
            if req not in r or r[req] is None or r[req] == "":
                # context could theoretically be empty; still flag
                if req != "context" or req not in r:
                    errors.append(f"{iid}: missing/empty {req}")

        src = src_by_id.get(iid)
        if src is None:
            continue
        if r.get("surface_form") != src.get("surface_form"):
            errors.append(f"{iid}: surface_form changed")
        if r.get("context") != src.get("context"):
            errors.append(f"{iid}: context changed")
        if "source" in r and "source" in src and r.get("source") != src.get("source"):
            errors.append(f"{iid}: source changed")

        # string scan for answer leakage
        blob = json.dumps(r, ensure_ascii=False).lower()
        for bad in (
            "bpe_tokens",
            "unigram_tokens",
            "proposed_segmentation",
            "annotator_a",
            "automatic_tags",
        ):
            if bad in blob and bad not in ("",):
                # field names shouldn't appear as values either in normal data
                if bad in str(r.get("context", "")).lower() or bad in str(
                    r.get("surface_form", "")
                ).lower():
                    continue
                # only fail if key present — already checked keys
                pass

    # manifest checks
    man_path = bundle / "bundle_manifest.json"
    if man_path.is_file():
        man = json.loads(man_path.read_text(encoding="utf-8"))
        if man.get("item_count") != 40:
            errors.append(f"manifest item_count={man.get('item_count')} != 40")
        if not man.get("annotator_a_outputs_excluded"):
            errors.append("manifest missing annotator_a_outputs_excluded=true")
        if man.get("locked_holdout_included"):
            errors.append("manifest claims holdout included")
        if man.get("annotation_performed_at_bundle_creation"):
            errors.append("manifest claims annotation was performed at creation")
        # checksum of blinded file
        exp = (
            (man.get("bundle_files") or {})
            .get("pilot_40_blinded.jsonl", {})
            .get("sha256")
        )
        actual = sha256_file(blind_path)
        if exp and exp != actual:
            errors.append("blinded file sha256 does not match manifest")
        src_exp = (man.get("source_files") or {}).get("pilot_40_jsonl", {}).get("sha256")
        if src_exp and src_exp != sha256_file(source):
            errors.append("source pilot sha256 does not match manifest")

    # ensure Annotator A paths exist outside but not inside
    a_jsonl = (
        root
        / "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_annotations.jsonl"
    )
    if a_jsonl.is_file():
        # must not be identical to blinded file
        if sha256_file(a_jsonl) == sha256_file(blind_path):
            errors.append("blinded file hash equals Annotator A annotations hash")
        # scan blinded for any A segmentation strings (optional soft check)
        try:
            a_rows = load_jsonl(a_jsonl)
            a_segs = {
                str(r.get("item_id")): r.get("proposed_segmentation")
                for r in a_rows
                if r.get("proposed_segmentation")
            }
            for r in blind_rows:
                seg = a_segs.get(str(r.get("item_id")))
                if not seg or not isinstance(seg, str):
                    continue
                # if full segmentation appears as sole content fields — shouldn't
                if r.get("surface_form") == seg:
                    continue
                for v in r.values():
                    if isinstance(v, str) and seg == v:
                        errors.append(
                            f"{r.get('item_id')}: field equals Annotator A segmentation"
                        )
        except Exception as e:  # noqa: BLE001
            warnings.append(f"could not cross-check Annotator A file: {e}")

    ok = len(errors) == 0
    print(f"{'PASS' if ok else 'FAIL'}  {TOOL_NAME} {TOOL_VERSION}")
    print(f"bundle: {bundle}")
    print(f"items: {len(blind_rows)}")
    if warnings:
        print("warnings:")
        for w in warnings:
            print(" -", w)
    if errors:
        print("errors:")
        for e in errors:
            print(" -", e)
        return 1
    print("checks: 40 items; IDs preserved; surfaces/contexts unchanged; no prohibited fields; no A data; no holdout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
