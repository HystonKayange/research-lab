"""Corpus-only statistical boundary discovery for StatBound-Unigram V1."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .leakage import assert_train_only_path


@dataclass(frozen=True)
class BoundaryDiscoveryConfig:
    max_affix_context_length: int = 6
    min_type_support: int = 5
    min_productivity: int = 3
    min_affix_len_for_full_weight: int = 2
    length_one_affix_weight: float = 0.15
    formula_id: str = "statbound_v1_branch_productivity_log"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BoundaryDiscoveryConfig":
        return cls(
            max_affix_context_length=int(d.get("max_affix_context_length", 6)),
            min_type_support=int(d.get("min_type_support", 5)),
            min_productivity=int(d.get("min_productivity", 3)),
            min_affix_len_for_full_weight=int(d.get("min_affix_len_for_full_weight", 2)),
            length_one_affix_weight=float(d.get("length_one_affix_weight", 0.15)),
            formula_id=str(d.get("formula_id", "statbound_v1_branch_productivity_log")),
        )


def is_stat_token(tok: str) -> bool:
    if len(tok) < 2:
        return False
    return any(ch.isalpha() for ch in tok)


def extract_tokens(text: str) -> list[str]:
    return text.split()


def load_type_frequencies(train_path: Path) -> Counter[str]:
    freq: Counter[str] = Counter()
    with train_path.open("r", encoding="utf-8") as f:
        for line in f:
            for tok in extract_tokens(line):
                if is_stat_token(tok):
                    freq[tok] += 1
    return freq


def _build_prefix_suffix_indexes(
    types: Iterable[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    """Return pref_types, suf_types, branch_pref (next chars), branch_suf (prev chars)."""
    pref_types: dict[str, set[str]] = defaultdict(set)
    suf_types: dict[str, set[str]] = defaultdict(set)
    branch_pref: dict[str, set[str]] = defaultdict(set)
    branch_suf: dict[str, set[str]] = defaultdict(set)

    for t in types:
        n = len(t)
        for i in range(1, n):
            a = t[:i]
            b = t[i:]
            pref_types[a].add(t)
            suf_types[b].add(t)
            # next char after prefix a
            branch_pref[a].add(t[i])
            # char immediately before suffix b
            branch_suf[b].add(t[i - 1])
    return pref_types, suf_types, branch_pref, branch_suf


def raw_cut_score(
    a: str,
    b: str,
    *,
    pref_types: dict[str, set[str]],
    suf_types: dict[str, set[str]],
    branch_pref: dict[str, set[str]],
    branch_suf: dict[str, set[str]],
    cfg: BoundaryDiscoveryConfig,
) -> float:
    pt = len(pref_types.get(a, ()))
    st = len(suf_types.get(b, ()))
    bp = len(branch_pref.get(a, ()))
    bs = len(branch_suf.get(b, ()))

    if pt < cfg.min_type_support or st < cfg.min_type_support:
        return 0.0
    if bp < cfg.min_productivity and bs < cfg.min_productivity:
        return 0.0

    if (
        len(a) < cfg.min_affix_len_for_full_weight
        or len(b) < cfg.min_affix_len_for_full_weight
    ):
        # length-one (or shorter than full-weight min) downweight when either side is short
        if len(a) == 1 or len(b) == 1:
            omega = cfg.length_one_affix_weight
        else:
            omega = 1.0
    else:
        omega = 1.0

    # exact length-one rule from spec
    if len(a) == 1 or len(b) == 1:
        omega = cfg.length_one_affix_weight

    r = (
        math.log(1.0 + pt)
        + math.log(1.0 + st)
        + math.log(1.0 + bp)
        + math.log(1.0 + bs)
    )
    return omega * r


def strengths_for_word(
    w: str,
    *,
    pref_types: dict[str, set[str]],
    suf_types: dict[str, set[str]],
    branch_pref: dict[str, set[str]],
    branch_suf: dict[str, set[str]],
    cfg: BoundaryDiscoveryConfig,
) -> dict[int, float]:
    n = len(w)
    if n < 2:
        return {}
    raws: dict[int, float] = {}
    for i in range(1, n):
        if min(i, n - i) > cfg.max_affix_context_length:
            continue
        a, b = w[:i], w[i:]
        raws[i] = raw_cut_score(
            a,
            b,
            pref_types=pref_types,
            suf_types=suf_types,
            branch_pref=branch_pref,
            branch_suf=branch_suf,
            cfg=cfg,
        )
    rmax = max(raws.values()) if raws else 0.0
    if rmax <= 0.0:
        return {i: 0.0 for i in raws}
    return {i: (v / rmax) for i, v in raws.items()}


def learn_boundary_stats(
    train_path: Path | str,
    cfg: BoundaryDiscoveryConfig,
    *,
    forbidden_substrings: Iterable[str] | None = None,
) -> dict[str, Any]:
    path = assert_train_only_path(train_path, forbidden_substrings=forbidden_substrings)
    freq = load_type_frequencies(path)
    types = list(freq.keys())
    pref_types, suf_types, branch_pref, branch_suf = _build_prefix_suffix_indexes(types)

    words_out: dict[str, Any] = {}
    for w, f in freq.items():
        s = strengths_for_word(
            w,
            pref_types=pref_types,
            suf_types=suf_types,
            branch_pref=branch_pref,
            branch_suf=branch_suf,
            cfg=cfg,
        )
        # store only positive strengths
        pos = {str(i): round(v, 10) for i, v in sorted(s.items()) if v > 0.0}
        words_out[w] = {"freq": int(f), "strengths": pos}

    return {
        "formula_id": cfg.formula_id,
        "train_path": str(path),
        "n_types": len(types),
        "n_tokens": int(sum(freq.values())),
        "config": {
            "max_affix_context_length": cfg.max_affix_context_length,
            "min_type_support": cfg.min_type_support,
            "min_productivity": cfg.min_productivity,
            "min_affix_len_for_full_weight": cfg.min_affix_len_for_full_weight,
            "length_one_affix_weight": cfg.length_one_affix_weight,
        },
        "words": words_out,
    }


def save_boundary_stats(obj: dict[str, Any], path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def load_boundary_stats(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_strength(stats: dict[str, Any], word: str, offset: int) -> float:
    w = stats.get("words", {}).get(word)
    if not w:
        return 0.0
    return float(w.get("strengths", {}).get(str(offset), 0.0))
