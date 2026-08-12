#!/usr/bin/env python3
"""Merge pilot 40 + remaining 160 Annotator A annotations into full development set.

Never overwrites pilot annotation source file.
Validates 200 unique IDs and surface reconstruction where segmentations exist.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import write_json, write_jsonl  # noqa: E402
from evaluate_morphology_boundaries import parse_segments  # noqa: E402

TOOL_NAME = "merge_annotator_a_full_200"
TOOL_VERSION = "0.1.0"

CSV_FIELDS = [
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
    "benchmark_partition",
    "adjudication_status",
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


def load_csv_annotations(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            iid = row.get("item_id")
            if not iid:
                continue
            # skip empty rows
            if not any(
                (row.get(k) or "").strip()
                for k in (
                    "proposed_segmentation",
                    "no_segmentation_required",
                    "mixed_language",
                    "uncertain",
                    "notes",
                )
            ):
                continue
            rec = dict(row)
            tags = rec.get("phenomenon_tags") or ""
            if isinstance(tags, str) and tags.strip():
                rec["phenomenon_tags"] = [t.strip() for t in tags.replace(",", "|").split("|") if t.strip()]
            else:
                rec["phenomenon_tags"] = []
            for bk in (
                "no_segmentation_required",
                "mixed_language",
                "spelling_or_ocr_issue",
                "insufficient_context",
                "uncertain",
            ):
                v = (rec.get(bk) or "").strip().lower()
                if v in ("true", "1", "yes"):
                    rec[bk] = True
                elif v in ("false", "0", "no"):
                    rec[bk] = False
                elif v == "":
                    rec[bk] = None
            rec["annotator_id"] = rec.get("annotator_id") or "annotator_a"
            out[iid] = rec
    return out


def reconstruction_ok(surface: str, segmentation: str | None) -> bool:
    if segmentation is None or str(segmentation).strip() == "":
        return True  # empty allowed with flags
    segs = parse_segments(segmentation)
    if not segs:
        return True
    return "".join(segs) == surface


def is_filled(r: dict[str, Any]) -> bool:
    if r.get("proposed_segmentation") not in (None, ""):
        return True
    if r.get("no_segmentation_required") is True:
        return True
    if r.get("mixed_language") is True:
        return True
    if r.get("spelling_or_ocr_issue") is True and r.get("proposed_segmentation") in (None, ""):
        return True
    if r.get("adjudication_status") == "annotated":
        return True
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge Annotator A pilot+remaining into full 200")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit non-zero unless all 200 items are filled",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    dev = root / "data/research/morphology_benchmark_v0.1/development"
    ann_dir = dev / "annotations"

    candidates = load_jsonl(dev / "annotation_candidates.jsonl")
    pilot_items = load_jsonl(dev / "pilot_40.jsonl")
    pilot_ids = {r["item_id"] for r in pilot_items}
    pilot_ann = load_jsonl(ann_dir / "annotator_a_annotations.jsonl")

    remaining_ann: dict[str, dict[str, Any]] = {}
    rem_jsonl = ann_dir / "annotator_a_remaining_160_annotations.jsonl"
    rem_csv = ann_dir / "annotator_a_remaining_160.csv"
    rem_progress_csv = ann_dir / "annotator_a_remaining_160_progress.csv"
    if rem_jsonl.is_file():
        for r in load_jsonl(rem_jsonl):
            remaining_ann[r["item_id"]] = r
    for path in (rem_csv, rem_progress_csv):
        if path.is_file():
            for iid, r in load_csv_annotations(path).items():
                # jsonl wins if already present and filled
                if iid in remaining_ann and is_filled(remaining_ann[iid]):
                    continue
                if is_filled(r):
                    remaining_ann[iid] = r

    errors: list[str] = []
    full: list[dict[str, Any]] = []
    for c in candidates:
        iid = c["item_id"]
        if iid in pilot_ids:
            src = next((x for x in pilot_ann if x["item_id"] == iid), None)
            if src is None:
                errors.append(f"missing pilot annotation: {iid}")
                continue
            rec = dict(src)
            rec["benchmark_partition"] = "pilot_40"
        else:
            if iid in remaining_ann:
                rec = dict(remaining_ann[iid])
            else:
                rec = {
                    "item_id": iid,
                    "surface_form": c["surface_form"],
                    "context": c.get("context") or "",
                    "source": c.get("source") or "",
                    "proposed_segmentation": None,
                    "alternative_segmentation": None,
                    "phenomenon_tags": None,
                    "no_segmentation_required": None,
                    "mixed_language": None,
                    "spelling_or_ocr_issue": None,
                    "insufficient_context": None,
                    "uncertain": None,
                    "confidence": None,
                    "annotator_id": "annotator_a",
                    "notes": None,
                    "adjudication_status": "pending_remaining",
                }
            rec.setdefault("surface_form", c["surface_form"])
            rec.setdefault("context", c.get("context") or "")
            rec.setdefault("source", c.get("source") or "")
            rec["benchmark_partition"] = "remaining_160"

        # reconstruction
        seg = rec.get("proposed_segmentation")
        surface = rec.get("surface_form") or c["surface_form"]
        if seg not in (None, "") and not reconstruction_ok(surface, str(seg)):
            errors.append(
                f"{iid}: segmentation does not reconstruct surface "
                f"({seg!r} vs {surface!r})"
            )
        alt = rec.get("alternative_segmentation")
        if alt not in (None, "") and not reconstruction_ok(surface, str(alt)):
            errors.append(f"{iid}: alternative segmentation does not reconstruct")

        # preserve flags if present
        for k in (
            "uncertain",
            "alternative_segmentation",
            "no_segmentation_required",
            "mixed_language",
            "spelling_or_ocr_issue",
            "insufficient_context",
            "phenomenon_tags",
            "confidence",
            "notes",
        ):
            rec.setdefault(k, None)

        if str(iid).startswith("morph_hold_"):
            errors.append(f"holdout id in development merge: {iid}")

        full.append(rec)

    ids = [r["item_id"] for r in full]
    if len(full) != 200:
        errors.append(f"n={len(full)} != 200")
    if len(set(ids)) != 200:
        errors.append("duplicate item_ids")

    n_filled = sum(1 for r in full if is_filled(r))
    n_pilot = sum(1 for r in full if r.get("benchmark_partition") == "pilot_40")
    n_rem = sum(1 for r in full if r.get("benchmark_partition") == "remaining_160")
    n_rem_filled = sum(
        1
        for r in full
        if r.get("benchmark_partition") == "remaining_160" and is_filled(r)
    )

    out_jsonl = ann_dir / "annotator_a_full_200.jsonl"
    out_csv = ann_dir / "annotator_a_full_200.csv"
    write_jsonl(out_jsonl, full)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in full:
            row = {k: r.get(k) for k in CSV_FIELDS}
            tags = row.get("phenomenon_tags")
            if isinstance(tags, list):
                row["phenomenon_tags"] = "|".join(tags)
            for k, v in list(row.items()):
                if v is None:
                    row[k] = ""
                elif isinstance(v, bool):
                    row[k] = "true" if v else "false"
            w.writerow(row)

    report = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc(),
        "n_total": len(full),
        "n_unique_ids": len(set(ids)),
        "n_pilot": n_pilot,
        "n_remaining": n_rem,
        "n_filled": n_filled,
        "n_remaining_filled": n_rem_filled,
        "pilot_source_preserved": str(ann_dir / "annotator_a_annotations.jsonl"),
        "outputs": {"jsonl": str(out_jsonl), "csv": str(out_csv)},
        "errors": errors,
        "status": "complete" if n_filled == 200 and not errors else "incomplete_or_errors",
        "annotator_count": 1,
        "annotator_id": "annotator_a",
    }
    write_json(ann_dir / "annotator_a_full_200_merge_report.json", report)

    print(
        f"merged n={len(full)} filled={n_filled}/200 "
        f"remaining_filled={n_rem_filled}/160 errors={len(errors)}"
    )
    for e in errors[:20]:
        print(" ERROR:", e)
    if errors:
        return 1
    if args.require_complete and n_filled != 200:
        print("require-complete: not all 200 filled")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
