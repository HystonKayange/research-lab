"""Shared morphology-boundary and efficiency metrics for Phase C (and tests).

No scientific evaluation entrypoints here — pure functions only.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence


def parse_segments(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        out = [str(x) for x in raw if str(x)]
        return out or None
    s = str(raw).strip()
    if not s:
        return None
    if "+" in s:
        parts = [p.strip() for p in s.split("+") if p.strip()]
    else:
        parts = [p.strip() for p in s.split() if p.strip()]
    return parts or None


def normalize_pieces(pieces: Sequence[str]) -> list[str]:
    return [p.lstrip("▁") for p in pieces]


def boundaries_from_segments(segments: Sequence[str]) -> set[int]:
    bounds: set[int] = set()
    pos = 0
    segs = list(segments)
    for i, seg in enumerate(segs):
        pos += len(seg)
        if i < len(segs) - 1:
            bounds.add(pos)
    return bounds


def boundary_metrics(gold: Sequence[str], pred: Sequence[str]) -> dict[str, Any]:
    """Per-item boundary metrics. gold/pred are surface pieces (no ▁)."""
    g_surf = "".join(gold)
    p_surf = "".join(pred)
    recon_ok = g_surf == p_surf
    g = boundaries_from_segments(gold)
    p = boundaries_from_segments(pred)
    tp = len(g & p)
    fp = len(p - g)
    fn = len(g - p)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    if prec is None or rec is None or (prec + rec) == 0:
        f1 = None if (prec is None or rec is None) else 0.0
    else:
        f1 = 2 * prec * rec / (prec + rec)
    if not g and not p:
        jacc = 1.0
    elif not g or not p:
        jacc = 0.0
    else:
        jacc = len(g & p) / len(g | p)
    return {
        "boundary_precision": prec,
        "boundary_recall": rec,
        "boundary_f1": f1,
        "boundary_jaccard": jacc,
        "exact_segmentation_match": list(gold) == list(pred),
        "surface_reconstruct_ok": recon_ok,
        "n_gold_pieces": len(gold),
        "n_pred_pieces": len(pred),
    }


def aggregate_boundary_metrics(item_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Macro-average over items with defined metric values."""
    if not item_metrics:
        return {
            "n_items": 0,
            "boundary_precision": None,
            "boundary_recall": None,
            "boundary_f1": None,
            "boundary_jaccard": None,
            "exact_segmentation_match": None,
            "exact_match_count": 0,
            "exact_match_rate": None,
        }

    def mean_key(key: str) -> float | None:
        vals = [m[key] for m in item_metrics if m.get(key) is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    exact_count = sum(1 for m in item_metrics if m.get("exact_segmentation_match"))
    n = len(item_metrics)
    return {
        "n_items": n,
        "boundary_precision": mean_key("boundary_precision"),
        "boundary_recall": mean_key("boundary_recall"),
        "boundary_f1": mean_key("boundary_f1"),
        "boundary_jaccard": mean_key("boundary_jaccard"),
        "exact_segmentation_match": exact_count / n if n else None,
        "exact_match_count": exact_count,
        "exact_match_rate": exact_count / n if n else None,
    }


def efficiency_metrics_from_encodings(
    words: Sequence[str],
    piece_lists: Sequence[Sequence[str]],
) -> dict[str, Any]:
    """Tokenizer efficiency over whitespace words and their piece sequences."""
    if len(words) != len(piece_lists):
        raise ValueError("words and piece_lists length mismatch")
    n_words = len(words)
    if n_words == 0:
        return {
            "n_words": 0,
            "n_chars": 0,
            "n_tokens": 0,
            "tokens_per_character": None,
            "word_fertility": None,
            "sequence_length_expansion": None,
            "single_character_fragment_rate": None,
            "whole_word_rate": None,
        }
    n_chars = sum(len(w) for w in words)
    n_tokens = sum(len(ps) for ps in piece_lists)
    # strip ▁ for fragment/whole-word analysis
    single_char = 0
    whole_word = 0
    for w, ps in zip(words, piece_lists):
        bodies = [p.lstrip("▁") for p in ps if p.lstrip("▁") != ""]
        # empty bodies can occur for pure ▁ pieces
        for b in bodies:
            if len(b) == 1:
                single_char += 1
        if len(bodies) == 1 and bodies[0] == w:
            whole_word += 1
    return {
        "n_words": n_words,
        "n_chars": n_chars,
        "n_tokens": n_tokens,
        "tokens_per_character": n_tokens / n_chars if n_chars else None,
        "word_fertility": n_tokens / n_words if n_words else None,
        # expansion vs one-token-per-word baseline
        "sequence_length_expansion": n_tokens / n_words if n_words else None,
        "single_character_fragment_rate": single_char / n_tokens if n_tokens else None,
        "whole_word_rate": whole_word / n_words if n_words else None,
    }


def select_lambda_star(
    candidates: Iterable[dict[str, Any]],
    *,
    unigram_tpc: float,
    max_relative_tpc: float = 1.10,
    allow_bpc_field: bool = False,
) -> dict[str, Any]:
    """Frozen λ selection rule (D-0011). Never uses LM BPC.

    Each candidate dict must include:
      - lambda (float)
      - boundary_f1 (float)
      - tokens_per_character (float)

    λ=0.0 is never selected as proposed method.
    """
    rows = list(candidates)
    for r in rows:
        if (not allow_bpc_field) and any(
            k.lower() in {"bpc", "validation_bpc", "lm_bpc", "bits_per_character"}
            for k in r
        ):
            # Presence is allowed only if explicitly ignored; refuse if used as key for selection
            pass
        # Hard refuse if a selection helper tries to pass preferred_by_bpc
        if r.get("select_by_bpc") or r.get("use_bpc_for_selection"):
            raise ValueError("LM BPC must never participate in lambda selection")

    nonzero = [r for r in rows if float(r["lambda"]) != 0.0]
    if not nonzero:
        raise ValueError("no nonzero lambda candidates")

    threshold = max_relative_tpc * float(unigram_tpc)
    eligible = [
        r for r in nonzero if float(r["tokens_per_character"]) <= threshold
    ]
    sc5_failed = len(eligible) == 0
    pool = eligible if eligible else nonzero

    def sort_key(r: dict[str, Any]) -> tuple:
        # maximize F1, then minimize tpc, then minimize lambda
        return (
            -float(r["boundary_f1"]),
            float(r["tokens_per_character"]),
            float(r["lambda"]),
        )

    pool_sorted = sorted(pool, key=sort_key)
    chosen = pool_sorted[0]
    return {
        "lambda_star": float(chosen["lambda"]),
        "selected": chosen,
        "eligible_count": len(eligible),
        "sc5_failed_all_nonzero": sc5_failed,
        "tpc_threshold": threshold,
        "unigram_tpc": float(unigram_tpc),
        "max_relative_tpc": float(max_relative_tpc),
        "selection_used_lm_bpc": False,
        "pool": "eligible" if eligible else "diagnostic_all_nonzero",
    }
