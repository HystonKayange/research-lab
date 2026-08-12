#!/usr/bin/env python3
"""Residual decomposition of existing_corpus vs Bible and Wikipedia.

Subtracts content attributable to Bible/Wikipedia under configurable
comparison modes and assesses remaining candidate lines. Read-only on
data/raw/. Does not create training data or set training eligibility.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from build_inventory import sha256_file  # noqa: E402
from audit_sources import (  # noqa: E402
    URL_LINE_RE,
    build_term_pattern,
    classify_language_signal,
    compile_boilerplate,
    compile_flags,
    deterministic_sample,
    excerpt,
    key_casefold_ws,
    key_exact,
    key_ws_normalized,
    load_json,
    percentile,
    read_utf8_text,
    utc_now_iso,
)

TOOL_NAME = "analyze_residual_corpus"
TOOL_VERSION = "1.0.0"

TOKEN_RE = re.compile(r"\w+", re.UNICODE)

CATEGORIES = (
    "duplicate_of_bible",
    "duplicate_of_wikipedia",
    "duplicate_of_both",
    "unique_candidate",
    "blank",
    "unresolved",
)

KEY_FNS: dict[str, Callable[[str], str]] = {
    "exact": key_exact,
    "whitespace_normalized": key_ws_normalized,
    "casefold_whitespace_normalized": key_casefold_ws,
}


# ---------------------------------------------------------------------------
# Core classification
# ---------------------------------------------------------------------------


def build_key_set(lines: Sequence[str], key_fn: Callable[[str], str]) -> set[str]:
    """Build comparison keys from non-blank lines only."""
    keys: set[str] = set()
    for ln in lines:
        if not ln.strip():
            continue
        keys.add(key_fn(ln))
    return keys


def classify_line(
    line: str,
    bible_keys: set[str],
    wiki_keys: set[str],
    key_fn: Callable[[str], str],
) -> str:
    """Assign residual category for one existing_corpus line."""
    if not line.strip():
        return "blank"
    k = key_fn(line)
    in_bible = k in bible_keys
    in_wiki = k in wiki_keys
    if in_bible and in_wiki:
        return "duplicate_of_both"
    if in_bible:
        return "duplicate_of_bible"
    if in_wiki:
        return "duplicate_of_wikipedia"
    return "unique_candidate"


def classify_all_lines(
    corpus_lines: Sequence[str],
    bible_keys: set[str],
    wiki_keys: set[str],
    key_fn: Callable[[str], str],
) -> list[dict[str, Any]]:
    """Classify every corpus line; preserve 1-based original line numbers."""
    records: list[dict[str, Any]] = []
    for i, line in enumerate(corpus_lines):
        cat = classify_line(line, bible_keys, wiki_keys, key_fn)
        rec: dict[str, Any] = {
            "line_number": i + 1,
            "category": cat,
            "text": line,
        }
        if cat not in ("blank", "unique_candidate"):
            rec["match_key_preview"] = excerpt(key_fn(line), 80)
        records.append(rec)
    return records


def category_counts(records: Sequence[dict[str, Any]]) -> dict[str, int]:
    c = Counter(r["category"] for r in records)
    return {cat: int(c.get(cat, 0)) for cat in CATEGORIES}


def subtraction_summary(
    corpus_lines: Sequence[str],
    bible_lines: Sequence[str],
    wiki_lines: Sequence[str],
    mode: str,
) -> dict[str, Any]:
    if mode not in KEY_FNS:
        raise ValueError(f"Unknown comparison mode: {mode}")
    key_fn = KEY_FNS[mode]
    bible_keys = build_key_set(bible_lines, key_fn)
    wiki_keys = build_key_set(wiki_lines, key_fn)
    records = classify_all_lines(corpus_lines, bible_keys, wiki_keys, key_fn)
    counts = category_counts(records)
    total = len(corpus_lines)
    unique_n = counts["unique_candidate"]
    blank_n = counts["blank"]
    attributed = (
        counts["duplicate_of_bible"]
        + counts["duplicate_of_wikipedia"]
        + counts["duplicate_of_both"]
    )
    return {
        "comparison_mode": mode,
        "bible_key_count": len(bible_keys),
        "wikipedia_key_count": len(wiki_keys),
        "bible_wikipedia_key_intersection": len(bible_keys & wiki_keys),
        "total_lines": total,
        "category_counts": counts,
        "attributed_to_bible_or_wikipedia": attributed,
        "unique_candidate_lines": unique_n,
        "blank_lines": blank_n,
        "unique_candidate_percentage_of_total": (
            round(100.0 * unique_n / total, 6) if total else 0.0
        ),
        "unique_candidate_percentage_of_nonblank": (
            round(100.0 * unique_n / (total - blank_n), 6)
            if (total - blank_n)
            else 0.0
        ),
        "records": records,
    }


# ---------------------------------------------------------------------------
# Residual quality metrics
# ---------------------------------------------------------------------------


def residual_quality_metrics(
    residual_lines: Sequence[tuple[int, str]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute structural / heuristic metrics for unique residual lines.

    residual_lines: list of (original_line_number, text)
    """
    texts = [t for _, t in residual_lines]
    short_th = int(config["short_line_threshold"])
    long_th = int(config["long_line_threshold"])
    excerpt_len = int(config["excerpt_length"])
    pct_list = config.get("percentiles", [50, 90, 95, 99])
    unusual_min = int(config.get("unusual_codepoint_min", 256))

    total_lines = len(texts)
    char_count = sum(len(t) for t in texts)
    # Word/token estimate: Unicode word tokens
    token_count = sum(len(TOKEN_RE.findall(t)) for t in texts)
    lengths = [len(t) for t in texts]
    lengths_sorted = sorted(lengths)

    exact_counts = Counter(texts)
    ws_counts = Counter(key_ws_normalized(t) for t in texts)
    unique_exact = len(exact_counts)
    unique_ws = len(ws_counts)
    lines_appearing_more_than_once = sum(
        1 for t in texts if exact_counts[t] > 1
    )
    ws_dup_lines = sum(1 for t in texts if ws_counts[key_ws_normalized(t)] > 1)

    url_lines = sum(1 for t in texts if URL_LINE_RE.search(t))
    digit_only = sum(1 for t in texts if t.strip().isdigit())
    unusual_lines = sum(
        1 for t in texts if any(ord(ch) >= unusual_min for ch in t)
    )
    repl = config.get("replacement_char", "\ufffd")
    replacement_lines = sum(1 for t in texts if repl in t)

    # Boilerplate
    bp_compiled = compile_boilerplate(config.get("boilerplate_patterns", []))
    bp_stats: dict[str, Any] = {}
    any_bp_line_indices: set[int] = set()
    for pid, desc, pat in bp_compiled:
        matching = []
        occ = 0
        for i, t in enumerate(texts):
            found = pat.findall(t)
            if found:
                occ += len(found)
                matching.append(i)
                any_bp_line_indices.add(i)
        bp_stats[pid] = {
            "description": desc,
            "matching_lines": len(matching),
            "total_occurrences": occ,
        }

    # Language signals
    ny = build_term_pattern(config.get("chichewa_signal_terms", []))
    en = build_term_pattern(config.get("english_signal_terms", []))
    de = build_term_pattern(config.get("german_signal_terms", []))
    min_m = int(config.get("language_signal", {}).get("min_matches_for_signal", 2))
    lang_counts: Counter[str] = Counter()
    lang_buckets: dict[str, list[tuple[int, str, dict[str, int]]]] = {
        "chichewa_signal": [],
        "english_signal": [],
        "german_signal": [],
        "mixed_signal": [],
        "insufficient_signal": [],
    }
    line_meta: list[dict[str, Any]] = []
    for (orig_n, t), length in zip(residual_lines, lengths):
        cat, hits = classify_language_signal(t, ny, en, de, min_m)
        lang_counts[cat] += 1
        lang_buckets[cat].append((orig_n, t, hits))
        bp_ids = [
            pid
            for pid, _, pat in bp_compiled
            if pat.search(t)
        ]
        line_meta.append(
            {
                "line_number": orig_n,
                "text": t,
                "length": length,
                "language_signal": cat,
                "term_hits": hits,
                "has_url": bool(URL_LINE_RE.search(t)),
                "boilerplate_ids": bp_ids,
                "has_unusual_unicode": any(ord(ch) >= unusual_min for ch in t),
            }
        )

    pct_values = {
        f"p{int(p)}": percentile(lengths_sorted, float(p)) for p in pct_list
    }

    # Top repeated
    limit = int(config.get("max_repeated_lines_report", 15))
    top_exact = sorted(
        ((t, c) for t, c in exact_counts.items() if c > 1),
        key=lambda kv: (-kv[1], kv[0]),
    )[:limit]
    top_ws = sorted(
        ((t, c) for t, c in ws_counts.items() if c > 1),
        key=lambda kv: (-kv[1], kv[0]),
    )[:limit]

    # Unusual codepoints among residual
    cp_counter: Counter[str] = Counter()
    for t in texts:
        for ch in t:
            if ord(ch) >= unusual_min:
                cp_counter[ch] += 1
    max_u = int(config.get("max_unusual_codepoints_report", 30))
    unusual_report = [
        {"char": ch, "codepoint": f"U+{ord(ch):04X}", "count": n}
        for ch, n in sorted(cp_counter.items(), key=lambda kv: (-kv[1], ord(kv[0])))[
            :max_u
        ]
    ]

    chichewa_chars = config.get("chichewa_chars", ["ŵ", "Ŵ"])
    chichewa_char_counts = {
        c: sum(t.count(c) for t in texts) for c in chichewa_chars
    }

    nonempty = total_lines  # residual unique candidates are non-blank by definition
    lang_pct = {
        k: round(100.0 * lang_counts[k] / nonempty, 4) if nonempty else 0.0
        for k in lang_buckets
    }

    return {
        "total_residual_lines": total_lines,
        "character_count": char_count,
        "estimated_word_token_count": token_count,
        "unique_exact_lines": unique_exact,
        "unique_ws_normalized_lines": unique_ws,
        "exact_duplicate_line_occurrences": lines_appearing_more_than_once,
        "exact_duplicate_percentage": (
            round(100.0 * lines_appearing_more_than_once / total_lines, 4)
            if total_lines
            else 0.0
        ),
        "ws_normalized_duplicate_line_occurrences": ws_dup_lines,
        "min_line_length": min(lengths) if lengths else None,
        "max_line_length": max(lengths) if lengths else None,
        "median_line_length": statistics.median(lengths) if lengths else None,
        "mean_line_length": (
            round(statistics.fmean(lengths), 4) if lengths else None
        ),
        "line_length_percentiles": pct_values,
        "very_short_lines": sum(1 for n in lengths if n < short_th),
        "very_long_lines": sum(1 for n in lengths if n > long_th),
        "short_line_threshold": short_th,
        "long_line_threshold": long_th,
        "url_containing_lines": url_lines,
        "digit_only_lines": digit_only,
        "unusual_unicode_lines": unusual_lines,
        "replacement_char_lines": replacement_lines,
        "boilerplate_matching_any_pattern": len(any_bp_line_indices),
        "boilerplate": bp_stats,
        "language_signals": {
            "disclaimer": (
                "Heuristic term-list signals only — not authoritative language labels."
            ),
            "counts": {k: int(lang_counts[k]) for k in lang_buckets},
            "percentages": lang_pct,
        },
        "chichewa_char_counts": chichewa_char_counts,
        "unusual_codepoints": unusual_report,
        "top_repeated_exact_lines": [
            {"count": c, "excerpt": excerpt(t, excerpt_len)} for t, c in top_exact
        ],
        "top_repeated_ws_normalized_lines": [
            {"count": c, "excerpt": excerpt(t, excerpt_len)} for t, c in top_ws
        ],
        "_line_meta": line_meta,
        "_lang_buckets": lang_buckets,
    }


def collect_residual_samples(
    residual_lines: Sequence[tuple[int, str]],
    quality: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    seed = int(config["random_seed"])
    sample_n = int(config["sample_count"])
    max_per = int(config["max_examples_per_category"])
    excerpt_len = int(config["excerpt_length"])
    short_th = int(config["short_line_threshold"])
    long_th = int(config["long_line_threshold"])
    k = min(sample_n, max_per)

    meta_by_line = {m["line_number"]: m for m in quality["_line_meta"]}
    samples: list[dict[str, Any]] = []

    def add(
        reason: str,
        items: Sequence[tuple[int, str]],
        metrics_fn=None,
        rank_key=None,
    ) -> None:
        ordered = list(items)
        if rank_key is not None:
            ordered = sorted(ordered, key=rank_key)
        picked = deterministic_sample(
            ordered, k, seed, salt=f"residual:{reason}"
        )
        for n, text in picked:
            m = meta_by_line.get(n, {})
            base_metrics = {
                "length": len(text),
                "language_signal": m.get("language_signal"),
                "term_hits": m.get("term_hits"),
                "has_url": m.get("has_url"),
                "boilerplate_ids": m.get("boilerplate_ids"),
            }
            if metrics_fn:
                base_metrics.update(metrics_fn(n, text, m))
            samples.append(
                {
                    "source_id": "existing_corpus",
                    "line_number": n,
                    "residual_category": "unique_candidate",
                    "reason": reason,
                    "excerpt": excerpt(text, excerpt_len),
                    "metrics": base_metrics,
                }
            )

    lang_buckets = quality["_lang_buckets"]

    # Strongest Chichewa: rank by chichewa hit count desc
    add(
        "chichewa_signal",
        [(n, t) for n, t, _ in lang_buckets["chichewa_signal"]],
        rank_key=lambda nt: (
            -(meta_by_line[nt[0]]["term_hits"].get("chichewa", 0)),
            nt[0],
        ),
    )
    add(
        "english_signal",
        [(n, t) for n, t, _ in lang_buckets["english_signal"]],
        rank_key=lambda nt: (
            -(meta_by_line[nt[0]]["term_hits"].get("english", 0)),
            nt[0],
        ),
    )
    add(
        "german_signal",
        [(n, t) for n, t, _ in lang_buckets["german_signal"]],
        rank_key=lambda nt: (
            -(meta_by_line[nt[0]]["term_hits"].get("german", 0)),
            nt[0],
        ),
    )
    add(
        "mixed_signal",
        [(n, t) for n, t, _ in lang_buckets["mixed_signal"]],
    )
    add(
        "insufficient_signal",
        [(n, t) for n, t, _ in lang_buckets["insufficient_signal"]],
    )

    bp_items = [
        (m["line_number"], m["text"])
        for m in quality["_line_meta"]
        if m["boilerplate_ids"]
    ]
    add("boilerplate", bp_items)

    url_items = [
        (m["line_number"], m["text"])
        for m in quality["_line_meta"]
        if m["has_url"]
    ]
    add("url_containing", url_items)

    long_items = [
        (m["line_number"], m["text"])
        for m in quality["_line_meta"]
        if m["length"] > long_th
    ]
    add(
        "extremely_long",
        long_items,
        rank_key=lambda nt: (-len(nt[1]), nt[0]),
    )

    short_items = [
        (m["line_number"], m["text"])
        for m in quality["_line_meta"]
        if m["length"] < short_th
    ]
    add("extremely_short", short_items)

    unusual_items = [
        (m["line_number"], m["text"])
        for m in quality["_line_meta"]
        if m["has_unusual_unicode"]
    ]
    add("unusual_unicode", unusual_items)

    # Repeated residual lines
    text_to_lines: dict[str, list[int]] = {}
    for n, t in residual_lines:
        text_to_lines.setdefault(t, []).append(n)
    repeated_items = [
        (nums[0], t)
        for t, nums in text_to_lines.items()
        if len(nums) > 1
    ]
    add(
        "repeated_residual",
        repeated_items,
        metrics_fn=lambda n, t, m: {"repeat_count": len(text_to_lines[t])},
        rank_key=lambda nt: (-len(text_to_lines[nt[1]]), nt[0]),
    )

    samples.sort(key=lambda r: (r["reason"], r["line_number"]))
    return samples


# ---------------------------------------------------------------------------
# Recommendation (evidence-based, non-automatic eligibility)
# ---------------------------------------------------------------------------


def evidence_based_recommendation(
    primary_summary: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    """Return a cautious recommendation among discard / review / clean-separately.

    Does not set allowed_for_training. Based only on measured residual size
    and contamination signals.
    """
    total = primary_summary["total_lines"]
    unique_n = primary_summary["unique_candidate_lines"]
    pct = primary_summary["unique_candidate_percentage_of_total"]
    ls = quality["language_signals"]["counts"]
    foreign = (
        ls.get("english_signal", 0)
        + ls.get("german_signal", 0)
        + ls.get("mixed_signal", 0)
    )
    chichewa = ls.get("chichewa_signal", 0)
    bp = quality["boilerplate_matching_any_pattern"]
    url_n = quality["url_containing_lines"]
    short_n = quality["very_short_lines"]

    foreign_rate = foreign / unique_n if unique_n else 0.0
    chichewa_rate = chichewa / unique_n if unique_n else 0.0
    bp_rate = bp / unique_n if unique_n else 0.0

    # Decision logic (documented thresholds for transparency)
    if unique_n == 0:
        option = "discard residual"
        rationale = (
            "No unique candidate lines remain after subtraction; residual is empty."
        )
    elif pct < 1.0 and foreign_rate > 0.3:
        option = "discard residual"
        rationale = (
            f"Residual is tiny ({pct:.3f}% of corpus) with high foreign-signal "
            f"rate ({foreign_rate:.1%}); evidence suggests little usable unique "
            "Chichewa after Bible/Wikipedia removal."
        )
    elif foreign_rate > 0.25 or bp_rate > 0.25:
        option = "preserve for manual review"
        rationale = (
            f"Residual retains {unique_n} lines ({pct:.3f}% of corpus) but "
            f"contamination signals are elevated (foreign_signal_rate={foreign_rate:.1%}, "
            f"boilerplate_rate={bp_rate:.1%}). Evidence supports human review before "
            "any cleaning design, not automatic discard or training use."
        )
    elif chichewa_rate >= 0.5 and foreign_rate < 0.15:
        option = "clean as a separate source"
        rationale = (
            f"Residual is non-trivial ({unique_n} lines, {pct:.3f}%) with majority "
            f"Chichewa-signal ({chichewa_rate:.1%}) and lower foreign-signal rate "
            f"({foreign_rate:.1%}). Evidence suggests it may be worth a separate "
            "cleaning design after license review — not approved for training here."
        )
    else:
        option = "preserve for manual review"
        rationale = (
            f"Residual has {unique_n} lines ({pct:.3f}%); Chichewa-signal "
            f"{chichewa_rate:.1%}, foreign-signal {foreign_rate:.1%}, "
            f"boilerplate {bp_rate:.1%}, short lines {short_n}, URLs {url_n}. "
            "Mixed quality signals warrant manual review before discard or cleaning."
        )

    return {
        "option": option,
        "allowed_options": [
            "discard residual",
            "preserve for manual review",
            "clean as a separate source",
        ],
        "rationale": rationale,
        "supporting_metrics": {
            "unique_candidate_lines": unique_n,
            "unique_percentage_of_total": pct,
            "chichewa_signal_rate": round(chichewa_rate, 4),
            "foreign_signal_rate": round(foreign_rate, 4),
            "boilerplate_rate": round(bp_rate, 4),
            "url_lines": url_n,
            "very_short_lines": short_n,
        },
        "training_eligibility": "not decided — residual is not approved training data",
        "note": (
            "This recommendation is analytical only. Licensing, provenance, and "
            "native-speaker review remain required before any training use."
        ),
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_report(result: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    primary = result["primary_decomposition"]
    quality = result["residual_quality"]
    rec = result["recommendation"]

    w("# Residual corpus analysis")
    w("")
    w(f"**Generated:** {result['generated_at']}")
    w(f"**Tool:** {result['tool']['name']} v{result['tool']['version']}")
    w(f"**Config version:** {result['config']['version']}")
    w(
        f"**Primary subtraction mode:** `{primary['comparison_mode']}`"
    )
    w("")
    w(
        "> **No raw files were modified.** This analysis only reads `data/raw/` "
        "and writes under `data/metadata/`, `data/reports/`, and optionally "
        "`data/interim/`."
    )
    w("")
    w(
        "> **Residual candidates are not approved training data.** "
        "They are uncleaned, unlicensed (unverified), and generated only for review."
    )
    w("")

    # 1
    w("## 1. Executive summary")
    w("")
    w(
        f"`existing_corpus` has **{primary['total_lines']}** lines. "
        f"Under **{primary['comparison_mode']}** subtraction against Bible and "
        f"Wikipedia, **{primary['unique_candidate_lines']}** lines "
        f"(**{primary['unique_candidate_percentage_of_total']}%** of total; "
        f"**{primary['unique_candidate_percentage_of_nonblank']}%** of non-blank) "
        "are classified as `unique_candidate`."
    )
    w("")
    w(
        f"Attributed to Bible and/or Wikipedia: "
        f"**{primary['attributed_to_bible_or_wikipedia']}** lines. "
        f"Blank: **{primary['blank_lines']}**."
    )
    w("")
    w("Category counts (primary mode):")
    w("")
    w("| category | count |")
    w("|----------|------:|")
    for cat, n in primary["category_counts"].items():
        w(f"| `{cat}` | {n} |")
    w("")
    w(
        f"Residual quality (unique candidates): "
        f"{quality['character_count']} characters; "
        f"~{quality['estimated_word_token_count']} word tokens; "
        f"Chichewa-signal {quality['language_signals']['counts'].get('chichewa_signal', 0)}; "
        f"EN/DE/mixed "
        f"{quality['language_signals']['counts'].get('english_signal', 0)}/"
        f"{quality['language_signals']['counts'].get('german_signal', 0)}/"
        f"{quality['language_signals']['counts'].get('mixed_signal', 0)}."
    )
    w("")
    w(
        f"**Analytical recommendation (not a training decision):** "
        f"`{rec['option']}` — {rec['rationale']}"
    )
    w("")

    # 2
    w("## 2. Decomposition methodology")
    w("")
    w("1. Load Bible, Wikipedia, and existing_corpus as UTF-8 (strict).")
    w("2. Build in-memory key sets for Bible and Wikipedia (non-blank lines only).")
    w("3. For each existing_corpus line (preserving original 1-based line numbers):")
    w("   - `blank` if empty/whitespace-only")
    w("   - `duplicate_of_both` if key ∈ Bible ∩ Wikipedia")
    w("   - `duplicate_of_bible` if key ∈ Bible only")
    w("   - `duplicate_of_wikipedia` if key ∈ Wikipedia only")
    w("   - `unique_candidate` otherwise")
    w("   - `unresolved` reserved (not used by current rules)")
    w("4. Comparison modes (in-memory only; no normalized corpus written):")
    w("   - `exact` — full line string equality")
    w("   - `whitespace_normalized` — trim + collapse internal whitespace")
    w("   - `casefold_whitespace_normalized` — diagnostic case-fold + whitespace")
    w(
        f"5. Primary residual decision uses "
        f"`{primary['comparison_mode']}` "
        f"(case-fold for residual decisions: "
        f"{result['config'].get('use_casefold_for_residual', False)})."
    )
    w(
        "6. Residual quality uses the same transparent language-signal and "
        "boilerplate heuristics as the source audit (not authoritative LID)."
    )
    w("")

    # 3
    w("## 3. Raw checksum verification")
    w("")
    w("| source | pre-audit SHA-256 | post-audit SHA-256 | match |")
    w("|--------|-------------------|--------------------|:-----:|")
    for sid, pre in result["pre_checksums"].items():
        post = result["post_checksums"][sid]
        match = "yes" if pre == post else "NO"
        w(f"| {sid} | `{pre}` | `{post}` | {match} |")
    w("")
    w(f"**raw_files_unchanged:** `{result['raw_files_unchanged']}`")
    w("")

    # 4–6 decompositions
    for section_num, key, title in (
        (4, "exact", "Exact subtraction results"),
        (5, "whitespace_normalized", "Whitespace-normalized subtraction results"),
        (6, "casefold_whitespace_normalized", "Case-fold diagnostic results"),
    ):
        w(f"## {section_num}. {title}")
        w("")
        block = result["decompositions"].get(key)
        if not block:
            w("_Not computed (disabled in config)._")
            w("")
            continue
        if key == "casefold_whitespace_normalized":
            w(
                "> Diagnostic only. Not used as the default residual decision "
                "unless `use_casefold_for_residual` is true."
            )
            w("")
        w(f"- Mode: `{block['comparison_mode']}`")
        w(f"- Bible keys: {block['bible_key_count']}")
        w(f"- Wikipedia keys: {block['wikipedia_key_count']}")
        w(
            f"- Bible ∩ Wikipedia keys: {block['bible_wikipedia_key_intersection']}"
        )
        w(f"- Unique candidates: **{block['unique_candidate_lines']}** "
          f"({block['unique_candidate_percentage_of_total']}% of total)")
        w(f"- Attributed (bible/wiki/both): {block['attributed_to_bible_or_wikipedia']}")
        w("")
        w("| category | count |")
        w("|----------|------:|")
        for cat, n in block["category_counts"].items():
            w(f"| `{cat}` | {n} |")
        w("")

    # 7
    w("## 7. Residual size and percentage")
    w("")
    w(
        f"Primary residual (`{primary['comparison_mode']}`): "
        f"**{quality['total_residual_lines']}** lines; "
        f"**{quality['character_count']}** characters; "
        f"**~{quality['estimated_word_token_count']}** estimated word tokens."
    )
    w("")
    w(
        f"Percentage of existing_corpus remaining as unique candidates: "
        f"**{primary['unique_candidate_percentage_of_total']}%** "
        f"(of non-blank: **{primary['unique_candidate_percentage_of_nonblank']}%**)."
    )
    w("")
    w(
        f"Line length: min={quality['min_line_length']}, "
        f"median={quality['median_line_length']}, "
        f"mean={quality['mean_line_length']}, "
        f"max={quality['max_line_length']}; "
        f"percentiles={quality['line_length_percentiles']}"
    )
    w(
        f"Very short (<{quality['short_line_threshold']}): "
        f"{quality['very_short_lines']}; "
        f"very long (>{quality['long_line_threshold']}): "
        f"{quality['very_long_lines']}"
    )
    w(
        f"URL lines: {quality['url_containing_lines']}; "
        f"digit-only: {quality['digit_only_lines']}; "
        f"unusual-unicode lines: {quality['unusual_unicode_lines']}"
    )
    w(f"Chichewa-relevant char counts: {quality['chichewa_char_counts']}")
    w("")

    # 8
    w("## 8. Residual language-signal distribution")
    w("")
    w(
        "> These are **heuristic signals**, not authoritative language labels."
    )
    w("")
    w("| category | count | % |")
    w("|----------|------:|--:|")
    for cat, n in quality["language_signals"]["counts"].items():
        pct = quality["language_signals"]["percentages"][cat]
        w(f"| `{cat}` | {n} | {pct} |")
    w("")

    # 9
    w("## 9. Boilerplate and contamination findings")
    w("")
    w(
        f"Lines matching any configured boilerplate pattern: "
        f"**{quality['boilerplate_matching_any_pattern']}**"
    )
    w("")
    w("| pattern | matching lines | occurrences |")
    w("|---------|---------------:|------------:|")
    for pid, d in quality["boilerplate"].items():
        if d["matching_lines"]:
            w(
                f"| `{pid}` | {d['matching_lines']} | {d['total_occurrences']} |"
            )
    w("")
    if quality["unusual_codepoints"]:
        top = ", ".join(
            f"{u['char']} ({u['codepoint']}, n={u['count']})"
            for u in quality["unusual_codepoints"][:10]
        )
        w(f"Top unusual codepoints in residual: {top}")
        w("")

    # 10
    w("## 10. Within-residual duplication")
    w("")
    w(
        f"- Lines appearing more than once (exact): "
        f"{quality['exact_duplicate_line_occurrences']} "
        f"({quality['exact_duplicate_percentage']}%)"
    )
    w(
        f"- Unique exact residual lines: {quality['unique_exact_lines']}"
    )
    w(
        f"- Unique ws-normalized residual lines: "
        f"{quality['unique_ws_normalized_lines']}"
    )
    if quality["top_repeated_exact_lines"]:
        w("- Top repeated exact residual lines:")
        for item in quality["top_repeated_exact_lines"][:8]:
            w(f"  - ×{item['count']}: `{item['excerpt']}`")
    w("")

    # 11
    w("## 11. Representative review samples")
    w("")
    w(
        f"Full sample set: `{result.get('samples_path', 'data/reports/residual_samples.jsonl')}` "
        f"({result.get('sample_record_count', '?')} records)."
    )
    w("")
    # Show a few from embedded preview
    by_reason: dict[str, list] = {}
    for s in result.get("sample_preview", []):
        by_reason.setdefault(s["reason"], []).append(s)
    for reason, items in sorted(by_reason.items()):
        w(f"### {reason}")
        w("")
        for s in items[:3]:
            w(
                f"- L{s['line_number']}: `{s['excerpt']}` "
                f"(lang={s['metrics'].get('language_signal')})"
            )
        w("")

    # 12
    w("## 12. Evidence-based recommendation")
    w("")
    w(f"**Option:** `{rec['option']}`")
    w("")
    w(f"**Rationale:** {rec['rationale']}")
    w("")
    w(f"**Supporting metrics:** `{json.dumps(rec['supporting_metrics'])}`")
    w("")
    w(f"**Training eligibility:** {rec['training_eligibility']}")
    w("")
    w(rec["note"])
    w("")
    w("Allowed options considered:")
    for opt in rec["allowed_options"]:
        mark = "← selected" if opt == rec["option"] else ""
        w(f"- `{opt}` {mark}")
    w("")

    # 13
    w("## 13. Limitations")
    w("")
    for note in result.get("limitations", []):
        w(f"- {note}")
    w("")

    # 14–15
    w("## 14. Raw modification statement")
    w("")
    w(
        "**No raw files were modified.** Pre- and post-analysis SHA-256 checksums "
        "match for Bible, Wikipedia, and existing_corpus."
    )
    w("")
    w("## 15. Training-data statement")
    w("")
    w(
        "**Residual candidates are not approved training data.** "
        "Any optional file under `data/interim/` is uncleaned, unlicensed "
        "(license not verified), and generated only for human review. "
        "Do not train tokenizers or models on it."
    )
    w("")
    if result.get("candidate_file"):
        w(f"Candidate review file (if written): `{result['candidate_file']}`")
        w("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_analysis(
    config: dict[str, Any],
    repo_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    paths = config["source_paths"]
    bible_path = repo_root / paths["bible"]
    wiki_path = repo_root / paths["wikipedia"]
    corpus_path = repo_root / paths["existing_corpus"]

    for p in (bible_path, wiki_path, corpus_path):
        if not p.is_file():
            raise FileNotFoundError(f"Required source missing: {p}")

    bible_text = read_utf8_text(bible_path)
    wiki_text = read_utf8_text(wiki_path)
    corpus_text = read_utf8_text(corpus_path)

    bible_lines = bible_text.splitlines()
    wiki_lines = wiki_text.splitlines()
    corpus_lines = corpus_text.splitlines()

    modes = ["exact", "whitespace_normalized"]
    if config.get("case_fold_diagnostic", True):
        modes.append("casefold_whitespace_normalized")

    decompositions: dict[str, Any] = {}
    for mode in modes:
        summary = subtraction_summary(
            corpus_lines, bible_lines, wiki_lines, mode
        )
        # Drop full records from stored JSON except for primary mode needs
        decompositions[mode] = {
            k: v for k, v in summary.items() if k != "records"
        }
        decompositions[mode]["_records"] = summary["records"]

    primary_mode = config.get(
        "subtraction_comparison_mode", "whitespace_normalized"
    )
    if config.get("use_casefold_for_residual", False):
        primary_mode = "casefold_whitespace_normalized"
    if primary_mode not in decompositions:
        raise ValueError(
            f"Primary mode {primary_mode!r} was not computed. "
            "Enable case_fold_diagnostic if using casefold mode."
        )

    primary = decompositions[primary_mode]
    residual_lines = [
        (r["line_number"], r["text"])
        for r in primary["_records"]
        if r["category"] == "unique_candidate"
    ]

    quality = residual_quality_metrics(residual_lines, config)
    samples = collect_residual_samples(residual_lines, quality, config)
    recommendation = evidence_based_recommendation(
        {k: v for k, v in primary.items() if k != "_records"},
        quality,
    )

    # Optional candidate file content (not written here)
    candidate_text: str | None = None
    if config.get("write_candidate_file", False):
        header = config.get("candidate_file_header", [])
        body_lines = [t for _, t in residual_lines]
        candidate_text = "\n".join(list(header) + body_lines)
        if body_lines:
            candidate_text += "\n"

    # Strip private fields from quality for JSON
    quality_public = {
        k: v for k, v in quality.items() if not k.startswith("_")
    }

    # Strip records from decomposition public view
    decompositions_public = {}
    for mode, block in decompositions.items():
        decompositions_public[mode] = {
            k: v for k, v in block.items() if k != "_records"
        }

    primary_public = {
        k: v for k, v in primary.items() if k != "_records"
    }

    result: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "config": {
            "version": config.get("version"),
            "subtraction_comparison_mode": config.get(
                "subtraction_comparison_mode"
            ),
            "case_fold_diagnostic": config.get("case_fold_diagnostic"),
            "use_casefold_for_residual": config.get(
                "use_casefold_for_residual", False
            ),
            "short_line_threshold": config.get("short_line_threshold"),
            "long_line_threshold": config.get("long_line_threshold"),
            "sample_count": config.get("sample_count"),
            "random_seed": config.get("random_seed"),
            "excerpt_length": config.get("excerpt_length"),
            "write_candidate_file": config.get("write_candidate_file"),
            "term_list_disclaimer": config.get("term_list_disclaimer"),
        },
        "source_paths": paths,
        "source_sizes": {
            "bible_lines": len(bible_lines),
            "wikipedia_lines": len(wiki_lines),
            "existing_corpus_lines": len(corpus_lines),
        },
        "decompositions": decompositions_public,
        "primary_decomposition": primary_public,
        "residual_quality": quality_public,
        "recommendation": recommendation,
        "sample_preview": samples[:24],
        "sample_record_count": len(samples),
        "limitations": [
            "Exact/normalized line equality misses paraphrase and near-duplicates.",
            "Language-signal categories are heuristics, not language identification.",
            "Term lists are provisional and require native-speaker review.",
            "No licensing or training-eligibility decision is made.",
            "Paragraph- or document-level attribution is not modeled.",
            "Case-fold mode is diagnostic unless use_casefold_for_residual is true.",
            "Residual candidate files under data/interim/ are not training corpora.",
        ],
        "warnings": [
            "existing_corpus must not be treated as an independent training source.",
            "Residual content remains uncleaned and unlicensed until human review.",
        ],
    }

    return result, samples, candidate_text


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Residual decomposition of existing_corpus after Bible/Wikipedia "
            "subtraction (read-only on raw data)."
        )
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/residual_analysis.json"),
    )
    p.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/metadata/residual_analysis.json"),
    )
    p.add_argument(
        "--report-output",
        type=Path,
        default=Path("data/reports/residual_analysis.md"),
    )
    p.add_argument(
        "--samples-output",
        type=Path,
        default=Path("data/reports/residual_samples.jsonl"),
    )
    p.add_argument(
        "--candidate-output",
        type=Path,
        default=None,
        help="Override candidate residual path (default from config).",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
    )
    p.add_argument(
        "--no-candidate-file",
        action="store_true",
        help="Do not write interim residual_candidates.txt even if config enables it.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )
    config_path = (
        args.config if args.config.is_absolute() else repo_root / args.config
    )

    try:
        config = load_json(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    paths = config["source_paths"]
    raw_files = {
        sid: repo_root / rel for sid, rel in paths.items()
    }

    pre_checksums: dict[str, str] = {}
    try:
        for sid, path in raw_files.items():
            pre_checksums[sid] = sha256_file(path)
    except OSError as e:
        print(f"error: cannot checksum raw file: {e}", file=sys.stderr)
        return 1

    try:
        result, samples, candidate_text = run_analysis(config, repo_root)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    post_checksums: dict[str, str] = {}
    for sid, path in raw_files.items():
        post_checksums[sid] = sha256_file(path)

    mismatches = [
        sid for sid in pre_checksums if pre_checksums[sid] != post_checksums[sid]
    ]
    if mismatches:
        print(
            f"error: raw files changed during analysis: {mismatches}",
            file=sys.stderr,
        )
        return 2

    result["pre_checksums"] = pre_checksums
    result["post_checksums"] = post_checksums
    result["raw_files_unchanged"] = True

    json_out = (
        args.json_output
        if args.json_output.is_absolute()
        else repo_root / args.json_output
    )
    report_out = (
        args.report_output
        if args.report_output.is_absolute()
        else repo_root / args.report_output
    )
    samples_out = (
        args.samples_output
        if args.samples_output.is_absolute()
        else repo_root / args.samples_output
    )

    result["samples_path"] = str(
        args.samples_output
        if not args.samples_output.is_absolute()
        else samples_out
    )

    # Candidate file
    candidate_path: Path | None = None
    write_cand = config.get("write_candidate_file", False) and not args.no_candidate_file
    if write_cand and candidate_text is not None:
        if args.candidate_output:
            candidate_path = (
                args.candidate_output
                if args.candidate_output.is_absolute()
                else repo_root / args.candidate_output
            )
        else:
            rel = config.get(
                "candidate_output_path",
                "data/interim/existing_corpus/residual_candidates.txt",
            )
            candidate_path = repo_root / rel
        write_text(candidate_path, candidate_text)
        result["candidate_file"] = str(
            candidate_path.relative_to(repo_root)
            if candidate_path.is_relative_to(repo_root)
            else candidate_path
        )
        result["candidate_file_disclaimer"] = (
            "UNCLEANED, UNLICENSED, NOT APPROVED FOR TRAINING — review only."
        )
    else:
        result["candidate_file"] = None

    report_md = render_report(result)

    try:
        write_json(json_out, result)
        write_text(report_out, report_md)
        write_jsonl(samples_out, samples)
    except OSError as e:
        print(f"error: failed to write outputs: {e}", file=sys.stderr)
        return 1

    primary = result["primary_decomposition"]
    print(
        f"Residual analysis complete. "
        f"unique_candidates={primary['unique_candidate_lines']} "
        f"({primary['unique_candidate_percentage_of_total']}% of corpus); "
        f"raw_files_unchanged={result['raw_files_unchanged']}"
    )
    print(f"  JSON:    {json_out}")
    print(f"  Report:  {report_out}")
    print(f"  Samples: {samples_out}")
    if candidate_path:
        print(f"  Candidates (review only): {candidate_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
