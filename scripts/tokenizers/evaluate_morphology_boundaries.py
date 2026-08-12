#!/usr/bin/env python3
"""Morphology boundary metrics once human labels exist.

Supports gold human_segments vs system segmentations.
Does not invent gold labels. Refuses LM test paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import load_json, utc_now_iso, write_json, write_text  # noqa: E402

TOOL_NAME = "evaluate_morphology_boundaries"
TOOL_VERSION = "0.1.0"


def refuse_test(path: Path | str) -> None:
    if "/test/" in str(path).replace("\\", "/"):
        raise RuntimeError(f"refusing test path: {path}")


def parse_segments(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x)]
    s = str(raw).strip()
    if not s:
        return None
    if "+" in s:
        parts = [p.strip() for p in s.split("+") if p.strip()]
    else:
        parts = [p.strip() for p in s.split() if p.strip()]
    return parts or None


def boundaries_from_segments(segments: list[str]) -> set[int]:
    """Character offsets after which a boundary occurs (exclusive end positions of pieces)."""
    bounds: set[int] = set()
    pos = 0
    for i, seg in enumerate(segments):
        pos += len(seg)
        if i < len(segments) - 1:
            bounds.add(pos)
    return bounds


def normalize_pieces(pieces: list[str]) -> list[str]:
    return [p.lstrip("▁") for p in pieces]


def boundary_scores(gold: list[str], pred: list[str]) -> dict[str, Any]:
    g = boundaries_from_segments(gold)
    p = boundaries_from_segments(pred)
    # also require same surface reconstruction
    if "".join(gold) != "".join(pred):
        # try if only whitespace differences — still fail exact
        recon_ok = False
    else:
        recon_ok = True
    tp = len(g & p)
    fp = len(p - g)
    fn = len(g - p)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    if prec is None or rec is None or (prec + rec) == 0:
        f1 = None
    else:
        f1 = 2 * prec * rec / (prec + rec)
    exact = gold == pred
    over = len(pred) > len(gold)
    under = len(pred) < len(gold)
    return {
        "boundary_precision": prec,
        "boundary_recall": rec,
        "boundary_f1": f1,
        "exact_segmentation": exact,
        "over_segmentation": over,
        "under_segmentation": under,
        "surface_reconstruct_ok": recon_ok,
        "n_gold_pieces": len(gold),
        "n_pred_pieces": len(pred),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def evaluate_file(
    gold_path: Path,
    *,
    system_key: str = "bpe_tokens",
) -> dict[str, Any]:
    rows = load_jsonl(gold_path)
    labeled = []
    for r in rows:
        gold = parse_segments(r.get("human_segments"))
        if not gold:
            continue
        pred_raw = r.get(system_key)
        if pred_raw is None:
            continue
        pred = normalize_pieces(list(pred_raw)) if isinstance(pred_raw, list) else parse_segments(pred_raw)
        if not pred:
            continue
        sc = boundary_scores(gold, pred)
        sc["item_id"] = r.get("item_id")
        labeled.append(sc)

    def avg(key: str) -> float | None:
        vals = [x[key] for x in labeled if x.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "n_total_records": len(rows),
        "n_with_human_segments": len(labeled),
        "system_key": system_key,
        "mean_boundary_precision": avg("boundary_precision"),
        "mean_boundary_recall": avg("boundary_recall"),
        "mean_boundary_f1": avg("boundary_f1"),
        "exact_segmentation_accuracy": avg("exact_segmentation")
        if labeled
        else None,
        "over_segmentation_rate": (
            sum(1 for x in labeled if x["over_segmentation"]) / len(labeled)
            if labeled
            else None
        ),
        "under_segmentation_rate": (
            sum(1 for x in labeled if x["under_segmentation"]) / len(labeled)
            if labeled
            else None
        ),
        "per_item": labeled,
        "note": "Metrics undefined until human_segments are filled.",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate morphology boundaries vs human labels")
    p.add_argument(
        "--annotations",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotation_candidates.jsonl"
        ),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--system-key", type=str, default="bpe_tokens",
                   help="Field with system pieces (bpe_tokens|unigram_tokens|system_tokens)")
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    ann = args.annotations if args.annotations.is_absolute() else root / args.annotations
    refuse_test(ann)
    # refuse locked holdout paths before any read (including missing files)
    ann_s = str(ann).replace("\\", "/")
    if "/locked/" in ann_s and "/released/" not in ann_s:
        print(
            "REFUSED: locked holdout annotations not for ordinary evaluation",
            file=sys.stderr,
        )
        return 2
    if not ann.is_file():
        print(f"annotations not found: {ann}", file=sys.stderr)
        return 1

    result = evaluate_file(ann, system_key=args.system_key)
    result["tool"] = {"name": TOOL_NAME, "version": TOOL_VERSION}
    result["generated_at"] = utc_now_iso()
    result["annotations_path"] = str(ann)

    out = args.output
    if out is None:
        out = root / "data/reports/morphology_boundary_eval_v0_1.json"
    elif not out.is_absolute():
        out = root / out
    write_json(out, result)

    # also human summary if any labels
    md = [
        "# Morphology boundary evaluation",
        "",
        f"_Generated {result['generated_at']}_",
        "",
        f"- Records: {result['n_total_records']}",
        f"- With human_segments: {result['n_with_human_segments']}",
        f"- System key: `{args.system_key}`",
        f"- Mean boundary F1: {result['mean_boundary_f1']}",
        f"- Exact accuracy: {result['exact_segmentation_accuracy']}",
        "",
    ]
    if result["n_with_human_segments"] == 0:
        md.append("No human labels yet — metrics are placeholders.")
    write_text(out.with_suffix(".md"), "\n".join(md))
    print(
        f"labeled={result['n_with_human_segments']}/{result['n_total_records']} "
        f"f1={result['mean_boundary_f1']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
