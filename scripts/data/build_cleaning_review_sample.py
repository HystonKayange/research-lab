#!/usr/bin/env python3
"""Build a deterministic human-review sample for Wikipedia cleaning.

Reads raw Wikipedia text, interim cleaned text, and removal logs. Writes a
JSONL review sample and annotation instructions. Does not modify raw files,
interim cleaned corpora, or cleaning configuration.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import (  # noqa: E402
    deterministic_sample,
    excerpt,
    load_json,
    read_utf8_text,
    utc_now_iso,
)
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "build_cleaning_review_sample"
TOOL_VERSION = "1.0.0"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_review_id(
    source_id: str,
    decision: str,
    rule_id: str | None,
    line_number: int,
    text_hash: str,
) -> str:
    """Stable review_id from immutable fields (not dependent on sample order)."""
    payload = f"{source_id}|{decision}|{rule_id or ''}|{line_number}|{text_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_removal_log(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL in {path} at line {i}: {e}") from e
        records.append(rec)
    return records


def build_removed_samples(
    removals: Sequence[dict[str, Any]],
    raw_lines: Sequence[str],
    rule_quotas: dict[str, int],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sample removed lines by rule with deterministic selection."""
    source_id = config["source_id"]
    seed = int(config["random_seed"])
    excerpt_len = int(config["excerpt_length"])

    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in removals:
        by_rule[rec["rule_id"]].append(rec)

    # Stable order within each rule by line_number
    for rid in by_rule:
        by_rule[rid].sort(key=lambda r: r["line_number"])

    samples: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "population_by_rule": {rid: len(items) for rid, items in sorted(by_rule.items())},
        "requested_by_rule": {},
        "sampled_by_rule": {},
        "missing_rules": [],
    }

    for rule_id, n_req in rule_quotas.items():
        stats["requested_by_rule"][rule_id] = n_req
        pool = by_rule.get(rule_id, [])
        if not pool:
            stats["sampled_by_rule"][rule_id] = 0
            stats["missing_rules"].append(rule_id)
            continue
        picked = deterministic_sample(
            pool, n_req, seed, salt=f"removed:{rule_id}"
        )
        stats["sampled_by_rule"][rule_id] = len(picked)
        for rec in picked:
            ln = int(rec["line_number"])
            if ln < 1 or ln > len(raw_lines):
                raise ValueError(
                    f"Removal log line_number {ln} out of range for raw "
                    f"(1..{len(raw_lines)}) rule={rule_id}"
                )
            full_text = raw_lines[ln - 1]
            th = text_sha256(full_text)
            samples.append(
                {
                    "review_id": make_review_id(
                        source_id, "removed", rule_id, ln, th
                    ),
                    "source_id": source_id,
                    "original_line_number": ln,
                    "decision": "removed",
                    "rule_id": rule_id,
                    "rule_type": rec.get("rule_type"),
                    "rule_description": rec.get("rule_description"),
                    "excerpt": excerpt(full_text, excerpt_len),
                    "text_sha256": th,
                    "metrics": rec.get("metrics", {}),
                    "review_label": None,
                    "review_notes": None,
                }
            )

    samples.sort(
        key=lambda r: (r["rule_id"] or "", r["original_line_number"], r["review_id"])
    )
    return samples, stats


def build_kept_samples(
    raw_lines: Sequence[str],
    removed_line_numbers: set[int],
    cleaned_lines: Sequence[str],
    n_kept: int,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sample kept original lines (present in raw, not in removal log)."""
    source_id = config["source_id"]
    seed = int(config["random_seed"])
    excerpt_len = int(config["excerpt_length"])

    kept_candidates: list[tuple[int, str]] = []
    for i, text in enumerate(raw_lines, start=1):
        if i in removed_line_numbers:
            continue
        # Skip blank originals that somehow weren't logged (should be rare)
        if not text.strip():
            continue
        kept_candidates.append((i, text))

    # Optional integrity: cleaned multiset should match kept non-blank texts
    # after cleaning transforms (strip). We only require counts as a soft check
    # in stats; do not fail hard on transform differences.
    cleaned_nonempty = [ln for ln in cleaned_lines if ln.strip()]

    picked = deterministic_sample(
        kept_candidates, n_kept, seed, salt="kept:wikipedia"
    )
    samples: list[dict[str, Any]] = []
    for ln, text in picked:
        th = text_sha256(text)
        samples.append(
            {
                "review_id": make_review_id(
                    source_id, "kept", None, ln, th
                ),
                "source_id": source_id,
                "original_line_number": ln,
                "decision": "kept",
                "rule_id": None,
                "rule_type": None,
                "rule_description": None,
                "excerpt": excerpt(text, excerpt_len),
                "text_sha256": th,
                "metrics": {"length": len(text)},
                "review_label": None,
                "review_notes": None,
            }
        )
    samples.sort(key=lambda r: (r["original_line_number"], r["review_id"]))

    stats = {
        "kept_population_nonblank": len(kept_candidates),
        "cleaned_nonempty_lines": len(cleaned_nonempty),
        "requested": n_kept,
        "sampled": len(samples),
    }
    return samples, stats


def merge_rule_quotas(config: dict[str, Any]) -> dict[str, int]:
    quotas: dict[str, int] = {}
    for section in ("priority_rule_samples", "other_rule_samples"):
        for rid, n in config.get(section, {}).items():
            quotas[rid] = int(n)
    return quotas


def render_instructions(
    config: dict[str, Any],
    sample_stats: dict[str, Any],
    total_records: int,
) -> str:
    labels = config["allowed_labels"]
    lines: list[str] = []
    w = lines.append

    w("# Cleaning review — annotation instructions")
    w("")
    w(f"**Source:** `{config['source_id']}`  ")
    w(f"**Sample file:** `{config['paths']['sample_output']}`  ")
    w(f"**Total review records:** {total_records}  ")
    w(f"**Random seed:** {config['random_seed']}  ")
    w("")
    w("## Goal")
    w("")
    w(
        "Measure **false removals** and **remaining noise** in the Wikipedia "
        "interim cleaning output before any promotion to `data/processed/`."
    )
    w("")
    w("## What you will label")
    w("")
    w("Each record in the JSONL sample has:")
    w("")
    w("- `review_id` — stable id (do not change)")
    w("- `decision` — `removed` or `kept`")
    w("- `rule_id` — cleaning rule for removals (`null` for kept)")
    w("- `original_line_number` — line number in raw Wikipedia file")
    w("- `excerpt` — truncated text for review")
    w("- `text_sha256` — hash of the **full original line** from raw")
    w("- `review_label` — **you fill this**")
    w("- `review_notes` — optional free text")
    w("")
    w("## Allowed labels")
    w("")
    for lab in labels:
        w(f"- `{lab}`")
    w("")
    w("### Label guide")
    w("")
    w("| Label | Use when |")
    w("|-------|----------|")
    w("| `valid_chichewa` | Fluent / usable Chichewa content worth training on |")
    w("| `useful_mixed_chichewa` | Mostly Chichewa with minor foreign/noise but still useful |")
    w("| `boilerplate_or_noise` | Nav, chrome, categories, stubs, garbage |")
    w("| `foreign_language` | Predominantly non-Chichewa (EN/DE/other) |")
    w("| `duplicate` | Clear duplicate / non-informative repeat |")
    w("| `uncertain` | Cannot decide confidently |")
    w("")
    w("## How labels map to metrics")
    w("")
    w("### Removed samples")
    w("")
    w("- **False removal:** `valid_chichewa` or `useful_mixed_chichewa`")
    w("- **Correct removal:** `boilerplate_or_noise`, `foreign_language`, or `duplicate`")
    w("- **`uncertain`:** counted separately; excluded from precision by default")
    w("")
    w("### Kept samples")
    w("")
    w("- **Useful text:** `valid_chichewa` or `useful_mixed_chichewa`")
    w("- **Noise:** `boilerplate_or_noise` or `duplicate`")
    w("- **Foreign leakage:** `foreign_language`")
    w("- **Boilerplate leakage:** `boilerplate_or_noise`")
    w("")
    w("## Annotation procedure")
    w("")
    w("1. Open `data/reports/cleaning_review_sample.jsonl`.")
    w("2. For each record, set `review_label` to exactly one allowed label.")
    w("3. Optionally set `review_notes` (short).")
    w("4. Do **not** change `review_id`, hashes, line numbers, or rule ids.")
    w("5. Save the file (or a copy) and run:")
    w("")
    w("```bash")
    w("python scripts/data/summarize_cleaning_review.py \\")
    w("  --config configs/data/cleaning_review.json \\")
    w("  --sample data/reports/cleaning_review_sample.jsonl")
    w("```")
    w("")
    w("## Sample composition (this build)")
    w("")
    w("### Removed — by rule")
    w("")
    w("| rule_id | population | requested | sampled |")
    w("|---------|----------:|----------:|--------:|")
    rem = sample_stats["removed"]
    for rid in sorted(
        set(rem["requested_by_rule"]) | set(rem["sampled_by_rule"])
    ):
        pop = rem["population_by_rule"].get(rid, 0)
        req = rem["requested_by_rule"].get(rid, 0)
        got = rem["sampled_by_rule"].get(rid, 0)
        w(f"| `{rid}` | {pop} | {req} | {got} |")
    w("")
    w(
        f"**Removed total sampled:** {sample_stats['removed_total']}  "
    )
    w(
        f"**Kept total sampled:** {sample_stats['kept']['sampled']} "
        f"(population non-blank kept ≈ {sample_stats['kept']['kept_population_nonblank']})"
    )
    w("")
    w("## Priority rules (higher scrutiny)")
    w("")
    for rid, n in config.get("priority_rule_samples", {}).items():
        w(f"- `{rid}` — target n={n}")
    w("")
    w("## Do not")
    w("")
    w("- Modify `data/raw/` or interim cleaned corpora while annotating")
    w("- Change `configs/data/cleaning.json` based on partial impressions alone")
    w("- Promote to `data/processed/` until validation metrics are reviewed")
    w("- Train tokenizers/models on interim data under review")
    w("")
    return "\n".join(lines) + "\n"


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
        description="Build deterministic Wikipedia cleaning review sample."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_review.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
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

    paths = config["paths"]
    raw_path = repo_root / paths["raw"]
    cleaned_path = repo_root / paths["cleaned"]
    log_path = repo_root / paths["removal_log"]

    for p, label in (
        (raw_path, "raw"),
        (cleaned_path, "cleaned"),
        (log_path, "removal_log"),
    ):
        if not p.is_file():
            print(f"error: missing {label} file: {p}", file=sys.stderr)
            return 1

    # Integrity checksums (read-only; not written back to sources)
    try:
        raw_sha = sha256_file(raw_path)
        cleaned_sha = sha256_file(cleaned_path)
        log_sha = sha256_file(log_path)
    except OSError as e:
        print(f"error: checksum failed: {e}", file=sys.stderr)
        return 1

    try:
        raw_lines = read_utf8_text(raw_path).splitlines()
        cleaned_lines = read_utf8_text(cleaned_path).splitlines()
        removals = load_removal_log(log_path)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    quotas = merge_rule_quotas(config)
    removed_samples, removed_stats = build_removed_samples(
        removals, raw_lines, quotas, config
    )
    removed_line_numbers = {int(r["line_number"]) for r in removals}
    kept_samples, kept_stats = build_kept_samples(
        raw_lines,
        removed_line_numbers,
        cleaned_lines,
        int(config.get("kept_sample_size", 80)),
        config,
    )

    all_samples = removed_samples + kept_samples
    # Stable global order: removed first by rule, then kept
    all_samples.sort(
        key=lambda r: (
            0 if r["decision"] == "removed" else 1,
            r.get("rule_id") or "",
            r["original_line_number"],
            r["review_id"],
        )
    )

    # Deduplicate review_ids (should be unique)
    ids = [r["review_id"] for r in all_samples]
    if len(ids) != len(set(ids)):
        print("error: duplicate review_id generated", file=sys.stderr)
        return 1

    sample_stats = {
        "removed": removed_stats,
        "removed_total": len(removed_samples),
        "kept": kept_stats,
        "total": len(all_samples),
    }

    sample_out = repo_root / paths["sample_output"]
    instr_out = repo_root / paths["instructions_output"]

    try:
        write_jsonl(sample_out, all_samples)
        write_text(
            instr_out,
            render_instructions(config, sample_stats, len(all_samples)),
        )
    except OSError as e:
        print(f"error: write failed: {e}", file=sys.stderr)
        return 1

    # Manifest sidecar next to sample (optional metadata in report dir)
    manifest = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "config_version": config.get("version"),
        "input_checksums": {
            "raw": raw_sha,
            "cleaned": cleaned_sha,
            "removal_log": log_sha,
        },
        "sample_stats": sample_stats,
        "sample_path": paths["sample_output"],
        "instructions_path": paths["instructions_output"],
        "annotation_status": "pending_human_labels",
        "note": (
            "review_label fields are null until human annotation. "
            "Run summarize_cleaning_review.py after labeling."
        ),
    }
    manifest_path = sample_out.with_suffix(".manifest.json")
    try:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        print(f"error: manifest write failed: {e}", file=sys.stderr)
        return 1

    print(
        f"Review sample written: {len(all_samples)} records "
        f"(removed={len(removed_samples)}, kept={len(kept_samples)})"
    )
    print(f"  sample:       {sample_out}")
    print(f"  instructions: {instr_out}")
    print(f"  manifest:     {manifest_path}")
    for rid, n in sorted(removed_stats["sampled_by_rule"].items(), key=lambda kv: -kv[1]):
        if n:
            print(f"  removed[{rid}]={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
