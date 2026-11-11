"""Strict internal-boundary metrics; see MORPHOLOGY_EVALUATOR_SPEC_v0_1.md."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

EVALUATOR_ID = "strict-internal-boundary-v0.1"
METRICS = ("boundary_precision", "boundary_recall", "boundary_f1", "boundary_jaccard")


class SegmentationError(ValueError):
    """Malformed input must not silently change the evaluated item set."""


def _surface(surface: str) -> None:
    if not isinstance(surface, str) or not surface:
        raise SegmentationError("surface must be an explicit nonempty string")


def _pieces(value: Sequence[str], name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SegmentationError(f"{name} must be a sequence of strings")
    result = tuple(value)
    if any(not isinstance(piece, str) for piece in result):
        raise SegmentationError(f"{name} contains a non-string piece")
    return result


def validate_internal_boundaries(surface: str, offsets: Iterable[int]) -> frozenset[int]:
    _surface(surface)
    seen = set()
    for offset in offsets:
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise SegmentationError("boundary offsets must be integers, not Boolean or other values")
        if not 0 < offset < len(surface):
            raise SegmentationError("boundary is not strictly internal to the surface")
        if offset in seen:
            raise SegmentationError("duplicate boundary offset")
        seen.add(offset)
    return frozenset(seen)


def _boundaries(surface: str, pieces: tuple[str, ...]) -> frozenset[int]:
    total = 0
    offsets = []
    for piece in pieces[:-1]:
        total += len(piece)
        offsets.append(total)
    return validate_internal_boundaries(surface, offsets)


def scores_from_counts(tp: int, fp: int, fn: int) -> dict[str, float]:
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (tp, fp, fn)):
        raise SegmentationError("TP/FP/FN must be nonnegative integers")
    predicted, gold = tp + fp, tp + fn
    if not predicted and not gold:
        precision = recall = f1 = jaccard = 1.0
    elif not predicted or not gold:
        precision = recall = f1 = jaccard = 0.0
    else:
        precision = tp / predicted
        recall = tp / gold
        f1 = 2 * tp / (2 * tp + fp + fn)
        jaccard = tp / (tp + fp + fn)
    return dict(zip(METRICS, (precision, recall, f1, jaccard)))


def evaluate_item(surface: str, gold: Sequence[str], prediction: Sequence[str]) -> dict[str, Any]:
    _surface(surface)
    gold_parts = _pieces(gold, "gold")
    input_parts = _pieces(prediction, "prediction")
    if not gold_parts or any(piece == "" for piece in gold_parts):
        raise SegmentationError("gold must contain nonempty pieces only")
    if "".join(gold_parts) != surface:
        raise SegmentationError("gold does not reconstruct the exact surface")
    canonical = tuple(piece for piece in input_parts if piece != "")
    if not canonical or "".join(canonical) != surface:
        raise SegmentationError("prediction does not reconstruct the exact surface")
    g = _boundaries(surface, gold_parts)
    p = _boundaries(surface, canonical)
    tp, fp, fn = len(g & p), len(p - g), len(g - p)
    return {
        "evaluator_id": EVALUATOR_ID,
        "surface_form": surface,
        "gold_pieces": list(gold_parts),
        "input_prediction_pieces": list(input_parts),
        "prediction_pieces": list(canonical),
        "gold_boundaries": sorted(g),
        "prediction_boundaries": sorted(p),
        "tp": tp, "fp": fp, "fn": fn,
        "n_gold_boundaries": len(g), "n_prediction_boundaries": len(p),
        "n_empty_prediction_pieces_removed": len(input_parts) - len(canonical),
        "raw_piece_list_exact_match": gold_parts == input_parts,
        "exact_segmentation_match": gold_parts == canonical,
        "surface_reconstruct_ok": True,
        "gold_is_whole_word": not g,
        "zero_boundary_case": "both_empty" if not g and not p else "gold_empty" if not g else "prediction_empty" if not p else "neither",
        **scores_from_counts(tp, fp, fn),
    }


def _summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    tp, fp, fn = (sum(r[key] for r in rows) for key in ("tp", "fp", "fn"))
    exact = sum(bool(r["exact_segmentation_match"]) for r in rows)
    return {
        "n_items": n,
        "metric_item_denominators": {key: n for key in METRICS},
        "macro": {key: math.fsum(r[key] for r in rows) / n if n else None for key in METRICS},
        "micro": {"tp": tp, "fp": fp, "fn": fn, **(scores_from_counts(tp, fp, fn) if n else {key: None for key in METRICS})},
        "exact_match": {"count": exact, "denominator": n, "rate": exact / n if n else None},
        "normalization": {
            "items_with_empty_prediction_pieces": sum(r["n_empty_prediction_pieces_removed"] > 0 for r in rows),
            "empty_prediction_pieces_removed": sum(r["n_empty_prediction_pieces_removed"] for r in rows),
            "canonical_exact_differs_from_input_exact": sum(r["exact_segmentation_match"] != r["raw_piece_list_exact_match"] for r in rows),
        },
    }


def aggregate_items(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if any(r.get("evaluator_id") != EVALUATOR_ID for r in rows):
        raise SegmentationError("cannot aggregate results from another evaluator version")
    return {
        "evaluator_id": EVALUATOR_ID,
        **_summarize(rows),
        "strata": {
            "gold_segmented": _summarize([r for r in rows if not r["gold_is_whole_word"]]),
            "gold_whole_word": _summarize([r for r in rows if r["gold_is_whole_word"]]),
        },
    }
