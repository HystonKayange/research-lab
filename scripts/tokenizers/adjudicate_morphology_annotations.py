#!/usr/bin/env python3
"""Adjudicate dual morphology annotations into a single reference file.

Development/pilot only. Never loads locked holdout.
Does not invent labels when both annotators left items empty without resolution.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import utc_now_iso, write_json, write_jsonl, write_text  # noqa: E402
from measure_morphology_annotation_agreement import (  # noqa: E402
    load_annotations,
    measure,
    needs_adjudication,
    normalize_annotation,
    refuse_locked,
)

TOOL_NAME = "adjudicate_morphology_annotations"
TOOL_VERSION = "0.1.0"


def auto_merge(na: dict[str, Any], nb: dict[str, Any]) -> dict[str, Any] | None:
    """If annotations already agree, produce adjudicated record without human input."""
    if needs_adjudication(na, nb):
        return None
    segs = na["segments"] if na["segments"] is not None else nb["segments"]
    prop = None
    if segs is not None:
        prop = "+".join(segs)
    tags = sorted(na["phenomenon_tags"] | nb["phenomenon_tags"])
    return {
        "item_id": na["item_id"],
        "surface_form": na.get("surface_form") or nb.get("surface_form"),
        "proposed_segmentation": prop,
        "alternative_segmentation": na.get("alternative_segmentation")
        or nb.get("alternative_segmentation"),
        "boundary_positions": "",
        "phenomenon_tags": tags,
        "no_segmentation_required": na.get("no_segmentation_required")
        if na.get("no_segmentation_required") is not None
        else nb.get("no_segmentation_required"),
        "mixed_language": na.get("mixed_language")
        if na.get("mixed_language") is not None
        else nb.get("mixed_language"),
        "spelling_or_ocr_issue": na.get("spelling_or_ocr_issue")
        if na.get("spelling_or_ocr_issue") is not None
        else nb.get("spelling_or_ocr_issue"),
        "insufficient_context": na.get("insufficient_context")
        if na.get("insufficient_context") is not None
        else nb.get("insufficient_context"),
        "uncertain": False if na.get("uncertain") is False and nb.get("uncertain") is False else na.get("uncertain"),
        "confidence": na.get("confidence") or nb.get("confidence"),
        "annotator_id": "adjudicator_auto_agree",
        "reviewer_id": "adjudicator_auto_agree",
        "adjudication_status": "auto_agreed",
        "notes": "Auto-merged: annotators already agreed.",
        "source_annotators": [na.get("annotator_id"), nb.get("annotator_id")],
    }


def write_queue_csv(path: Path, items: list[dict[str, Any]]) -> None:
    fields = [
        "item_id",
        "surface_form",
        "context_a",
        "annotator_a_segmentation",
        "annotator_b_segmentation",
        "annotator_a_tags",
        "annotator_b_tags",
        "annotator_a_uncertain",
        "annotator_b_uncertain",
        "proposed_segmentation",
        "alternative_segmentation",
        "phenomenon_tags",
        "no_segmentation_required",
        "mixed_language",
        "spelling_or_ocr_issue",
        "insufficient_context",
        "uncertain",
        "confidence",
        "reviewer_id",
        "adjudication_status",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            w.writerow({k: it.get(k, "") for k in fields})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adjudicate dual morphology annotations")
    p.add_argument("--annotator-a", type=Path, required=True)
    p.add_argument("--annotator-b", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/research/morphology_benchmark_v0.1/development/adjudication"),
    )
    p.add_argument(
        "--adjudicated-csv",
        type=Path,
        default=None,
        help="Optional filled adjudication CSV to merge into final JSONL",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()

    def resolve(p: Path) -> Path:
        return p if p.is_absolute() else root / p

    a_path, b_path = resolve(args.annotator_a), resolve(args.annotator_b)
    out_dir = resolve(args.output_dir)
    refuse_locked(a_path)
    refuse_locked(b_path)
    refuse_locked(out_dir)

    a_raw = load_annotations(a_path)
    b_raw = load_annotations(b_path)
    a_map = {k: normalize_annotation(v) for k, v in a_raw.items()}
    b_map = {k: normalize_annotation(v) for k, v in b_raw.items()}
    common = sorted(set(a_map) & set(b_map))

    auto_records: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []

    for iid in common:
        na, nb = a_map[iid], b_map[iid]
        merged = auto_merge(na, nb)
        if merged is not None:
            # attach context if available
            ctx = (a_raw[iid].get("context") or b_raw[iid].get("context") or "")
            merged["context"] = ctx
            auto_records.append(merged)
            continue
        queue.append(
            {
                "item_id": iid,
                "surface_form": na.get("surface_form") or nb.get("surface_form") or "",
                "context_a": a_raw[iid].get("context") or "",
                "annotator_a_segmentation": na.get("proposed_segmentation") or "",
                "annotator_b_segmentation": nb.get("proposed_segmentation") or "",
                "annotator_a_tags": "|".join(sorted(na["phenomenon_tags"])),
                "annotator_b_tags": "|".join(sorted(nb["phenomenon_tags"])),
                "annotator_a_uncertain": na.get("uncertain"),
                "annotator_b_uncertain": nb.get("uncertain"),
                "proposed_segmentation": "",
                "alternative_segmentation": "",
                "phenomenon_tags": "",
                "no_segmentation_required": "",
                "mixed_language": "",
                "spelling_or_ocr_issue": "",
                "insufficient_context": "",
                "uncertain": "",
                "confidence": "",
                "reviewer_id": "",
                "adjudication_status": "pending",
                "notes": "",
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "adjudicated_auto_agree.jsonl", auto_records)
    write_queue_csv(out_dir / "adjudication_queue.csv", queue)

    agreement = measure(a_path, b_path)
    write_json(out_dir / "agreement_snapshot.json", agreement)

    # optional merge of human-filled adjudication CSV
    final: list[dict[str, Any]] = list(auto_records)
    if args.adjudicated_csv:
        adj_path = resolve(args.adjudicated_csv)
        refuse_locked(adj_path)
        filled = load_annotations(adj_path)
        for iid, row in filled.items():
            n = normalize_annotation(row)
            segs = n["segments"]
            final.append(
                {
                    "item_id": iid,
                    "surface_form": n.get("surface_form"),
                    "context": row.get("context_a") or row.get("context") or "",
                    "proposed_segmentation": "+".join(segs) if segs else n.get("proposed_segmentation"),
                    "alternative_segmentation": n.get("alternative_segmentation"),
                    "phenomenon_tags": sorted(n["phenomenon_tags"]),
                    "no_segmentation_required": n.get("no_segmentation_required"),
                    "mixed_language": n.get("mixed_language"),
                    "spelling_or_ocr_issue": n.get("spelling_or_ocr_issue"),
                    "insufficient_context": n.get("insufficient_context"),
                    "uncertain": n.get("uncertain"),
                    "confidence": n.get("confidence"),
                    "annotator_id": row.get("reviewer_id") or "adjudicator",
                    "reviewer_id": row.get("reviewer_id") or "adjudicator",
                    "adjudication_status": row.get("adjudication_status") or "adjudicated",
                    "notes": n.get("notes"),
                }
            )

    final.sort(key=lambda r: str(r.get("item_id")))
    write_jsonl(out_dir / "adjudicated_reference.jsonl", final)

    summary = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "n_common": len(common),
        "n_auto_agreed": len(auto_records),
        "n_queued_for_human_adjudication": len(queue),
        "n_final_records": len(final),
        "outputs": {
            "auto_agree": str(out_dir / "adjudicated_auto_agree.jsonl"),
            "queue": str(out_dir / "adjudication_queue.csv"),
            "final": str(out_dir / "adjudicated_reference.jsonl"),
        },
        "locked_holdout_used": False,
        "test_split_used": False,
    }
    write_json(out_dir / "adjudication_summary.json", summary)
    write_text(
        out_dir / "README.md",
        "\n".join(
            [
                "# Adjudication workspace",
                "",
                f"- Auto-agreed: **{len(auto_records)}**",
                f"- Queued for human adjudication: **{len(queue)}**",
                "",
                "1. Fill `adjudication_queue.csv` (reviewer).",
                "2. Re-run with `--adjudicated-csv adjudication_queue.csv` "
                "(or a filled copy) to refresh `adjudicated_reference.jsonl`.",
                "",
                "Does not include locked holdout items.",
                "",
            ]
        ),
    )
    print(
        f"auto_agree={len(auto_records)} queue={len(queue)} final={len(final)} -> {out_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
