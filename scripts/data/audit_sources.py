#!/usr/bin/env python3
"""Read-only audit of raw Chichewa corpus sources.

Computes structural statistics, orthography signals, provisional language
heuristics, boilerplate pattern hits, within-source duplication, and
cross-source overlap. Never modifies files under data/raw/.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

# Allow importing sibling helpers when run as a script
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "audit_sources"
TOOL_VERSION = "1.0.0"

URL_LINE_RE = re.compile(r"https?://|\bwww\.", re.IGNORECASE)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TOKEN_RE = re.compile(r"\w+", re.UNICODE)
WORD_BOUNDARY_TEMPLATE = r"(?<!\w){term}(?!\w)"


# ---------------------------------------------------------------------------
# I/O and config
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Config or input not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def load_sources_jsonl(path: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Sources registry not found: {path}") from e
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL at {path}:{lineno}: {e}") from e
        if "source_id" not in obj or "file_path" not in obj:
            raise ValueError(
                f"Source entry at {path}:{lineno} missing source_id or file_path"
            )
        sources.append(obj)
    if not sources:
        raise ValueError(f"No sources found in {path}")
    return sources


def read_utf8_text(path: Path) -> str:
    """Read a text file as UTF-8. Clear error on malformed bytes."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(
            f"Malformed UTF-8 in {path}: {e}. "
            "Audit requires well-formed UTF-8; fix or re-export the source."
        ) from e


def compile_flags(flag_str: str) -> int:
    flags = 0
    if not flag_str:
        return flags
    for ch in flag_str:
        if ch == "i":
            flags |= re.IGNORECASE
        elif ch == "m":
            flags |= re.MULTILINE
        elif ch == "s":
            flags |= re.DOTALL
        else:
            raise ValueError(f"Unsupported regex flag '{ch}' in config")
    return flags


def build_term_pattern(terms: Sequence[str]) -> re.Pattern[str]:
    """Case-insensitive whole-word matcher for a term list."""
    if not terms:
        return re.compile(r"(?!)")  # never matches
    # Sort longer first to prefer longer matches in alternation (clarity)
    escaped = [re.escape(t) for t in sorted(terms, key=len, reverse=True)]
    body = "|".join(escaped)
    return re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.IGNORECASE | re.UNICODE)


def excerpt(text: str, limit: int) -> str:
    """Truncate to excerpt_length, collapsing internal newlines for display."""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    if limit <= 3:
        return flat[:limit]
    return flat[: limit - 3] + "..."


def percentile(sorted_vals: Sequence[float | int], p: float) -> float | None:
    if not sorted_vals:
        return None
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


def deterministic_sample(
    items: Sequence[Any],
    k: int,
    seed: int,
    salt: str = "",
) -> list[Any]:
    """Sample up to k items deterministically.

    Uses a local Random instance seeded from (seed, salt). Order of returned
    items follows the order of the input sequence among the selected indices.
    """
    if k <= 0 or not items:
        return []
    if len(items) <= k:
        return list(items)
    rng = random.Random(f"{seed}:{salt}")
    indices = sorted(rng.sample(range(len(items)), k))
    return [items[i] for i in indices]


# ---------------------------------------------------------------------------
# Normalization keys (in-memory only; never written as corpus)
# ---------------------------------------------------------------------------


def key_exact(s: str) -> str:
    return s


def key_ws_normalized(s: str) -> str:
    return " ".join(s.split())


def key_casefold_ws(s: str) -> str:
    return " ".join(s.split()).casefold()


# ---------------------------------------------------------------------------
# Structural statistics
# ---------------------------------------------------------------------------


def line_lengths(lines: Sequence[str]) -> list[int]:
    return [len(line) for line in lines]


def structural_stats(
    text: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    # Preserve whether final newline existed for inventory parity, but stats
    # operate on splitlines (drops trailing empty caused by final \n only if
    # using splitlines keepends=False — matches prior audit notes).
    raw_lines = text.splitlines()
    total_lines = len(raw_lines)
    blank_indices = [i for i, ln in enumerate(raw_lines) if not ln.strip()]
    nonempty = [(i, ln) for i, ln in enumerate(raw_lines) if ln.strip()]
    nonempty_lines = [ln for _, ln in nonempty]
    blank_count = len(blank_indices)
    nonempty_count = len(nonempty_lines)

    exact_counts = Counter(nonempty_lines)
    unique_exact = len(exact_counts)
    # duplicate lines = total nonempty that are not unique occurrences
    duplicate_line_occurrences = sum(c for c in exact_counts.values() if c > 1)
    lines_that_are_dupes = sum(1 for ln in nonempty_lines if exact_counts[ln] > 1)
    dup_pct = (
        100.0 * lines_that_are_dupes / nonempty_count if nonempty_count else 0.0
    )

    lengths = [len(ln) for ln in nonempty_lines]
    lengths_sorted = sorted(lengths)
    short_th = int(config["short_line_threshold"])
    long_th = int(config["long_line_threshold"])

    only_numbers = sum(
        1 for ln in nonempty_lines if ln.strip().isdigit()
    )
    # also pure numeric with punctuation?
    only_numbers_strict = sum(
        1
        for ln in nonempty_lines
        if re.fullmatch(r"[\d\s.,:+\-/]+", ln.strip()) is not None
        and re.search(r"\d", ln) is not None
        and not re.search(r"[A-Za-z\u00C0-\u024F]", ln)
    )
    url_lines = sum(1 for ln in nonempty_lines if URL_LINE_RE.search(ln))
    control_lines = sum(1 for ln in nonempty_lines if CONTROL_RE.search(ln))
    repl = config.get("replacement_char", "\ufffd")
    replacement_lines = sum(1 for ln in nonempty_lines if repl in ln)

    pct_cfg = config.get("percentiles", [50, 90, 95, 99])
    pct_values = {f"p{int(p)}": percentile(lengths_sorted, float(p)) for p in pct_cfg}

    stats: dict[str, Any] = {
        "total_characters": len(text),
        "total_lines": total_lines,
        "non_empty_lines": nonempty_count,
        "blank_lines": blank_count,
        "unique_exact_lines": unique_exact,
        "exact_duplicate_line_occurrences": duplicate_line_occurrences,
        "lines_appearing_more_than_once": lines_that_are_dupes,
        "duplicate_line_percentage": round(dup_pct, 4),
        "min_line_length": min(lengths) if lengths else None,
        "max_line_length": max(lengths) if lengths else None,
        "mean_line_length": round(statistics.fmean(lengths), 4) if lengths else None,
        "median_line_length": statistics.median(lengths) if lengths else None,
        "line_length_percentiles": pct_values,
        "very_short_lines": sum(1 for n in lengths if n < short_th),
        "very_long_lines": sum(1 for n in lengths if n > long_th),
        "short_line_threshold": short_th,
        "long_line_threshold": long_th,
        "lines_only_digits": only_numbers,
        "lines_numeric_only_heuristic": only_numbers_strict,
        "lines_containing_urls": url_lines,
        "lines_containing_control_chars": control_lines,
        "lines_containing_replacement_char": replacement_lines,
    }
    return stats


# ---------------------------------------------------------------------------
# Character / orthography
# ---------------------------------------------------------------------------


def character_audit(text: str, config: dict[str, Any]) -> dict[str, Any]:
    ascii_count = 0
    non_ascii_count = 0
    alphabetic = 0
    numeric = 0
    whitespace = 0
    punctuation = 0
    other = 0
    cp_counter: Counter[str] = Counter()

    for ch in text:
        o = ord(ch)
        if o < 128:
            ascii_count += 1
        else:
            non_ascii_count += 1
            cp_counter[ch] += 1
        if ch.isalpha():
            alphabetic += 1
        elif ch.isdigit():
            numeric += 1
        elif ch.isspace():
            whitespace += 1
        elif unicodedata.category(ch).startswith("P"):
            punctuation += 1
        else:
            other += 1

    chichewa_chars = config.get("chichewa_chars", ["ŵ", "Ŵ"])
    chichewa_char_counts = {c: text.count(c) for c in chichewa_chars}

    unusual_min = int(config.get("unusual_codepoint_min", 256))
    unusual = {
        ch: n
        for ch, n in cp_counter.items()
        if ord(ch) >= unusual_min
    }
    # Sort by count desc, then codepoint
    unusual_sorted = sorted(
        unusual.items(), key=lambda kv: (-kv[1], ord(kv[0]))
    )
    max_u = int(config.get("max_unusual_codepoints_report", 40))
    unusual_report = [
        {
            "char": ch,
            "codepoint": f"U+{ord(ch):04X}",
            "name": _safe_uname(ch),
            "count": n,
        }
        for ch, n in unusual_sorted[:max_u]
    ]

    # Normalization-form observations without modifying stored text
    # Sample up to N non-empty lines for NFC/NFD difference detection
    lines = [ln for ln in text.splitlines() if ln.strip()]
    sample_lines = lines[:5000]  # bounded deterministic prefix sample
    nfc_diff_lines = 0
    nfd_diff_lines = 0
    nfkc_diff_lines = 0
    for ln in sample_lines:
        if unicodedata.normalize("NFC", ln) != ln:
            nfc_diff_lines += 1
        if unicodedata.normalize("NFD", ln) != ln:
            nfd_diff_lines += 1
        if unicodedata.normalize("NFKC", ln) != ln:
            nfkc_diff_lines += 1

    # Examples with unusual non-ASCII (deterministic sample of lines)
    unusual_set = set(unusual.keys())
    unusual_examples: list[dict[str, Any]] = []
    excerpt_len = int(config["excerpt_length"])
    max_ex = int(config["max_examples_per_category"])
    for i, ln in enumerate(text.splitlines()):
        if not ln.strip():
            continue
        if any(ch in unusual_set for ch in ln):
            unusual_examples.append(
                {
                    "line_number": i + 1,
                    "excerpt": excerpt(ln, excerpt_len),
                }
            )
            if len(unusual_examples) >= max_ex:
                break

    return {
        "ascii_characters": ascii_count,
        "non_ascii_characters": non_ascii_count,
        "alphabetic_characters": alphabetic,
        "numeric_characters": numeric,
        "whitespace_characters": whitespace,
        "punctuation_characters": punctuation,
        "other_characters": other,
        "chichewa_char_counts": chichewa_char_counts,
        "unusual_codepoints": unusual_report,
        "unusual_codepoint_types": len(unusual),
        "normalization_observations": {
            "sampled_nonempty_lines": len(sample_lines),
            "lines_differ_from_nfc": nfc_diff_lines,
            "lines_differ_from_nfd": nfd_diff_lines,
            "lines_differ_from_nfkc": nfkc_diff_lines,
            "note": (
                "Observations only; text was not normalized or rewritten. "
                "Counts reflect the first up-to-5000 non-empty lines."
            ),
        },
        "unusual_character_examples": unusual_examples,
    }


def _safe_uname(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "<unnamed>"


# ---------------------------------------------------------------------------
# Language-signal heuristics
# ---------------------------------------------------------------------------


def count_term_hits(line: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(line))


def classify_language_signal(
    line: str,
    ny_pat: re.Pattern[str],
    en_pat: re.Pattern[str],
    de_pat: re.Pattern[str],
    min_matches: int,
) -> tuple[str, dict[str, int]]:
    """Return (category, hit_counts). Heuristic only — not LID."""
    counts = {
        "chichewa": count_term_hits(line, ny_pat),
        "english": count_term_hits(line, en_pat),
        "german": count_term_hits(line, de_pat),
    }
    active = {lang: n for lang, n in counts.items() if n >= min_matches}
    if not active:
        return "insufficient_signal", counts
    if len(active) == 1:
        lang = next(iter(active))
        return f"{lang}_signal", counts
    return "mixed_signal", counts


def language_signal_audit(
    lines: Sequence[str],
    config: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    ls = config.get("language_signal", {})
    min_matches = int(ls.get("min_matches_for_signal", 2))
    ny_pat = build_term_pattern(config.get("chichewa_signal_terms", []))
    en_pat = build_term_pattern(config.get("english_signal_terms", []))
    de_pat = build_term_pattern(config.get("german_signal_terms", []))

    categories = [
        "chichewa_signal",
        "english_signal",
        "german_signal",
        "mixed_signal",
        "insufficient_signal",
    ]
    buckets: dict[str, list[tuple[int, str, dict[str, int]]]] = {
        c: [] for c in categories
    }
    counts: Counter[str] = Counter()

    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        cat, hits = classify_language_signal(
            ln, ny_pat, en_pat, de_pat, min_matches
        )
        counts[cat] += 1
        buckets[cat].append((i + 1, ln, hits))

    nonempty = sum(counts.values())
    seed = int(config["random_seed"])
    sample_n = int(config["sample_count"])
    excerpt_len = int(config["excerpt_length"])

    samples: dict[str, list[dict[str, Any]]] = {}
    for cat in categories:
        picked = deterministic_sample(
            buckets[cat], sample_n, seed, salt=f"{source_id}:{cat}"
        )
        samples[cat] = [
            {
                "line_number": ln_no,
                "excerpt": excerpt(text, excerpt_len),
                "term_hits": hits,
            }
            for ln_no, text, hits in picked
        ]

    # Strongest suspicious non-Chichewa: english/german/mixed sorted by foreign hits
    suspicious: list[dict[str, Any]] = []
    for cat in ("german_signal", "english_signal", "mixed_signal"):
        ranked = sorted(
            buckets[cat],
            key=lambda t: (
                -(t[2].get("german", 0) + t[2].get("english", 0)),
                t[0],
            ),
        )
        for ln_no, text, hits in ranked[: int(config["max_examples_per_category"])]:
            suspicious.append(
                {
                    "category": cat,
                    "line_number": ln_no,
                    "excerpt": excerpt(text, excerpt_len),
                    "term_hits": hits,
                }
            )

    percentages = {
        cat: round(100.0 * counts[cat] / nonempty, 4) if nonempty else 0.0
        for cat in categories
    }

    return {
        "disclaimer": (
            "Language categories are transparent term-list heuristics, not "
            "authoritative language identification. Short lines and shared "
            "function-word collisions can mislead. Requires human review."
        ),
        "min_matches_for_signal": min_matches,
        "nonempty_lines_scored": nonempty,
        "counts": {cat: counts[cat] for cat in categories},
        "percentages": percentages,
        "samples": samples,
        "suspicious_non_chichewa_examples": suspicious[: int(config["max_examples_per_category"])],
    }


# ---------------------------------------------------------------------------
# Boilerplate / markup
# ---------------------------------------------------------------------------


def compile_boilerplate(
    patterns_cfg: Sequence[dict[str, Any]],
) -> list[tuple[str, str, re.Pattern[str]]]:
    compiled: list[tuple[str, str, re.Pattern[str]]] = []
    for entry in patterns_cfg:
        pid = entry["id"]
        desc = entry.get("description", "")
        pat = re.compile(entry["pattern"], compile_flags(entry.get("flags", "")))
        compiled.append((pid, desc, pat))
    return compiled


def boilerplate_audit(
    lines: Sequence[str],
    compiled: Sequence[tuple[str, str, re.Pattern[str]]],
    config: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    seed = int(config["random_seed"])
    sample_n = int(config["sample_count"])
    excerpt_len = int(config["excerpt_length"])
    results: dict[str, Any] = {}

    for pid, desc, pat in compiled:
        total_occurrences = 0
        matching_indices: list[int] = []
        for i, ln in enumerate(lines):
            found = pat.findall(ln)
            if found:
                total_occurrences += len(found)
                matching_indices.append(i)
        examples_src = [
            (i + 1, lines[i]) for i in matching_indices
        ]
        picked = deterministic_sample(
            examples_src, sample_n, seed, salt=f"bp:{source_id}:{pid}"
        )
        results[pid] = {
            "description": desc,
            "total_occurrences": total_occurrences,
            "matching_lines": len(matching_indices),
            "examples": [
                {"line_number": n, "excerpt": excerpt(t, excerpt_len)}
                for n, t in picked
            ],
        }
    return results


# ---------------------------------------------------------------------------
# Paragraphs and shingles
# ---------------------------------------------------------------------------


def extract_paragraphs(lines: Sequence[str]) -> list[str]:
    """Blank-line-separated paragraphs of non-empty lines joined by space."""
    paragraphs: list[str] = []
    buf: list[str] = []
    for ln in lines:
        if not ln.strip():
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
        else:
            buf.append(ln.strip())
    if buf:
        paragraphs.append(" ".join(buf))
    return paragraphs


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def shingles_from_text(
    text: str,
    window: int,
    stride: int,
    min_tokens: int,
    mode: str = "token",
) -> list[str]:
    if mode == "token":
        toks = tokenize(text)
        if len(toks) < max(window, min_tokens):
            return []
        out: list[str] = []
        for i in range(0, len(toks) - window + 1, stride):
            out.append(" ".join(toks[i : i + window]))
        return out
    if mode == "character":
        if len(text) < window:
            return []
        return [text[i : i + window] for i in range(0, len(text) - window + 1, stride)]
    raise ValueError(f"Unknown shingle mode: {mode}")


def unit_set(
    units: Iterable[str],
    key_fn,
) -> set[str]:
    return {key_fn(u) for u in units if u}


# ---------------------------------------------------------------------------
# Duplication and overlap
# ---------------------------------------------------------------------------


def top_repeated(
    counter: Counter[str],
    limit: int,
    excerpt_len: int,
) -> list[dict[str, Any]]:
    items = [(s, c) for s, c in counter.items() if c > 1]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return [
        {"count": c, "excerpt": excerpt(s, excerpt_len)}
        for s, c in items[:limit]
    ]


def within_source_duplication(
    lines: Sequence[str],
    paragraphs: Sequence[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    excerpt_len = int(config["excerpt_length"])
    limit = int(config.get("max_repeated_lines_report", 15))
    nonempty = [ln for ln in lines if ln.strip()]

    exact = Counter(nonempty)
    ws = Counter(key_ws_normalized(ln) for ln in nonempty)
    cf = Counter(key_casefold_ws(ln) for ln in nonempty)
    para_exact = Counter(paragraphs)
    para_ws = Counter(key_ws_normalized(p) for p in paragraphs)

    return {
        "repeated_exact_lines": sum(1 for c in exact.values() if c > 1),
        "repeated_ws_normalized_lines": sum(1 for c in ws.values() if c > 1),
        "repeated_casefold_lines": sum(1 for c in cf.values() if c > 1),
        "top_repeated_exact_lines": top_repeated(exact, limit, excerpt_len),
        "top_repeated_ws_normalized_lines": top_repeated(ws, limit, excerpt_len),
        "repeated_exact_paragraphs": sum(1 for c in para_exact.values() if c > 1),
        "repeated_ws_normalized_paragraphs": sum(
            1 for c in para_ws.values() if c > 1
        ),
        "top_repeated_paragraphs": top_repeated(para_exact, limit, excerpt_len),
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def coverage(a: set[str], b: set[str]) -> float:
    """Fraction of A covered by B: |A∩B| / |A|."""
    if not a:
        return 0.0
    return len(a & b) / len(a)


def overlap_pair(
    id_a: str,
    units_a: Sequence[str],
    id_b: str,
    units_b: Sequence[str],
    key_fn,
    mode_name: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    set_a = unit_set(units_a, key_fn)
    set_b = unit_set(units_b, key_fn)
    inter = set_a & set_b
    seed = int(config["random_seed"])
    excerpt_len = int(config["excerpt_length"])
    sample_n = int(config["sample_count"])

    # Deterministic examples: sort intersection keys, sample
    inter_list = sorted(inter)
    sampled_keys = deterministic_sample(
        inter_list, sample_n, seed, salt=f"ov:{mode_name}:{id_a}:{id_b}"
    )
    # Map key -> example original (first occurrence in A then B)
    def first_example(units: Sequence[str], key: str) -> str:
        for u in units:
            if key_fn(u) == key:
                return u
        return key

    examples = [
        {
            "key_preview": excerpt(k, min(excerpt_len, 80)),
            "example_excerpt": excerpt(first_example(units_a, k), excerpt_len),
        }
        for k in sampled_keys
    ]

    cov_a = coverage(set_a, set_b)
    cov_b = coverage(set_b, set_a)
    direction = "neither_substantially_contained"
    # Heuristic thresholds for reporting only
    if cov_a >= 0.5 and cov_a > cov_b + 0.1:
        direction = f"{id_a}_substantially_covered_by_{id_b}"
    elif cov_b >= 0.5 and cov_b > cov_a + 0.1:
        direction = f"{id_b}_substantially_covered_by_{id_a}"
    elif cov_a >= 0.5 and cov_b >= 0.5:
        direction = "mutual_high_coverage"

    return {
        "comparison_mode": mode_name,
        "unit_count_a": len(set_a),
        "unit_count_b": len(set_b),
        "shared_units": len(inter),
        "coverage_a_by_b": round(cov_a, 6),
        "coverage_b_by_a": round(cov_b, 6),
        "jaccard": round(jaccard(set_a, set_b), 6),
        "directionality_note": direction,
        "examples": examples,
    }


def build_shingle_units(
    lines: Sequence[str],
    config: dict[str, Any],
) -> list[str]:
    sh = config.get("shingles", {})
    mode = sh.get("mode", "token")
    window = int(sh.get("window_size", 5))
    stride = int(sh.get("stride", 1))
    min_tok = int(sh.get("min_tokens_in_unit", window))
    units: list[str] = []
    for ln in lines:
        if not ln.strip():
            continue
        units.extend(
            shingles_from_text(ln, window, stride, min_tok, mode=mode)
        )
    return units


# ---------------------------------------------------------------------------
# Candidate rejection samples
# ---------------------------------------------------------------------------


def collect_candidate_samples(
    source_id: str,
    lines: Sequence[str],
    lang_audit: dict[str, Any],
    bp_audit: dict[str, Any],
    config: dict[str, Any],
    cross_dup_line_numbers: set[int],
) -> list[dict[str, Any]]:
    """Build JSONL-oriented sample records (deterministic, truncated)."""
    seed = int(config["random_seed"])
    sample_n = int(config["sample_count"])
    excerpt_len = int(config["excerpt_length"])
    short_th = int(config["short_line_threshold"])
    long_th = int(config["long_line_threshold"])
    unusual_min = int(config.get("unusual_codepoint_min", 256))
    max_per = int(config["max_examples_per_category"])

    records: list[dict[str, Any]] = []

    def add_from_indices(
        reason: str,
        indices_1based: Sequence[int],
        metrics_fn=None,
    ) -> None:
        # convert to (lineno, line) pairs, sample
        pairs = []
        for n in indices_1based:
            if 1 <= n <= len(lines):
                pairs.append((n, lines[n - 1]))
        picked = deterministic_sample(
            pairs, min(sample_n, max_per), seed, salt=f"cand:{source_id}:{reason}"
        )
        for n, text in picked:
            rec = {
                "source_id": source_id,
                "line_number": n,
                "reason": reason,
                "excerpt": excerpt(text, excerpt_len),
                "metrics": metrics_fn(n, text) if metrics_fn else {},
            }
            records.append(rec)

    # Language samples from stored samples already; re-scan for line numbers
    en_idx, de_idx, mix_idx = [], [], []
    ny_pat = build_term_pattern(config.get("chichewa_signal_terms", []))
    en_pat = build_term_pattern(config.get("english_signal_terms", []))
    de_pat = build_term_pattern(config.get("german_signal_terms", []))
    min_m = int(config.get("language_signal", {}).get("min_matches_for_signal", 2))
    short_idx, long_idx, url_idx, unusual_idx = [], [], [], []
    bp_idx: set[int] = set()

    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        n = i + 1
        cat, hits = classify_language_signal(ln, ny_pat, en_pat, de_pat, min_m)
        if cat == "english_signal":
            en_idx.append(n)
        elif cat == "german_signal":
            de_idx.append(n)
        elif cat == "mixed_signal":
            mix_idx.append(n)
        if len(ln) < short_th:
            short_idx.append(n)
        if len(ln) > long_th:
            long_idx.append(n)
        if URL_LINE_RE.search(ln):
            url_idx.append(n)
        if any(ord(ch) >= unusual_min for ch in ln):
            unusual_idx.append(n)

    for pid, data in bp_audit.items():
        for ex in data.get("examples", []):
            # We need all matching lines; re-run pattern — stored only examples.
            pass
    # Collect all boilerplate matching lines by recompiling
    for entry in config.get("boilerplate_patterns", []):
        pat = re.compile(entry["pattern"], compile_flags(entry.get("flags", "")))
        for i, ln in enumerate(lines):
            if pat.search(ln):
                bp_idx.add(i + 1)

    add_from_indices("english_signal", en_idx)
    add_from_indices("german_signal", de_idx)
    add_from_indices("mixed_signal", mix_idx)
    add_from_indices("boilerplate", sorted(bp_idx))
    add_from_indices("url_containing", url_idx)
    add_from_indices("extremely_short", short_idx)
    add_from_indices("extremely_long", long_idx)
    add_from_indices("unusual_unicode", unusual_idx)
    add_from_indices(
        "cross_source_duplicate",
        sorted(cross_dup_line_numbers),
    )

    # Stable sort for output
    records.sort(key=lambda r: (r["source_id"], r["reason"], r["line_number"]))
    return records


# ---------------------------------------------------------------------------
# Full source processing
# ---------------------------------------------------------------------------


def process_source(
    source: dict[str, Any],
    repo_root: Path,
    config: dict[str, Any],
    bp_compiled: Sequence[tuple[str, str, re.Pattern[str]]],
) -> tuple[dict[str, Any], list[str], list[str], list[str], list[dict[str, Any]]]:
    """Return (metrics_dict, lines, paragraphs, shingles, partial_samples)."""
    rel = source["file_path"]
    path = (repo_root / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found for {source['source_id']}: {path}")

    checksum = sha256_file(path)
    size_bytes = path.stat().st_size
    text = read_utf8_text(path)
    lines = text.splitlines()
    paragraphs = extract_paragraphs(lines)
    shingles = build_shingle_units(lines, config)

    struct = structural_stats(text, config)
    chars = character_audit(text, config)
    lang = language_signal_audit(lines, config, source["source_id"])
    bp = boilerplate_audit(lines, bp_compiled, config, source["source_id"])
    within = within_source_duplication(lines, paragraphs, config)

    metrics = {
        "source_id": source["source_id"],
        "source_name": source.get("source_name"),
        "file_path": rel,
        "size_bytes": size_bytes,
        "sha256": checksum,
        "structural": struct,
        "character_orthography": chars,
        "language_signals": lang,
        "boilerplate": bp,
        "within_source_duplication": within,
        "paragraph_count": len(paragraphs),
        "shingle_count": len(shingles),
        "unique_shingle_count": len(set(shingles)),
    }
    return metrics, lines, paragraphs, shingles, []


def compute_pairwise_overlaps(
    source_ids: list[str],
    lines_map: dict[str, list[str]],
    para_map: dict[str, list[str]],
    shingle_map: dict[str, list[str]],
    config: dict[str, Any],
) -> dict[str, Any]:
    pairs = []
    for i in range(len(source_ids)):
        for j in range(i + 1, len(source_ids)):
            pairs.append((source_ids[i], source_ids[j]))

    key_modes = [
        ("exact", key_exact),
        ("whitespace_normalized", key_ws_normalized),
    ]
    if config.get("case_fold_comparison", True):
        key_modes.append(("casefold_whitespace_normalized", key_casefold_ws))

    results: dict[str, Any] = {}
    for a, b in pairs:
        pair_key = f"{a}__vs__{b}"
        pair_out: dict[str, Any] = {"source_a": a, "source_b": b, "units": {}}

        nonempty_a = [ln for ln in lines_map[a] if ln.strip()]
        nonempty_b = [ln for ln in lines_map[b] if ln.strip()]

        for unit_name, ua, ub in (
            ("nonempty_lines", nonempty_a, nonempty_b),
            ("paragraphs", para_map[a], para_map[b]),
            ("token_shingles", shingle_map[a], shingle_map[b]),
        ):
            mode_results = {}
            for mode_name, key_fn in key_modes:
                mode_results[mode_name] = overlap_pair(
                    a, ua, b, ub, key_fn, mode_name, config
                )
            pair_out["units"][unit_name] = mode_results

        results[pair_key] = pair_out
    return results


def cross_dup_line_numbers(
    source_id: str,
    lines_map: dict[str, list[str]],
    other_ids: Sequence[str],
) -> set[int]:
    """Line numbers (1-based) whose exact text appears in any other source."""
    other_exact: set[str] = set()
    for oid in other_ids:
        for ln in lines_map[oid]:
            if ln.strip():
                other_exact.add(ln)
    nums: set[int] = set()
    for i, ln in enumerate(lines_map[source_id]):
        if ln.strip() and ln in other_exact:
            nums.add(i + 1)
    return nums


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def pct(n: int, d: int) -> str:
    if d == 0:
        return "n/a"
    return f"{100.0 * n / d:.2f}%"


def render_markdown_report(audit: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append

    w("# Source audit report")
    w("")
    w(f"**Generated:** {audit['generated_at']}")
    w(f"**Tool:** {audit['tool']['name']} v{audit['tool']['version']}")
    w(f"**Config version:** {audit['config']['version']}")
    w("")
    w(
        "> **No source content was modified.** This audit only reads files under "
        "`data/raw/` and writes reports under `data/reports/` and `data/metadata/`."
    )
    w("")

    # 1. Executive summary
    w("## 1. Executive summary")
    w("")
    w(
        "This report measures structural quality, orthography, provisional "
        "language-signal heuristics, boilerplate patterns, within-source "
        "duplication, and cross-source exact overlap for three local Chichewa "
        "corpus sources."
    )
    w("")
    w("**Measured highlights (see body for detail):**")
    w("")
    for sid, src in audit["sources"].items():
        st = src["structural"]
        ls = src["language_signals"]["counts"]
        w(
            f"- **{sid}**: {st['non_empty_lines']} non-empty lines; "
            f"duplicate-line rate {st['duplicate_line_percentage']}%; "
            f"heuristic EN/DE/mixed signals "
            f"{ls.get('english_signal', 0)}/"
            f"{ls.get('german_signal', 0)}/"
            f"{ls.get('mixed_signal', 0)}; "
            f"ŵ count={src['character_orthography']['chichewa_char_counts'].get('ŵ', 0)}."
        )
    w("")
    w("**Cross-source (whitespace-normalized nonempty lines):**")
    w("")
    for pair_key, pair in audit["pairwise_overlap"].items():
        m = pair["units"]["nonempty_lines"]["whitespace_normalized"]
        w(
            f"- `{pair['source_a']}` vs `{pair['source_b']}`: "
            f"shared={m['shared_units']}, "
            f"Jaccard={m['jaccard']}, "
            f"cov(A←B)={m['coverage_a_by_b']}, "
            f"cov(B←A)={m['coverage_b_by_a']}, "
            f"note=`{m['directionality_note']}`"
        )
    w("")
    w(
        "Licensing and training eligibility remain **unresolved** for all "
        "sources. See `data/reports/training_eligibility_review.md`."
    )
    w("")

    # 2. Methodology
    w("## 2. Methodology")
    w("")
    w("- Read each registered source as UTF-8; compute SHA-256.")
    w("- Structural stats use newline-split lines; blank = empty/whitespace-only.")
    w(
        "- Language signals: whole-word, case-insensitive matches against "
        "provisional Chichewa / English / German term lists from config. "
        f"A language signal requires ≥ "
        f"{audit['config']['language_signal']['min_matches_for_signal']} hits."
    )
    w(
        "- Boilerplate: configured regular expressions (navigation, Category, "
        "URLs, HTML/wiki remnants, etc.)."
    )
    w(
        "- Overlap: in-memory comparison keys only — exact; whitespace-collapsed; "
        "optional case-folded. Units: nonempty lines, blank-line paragraphs, "
        f"token shingles (window="
        f"{audit['config']['shingles']['window_size']})."
    )
    w(
        f"- Sampling: deterministic `random.Random` with seed "
        f"{audit['config']['random_seed']}."
    )
    w("- No NFC/NFD/NFKC/NFKD rewrites; normalization only observed.")
    w("")

    # 3. Limitations
    w("## 3. Limitations")
    w("")
    w("- Heuristic language signals are **not** language identification.")
    w("- Term lists are small, provisional, and need native-speaker review.")
    w("- Exact/shingle overlap misses paraphrase and near-duplicate content.")
    w("- Filenames like `*_clean.txt` do not prove prior cleaning quality.")
    w("- No external LID, web APIs, or ML models were used.")
    w("- License/provenance cannot be inferred from text statistics.")
    w("")

    # 4. Per-source structural
    w("## 4. Per-source structural statistics")
    w("")
    for sid, src in audit["sources"].items():
        st = src["structural"]
        w(f"### {sid}")
        w("")
        w(f"- Path: `{src['file_path']}`")
        w(f"- Size (bytes): {src['size_bytes']}")
        w(f"- SHA-256: `{src['sha256']}`")
        w(f"- Characters: {st['total_characters']}")
        w(f"- Total lines: {st['total_lines']}")
        w(f"- Non-empty lines: {st['non_empty_lines']}")
        w(f"- Blank lines: {st['blank_lines']}")
        w(f"- Unique exact lines: {st['unique_exact_lines']}")
        w(
            f"- Lines appearing >1 time: {st['lines_appearing_more_than_once']} "
            f"({st['duplicate_line_percentage']}%)"
        )
        w(
            f"- Line length min/mean/median/max: "
            f"{st['min_line_length']} / {st['mean_line_length']} / "
            f"{st['median_line_length']} / {st['max_line_length']}"
        )
        w(f"- Percentiles: {st['line_length_percentiles']}")
        w(
            f"- Very short (<{st['short_line_threshold']}): {st['very_short_lines']}; "
            f"very long (>{st['long_line_threshold']}): {st['very_long_lines']}"
        )
        w(f"- Digit-only lines: {st['lines_only_digits']}")
        w(f"- URL-containing lines: {st['lines_containing_urls']}")
        w(f"- Control-char lines: {st['lines_containing_control_chars']}")
        w(f"- Replacement-char (U+FFFD) lines: {st['lines_containing_replacement_char']}")
        w(f"- Paragraphs: {src['paragraph_count']}; shingles: {src['shingle_count']} "
          f"(unique {src['unique_shingle_count']})")
        w("")

    # 5. Language signals
    w("## 5. Language-signal findings")
    w("")
    w(
        "> Categories are **heuristic signals**, not definitive language labels. "
        "Collisions (e.g. short function words) can produce false positives."
    )
    w("")
    for sid, src in audit["sources"].items():
        ls = src["language_signals"]
        w(f"### {sid}")
        w("")
        w(f"Non-empty lines scored: {ls['nonempty_lines_scored']}")
        w("")
        w("| category | count | % |")
        w("|----------|------:|--:|")
        for cat, n in ls["counts"].items():
            w(f"| {cat} | {n} | {ls['percentages'][cat]} |")
        w("")
        if ls["suspicious_non_chichewa_examples"]:
            w("Suspicious examples (heuristic; truncated):")
            w("")
            for ex in ls["suspicious_non_chichewa_examples"][:5]:
                w(
                    f"- L{ex['line_number']} [{ex['category']}] "
                    f"hits={ex['term_hits']}: `{ex['excerpt']}`"
                )
            w("")
        else:
            w("No english/german/mixed-signal examples retained under sampling limits.")
            w("")

    # 6. Character / Unicode
    w("## 6. Character and Unicode findings")
    w("")
    for sid, src in audit["sources"].items():
        ch = src["character_orthography"]
        w(f"### {sid}")
        w("")
        w(
            f"- ASCII / non-ASCII: {ch['ascii_characters']} / {ch['non_ascii_characters']}"
        )
        w(
            f"- alpha/num/ws/punct/other: "
            f"{ch['alphabetic_characters']}/"
            f"{ch['numeric_characters']}/"
            f"{ch['whitespace_characters']}/"
            f"{ch['punctuation_characters']}/"
            f"{ch['other_characters']}"
        )
        w(f"- Chichewa-relevant chars: {ch['chichewa_char_counts']}")
        nobs = ch["normalization_observations"]
        w(
            f"- Normalization observations (first {nobs['sampled_nonempty_lines']} "
            f"non-empty lines): differ NFC={nobs['lines_differ_from_nfc']}, "
            f"NFD={nobs['lines_differ_from_nfd']}, "
            f"NFKC={nobs['lines_differ_from_nfkc']}"
        )
        if ch["unusual_codepoints"]:
            top = ", ".join(
                f"{u['char']} ({u['codepoint']}, n={u['count']})"
                for u in ch["unusual_codepoints"][:8]
            )
            w(f"- Top unusual codepoints: {top}")
        w("")

    # 7. Boilerplate
    w("## 7. Boilerplate findings")
    w("")
    # Aggregate table
    pattern_ids = sorted(
        next(iter(audit["sources"].values()))["boilerplate"].keys()
    )
    header = "| pattern | " + " | ".join(audit["sources"].keys()) + " |"
    sep = "|---------|" + "|".join(["------:"] * len(audit["sources"])) + "|"
    w("Matching lines by pattern and source:")
    w("")
    w(header)
    w(sep)
    for pid in pattern_ids:
        cells = []
        for sid in audit["sources"]:
            cells.append(str(audit["sources"][sid]["boilerplate"][pid]["matching_lines"]))
        w(f"| `{pid}` | " + " | ".join(cells) + " |")
    w("")
    for sid, src in audit["sources"].items():
        notable = [
            (pid, d)
            for pid, d in src["boilerplate"].items()
            if d["matching_lines"] > 0
        ]
        if not notable:
            continue
        w(f"### Examples — {sid}")
        w("")
        for pid, d in sorted(notable, key=lambda x: -x[1]["matching_lines"])[:6]:
            w(
                f"- `{pid}` ({d['description']}): "
                f"{d['matching_lines']} lines, {d['total_occurrences']} hits"
            )
            for ex in d["examples"][:2]:
                w(f"  - L{ex['line_number']}: `{ex['excerpt']}`")
        w("")

    # 8. Within-source duplication
    w("## 8. Within-source duplication")
    w("")
    for sid, src in audit["sources"].items():
        d = src["within_source_duplication"]
        w(f"### {sid}")
        w("")
        w(f"- Distinct lines with exact repeats: {d['repeated_exact_lines']}")
        w(
            f"- Distinct lines with ws-normalized repeats: "
            f"{d['repeated_ws_normalized_lines']}"
        )
        w(f"- Distinct repeated paragraphs: {d['repeated_exact_paragraphs']}")
        if d["top_repeated_exact_lines"]:
            w("- Top repeated exact lines:")
            for item in d["top_repeated_exact_lines"][:5]:
                w(f"  - ×{item['count']}: `{item['excerpt']}`")
        w("")

    # 9. Overlap matrix
    w("## 9. Cross-source overlap matrix")
    w("")
    w(
        "Values below use **whitespace-normalized nonempty lines** "
        "(Jaccard / coverage of row by column)."
    )
    w("")
    sids = list(audit["sources"].keys())
    w("| A \\ B | " + " | ".join(sids) + " |")
    w("|-------|" + "|".join(["---"] * len(sids)) + "|")
    for a in sids:
        row = [a]
        for b in sids:
            if a == b:
                row.append("—")
            else:
                # find pair
                key1 = f"{a}__vs__{b}"
                key2 = f"{b}__vs__{a}"
                pair = audit["pairwise_overlap"].get(key1) or audit["pairwise_overlap"].get(key2)
                m = pair["units"]["nonempty_lines"]["whitespace_normalized"]
                if pair["source_a"] == a:
                    cov = m["coverage_a_by_b"]
                    jac = m["jaccard"]
                else:
                    cov = m["coverage_b_by_a"]
                    jac = m["jaccard"]
                row.append(f"J={jac:.4f}; cov={cov:.4f}")
        w("| " + " | ".join(row) + " |")
    w("")

    # 10. Pair details
    w("## 10. Source-pair overlap details")
    w("")
    for pair_key, pair in audit["pairwise_overlap"].items():
        w(f"### {pair['source_a']} vs {pair['source_b']}")
        w("")
        for unit_name, modes in pair["units"].items():
            w(f"#### Unit: `{unit_name}`")
            w("")
            w("| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |")
            w("|------|----:|----:|-------:|--------:|--------:|--------:|-----------|")
            for mode_name, m in modes.items():
                w(
                    f"| {mode_name} | {m['unit_count_a']} | {m['unit_count_b']} | "
                    f"{m['shared_units']} | {m['coverage_a_by_b']} | "
                    f"{m['coverage_b_by_a']} | {m['jaccard']} | "
                    f"{m['directionality_note']} |"
                )
            # examples from whitespace_normalized if present
            m0 = modes.get("whitespace_normalized") or next(iter(modes.values()))
            if m0["examples"]:
                w("")
                w("Shared examples (truncated):")
                for ex in m0["examples"][:3]:
                    w(f"- `{ex['example_excerpt']}`")
            w("")

    # 11. Suspicious examples
    w("## 11. Representative suspicious examples")
    w("")
    w(
        f"Full deterministic sample records: "
        f"`{audit.get('samples_path', 'data/reports/source_audit_samples.jsonl')}`."
    )
    w("")
    for sid, src in audit["sources"].items():
        w(f"### {sid}")
        w("")
        shown = 0
        for ex in src["language_signals"].get("suspicious_non_chichewa_examples", []):
            w(f"- [{ex['category']}] L{ex['line_number']}: `{ex['excerpt']}`")
            shown += 1
        for pid, d in src["boilerplate"].items():
            if d["matching_lines"] and d["examples"] and shown < 8:
                ex = d["examples"][0]
                w(f"- [boilerplate:{pid}] L{ex['line_number']}: `{ex['excerpt']}`")
                shown += 1
        if shown == 0:
            w("- (no high-priority suspicious samples under current heuristics)")
        w("")

    # 12. Recommended human decisions
    w("## 12. Recommended human decisions")
    w("")
    w(
        "The following are **decision prompts**, not automated outcomes. "
        "Licensing cannot be decided by this tool."
    )
    w("")
    w("| Source | Evidence summary | Suggested options for human review |")
    w("|--------|------------------|------------------------------------|")
    for sid, src in audit["sources"].items():
        st = src["structural"]
        ls = src["language_signals"]["counts"]
        foreign = (
            ls.get("english_signal", 0)
            + ls.get("german_signal", 0)
            + ls.get("mixed_signal", 0)
        )
        summary = (
            f"dup={st['duplicate_line_percentage']}%; "
            f"foreign_heuristic_lines={foreign}; "
            f"url_lines={st['lines_containing_urls']}"
        )
        if sid == "bible":
            opts = "train (if licensed) / holdout / exclude — evidence suggests relatively homogeneous religious text"
        elif sid == "wikipedia":
            opts = "train after cleaning (if licensed) / holdout — evidence suggests boilerplate + possible non-Chichewa lines"
        else:
            opts = "exclude or heavy filter / holdout — evidence suggests mixed content and likely overlap with other sources"
        w(f"| {sid} | {summary} | {opts} |")
    w("")

    # 13. Cleaning priorities
    w("## 13. Proposed cleaning priorities")
    w("")
    w("Priorities for a **future** cleaning design (not implemented here):")
    w("")
    w("1. Complete license/provenance review before any training use.")
    w("2. Language-filter and boilerplate removal for `wikipedia` and especially `existing_corpus`.")
    w("3. Cross-source deduplication with explicit priority order once eligibility is known.")
    w("4. Light structural normalization only (documented); keep raw immutable.")
    w("5. Re-audit after cleaning before splits.")
    w("")

    # 14. No modification statement
    w("## 14. Modification statement")
    w("")
    w(
        "**No source content was modified.** Raw SHA-256 checksums recorded in "
        "this audit should match pre-audit inventory values."
    )
    w("")
    w("### Warnings and limitations (machine copy)")
    w("")
    for note in audit.get("warnings", []):
        w(f"- {note}")
    w("")

    return "\n".join(lines) + "\n"


def render_eligibility_review(sources: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    w = lines.append
    w("# Training eligibility review")
    w("")
    w(f"**Status:** pending human review  ")
    w(f"**Generated:** {utc_now_iso()}  ")
    w(
        "**Note:** This checklist is an aid only. No automated licensing "
        "decision was made."
    )
    w("")
    w("## Decision table")
    w("")
    w(
        "| Source | Provenance known | License known | Allowed for training | "
        "Holdout only | Decision | Evidence needed |"
    )
    w(
        "| ------ | ---------------: | ------------: | -------------------: | "
        "-----------: | -------- | --------------- |"
    )
    for s in sources:
        sid = s["source_id"]
        w(
            f"| {sid} | unknown | unknown | not yet verified | not yet verified | "
            f"pending human review | Origin URL/dump date; license text; "
            f"redistribution + training rights; attribution rules |"
        )
    w("")
    w("## Reviewer checklist (per source)")
    w("")
    w("- [ ] Confirm source origin")
    w("- [ ] Confirm license or permission")
    w("- [ ] Confirm redistribution rights")
    w("- [ ] Confirm training rights")
    w("- [ ] Confirm whether attribution is required")
    w("- [ ] Confirm whether derived datasets may be published")
    w("- [ ] Record decision in `data/metadata/sources.jsonl` "
      "(`allowed_for_training`, `holdout_only`, `license`, `source_url`)")
    w("")
    w("## Guidance")
    w("")
    w(
        "Do not set `allowed_for_training` to true without documented rights. "
        "When uncertain, prefer holdout or exclude. Audit statistics do not "
        "substitute for legal review."
    )
    w("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_audit(
    raw_dir: Path,
    sources_path: Path,
    config_path: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str]:
    config = load_json(config_path)
    sources = load_sources_jsonl(sources_path)
    bp_compiled = compile_boilerplate(config.get("boilerplate_patterns", []))

    source_metrics: dict[str, Any] = {}
    lines_map: dict[str, list[str]] = {}
    para_map: dict[str, list[str]] = {}
    shingle_map: dict[str, list[str]] = {}
    checksums: dict[str, str] = {}

    # Stable order by source_id
    sources_sorted = sorted(sources, key=lambda s: s["source_id"])

    for src in sources_sorted:
        # Prefer registry path; verify it is under raw_dir when possible
        metrics, lines, paragraphs, shingles, _ = process_source(
            src, repo_root, config, bp_compiled
        )
        sid = src["source_id"]
        source_metrics[sid] = metrics
        lines_map[sid] = lines
        para_map[sid] = paragraphs
        shingle_map[sid] = shingles
        checksums[sid] = metrics["sha256"]

    sids = list(source_metrics.keys())
    pairwise = compute_pairwise_overlaps(
        sids, lines_map, para_map, shingle_map, config
    )

    # Candidate samples
    all_samples: list[dict[str, Any]] = []
    for sid in sids:
        others = [o for o in sids if o != sid]
        xd = cross_dup_line_numbers(sid, lines_map, others)
        samples = collect_candidate_samples(
            sid,
            lines_map[sid],
            source_metrics[sid]["language_signals"],
            source_metrics[sid]["boilerplate"],
            config,
            xd,
        )
        all_samples.extend(samples)

    warnings = [
        "Language-signal categories are heuristics, not language identification.",
        "Term lists are provisional and require native-speaker review.",
        "Exact overlap does not capture near-duplicates or paraphrases.",
        "No licensing or training-eligibility decision is made by this tool.",
        "Raw corpus files must remain byte-identical after the audit.",
        config.get(
            "term_list_disclaimer",
            "Signal term lists are provisional.",
        ),
    ]

    audit: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
        },
        "config": {
            "version": config.get("version"),
            "path": str(config_path),
            "short_line_threshold": config.get("short_line_threshold"),
            "long_line_threshold": config.get("long_line_threshold"),
            "sample_count": config.get("sample_count"),
            "excerpt_length": config.get("excerpt_length"),
            "random_seed": config.get("random_seed"),
            "case_fold_comparison": config.get("case_fold_comparison"),
            "language_signal": config.get("language_signal"),
            "shingles": config.get("shingles"),
            "term_list_disclaimer": config.get("term_list_disclaimer"),
        },
        "raw_dir": str(raw_dir),
        "raw_checksums": checksums,
        "sources": source_metrics,
        "pairwise_overlap": pairwise,
        "warnings": warnings,
        "limitations": [
            "No external language identification.",
            "No content modification or cleaning.",
            "Normalization used only for in-memory comparison keys and observations.",
        ],
        "samples_path": "data/reports/source_audit_samples.jsonl",
    }

    report_md = render_markdown_report(audit)
    eligibility_md = render_eligibility_review(sources_sorted)
    return audit, all_samples, report_md, eligibility_md


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
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
        description="Read-only multi-source corpus audit (no raw modification).",
    )
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument(
        "--sources",
        type=Path,
        default=Path("data/metadata/sources.jsonl"),
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/source_audit.json"),
    )
    p.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/metadata/source_audit.json"),
    )
    p.add_argument(
        "--report-output",
        type=Path,
        default=Path("data/reports/source_audit.md"),
    )
    p.add_argument(
        "--samples-output",
        type=Path,
        default=Path("data/reports/source_audit_samples.jsonl"),
    )
    p.add_argument(
        "--eligibility-output",
        type=Path,
        default=Path("data/reports/training_eligibility_review.md"),
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for resolving relative source paths "
        "(default: inferred from script location).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else Path(__file__).resolve().parents[2]
    )

    # Pre-checksums of all files under raw that we will read
    raw_dir = args.raw_dir if args.raw_dir.is_absolute() else repo_root / args.raw_dir
    try:
        sources = load_sources_jsonl(
            args.sources if args.sources.is_absolute() else repo_root / args.sources
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    pre_checksums: dict[str, str] = {}
    for src in sources:
        path = repo_root / src["file_path"]
        try:
            pre_checksums[src["source_id"]] = sha256_file(path)
        except OSError as e:
            print(f"error: cannot checksum {path}: {e}", file=sys.stderr)
            return 1

    try:
        audit, samples, report_md, eligibility_md = run_audit(
            raw_dir=raw_dir,
            sources_path=(
                args.sources
                if args.sources.is_absolute()
                else repo_root / args.sources
            ),
            config_path=(
                args.config
                if args.config.is_absolute()
                else repo_root / args.config
            ),
            repo_root=repo_root,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    # Post-checksum verification (raw immutability)
    post_checksums: dict[str, str] = {}
    for src in sources:
        path = repo_root / src["file_path"]
        post_checksums[src["source_id"]] = sha256_file(path)

    mismatches = [
        sid
        for sid in pre_checksums
        if pre_checksums[sid] != post_checksums[sid]
    ]
    if mismatches:
        print(
            f"error: raw files changed during audit: {mismatches}",
            file=sys.stderr,
        )
        return 2

    audit["pre_audit_checksums"] = pre_checksums
    audit["post_audit_checksums"] = post_checksums
    audit["raw_files_unchanged"] = True
    audit["samples_path"] = str(
        args.samples_output
        if args.samples_output.is_absolute()
        else args.samples_output
    )

    try:
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
        elig_out = (
            args.eligibility_output
            if args.eligibility_output.is_absolute()
            else repo_root / args.eligibility_output
        )

        # Refresh report with final checksum fields already in audit
        report_md = render_markdown_report(audit)

        write_json(json_out, audit)
        write_text(report_out, report_md)
        write_jsonl(samples_out, samples)
        write_text(elig_out, eligibility_md)
    except OSError as e:
        print(f"error: failed to write outputs: {e}", file=sys.stderr)
        return 1

    print(
        f"Audit complete: {len(audit['sources'])} sources, "
        f"{len(samples)} sample records. "
        f"raw_files_unchanged={audit['raw_files_unchanged']}"
    )
    print(f"  JSON:    {json_out}")
    print(f"  Report:  {report_out}")
    print(f"  Samples: {samples_out}")
    print(f"  Eligibility: {elig_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
