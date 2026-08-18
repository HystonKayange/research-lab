"""Analysis-only Unigram n-best morphology oracle.

Gold labels are used only to score already-generated candidates.  Nothing in
this module trains a tokenizer, writes vocabulary, or selects hyperparameters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .metrics import aggregate_boundary_metrics, boundaries_from_segments, boundary_metrics

EPS = 1e-12
SC4_DEV_MARGIN = 0.03
ALIGNMENT_MAJORITY = 0.5
LEFT_EDGE_MAX = 4
RIGHT_EDGE_MAX = 2


@dataclass(frozen=True)
class ScoredCandidate:
    pieces: tuple[str, ...]
    raw_pieces: tuple[str, ...]
    unigram_score: float
    unigram_rank: int
    is_s0: bool
    compat: float | None
    metrics: dict[str, Any]

    @property
    def segmentation(self) -> str:
        return "+".join(self.pieces)


def selection_f1(metrics: dict[str, Any]) -> float:
    """Ranking F1 only. Exact match is 1.0; undefined non-exact is -1.0."""
    if metrics.get("exact_segmentation_match"):
        return 1.0
    value = metrics.get("boundary_f1")
    if isinstance(value, (int, float)):
        return float(value)
    return -1.0


def oracle_sort_key(cand: ScoredCandidate) -> tuple:
    """Lower is better. Primary: official item F1 (via selection_f1)."""
    return (
        -selection_f1(cand.metrics),
        0 if cand.metrics.get("exact_segmentation_match") else 1,
        int(cand.unigram_rank),
        -float(cand.unigram_score),
        len(cand.pieces),
        "\x1f".join(cand.pieces),
    )


def compat_oracle_sort_key(cand: ScoredCandidate) -> tuple:
    compat = float("-inf") if cand.compat is None else float(cand.compat)
    return (
        -compat,
        0 if cand.is_s0 else 1,
        int(cand.unigram_rank),
        -float(cand.unigram_score),
        len(cand.pieces),
        "\x1f".join(cand.pieces),
    )


def pick_oracle(candidates: Sequence[ScoredCandidate]) -> ScoredCandidate:
    if not candidates:
        raise ValueError("empty candidate set")
    return sorted(candidates, key=oracle_sort_key)[0]


def pick_compat_oracle(candidates: Sequence[ScoredCandidate]) -> ScoredCandidate:
    if not candidates:
        raise ValueError("empty candidate set")
    return sorted(candidates, key=compat_oracle_sort_key)[0]


def assign_unigram_ranks(
    rows: Sequence[tuple[tuple[str, ...], float, bool]],
) -> list[int]:
    """Stable Unigram ranks. S0 wins score ties so the deployed default is rank 1 when tied."""
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda it: (-it[1][1], 0 if it[1][2] else 1, it[0], it[1][0]))
    ranks = [0] * len(rows)
    for rank, (idx, _) in enumerate(indexed, start=1):
        ranks[idx] = rank
    return ranks


def official_f1(metrics: dict[str, Any]) -> float | None:
    value = metrics.get("boundary_f1")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def micro_boundary_metrics(pairs: Sequence[tuple[Sequence[str], Sequence[str]]]) -> dict[str, Any]:
    tp = fp = fn = 0
    n_gold_bounds = 0
    n_pred_bounds = 0
    for gold, pred in pairs:
        g = boundaries_from_segments(gold)
        p = boundaries_from_segments(pred)
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
        n_gold_bounds += len(g)
        n_pred_bounds += len(p)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    if prec is None or rec is None:
        f1 = None
    elif prec + rec == 0:
        f1 = 0.0
    else:
        f1 = 2.0 * prec * rec / (prec + rec)
    return {
        "boundary_precision": prec,
        "boundary_recall": rec,
        "boundary_f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_gold_boundaries": n_gold_bounds,
        "n_pred_boundaries": n_pred_bounds,
        "n_items": len(pairs),
    }


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx <= EPS or dy <= EPS:
        return None
    return num / (dx * dy)


def _average_ranks(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = 0.5 * ((i + 1) + (j + 1))
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    return pearson(_average_ranks(xs), _average_ranks(ys))


def summarize(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "p10": None,
            "p90": None,
        }
    xs = sorted(float(v) for v in values)
    n = len(xs)
    mid = n // 2
    median = xs[mid] if n % 2 else 0.5 * (xs[mid - 1] + xs[mid])

    def pct(p: float) -> float:
        if n == 1:
            return xs[0]
        idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
        return xs[idx]

    return {
        "count": n,
        "mean": sum(xs) / n,
        "median": median,
        "min": xs[0],
        "max": xs[-1],
        "p10": pct(10),
        "p90": pct(90),
    }


def compare_f1(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "undefined"
    if a > b + EPS:
        return "better"
    if a < b - EPS:
        return "worse"
    return "tied"


def sign_delta(value: float | None) -> str:
    if value is None:
        return "undefined"
    if value > EPS:
        return "positive"
    if value < -EPS:
        return "negative"
    return "zero"


def family_decision(
    *,
    oracle_delta_macro_f1: float | None,
    n_strictly_better_f1: int,
    n_better_with_pos_compat: int,
    sc4_margin: float = SC4_DEV_MARGIN,
    alignment_majority: float = ALIGNMENT_MAJORITY,
) -> dict[str, Any]:
    """Map oracle + alignment to the pre-declared family decision. Does not choose α."""
    if oracle_delta_macro_f1 is None:
        code = "incomplete"
        reason = "oracle macro-F1 delta is undefined"
    elif oracle_delta_macro_f1 + EPS < sc4_margin:
        code = "abandon_reranking_generator_ceiling"
        reason = (
            f"oracle macro ΔF1 {oracle_delta_macro_f1:.4f} is below the SC4 margin "
            f"{sc4_margin:.2f}; this generator cannot meet SC4"
        )
    elif n_strictly_better_f1 <= 0:
        code = "abandon_reranking_no_better_candidates"
        reason = "no item has a strictly higher-F1 n-best neighbour"
    else:
        frac = n_better_with_pos_compat / n_strictly_better_f1
        if frac + EPS >= alignment_majority:
            code = "relbound_v2_warranted"
            reason = (
                f"oracle macro ΔF1 {oracle_delta_macro_f1:.4f} ≥ {sc4_margin:.2f} and "
                f"{n_better_with_pos_compat}/{n_strictly_better_f1} "
                f"({100.0 * frac:.1f}%) of better-F1 items have Δcompat > 0"
            )
        else:
            code = "do_not_calibrate_wrong_signal"
            reason = (
                f"oracle room exists (ΔF1 {oracle_delta_macro_f1:.4f}) but only "
                f"{n_better_with_pos_compat}/{n_strictly_better_f1} "
                f"({100.0 * frac:.1f}%) of better-F1 items have Δcompat > 0"
            )
    return {
        "code": code,
        "reason": reason,
        "sc4_margin": sc4_margin,
        "alignment_majority": alignment_majority,
        "oracle_delta_macro_f1": oracle_delta_macro_f1,
        "n_strictly_better_f1": n_strictly_better_f1,
        "n_better_with_pos_compat": n_better_with_pos_compat,
        "chooses_alpha": False,
        "uses_gold_as_training_signal": False,
    }


def restricted_rank_oracle(
    candidates: Sequence[ScoredCandidate],
    max_rank: int,
) -> ScoredCandidate:
    pool = [c for c in candidates if c.unigram_rank <= max_rank]
    if not pool:
        pool = [c for c in candidates if c.is_s0] or list(candidates)
    return pick_oracle(pool)


def defined_correlations(
    candidates: Sequence[ScoredCandidate],
) -> dict[str, float | None]:
    pairs: list[tuple[float, float]] = []
    for cand in candidates:
        if cand.compat is None:
            continue
        f1 = official_f1(cand.metrics)
        if f1 is None:
            continue
        pairs.append((float(cand.compat), f1))
    if len(pairs) < 2:
        return {"n_pairs": 0, "pearson": None, "spearman": None}
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    return {
        "n_pairs": len(pairs),
        "pearson": pearson(xs, ys),
        "spearman": spearman(xs, ys),
    }


def aggregate_or_none(item_metrics: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return aggregate_boundary_metrics(list(item_metrics))


def cut_zone(word_len: int, offset: int) -> str:
    """Classify a character offset as left-edge, right-edge, or internal."""
    if offset <= LEFT_EDGE_MAX:
        return "left_edge"
    if word_len - offset <= RIGHT_EDGE_MAX:
        return "right_edge"
    return "internal"


def gold_miss_zone_counts(
    word: str,
    gold_pieces: Sequence[str],
    pred_pieces: Sequence[str],
) -> dict[str, int]:
    gold_bounds = boundaries_from_segments(gold_pieces)
    pred_bounds = boundaries_from_segments(pred_pieces)
    missed = gold_bounds - pred_bounds
    counts = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": len(missed)}
    n = len(word)
    for offset in missed:
        counts[cut_zone(n, offset)] += 1
    return counts


def classify_oracle_change(
    word: str,
    gold_pieces: Sequence[str],
    unigram_pieces: Sequence[str],
    oracle_pieces: Sequence[str],
) -> str:
    """Label an oracle-vs-Unigram change. Not a tokenizer decision rule.

    clean_prefix: only left-edge gold cuts added; no removals; no new false positives
    junk_fp: at least one added cut is not gold
    mixed_gold: other gold-improving changes (right/internal adds or removals)
    unchanged: same piece sequence
    """
    if list(unigram_pieces) == list(oracle_pieces):
        return "unchanged"
    gold_bounds = boundaries_from_segments(gold_pieces)
    uni_bounds = boundaries_from_segments(unigram_pieces)
    ora_bounds = boundaries_from_segments(oracle_pieces)
    added = ora_bounds - uni_bounds
    removed = uni_bounds - ora_bounds
    added_fp = {i for i in added if i not in gold_bounds}
    n = len(word)
    added_right = [i for i in added if cut_zone(n, i) == "right_edge"]
    added_internal = [i for i in added if cut_zone(n, i) == "internal"]
    if not removed and added and not added_fp and not added_right and not added_internal:
        return "clean_prefix"
    if added_fp:
        return "junk_fp"
    return "mixed_gold"
