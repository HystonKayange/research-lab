#!/usr/bin/env python3
"""Prepare remaining 160 development items for single Annotator A.

Does not overwrite pilot annotations. Does not fill human labels.
Does not include BPE/Unigram suggestions in annotation templates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import sha256_file, write_json, write_jsonl, write_text  # noqa: E402

TOOL_NAME = "prepare_annotator_a_remaining_160"
TOOL_VERSION = "0.1.0"

ANNOT_CSV_FIELDS = [
    "item_id",
    "surface_form",
    "context",
    "source",
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


def utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def stable_pick(ids: list[str], k: int, seed: str) -> list[str]:
    scored = sorted(ids, key=lambda i: hashlib.sha256(f"{seed}:{i}".encode()).hexdigest())
    return scored[:k]


def empty_ann_fields(item: dict[str, Any], annotator_id: str = "annotator_a") -> dict[str, Any]:
    return {
        "item_id": item["item_id"],
        "surface_form": item["surface_form"],
        "context": item.get("context") or "",
        "source": item.get("source") or "",
        "split": item.get("split"),
        "line_ref": item.get("line_ref"),
        "proposed_segmentation": None,
        "alternative_segmentation": None,
        "boundary_positions": None,
        "phenomenon_tags": None,
        "no_segmentation_required": None,
        "mixed_language": None,
        "spelling_or_ocr_issue": None,
        "insufficient_context": None,
        "uncertain": None,
        "confidence": None,
        "annotator_id": annotator_id,
        "notes": None,
        "adjudication_status": "pending_remaining",
        "human_segments": None,
        "human_phenomenon_tags": None,
        "source_item_preserved": True,
        # explicitly no tokenizer hints
        "tokenizer_hints_included": False,
    }


def source_record_for_remaining(item: dict[str, Any]) -> dict[str, Any]:
    """Keep provenance fields; strip tokenizer/auto tags for remaining pool file."""
    return {
        "item_id": item["item_id"],
        "surface_form": item["surface_form"],
        "context": item.get("context") or "",
        "source": item.get("source") or "",
        "split": item.get("split"),
        "line_ref": item.get("line_ref"),
        "frequency_train": item.get("frequency_train"),
        # keep strata for researcher sampling only — NOT for UI
        "candidate_strata": item.get("candidate_strata"),
        "automatic_tags": item.get("automatic_tags"),
        "bpe_tokens": item.get("bpe_tokens"),
        "unigram_tokens": item.get("unigram_tokens"),
        "note": (
            "Tokenizer fields retained in remaining_160.jsonl for researcher provenance only. "
            "Annotation CSV and UI must not expose them."
        ),
    }


def write_ann_csv(path: Path, rows: list[dict[str, Any]], *, blank_answers: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ANNOT_CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = {k: r.get(k) for k in ANNOT_CSV_FIELDS}
            if blank_answers:
                for k in (
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
                    "notes",
                ):
                    row[k] = ""
                row["annotator_id"] = "annotator_a"
            else:
                tags = row.get("phenomenon_tags")
                if isinstance(tags, list):
                    row["phenomenon_tags"] = "|".join(tags)
                for k, v in list(row.items()):
                    if v is None:
                        row[k] = ""
                    elif isinstance(v, bool):
                        row[k] = "true" if v else "false"
            w.writerow(row)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare remaining 160 + full merge scaffolding")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    dev = root / "data/research/morphology_benchmark_v0.1/development"
    ann_dir = dev / "annotations"
    ann_dir.mkdir(parents=True, exist_ok=True)

    cand_path = dev / "annotation_candidates.jsonl"
    pilot_path = dev / "pilot_40.jsonl"
    pilot_ann_path = ann_dir / "annotator_a_annotations.jsonl"

    candidates = load_jsonl(cand_path)
    pilot_items = load_jsonl(pilot_path)
    pilot_ids = {r["item_id"] for r in pilot_items}
    if len(candidates) != 200:
        raise SystemExit(f"expected 200 candidates, got {len(candidates)}")
    if len(pilot_ids) != 40:
        raise SystemExit(f"expected 40 pilot ids, got {len(pilot_ids)}")

    remaining_src = [r for r in candidates if r["item_id"] not in pilot_ids]
    if len(remaining_src) != 160:
        raise SystemExit(f"expected 160 remaining, got {len(remaining_src)}")

    remaining_path = dev / "remaining_160.jsonl"
    remaining_csv = ann_dir / "annotator_a_remaining_160.csv"
    full_jsonl = ann_dir / "annotator_a_full_200.jsonl"
    full_csv = ann_dir / "annotator_a_full_200.csv"
    self_review = dev / "self_review_25_blinded.jsonl"
    prep_manifest = ann_dir / "annotator_a_remaining_160_prep_manifest.json"

    if remaining_path.is_file() and not args.force:
        print(f"exists: {remaining_path} (use --force)")
    else:
        write_jsonl(remaining_path, [source_record_for_remaining(r) for r in remaining_src])

    # CSV for annotation: no BPE/Unigram
    remaining_blank = [empty_ann_fields(r) for r in remaining_src]
    write_ann_csv(remaining_csv, remaining_blank, blank_answers=True)

    # Do not overwrite pilot annotations
    if not pilot_ann_path.is_file():
        raise SystemExit(f"missing pilot annotations: {pilot_ann_path}")
    pilot_ann = load_jsonl(pilot_ann_path)
    if len(pilot_ann) != 40:
        raise SystemExit(f"pilot annotations count {len(pilot_ann)} != 40")
    pilot_ann_ids = {r["item_id"] for r in pilot_ann}
    if pilot_ann_ids != pilot_ids:
        raise SystemExit("pilot annotation IDs do not match pilot_40.jsonl")

    # Optional remaining annotations if already started
    remaining_ann_path = ann_dir / "annotator_a_remaining_160_annotations.jsonl"
    remaining_ann_by_id: dict[str, dict[str, Any]] = {}
    if remaining_ann_path.is_file():
        for r in load_jsonl(remaining_ann_path):
            remaining_ann_by_id[r["item_id"]] = r

    # Build full 200: pilot filled + remaining (annotated if present else pending blank)
    full_by_id: dict[str, dict[str, Any]] = {}
    for r in pilot_ann:
        full_by_id[r["item_id"]] = dict(r)
        full_by_id[r["item_id"]]["benchmark_partition"] = "pilot_40"
    for r in remaining_src:
        iid = r["item_id"]
        if iid in remaining_ann_by_id:
            rec = empty_ann_fields(r)
            for k, v in remaining_ann_by_id[iid].items():
                if v is not None and v != "":
                    rec[k] = v
        else:
            rec = empty_ann_fields(r)
        rec["benchmark_partition"] = "remaining_160"
        full_by_id[iid] = rec

    # order by original candidate order
    full_rows = []
    for r in candidates:
        iid = r["item_id"]
        if iid not in full_by_id:
            raise SystemExit(f"missing from full merge: {iid}")
        full_rows.append(full_by_id[iid])

    if len(full_rows) != 200:
        raise SystemExit(f"full rows {len(full_rows)} != 200")
    if len({r["item_id"] for r in full_rows}) != 200:
        raise SystemExit("duplicate item_id in full 200")

    n_pilot_filled = sum(
        1
        for r in full_rows
        if r.get("benchmark_partition") == "pilot_40"
        and (
            r.get("proposed_segmentation")
            or r.get("no_segmentation_required") is True
            or r.get("mixed_language") is True
        )
    )
    n_remaining_filled = sum(
        1
        for r in full_rows
        if r.get("benchmark_partition") == "remaining_160"
        and (
            (r.get("proposed_segmentation") not in (None, ""))
            or r.get("no_segmentation_required") is True
            or r.get("mixed_language") is True
            or r.get("adjudication_status") == "annotated"
        )
    )

    write_jsonl(full_jsonl, full_rows)
    write_ann_csv(full_csv, full_rows, blank_answers=False)

    # Self-review 25: deterministic from all 200 development IDs (blinded)
    all_ids = [r["item_id"] for r in candidates]
    review_ids = stable_pick(all_ids, 25, seed="self_review_v0_1_annotator_a")
    blinded = []
    for r in candidates:
        if r["item_id"] not in review_ids:
            continue
        if str(r["item_id"]).startswith("morph_hold_"):
            raise SystemExit("holdout in self-review")
        blinded.append(
            {
                "item_id": r["item_id"],
                "surface_form": r["surface_form"],
                "context": r.get("context") or "",
                "source": r.get("source") or "",
                "self_review": True,
                "annotator_id": "annotator_a",
                "pass": "delayed_reannotation",
                "note": "Original annotation hidden. Re-annotate later for self-consistency.",
            }
        )
    # stable order by id
    blinded.sort(key=lambda x: x["item_id"])
    if len(blinded) != 25:
        raise SystemExit(f"self-review count {len(blinded)}")
    write_jsonl(self_review, blinded)

    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc(),
        "annotator_id": "annotator_a",
        "annotator_count": 1,
        "development_benchmark_mode": "single_native_speaker",
        "pilot_40": {
            "path": str(pilot_path.relative_to(root)),
            "annotations": str(pilot_ann_path.relative_to(root)),
            "n": 40,
            "preserved": True,
            "not_overwritten": True,
        },
        "remaining_160": {
            "path": str(remaining_path.relative_to(root)),
            "annotation_csv": str(remaining_csv.relative_to(root)),
            "annotations_jsonl_target": str(remaining_ann_path.relative_to(root)),
            "n": 160,
            "n_annotated_so_far": n_remaining_filled,
        },
        "full_200": {
            "jsonl": str(full_jsonl.relative_to(root)),
            "csv": str(full_csv.relative_to(root)),
            "n": 200,
            "unique_ids": 200,
            "n_pilot_filled": n_pilot_filled,
            "n_remaining_filled": n_remaining_filled,
            "status": (
                "complete"
                if n_pilot_filled == 40 and n_remaining_filled == 160
                else "pilot_complete_remaining_pending"
            ),
        },
        "self_review_25": {
            "path": str(self_review.relative_to(root)),
            "n": 25,
            "selection_seed": "self_review_v0_1_annotator_a",
            "original_annotations_hidden": True,
            "comparison_deferred_until_second_pass": True,
        },
        "human_ai_pilot": {
            "status": "exploratory_only",
            "not_gold": True,
            "exclude_from_final_development_benchmark_gold": True,
            "note": "Claude/AI co-pilot chat data is not gold; Annotator A native labels are development labels.",
        },
        "tokenizer_hints_in_annotation_csv": False,
        "locked_holdout_released": False,
        "lm_test_evaluations": 0,
        "source_checksums": {
            "annotation_candidates": sha256_file(cand_path),
            "pilot_40": sha256_file(pilot_path),
            "pilot_annotations": sha256_file(pilot_ann_path),
        },
    }
    write_json(prep_manifest, manifest)

    write_text(
        dev / "REMAINING_160_README.md",
        "\n".join(
            [
                "# Remaining 160 — Annotator A",
                "",
                "Single native-speaker annotator (`annotator_a`).",
                "",
                "## Files",
                "",
                f"- Pool: `{remaining_path.relative_to(root)}`",
                f"- Annotation CSV (no BPE/Unigram): `{remaining_csv.relative_to(root)}`",
                f"- Progress JSONL (create/update while annotating): `{remaining_ann_path.relative_to(root)}`",
                f"- Merged full 200: `{full_jsonl.relative_to(root)}`",
                "",
                "## Annotate (UI, no tokenizer hints)",
                "",
                "```bash",
                ".venv/bin/python scripts/tokenizers/morphology_annotation_ui.py \\",
                "  --items data/research/morphology_benchmark_v0.1/development/remaining_160.jsonl \\",
                "  --annotator-id annotator_a \\",
                "  --save data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160_annotations.jsonl \\",
                "  --export-csv data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160_progress.csv \\",
                "  --hide-tokenizer-hints \\",
                "  --port 8765",
                "```",
                "",
                "Or fill the CSV and convert with merge script.",
                "",
                "## Merge after remaining complete",
                "",
                "```bash",
                ".venv/bin/python scripts/tokenizers/merge_annotator_a_full_200.py",
                "```",
                "",
                "Pilot: pilot annotations are never overwritten.",
                "",
                f"Guidelines: `docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md`",
                "",
            ]
        ),
    )

    print(
        f"remaining=160 pilot_preserved=40 full_200_written "
        f"pilot_filled={n_pilot_filled} remaining_filled={n_remaining_filled} "
        f"self_review=25"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
