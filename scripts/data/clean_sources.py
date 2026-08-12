#!/usr/bin/env python3
"""Config-driven cleaning pipeline for Bible and Wikipedia.

Reads immutable files under data/raw/, applies ordered filter/transform rules
from config, and writes all artifacts under data/interim/ only.

Logs every removed line (with rule id) and every content-changing transform.
Produces before/after quality metrics and a human-readable report.

Does not train models, create splits, or set training eligibility.
Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
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
    compile_flags,
    excerpt,
    load_json,
    percentile,
    read_utf8_text,
    utc_now_iso,
)

TOOL_NAME = "clean_sources"
TOOL_VERSION = "2.0.0"

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
PUNCT_ONLY_RE = re.compile(r"^[\W_]+$", re.UNICODE)
URL_TOKEN_RE = re.compile(
    r"https?://\S+|www\.\S+",
    re.IGNORECASE,
)
# Remainder after URL strip is "empty-ish"
META_ONLY_RE = re.compile(
    r"^(?:link|thumb|file|image|archive\.org|retrieved|doi:|pmid)\b",
    re.IGNORECASE,
)
TABLE_DUMP_RE = re.compile(
    r"(appsgoals|capacity:\s*\d|matchday\s*\d|previous final appearances|"
    r"portrait name took office|teamlocationstadium|"
    r"\d{2,}%\s*\d|\d+\s*ophedwa\d)",
    re.IGNORECASE,
)
THUMB_LOGO_RE = re.compile(
    r"^\s*(?:thumb|right|left)\b.*(?:logo|wikimedia)|"
    r"^\s*thumb\s+\d+x\d+|"
    r"^\s*thumb\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Quality snapshot (before/after)
# ---------------------------------------------------------------------------


def quality_snapshot(
    lines: Sequence[str],
    config: dict[str, Any],
    *,
    lang_patterns: dict[str, re.Pattern[str]] | None = None,
    bp_patterns: list[tuple[str, re.Pattern[str]]] | None = None,
) -> dict[str, Any]:
    short_th = int(config.get("short_line_threshold", 20))
    long_th = int(config.get("long_line_threshold", 500))
    pct_list = config.get("percentiles", [50, 90, 95, 99])

    total = len(lines)
    blank = sum(1 for ln in lines if not ln.strip())
    nonempty = [ln for ln in lines if ln.strip()]
    lengths = [len(ln) for ln in nonempty]
    lengths_sorted = sorted(lengths)
    exact = Counter(nonempty)
    text = "\n".join(lines)
    if lines:
        # approximate original text size without forcing trailing newline semantics
        char_count = sum(len(ln) for ln in lines) + max(0, len(lines) - 1)
    else:
        char_count = 0
    token_count = sum(len(TOKEN_RE.findall(ln)) for ln in nonempty)

    lang_counts: Counter[str] = Counter()
    if lang_patterns is None:
        lang_patterns = _build_lang_patterns(config)
    min_m = int(config.get("language_signal", {}).get("min_matches_for_signal", 2))
    for ln in nonempty:
        cat, _ = classify_language_signal(
            ln,
            lang_patterns["ny"],
            lang_patterns["en"],
            lang_patterns["de"],
            min_m,
        )
        lang_counts[cat] += 1

    if bp_patterns is None:
        bp_patterns = _build_bp_patterns(config)
    bp_counts: dict[str, int] = {}
    for pid, pat in bp_patterns:
        bp_counts[pid] = sum(1 for ln in nonempty if pat.search(ln))

    url_lines = sum(1 for ln in nonempty if URL_LINE_RE.search(ln))
    digit_only = sum(1 for ln in nonempty if ln.strip().isdigit())

    pct_values = {
        f"p{int(p)}": percentile(lengths_sorted, float(p)) for p in pct_list
    }
    n_non = len(nonempty)
    lang_pct = {
        k: round(100.0 * lang_counts.get(k, 0) / n_non, 4) if n_non else 0.0
        for k in (
            "chichewa_signal",
            "english_signal",
            "german_signal",
            "mixed_signal",
            "insufficient_signal",
        )
    }

    return {
        "total_lines": total,
        "blank_lines": blank,
        "non_empty_lines": n_non,
        "unique_exact_nonempty": len(exact),
        "duplicate_line_percentage": (
            round(
                100.0 * sum(1 for ln in nonempty if exact[ln] > 1) / n_non,
                4,
            )
            if n_non
            else 0.0
        ),
        "character_count_estimate": char_count,
        "estimated_word_token_count": token_count,
        "min_line_length": min(lengths) if lengths else None,
        "max_line_length": max(lengths) if lengths else None,
        "mean_line_length": (
            round(statistics.fmean(lengths), 4) if lengths else None
        ),
        "median_line_length": statistics.median(lengths) if lengths else None,
        "line_length_percentiles": pct_values,
        "very_short_lines": sum(1 for n in lengths if n < short_th),
        "very_long_lines": sum(1 for n in lengths if n > long_th),
        "url_containing_lines": url_lines,
        "digit_only_lines": digit_only,
        "language_signals": {
            "disclaimer": (
                "Heuristic term-list signals only — not authoritative language labels."
            ),
            "counts": {
                k: int(lang_counts.get(k, 0))
                for k in (
                    "chichewa_signal",
                    "english_signal",
                    "german_signal",
                    "mixed_signal",
                    "insufficient_signal",
                )
            },
            "percentages": lang_pct,
        },
        "boilerplate_matching_lines": bp_counts,
    }


def _build_lang_patterns(config: dict[str, Any]) -> dict[str, re.Pattern[str]]:
    return {
        "ny": build_term_pattern(config.get("chichewa_signal_terms", [])),
        "en": build_term_pattern(config.get("english_signal_terms", [])),
        "de": build_term_pattern(config.get("german_signal_terms", [])),
    }


def _build_bp_patterns(
    config: dict[str, Any],
) -> list[tuple[str, re.Pattern[str]]]:
    out: list[tuple[str, re.Pattern[str]]] = []
    for entry in config.get("boilerplate_patterns_for_metrics", []):
        out.append(
            (
                entry["id"],
                re.compile(entry["pattern"], compile_flags(entry.get("flags", ""))),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


class RuleContext:
    """Mutable per-source state for stateful rules (e.g. dedupe)."""

    def __init__(self) -> None:
        self.seen_exact: set[str] = set()


def _lang_hits(
    line: str,
    lang_patterns: dict[str, re.Pattern[str]],
) -> dict[str, int]:
    return {
        "chichewa": len(lang_patterns["ny"].findall(line)),
        "english": len(lang_patterns["en"].findall(line)),
        "german": len(lang_patterns["de"].findall(line)),
    }


def strip_urls(line: str) -> str:
    """Remove URL tokens; collapse leftover whitespace."""
    without = URL_TOKEN_RE.sub(" ", line)
    return " ".join(without.split())


def is_punctuation_only(s: str) -> bool:
    t = s.strip()
    return bool(t) and PUNCT_ONLY_RE.match(t) is not None


def is_url_only_line(s: str) -> bool:
    t = s.strip()
    if not t:
        return False
    remainder = strip_urls(t)
    return not remainder or is_punctuation_only(remainder)


def compile_rule(
    rule: dict[str, Any],
    config: dict[str, Any],
    lang_patterns: dict[str, re.Pattern[str]],
) -> dict[str, Any]:
    """Attach compiled callables to a rule dict (returns enriched copy)."""
    r = dict(rule)
    rtype = rule["type"]
    min_m = int(config.get("language_signal", {}).get("min_matches_for_signal", 2))
    ls = config.get("language_signal", {})

    if rtype == "drop_blank":
        def pred(line: str, ctx: RuleContext) -> bool:
            return not line.strip()

        r["_predicate"] = pred

    elif rtype == "drop_digit_only":
        def pred(line: str, ctx: RuleContext) -> bool:
            s = line.strip()
            return bool(s) and s.isdigit()

        r["_predicate"] = pred

    elif rtype == "drop_punctuation_only":
        def pred(line: str, ctx: RuleContext) -> bool:
            return is_punctuation_only(line)

        r["_predicate"] = pred

    elif rtype == "drop_url":
        # v1: remove any line containing a URL
        def pred(line: str, ctx: RuleContext) -> bool:
            return bool(URL_LINE_RE.search(line))

        r["_predicate"] = pred

    elif rtype == "drop_url_only":
        def pred(line: str, ctx: RuleContext) -> bool:
            return is_url_only_line(line)

        r["_predicate"] = pred

    elif rtype == "drop_regex":
        pat = re.compile(rule["pattern"], compile_flags(rule.get("flags", "")))

        def pred(line: str, ctx: RuleContext, _pat=pat) -> bool:
            return bool(_pat.search(line))

        r["_predicate"] = pred

    elif rtype == "drop_regex_fullmatch":
        pat = re.compile(rule["pattern"], compile_flags(rule.get("flags", "")))

        def pred(line: str, ctx: RuleContext, _pat=pat) -> bool:
            return _pat.fullmatch(line.strip()) is not None

        r["_predicate"] = pred

    elif rtype == "drop_min_length":
        min_len = int(rule["min_length"])

        def pred(line: str, ctx: RuleContext, _m=min_len) -> bool:
            if not line.strip():
                return False
            return len(line) < _m

        r["_predicate"] = pred

    elif rtype == "drop_short_conditional":
        # Precision-first: short lines only if also empty-of-language noise.
        max_len = int(rule.get("max_length", config.get("short_line_threshold", 20)))
        nav_pats = [
            re.compile(p["pattern"], compile_flags(p.get("flags", "")))
            for p in rule.get("boilerplate_patterns", [])
        ]

        def pred(line: str, ctx: RuleContext, _max=max_len, _pats=nav_pats) -> bool:
            s = line.strip()
            if not s or len(s) >= _max:
                return False
            if s.isdigit() or is_punctuation_only(s) or is_url_only_line(s):
                return True
            if META_ONLY_RE.match(s):
                return True
            for pat in _pats:
                if pat.search(s):
                    return True
            # bare Category: or thumb
            if re.match(r"^(category\s*:|thumb\b)", s, re.I):
                return True
            return False

        r["_predicate"] = pred

    elif rtype == "drop_max_length":
        max_len = int(rule["max_length"])

        def pred(line: str, ctx: RuleContext, _m=max_len) -> bool:
            if not line.strip():
                return False
            return len(line) > _m

        r["_predicate"] = pred

    elif rtype == "drop_long_table_dump":
        min_len = int(rule.get("min_length", 500))

        def pred(line: str, ctx: RuleContext, _m=min_len) -> bool:
            if len(line) < _m:
                return False
            if TABLE_DUMP_RE.search(line):
                return True
            # high digit density + few spaces relative to length
            digits = sum(c.isdigit() for c in line)
            if digits / max(len(line), 1) > 0.25 and line.count(" ") < len(line) / 40:
                return True
            return False

        r["_predicate"] = pred

    elif rtype == "drop_language_signal":
        targets = set(rule.get("signals", []))

        def pred(
            line: str,
            ctx: RuleContext,
            _targets=targets,
            _min_m=min_m,
        ) -> bool:
            if not line.strip():
                return False
            cat, hits = classify_language_signal(
                line,
                lang_patterns["ny"],
                lang_patterns["en"],
                lang_patterns["de"],
                _min_m,
            )
            if cat in _targets:
                ctx._last_lang = {"category": cat, "term_hits": hits}  # type: ignore[attr-defined]
                return True
            return False

        r["_predicate"] = pred

    elif rtype == "drop_high_confidence_foreign":
        # Transparent thresholds from config / rule
        min_en = int(rule.get("min_english_hits", ls.get("min_english_hits", 3)))
        min_de = int(rule.get("min_german_hits", ls.get("min_german_hits", 2)))
        max_ny = int(rule.get("max_chichewa_hits", ls.get("max_chichewa_hits", 0)))
        margin = int(rule.get("dominance_margin", ls.get("dominance_margin", 3)))

        def pred(
            line: str,
            ctx: RuleContext,
            _min_en=min_en,
            _min_de=min_de,
            _max_ny=max_ny,
            _margin=margin,
        ) -> bool:
            if not line.strip():
                return False
            hits = _lang_hits(line, lang_patterns)
            ny, en, de = hits["chichewa"], hits["english"], hits["german"]
            # Pure foreign: English/German signal with little/no Chichewa
            if en >= _min_en and ny <= _max_ny:
                ctx._last_lang = {"category": "high_conf_english", "term_hits": hits}  # type: ignore[attr-defined]
                return True
            if de >= _min_de and ny <= _max_ny:
                ctx._last_lang = {"category": "high_conf_german", "term_hits": hits}  # type: ignore[attr-defined]
                return True
            # Strong English dominance over Chichewa
            if en >= _min_en and en >= ny + _margin:
                ctx._last_lang = {"category": "english_dominant", "term_hits": hits}  # type: ignore[attr-defined]
                return True
            return False

        r["_predicate"] = pred

    elif rtype == "drop_wikimedia_chrome":
        max_len = int(rule.get("max_length", 80))

        def pred(line: str, ctx: RuleContext, _max=max_len) -> bool:
            s = line.strip()
            if not s:
                return False
            if THUMB_LOGO_RE.search(s):
                return True
            # short chrome only
            if len(s) <= _max and re.search(r"\bWikimedia\b", s, re.I):
                # keep if strong Chichewa content words beyond name-drop
                hits = _lang_hits(s, lang_patterns)
                if hits["chichewa"] >= 2 and hits["english"] <= hits["chichewa"]:
                    return False
                return True
            return False

        r["_predicate"] = pred

    elif rtype == "dedupe_exact":
        def pred(line: str, ctx: RuleContext) -> bool:
            if not line.strip():
                return False
            if line in ctx.seen_exact:
                return True
            ctx.seen_exact.add(line)
            return False

        r["_predicate"] = pred
        r["_stateful"] = True

    elif rtype == "transform_strip":
        def transform(line: str) -> str:
            return line.strip()

        r["_transform"] = transform

    elif rtype == "transform_strip_urls":
        def transform(line: str) -> str:
            if not URL_TOKEN_RE.search(line):
                return line
            return strip_urls(line)

        r["_transform"] = transform

    else:
        raise ValueError(f"Unknown rule type: {rtype!r} (rule id={rule.get('id')})")

    return r


def apply_rules(
    lines: Sequence[str],
    rules: Sequence[dict[str, Any]],
    config: dict[str, Any],
    source_id: str,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Apply enabled rules in config order (drops and transforms interleaved).

    Drop: first matching drop wins.
    Transform: applied in place; may empty the line (then dropped as blank).
    Dedupe runs only among lines that reach it (after prior drops).

    Returns (kept_lines, removal_records, transform_records, rule_counts).
    """
    lang_patterns = _build_lang_patterns(config)
    compiled = [
        compile_rule(r, config, lang_patterns)
        for r in rules
        if r.get("enabled", True)
    ]

    ctx = RuleContext()
    excerpt_len = int(config.get("excerpt_length", 120))
    removals: list[dict[str, Any]] = []
    transforms: list[dict[str, Any]] = []
    kept: list[str] = []
    rule_counts: Counter[str] = Counter()

    for line_no, original in enumerate(lines, start=1):
        line = original
        dropped = False

        for rule in compiled:
            rtype = rule["type"]

            if "_transform" in rule:
                new = rule["_transform"](line)
                if new != line:
                    transforms.append(
                        {
                            "source_id": source_id,
                            "line_number": line_no,
                            "rule_id": rule["id"],
                            "rule_type": rtype,
                            "rule_description": rule.get("description", ""),
                            "before_excerpt": excerpt(line, excerpt_len),
                            "after_excerpt": excerpt(new, excerpt_len),
                        }
                    )
                    rule_counts[f"transform:{rule['id']}"] += 1
                    line = new
                continue

            if "_predicate" not in rule:
                continue

            # Dedupe: mark seen only for survivors of this rule as non-dup
            if rtype == "dedupe_exact":
                if not line.strip():
                    continue
                if line in ctx.seen_exact:
                    removals.append(
                        {
                            "source_id": source_id,
                            "line_number": line_no,
                            "rule_id": rule["id"],
                            "rule_type": rtype,
                            "rule_description": rule.get("description", ""),
                            "excerpt": excerpt(line, excerpt_len),
                            "metrics": {"length": len(line)},
                        }
                    )
                    rule_counts[rule["id"]] += 1
                    dropped = True
                    break
                ctx.seen_exact.add(line)
                continue

            if rule["_predicate"](line, ctx):
                metrics: dict[str, Any] = {"length": len(line)}
                if hasattr(ctx, "_last_lang"):
                    metrics.update(ctx._last_lang)  # type: ignore[attr-defined]
                if "pattern" in rule:
                    metrics["pattern"] = rule.get("pattern")
                removals.append(
                    {
                        "source_id": source_id,
                        "line_number": line_no,
                        "rule_id": rule["id"],
                        "rule_type": rtype,
                        "rule_description": rule.get("description", ""),
                        "excerpt": excerpt(line if line.strip() else original, excerpt_len),
                        "metrics": metrics,
                    }
                )
                rule_counts[rule["id"]] += 1
                dropped = True
                break

        if dropped:
            continue

        if not line.strip():
            if original.strip():
                removals.append(
                    {
                        "source_id": source_id,
                        "line_number": line_no,
                        "rule_id": "drop_blank_after_transform",
                        "rule_type": "drop_blank_after_transform",
                        "rule_description": "Line became blank after transforms",
                        "excerpt": excerpt(original, excerpt_len),
                        "metrics": {},
                    }
                )
                rule_counts["drop_blank_after_transform"] += 1
            continue

        kept.append(line)

    return kept, removals, transforms, dict(rule_counts)


# ---------------------------------------------------------------------------
# Per-source cleaning
# ---------------------------------------------------------------------------


def clean_source(
    source_cfg: dict[str, Any],
    config: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    source_id = source_cfg["source_id"]
    input_path = repo_root / source_cfg["input_path"]
    if not input_path.is_file():
        raise FileNotFoundError(f"Input not found for {source_id}: {input_path}")

    raw_sha = sha256_file(input_path)
    text = read_utf8_text(input_path)
    original_lines = text.splitlines()
    # Preserve whether file ended with newline for fidelity of line count
    ended_with_newline = text.endswith("\n") if text else False

    lang_patterns = _build_lang_patterns(config)
    bp_patterns = _build_bp_patterns(config)
    before = quality_snapshot(
        original_lines, config, lang_patterns=lang_patterns, bp_patterns=bp_patterns
    )

    kept, removals, transforms, rule_counts = apply_rules(
        original_lines, source_cfg.get("rules", []), config, source_id
    )

    after = quality_snapshot(
        kept, config, lang_patterns=lang_patterns, bp_patterns=bp_patterns
    )

    # Build cleaned text: join with \n and trailing newline for POSIX text
    cleaned_body = "\n".join(kept)
    if kept:
        cleaned_body += "\n"
    cleaned_bytes = cleaned_body.encode("utf-8")
    cleaned_sha = __import__("hashlib").sha256(cleaned_bytes).hexdigest()

    return {
        "source_id": source_id,
        "input_path": source_cfg["input_path"],
        "output_subdir": source_cfg.get("output_subdir", source_id),
        "notes": source_cfg.get("notes", ""),
        "raw_sha256": raw_sha,
        "cleaned_sha256": cleaned_sha,
        "input_ended_with_newline": ended_with_newline,
        "before": before,
        "after": after,
        "removed_line_count": len(removals),
        "transform_event_count": len(transforms),
        "kept_line_count": len(kept),
        "rule_counts": rule_counts,
        "rules_configured": [
            {
                "id": r["id"],
                "type": r["type"],
                "enabled": r.get("enabled", True),
                "description": r.get("description", ""),
            }
            for r in source_cfg.get("rules", [])
        ],
        "kept_lines": kept,
        "removals": removals,
        "transforms": transforms,
        "cleaned_text": cleaned_body,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def delta(before: dict[str, Any], after: dict[str, Any], key: str) -> dict[str, Any]:
    b, a = before.get(key), after.get(key)
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        return {"before": b, "after": a, "delta": a - b}
    return {"before": b, "after": a}


def render_report(run: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append

    w("# Cleaning before/after report")
    w("")
    w(f"**Generated:** {run['generated_at']}")
    w(f"**Tool:** {run['tool']['name']} v{run['tool']['version']}")
    w(f"**Config version:** {run['config']['version']}")
    w("")
    w(
        "> **Raw files were not modified.** All outputs are under "
        f"`{run['output']['interim_root']}`."
    )
    w("")
    w(
        "> Interim cleaned text is **not** final processed training data and is "
        "**not** an approval for training. Licensing remains unresolved."
    )
    w("")

    w("## Sources cleaned")
    w("")
    for sid, src in run["sources"].items():
        w(
            f"- **{sid}**: removed {src['removed_line_count']} lines; "
            f"kept {src['kept_line_count']}; "
            f"transform events {src['transform_event_count']}"
        )
    w("")

    for sid, src in run["sources"].items():
        w(f"## {sid}")
        w("")
        w(f"- Input: `{src['input_path']}`")
        w(f"- Input SHA-256: `{src['raw_sha256']}`")
        w(f"- Cleaned SHA-256: `{src['cleaned_sha256']}`")
        w(f"- Notes: {src['notes']}")
        w("")
        w("### Rule hit counts (removals / transforms)")
        w("")
        w("| rule | count |")
        w("|------|------:|")
        if src["rule_counts"]:
            for rid, n in sorted(src["rule_counts"].items(), key=lambda kv: (-kv[1], kv[0])):
                w(f"| `{rid}` | {n} |")
        else:
            w("| _(none)_ | 0 |")
        w("")

        w("### Before → after quality")
        w("")
        b, a = src["before"], src["after"]
        keys = [
            "total_lines",
            "non_empty_lines",
            "blank_lines",
            "character_count_estimate",
            "estimated_word_token_count",
            "unique_exact_nonempty",
            "duplicate_line_percentage",
            "very_short_lines",
            "very_long_lines",
            "url_containing_lines",
            "digit_only_lines",
            "min_line_length",
            "median_line_length",
            "max_line_length",
        ]
        w("| metric | before | after | delta |")
        w("|--------|-------:|------:|------:|")
        for k in keys:
            d = delta(b, a, k)
            bv, av = d["before"], d["after"]
            if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
                w(f"| {k} | {bv} | {av} | {d['delta']} |")
            else:
                w(f"| {k} | {bv} | {av} |  |")
        w("")

        w("#### Language-signal distribution (heuristic)")
        w("")
        w("| category | before | after | before % | after % |")
        w("|----------|-------:|------:|---------:|--------:|")
        for cat in (
            "chichewa_signal",
            "english_signal",
            "german_signal",
            "mixed_signal",
            "insufficient_signal",
        ):
            bc = b["language_signals"]["counts"][cat]
            ac = a["language_signals"]["counts"][cat]
            bp = b["language_signals"]["percentages"][cat]
            ap = a["language_signals"]["percentages"][cat]
            w(f"| `{cat}` | {bc} | {ac} | {bp} | {ap} |")
        w("")

        w("#### Boilerplate matching lines")
        w("")
        w("| pattern | before | after |")
        w("|---------|-------:|------:|")
        all_bp = sorted(
            set(b["boilerplate_matching_lines"]) | set(a["boilerplate_matching_lines"])
        )
        for pid in all_bp:
            w(
                f"| `{pid}` | {b['boilerplate_matching_lines'].get(pid, 0)} | "
                f"{a['boilerplate_matching_lines'].get(pid, 0)} |"
            )
        w("")

        w("### Sample removals (first matches by rule)")
        w("")
        by_rule: dict[str, list[dict[str, Any]]] = {}
        for rec in src["removal_samples"]:
            by_rule.setdefault(rec["rule_id"], []).append(rec)
        if not by_rule:
            w("_No lines removed._")
            w("")
        else:
            for rid, recs in sorted(by_rule.items()):
                w(f"- **`{rid}`**")
                for rec in recs[:3]:
                    w(f"  - L{rec['line_number']}: `{rec['excerpt']}`")
            w("")

    w("## Raw checksum verification")
    w("")
    w("| source | pre | post | match |")
    w("|--------|-----|------|:-----:|")
    for sid, pre in run["pre_checksums"].items():
        post = run["post_checksums"][sid]
        w(f"| {sid} | `{pre}` | `{post}` | {'yes' if pre == post else 'NO'} |")
    w("")
    w(f"**raw_files_unchanged:** `{run['raw_files_unchanged']}`")
    w("")

    w("## Disclaimers")
    w("")
    for d in run.get("disclaimers", []):
        w(f"- {d}")
    w("")
    return "\n".join(lines) + "\n"


def interim_readme(run: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Interim cleaning outputs",
            "",
            "These files are **intermediate** cleaning artifacts.",
            "",
            "## Status",
            "",
            "- Generated from immutable `data/raw/` sources",
            "- **Not** final `data/processed/` training corpora",
            "- **Not** approved for training (license/eligibility unresolved)",
            "- Safe to delete and regenerate from config + raw",
            "",
            f"Tool: `{run['tool']['name']}` v{run['tool']['version']}",
            f"Generated: {run['generated_at']}",
            "",
            "Each source subdirectory contains:",
            "",
            "- `cleaned.txt` — lines kept after configured rules",
            "- `removal_log.jsonl` — one record per removed line (rule id + excerpt)",
            "- `transform_log.jsonl` — content-changing transforms on kept lines",
            "",
            "Do not edit files under `data/raw/`.",
            "",
        ]
    )


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


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


def sample_removals(
    removals: Sequence[dict[str, Any]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Deterministic samples: up to n per rule_id, stable order."""
    from audit_sources import deterministic_sample

    by_rule: dict[str, list[dict[str, Any]]] = {}
    for rec in removals:
        by_rule.setdefault(rec["rule_id"], []).append(rec)
    out: list[dict[str, Any]] = []
    for rid in sorted(by_rule):
        out.extend(
            deterministic_sample(
                by_rule[rid], n, seed, salt=f"removal:{rid}"
            )
        )
    out.sort(key=lambda r: (r["rule_id"], r["line_number"]))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Config-driven Bible/Wikipedia cleaner. "
            "Writes only under data/interim/. Never modifies data/raw/."
        )
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning.json"),
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
    )
    p.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="Optional subset of source ids (default: all enabled in config)",
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

    sources_cfg: dict[str, Any] = config.get("sources", {})
    selected = args.sources
    to_run: list[dict[str, Any]] = []
    for sid, scfg in sources_cfg.items():
        if selected is not None and sid not in selected:
            continue
        if not scfg.get("enabled", True):
            continue
        # ensure source_id field
        scfg = dict(scfg)
        scfg.setdefault("source_id", sid)
        to_run.append(scfg)

    if not to_run:
        print("error: no sources selected to clean", file=sys.stderr)
        return 1

    # Pre-checksums for all inputs we will read
    pre_checksums: dict[str, str] = {}
    try:
        for scfg in to_run:
            path = repo_root / scfg["input_path"]
            pre_checksums[scfg["source_id"]] = sha256_file(path)
    except OSError as e:
        print(f"error: cannot checksum input: {e}", file=sys.stderr)
        return 1

    results: dict[str, Any] = {}
    try:
        for scfg in to_run:
            results[scfg["source_id"]] = clean_source(scfg, config, repo_root)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    # Post-checksums
    post_checksums: dict[str, str] = {}
    for scfg in to_run:
        path = repo_root / scfg["input_path"]
        post_checksums[scfg["source_id"]] = sha256_file(path)

    mismatches = [
        sid for sid in pre_checksums if pre_checksums[sid] != post_checksums[sid]
    ]
    if mismatches:
        print(
            f"error: raw input files changed during cleaning: {mismatches}",
            file=sys.stderr,
        )
        return 2

    out_cfg = config.get("output", {})
    interim_root = repo_root / out_cfg.get(
        "interim_root", "data/interim/cleaning"
    )
    cleaned_name = out_cfg.get("cleaned_filename", "cleaned.txt")
    removal_name = out_cfg.get("removal_log_filename", "removal_log.jsonl")
    transform_name = out_cfg.get("transform_log_filename", "transform_log.jsonl")
    summary_name = out_cfg.get("summary_filename", "summary.json")
    report_name = out_cfg.get("report_filename", "before_after_report.md")
    readme_name = out_cfg.get("readme_filename", "README.md")

    seed = int(config.get("random_seed", 42))
    sample_n = int(config.get("sample_count", 5))

    # Write per-source artifacts
    public_sources: dict[str, Any] = {}
    for sid, res in results.items():
        sub = interim_root / res["output_subdir"]
        write_text(sub / cleaned_name, res["cleaned_text"])
        write_jsonl(sub / removal_name, res["removals"])
        write_jsonl(sub / transform_name, res["transforms"])

        removal_samples = sample_removals(res["removals"], sample_n, seed)
        public_sources[sid] = {
            "source_id": sid,
            "input_path": res["input_path"],
            "output_dir": str(sub.relative_to(repo_root)),
            "cleaned_path": str((sub / cleaned_name).relative_to(repo_root)),
            "removal_log_path": str((sub / removal_name).relative_to(repo_root)),
            "transform_log_path": str((sub / transform_name).relative_to(repo_root)),
            "notes": res["notes"],
            "raw_sha256": res["raw_sha256"],
            "cleaned_sha256": res["cleaned_sha256"],
            "before": res["before"],
            "after": res["after"],
            "removed_line_count": res["removed_line_count"],
            "transform_event_count": res["transform_event_count"],
            "kept_line_count": res["kept_line_count"],
            "rule_counts": res["rule_counts"],
            "rules_configured": res["rules_configured"],
            "removal_samples": removal_samples,
        }

    run: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "config": {
            "version": config.get("version"),
            "path": str(
                config_path.relative_to(repo_root)
                if config_path.is_relative_to(repo_root)
                else config_path
            ),
            "random_seed": seed,
        },
        "output": {
            "interim_root": str(interim_root.relative_to(repo_root)),
        },
        "pre_checksums": pre_checksums,
        "post_checksums": post_checksums,
        "raw_files_unchanged": True,
        "sources": public_sources,
        "disclaimers": config.get("disclaimers", []),
        "warnings": [
            "Language-signal filters are heuristics, not language identification.",
            "Interim outputs must not be treated as licensed training data.",
            "existing_corpus is intentionally not cleaned here (redundant composite).",
        ],
    }

    report_md = render_report(run)
    write_json(interim_root / summary_name, run)
    write_text(interim_root / report_name, report_md)
    write_text(interim_root / readme_name, interim_readme(run))

    print(
        f"Cleaning complete → {interim_root} "
        f"(raw_files_unchanged={run['raw_files_unchanged']})"
    )
    for sid, src in public_sources.items():
        print(
            f"  {sid}: kept={src['kept_line_count']} "
            f"removed={src['removed_line_count']} "
            f"→ {src['cleaned_path']}"
        )
    print(f"  summary: {interim_root / summary_name}")
    print(f"  report:  {interim_root / report_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
