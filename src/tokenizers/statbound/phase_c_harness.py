"""Phase C evaluation harness (prepared; scientific runs gated).

Supports:
- morphology metrics on in-memory gold/pred pairs
- efficiency metrics on in-memory encodings
- frozen lambda selection
- path guards against holdout / LM test / premature scientific paths

Does NOT train LMs. Does NOT unlock holdout/test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .leakage import LeakageError, normalize_path
from .metrics import (
    aggregate_boundary_metrics,
    boundary_metrics,
    efficiency_metrics_from_encodings,
    normalize_pieces,
    parse_segments,
    select_lambda_star,
)

# Paths that must not be consumed by scientific Phase C until gates pass
BLOCKED_SUBSTRINGS = (
    "/locked/",
    "/test/",
    "self_review_25",
    "annotator_a_self_review",
)

# Active morphology development is blocked for *this infrastructure task* and
# until Phase B freezes the final file; harness refuses unless explicitly allowed.
DEFAULT_BLOCKED_UNTIL_PHASE_B = (
    "annotator_a_active_",
    "morphology_benchmark",
)


class PhaseCGateError(RuntimeError):
    """Scientific path refused by evaluation protocol gates."""


def assert_path_allowed_for_phase_c(
    path: Path | str,
    *,
    allow_morphology_dev: bool = False,
    allow_lm_validation: bool = False,
) -> Path:
    """Refuse holdout/test; optionally refuse morph-dev and val until later phases."""
    p = Path(path).resolve()
    s = normalize_path(p)
    for bad in BLOCKED_SUBSTRINGS:
        if bad in s:
            raise PhaseCGateError(f"blocked path for Phase C harness: {s} (matched {bad!r})")
    if not allow_morphology_dev:
        for bad in DEFAULT_BLOCKED_UNTIL_PHASE_B:
            if bad in s:
                raise PhaseCGateError(
                    f"morphology development path blocked until Phase B gate + "
                    f"explicit allow_morphology_dev=True: {s}"
                )
    if not allow_lm_validation and "/validation/" in s:
        raise PhaseCGateError(
            f"LM validation path blocked until scientific Phase C is authorized: {s}"
        )
    return p


def filter_active_rows(
    rows: Iterable[dict[str, Any]],
    *,
    exclude_excluded: bool = True,
) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if exclude_excluded and (
            r.get("excluded") is True
            or (r.get("human_review") or {}).get("excluded") is True
            or str((r.get("human_review") or {}).get("human_review_decision") or "").upper()
            == "EXCLUDE"
            or r.get("adjudication_status") == "excluded_by_human_review"
        ):
            continue
        out.append(r)
    return out


def gold_segments_from_row(row: dict[str, Any]) -> list[str] | None:
    for key in (
        "proposed_segmentation",
        "human_segments",
        "gold_segmentation",
        "segmentation",
    ):
        segs = parse_segments(row.get(key))
        if segs:
            return segs
    return None


def evaluate_morphology_pairs(
    pairs: Sequence[tuple[list[str], list[str]]],
) -> dict[str, Any]:
    """pairs: list of (gold_pieces, pred_pieces) surface segments."""
    item_metrics = [boundary_metrics(g, p) for g, p in pairs]
    agg = aggregate_boundary_metrics(item_metrics)
    return {
        "aggregate": agg,
        "items": item_metrics,
        "schema_version": "phase_c_morphology_v0_1",
    }


def evaluate_morphology_rows(
    rows: Sequence[dict[str, Any]],
    predict_fn: Callable[[dict[str, Any]], Sequence[str]],
    *,
    skip_excluded: bool = True,
) -> dict[str, Any]:
    """predict_fn returns surface pieces for a gold row."""
    active = filter_active_rows(rows, exclude_excluded=skip_excluded) if skip_excluded else list(rows)
    pairs: list[tuple[list[str], list[str]]] = []
    skipped = 0
    for r in active:
        gold = gold_segments_from_row(r)
        if not gold:
            skipped += 1
            continue
        pred_raw = list(predict_fn(r))
        pred = normalize_pieces(pred_raw)
        pairs.append((gold, pred))
    result = evaluate_morphology_pairs(pairs)
    result["n_input_rows"] = len(rows)
    result["n_active_rows"] = len(active)
    result["n_skipped_no_gold"] = skipped
    return result


def evaluate_efficiency_words(
    words: Sequence[str],
    encode_fn: Callable[[str], Sequence[str]],
) -> dict[str, Any]:
    piece_lists = [list(encode_fn(w)) for w in words]
    metrics = efficiency_metrics_from_encodings(words, piece_lists)
    metrics["schema_version"] = "phase_c_efficiency_v0_1"
    return metrics


SYSTEM_IDS = (
    "bpe_8000",
    "unigram_8000",
    "statbound_lambda_0_0",
    "statbound_lambda_0_25",
    "statbound_lambda_0_5",
    "statbound_lambda_1_0",
    "statbound_lambda_2_0",
)

LAMBDA_BY_SYSTEM = {
    "statbound_lambda_0_0": 0.0,
    "statbound_lambda_0_25": 0.25,
    "statbound_lambda_0_5": 0.5,
    "statbound_lambda_1_0": 1.0,
    "statbound_lambda_2_0": 2.0,
}


def build_lambda_selection_table(
    system_results: dict[str, dict[str, Any]],
    *,
    unigram_system_id: str = "unigram_8000",
    max_relative_tpc: float = 1.10,
) -> dict[str, Any]:
    """Build selection input from per-system morph+efficiency result dicts.

    Each system_results[sid] should have:
      morphology.aggregate.boundary_f1
      efficiency.tokens_per_character
    """
    uni = system_results[unigram_system_id]
    unigram_tpc = float(uni["efficiency"]["tokens_per_character"])
    candidates = []
    for sid, lam in LAMBDA_BY_SYSTEM.items():
        if sid not in system_results:
            continue
        r = system_results[sid]
        candidates.append(
            {
                "system_id": sid,
                "lambda": lam,
                "boundary_f1": float(r["morphology"]["aggregate"]["boundary_f1"]),
                "tokens_per_character": float(r["efficiency"]["tokens_per_character"]),
            }
        )
    selection = select_lambda_star(
        candidates,
        unigram_tpc=unigram_tpc,
        max_relative_tpc=max_relative_tpc,
    )
    # Attach non-selected systems for reporting schema
    selection["schema_version"] = "phase_c_lambda_selection_v0_1"
    selection["candidates"] = candidates
    selection["systems_evaluated"] = list(system_results.keys())
    return selection


def empty_phase_c_result_schema() -> dict[str, Any]:
    return {
        "schema_version": "phase_c_full_result_v0_1",
        "systems": list(SYSTEM_IDS),
        "morphology_metrics": [
            "boundary_precision",
            "boundary_recall",
            "boundary_f1",
            "exact_segmentation_match",
            "boundary_jaccard",
        ],
        "efficiency_metrics": [
            "tokens_per_character",
            "word_fertility",
            "sequence_length_expansion",
            "single_character_fragment_rate",
            "whole_word_rate",
        ],
        "lambda_selection": None,
        "scientific_run": False,
        "notes": "Harness prepared; scientific Phase C not executed in infrastructure commit.",
    }


def dump_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
