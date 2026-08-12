#!/usr/bin/env python3
"""Inter-annotator agreement for morphology annotations (development/pilot only).

Does not load locked holdout. Does not invent labels.
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

from common import utc_now_iso, write_json, write_text  # noqa: E402
from evaluate_morphology_boundaries import (  # noqa: E402
    boundary_scores,
    boundaries_from_segments,
    parse_segments,
)

TOOL_NAME = "measure_morphology_annotation_agreement"
TOOL_VERSION = "0.1.0"


def refuse_locked(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def parse_bool(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return True
    if s in ("false", "0", "no", "n"):
        return False
    return None


def parse_tags(v: Any) -> set[str]:
    if v is None or v == "":
        return set()
    if isinstance(v, list):
        return {str(x).strip() for x in v if str(x).strip()}
    return {t.strip() for t in str(v).replace(",", "|").split("|") if t.strip()}


def load_annotations(path: Path) -> dict[str, dict[str, Any]]:
    refuse_locked(path)
    by_id: dict[str, dict[str, Any]] = {}
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            iid = row.get("item_id")
            if iid:
                by_id[str(iid)] = row
        return by_id
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                iid = row.get("item_id")
                if iid:
                    by_id[str(iid)] = dict(row)
        return by_id
    raise ValueError(f"unsupported annotation format: {path}")


def normalize_annotation(row: dict[str, Any]) -> dict[str, Any]:
    """Map schema variants to a common view."""
    prop = (
        row.get("proposed_segmentation")
        or row.get("human_segments")
        or row.get("segmentation")
    )
    alt = row.get("alternative_segmentation") or row.get("alternative_analysis")
    segs = parse_segments(prop)
    return {
        "item_id": row.get("item_id"),
        "surface_form": row.get("surface_form"),
        "proposed_segmentation": prop,
        "segments": segs,
        "alternative_segmentation": alt,
        "phenomenon_tags": parse_tags(
            row.get("phenomenon_tags") or row.get("human_phenomenon_tags")
        ),
        "no_segmentation_required": parse_bool(row.get("no_segmentation_required")),
        "mixed_language": parse_bool(row.get("mixed_language")),
        "spelling_or_ocr_issue": parse_bool(row.get("spelling_or_ocr_issue")),
        "insufficient_context": parse_bool(row.get("insufficient_context")),
        "uncertain": parse_bool(row.get("uncertain")),
        "confidence": row.get("confidence"),
        "annotator_id": row.get("annotator_id"),
        "notes": row.get("notes"),
        "raw": row,
    }


def jaccard(a: set[str], b: set[str]) -> float | None:
    if not a and not b:
        return 1.0
    if not a and not b:
        return 1.0
    u = a | b
    if not u:
        return 1.0
    return len(a & b) / len(u)


def bool_agree(a: bool | None, b: bool | None) -> bool | None:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return None  # missing
    return a == b


def needs_adjudication(na: dict[str, Any], nb: dict[str, Any]) -> bool:
    sa, sb = na["segments"], nb["segments"]
    if sa is None and sb is None:
        # both empty: adjudicate if uncertainty mismatch or tags differ
        if na["uncertain"] != nb["uncertain"]:
            return True
        if na["phenomenon_tags"] != nb["phenomenon_tags"]:
            return True
        return False
    if sa is None or sb is None:
        return True
    if sa != sb:
        return True
    if na["uncertain"] is True or nb["uncertain"] is True:
        if na["uncertain"] != nb["uncertain"]:
            return True
    if jaccard(na["phenomenon_tags"], nb["phenomenon_tags"]) is not None:
        if jaccard(na["phenomenon_tags"], nb["phenomenon_tags"]) < 1.0:
            # tag disagreement alone can flag adjudication
            if na["phenomenon_tags"] or nb["phenomenon_tags"]:
                return True
    return False


def measure(a_path: Path, b_path: Path) -> dict[str, Any]:
    a_map = {k: normalize_annotation(v) for k, v in load_annotations(a_path).items()}
    b_map = {k: normalize_annotation(v) for k, v in load_annotations(b_path).items()}
    common = sorted(set(a_map) & set(b_map))
    only_a = sorted(set(a_map) - set(b_map))
    only_b = sorted(set(b_map) - set(a_map))

    exact = 0
    both_segmented = 0
    bound_f1s: list[float] = []
    bound_precs: list[float] = []
    bound_recs: list[float] = []
    tag_jacs: list[float] = []
    unc_agree = 0
    unc_compared = 0
    adj_ids: list[str] = []
    per_item: list[dict[str, Any]] = []

    for iid in common:
        na, nb = a_map[iid], b_map[iid]
        sa, sb = na["segments"], nb["segments"]
        item: dict[str, Any] = {"item_id": iid}

        if sa is not None and sb is not None:
            both_segmented += 1
            exact_match = sa == sb
            if exact_match:
                exact += 1
            item["exact_segmentation_agreement"] = exact_match
            sc = boundary_scores(sa, sb)
            item["boundary"] = {
                "precision": sc["boundary_precision"],
                "recall": sc["boundary_recall"],
                "f1": sc["boundary_f1"],
            }
            if sc["boundary_f1"] is not None:
                bound_f1s.append(float(sc["boundary_f1"]))
            if sc["boundary_precision"] is not None:
                bound_precs.append(float(sc["boundary_precision"]))
            if sc["boundary_recall"] is not None:
                bound_recs.append(float(sc["boundary_recall"]))
            # boundary-level set agreement (Jaccard on boundary offsets)
            ga = boundaries_from_segments(sa)
            gb = boundaries_from_segments(sb)
            if not ga and not gb:
                item["boundary_set_jaccard"] = 1.0
            else:
                item["boundary_set_jaccard"] = len(ga & gb) / len(ga | gb)
        else:
            item["exact_segmentation_agreement"] = sa is None and sb is None
            item["boundary"] = None
            if sa is None and sb is None:
                exact += 1  # both chose no segments — exact empty agreement

        tj = jaccard(na["phenomenon_tags"], nb["phenomenon_tags"])
        item["phenomenon_tag_jaccard"] = tj
        if tj is not None:
            tag_jacs.append(tj)

        ba = bool_agree(na["uncertain"], nb["uncertain"])
        item["uncertainty_agreement"] = ba
        if ba is not None:
            unc_compared += 1
            if ba:
                unc_agree += 1

        adj = needs_adjudication(na, nb)
        item["needs_adjudication"] = adj
        if adj:
            adj_ids.append(iid)

        per_item.append(item)

    n = len(common)
    result = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "annotator_a_path": str(a_path),
        "annotator_b_path": str(b_path),
        "n_items_a": len(a_map),
        "n_items_b": len(b_map),
        "n_common": n,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "exact_segmentation_agreement": {
            "n_agree": exact,
            "n_common": n,
            "rate": exact / n if n else None,
            "note": (
                "Includes pairs where both left segmentation empty. "
                "Pairs with only one side segmented count as disagreement."
            ),
        },
        "boundary_agreement_when_both_segmented": {
            "n_pairs": both_segmented,
            "mean_precision": sum(bound_precs) / len(bound_precs) if bound_precs else None,
            "mean_recall": sum(bound_recs) / len(bound_recs) if bound_recs else None,
            "mean_f1": sum(bound_f1s) / len(bound_f1s) if bound_f1s else None,
            "note": "Treating annotator A as reference, B as prediction (symmetric F1).",
        },
        "phenomenon_tag_agreement": {
            "mean_jaccard": sum(tag_jacs) / len(tag_jacs) if tag_jacs else None,
            "n": len(tag_jacs),
            "note": "Multi-label Jaccard over phenomenon_tags sets.",
        },
        "uncertainty_agreement": {
            "n_agree": unc_agree,
            "n_compared": unc_compared,
            "rate": unc_agree / unc_compared if unc_compared else None,
            "note": "Only items where both provided true/false for uncertain.",
        },
        "adjudication": {
            "n_requiring_adjudication": len(adj_ids),
            "percentage": (100.0 * len(adj_ids) / n) if n else None,
            "item_ids": adj_ids,
        },
        "cohens_kappa": {
            "reported": False,
            "reason": (
                "Cohen's kappa is not reported by default for multi-label tags or "
                "structured segmentations with many rare categories and empty cells; "
                "assumptions of single categorical labels and adequate marginals often "
                "fail. Prefer exact match, boundary F1, and tag Jaccard. Kappa may be "
                "added later for a pre-registered binary field (e.g. uncertain) with "
                "adequate cell counts."
            ),
        },
        "per_item": per_item,
        "locked_holdout_used": False,
        "test_split_used": False,
    }
    return result


def render_md(result: dict[str, Any]) -> str:
    lines = [
        "# Morphology annotation agreement report",
        "",
        f"_Generated {result['generated_at']} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        f"- Common items: **{result['n_common']}**",
        f"- Exact segmentation agreement: **{result['exact_segmentation_agreement']['rate']}**",
        f"- Mean boundary F1 (both segmented): **{result['boundary_agreement_when_both_segmented']['mean_f1']}**",
        f"- Mean phenomenon-tag Jaccard: **{result['phenomenon_tag_agreement']['mean_jaccard']}**",
        f"- Uncertainty agreement: **{result['uncertainty_agreement']['rate']}**",
        f"- Requiring adjudication: **{result['adjudication']['n_requiring_adjudication']}** "
        f"({result['adjudication']['percentage']}%)",
        "",
        "## Cohen's kappa",
        "",
        result["cohens_kappa"]["reason"],
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Measure morphology IAA")
    p.add_argument("--annotator-a", type=Path, required=True)
    p.add_argument("--annotator-b", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/morphology_annotation_agreement_v0_1.json"),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()

    def resolve(p: Path) -> Path:
        return p if p.is_absolute() else root / p

    a = resolve(args.annotator_a)
    b = resolve(args.annotator_b)
    out = resolve(args.output)
    result = measure(a, b)
    write_json(out, result)
    write_text(out.with_suffix(".md"), render_md(result))
    print(
        f"common={result['n_common']} exact={result['exact_segmentation_agreement']['rate']} "
        f"adj%={result['adjudication']['percentage']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
