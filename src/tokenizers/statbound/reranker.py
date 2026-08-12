"""Unigram n-best re-ranking with statistical boundary compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .boundary_stats import get_strength
from .unigram_adapter import SegmentCandidate, UnigramAdapter


def surface_from_pieces(pieces: list[str]) -> str:
    """Map SP pieces to surface word characters (strip word-boundary marker)."""
    parts: list[str] = []
    for p in pieces:
        if p.startswith("▁"):
            parts.append(p[1:])
        else:
            parts.append(p)
    return "".join(parts)


def boundary_offsets(word: str, pieces: list[str]) -> list[int] | None:
    """Return internal boundary character offsets; None if pieces do not map to word."""
    if surface_from_pieces(pieces) != word:
        return None
    n = len(word)
    if n < 2:
        return []
    bounds: list[int] = []
    pos = 0
    for j, p in enumerate(pieces):
        body = p[1:] if p.startswith("▁") else p
        if word[pos : pos + len(body)] != body:
            return None
        pos += len(body)
        if j < len(pieces) - 1 and 0 < pos < n:
            bounds.append(pos)
    if pos != n:
        return None
    return bounds


def boundary_compatibility(
    word: str,
    pieces: list[str],
    stats: dict[str, Any],
) -> float | None:
    """compat(S,w) in approx [-1, 1] scaled by 1/(n-1). None if invalid mapping."""
    n = len(word)
    if n < 2:
        return 0.0
    bounds = boundary_offsets(word, pieces)
    if bounds is None:
        return None
    bound_set = set(bounds)
    total = 0.0
    for i in range(1, n):
        s = get_strength(stats, word, i)
        if i in bound_set:
            total += s
        else:
            total -= s
    return total / float(n - 1)


@dataclass(frozen=True)
class RankedCandidate:
    pieces: list[str]
    unigram_score: float
    boundary_compatibility: float
    combined_score: float


def tie_key(c: RankedCandidate) -> tuple:
    """Lower is better for Python sort after negating scores we want higher."""
    return (
        -c.combined_score,
        -c.unigram_score,
        -c.boundary_compatibility,
        len(c.pieces),
        "\x1f".join(c.pieces),
    )


def rank_candidates(
    word: str,
    candidates: list[SegmentCandidate],
    stats: dict[str, Any],
    *,
    lambda_bias: float,
) -> list[RankedCandidate]:
    ranked: list[RankedCandidate] = []
    for cand in candidates:
        if surface_from_pieces(cand.pieces) != word:
            continue
        compat = boundary_compatibility(word, cand.pieces, stats)
        if compat is None:
            continue
        combined = cand.unigram_score + float(lambda_bias) * compat
        ranked.append(
            RankedCandidate(
                pieces=list(cand.pieces),
                unigram_score=cand.unigram_score,
                boundary_compatibility=compat,
                combined_score=combined,
            )
        )
    ranked.sort(key=tie_key)
    return ranked


def select_segmentation(
    word: str,
    adapter: UnigramAdapter,
    stats: dict[str, Any],
    *,
    lambda_bias: float,
    nbest_size: int,
) -> RankedCandidate:
    cands = adapter.default_and_nbest(word, nbest_size)
    ranked = rank_candidates(word, cands, stats, lambda_bias=lambda_bias)
    if not ranked:
        # Fallback: default SP pieces even if surface check fails (should not happen)
        default = adapter.encode_as_pieces(word)
        return RankedCandidate(
            pieces=default,
            unigram_score=adapter.unigram_score(default),
            boundary_compatibility=0.0,
            combined_score=adapter.unigram_score(default),
        )
    return ranked[0]
