#!/usr/bin/env python3
"""Build a blind holdout sample for Cleaning Policy v2 evaluation.

Excludes every record from the development review set (original ~367 labels).
Stratified deterministic sampling over v2 removed/kept strata.

Does not modify cleaning_v2, raw data, interim cleaned outputs, or development labels.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import (  # noqa: E402
    build_term_pattern,
    classify_language_signal,
    deterministic_sample,
    excerpt,
    load_json,
    read_utf8_text,
    utc_now_iso,
)
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "build_cleaning_holdout_sample"
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
    payload = (
        f"holdout|{source_id}|{decision}|{rule_id or ''}|{line_number}|{text_hash}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL {path}:{i}: {e}") from e
    return out


def development_exclusion_sets(
    dev_records: Sequence[dict[str, Any]],
) -> tuple[set[str], set[int], set[str], set[str]]:
    """Return (hashes, line_numbers, review_ids, line_hash_keys)."""
    hashes: set[str] = set()
    lines: set[int] = set()
    ids: set[str] = set()
    line_hash: set[str] = set()
    for r in dev_records:
        h = r.get("text_sha256") or text_sha256(r.get("excerpt", ""))
        ln = int(r["original_line_number"])
        hashes.add(h)
        lines.add(ln)
        ids.add(str(r["review_id"]))
        line_hash.add(f"{ln}:{h}")
    return hashes, lines, ids, line_hash


def is_excluded(
    line_number: int,
    text: str,
    *,
    dev_hashes: set[str],
    dev_lines: set[int],
    dev_line_hash: set[str],
) -> bool:
    h = text_sha256(text)
    if h in dev_hashes:
        return True
    if line_number in dev_lines:
        return True
    if f"{line_number}:{h}" in dev_line_hash:
        return True
    return False


def sample_stratum(
    pool: list[dict[str, Any]],
    n: int,
    seed: int,
    salt: str,
) -> list[dict[str, Any]]:
    if n <= 0 or not pool:
        return []
    # stable sort then deterministic sample
    pool_sorted = sorted(
        pool,
        key=lambda r: (r["original_line_number"], r["text_sha256"]),
    )
    return deterministic_sample(pool_sorted, n, seed, salt=salt)


def build_candidate_record(
    *,
    source_id: str,
    line_number: int,
    text: str,
    decision: str,
    rule_id: str | None,
    excerpt_len: int,
    strata: list[str],
) -> dict[str, Any]:
    th = text_sha256(text)
    return {
        "review_id": make_review_id(source_id, decision, rule_id, line_number, th),
        "source_id": source_id,
        "original_line_number": line_number,
        "v2_decision": decision,
        "v2_rule_id": rule_id,
        "excerpt": excerpt(text, excerpt_len),
        "text_sha256": th,
        "review_label": None,
        "review_notes": None,
        "holdout_strata": strata,
        "dataset_role": "blind_holdout",
    }


def classify_kept_strata(
    text: str,
    line_number: int,
    *,
    config: dict[str, Any],
    ny_pat: re.Pattern[str],
    en_pat: re.Pattern[str],
    de_pat: re.Pattern[str],
    url_stripped_lines: set[int],
) -> list[str]:
    """Assign a kept line to one or more strata (first is primary)."""
    min_m = int(config.get("language_signal", {}).get("min_matches_for_signal", 2))
    cat, _hits = classify_language_signal(text, ny_pat, en_pat, de_pat, min_m)
    short_th = int(config.get("short_line_threshold", 20))
    long_th = int(config.get("long_line_threshold", 500))
    ns, xs = int(config["near_threshold_short_min"]), int(config["near_threshold_short_max"])
    nl, xl = int(config["near_threshold_long_min"]), int(config["near_threshold_long_max"])
    length = len(text)

    strata: list[str] = []
    if cat == "chichewa_signal":
        strata.append("chichewa_signal")
    elif cat == "mixed_signal":
        strata.append("mixed_signal")
    elif cat == "insufficient_signal":
        strata.append("insufficient_signal")
    else:
        # english/german signal kept lines → bucket as mixed/ambiguous for sampling
        strata.append("mixed_signal")

    if length < short_th and text.strip():
        strata.append("short_retained")
    if length > long_th:
        strata.append("long_retained")
    if line_number in url_stripped_lines:
        strata.append("url_stripped_retained")
    if any(
        re.search(re.escape(p), text)
        for p in config.get("institution_name_patterns", [])
    ):
        strata.append("english_names_institutions")
    if ns <= length <= xs or nl <= length <= xl:
        strata.append("near_threshold")

    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in strata:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out or ["insufficient_signal"]


def fill_quotas(
    pools: dict[str, list[dict[str, Any]]],
    quotas: dict[str, int],
    seed: int,
    salt_prefix: str,
    *,
    used_hashes: set[str],
    used_lines: set[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sample without replacement across strata; spill shortfalls to largest pools."""
    selected: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "requested": dict(quotas),
        "sampled": {},
        "pool_sizes": {k: len(v) for k, v in pools.items()},
        "shortfalls": {},
    }

    def take(stratum: str, n: int) -> list[dict[str, Any]]:
        pool = [
            r
            for r in pools.get(stratum, [])
            if r["text_sha256"] not in used_hashes
            and r["original_line_number"] not in used_lines
        ]
        picked = sample_stratum(pool, n, seed, f"{salt_prefix}:{stratum}")
        for r in picked:
            used_hashes.add(r["text_sha256"])
            used_lines.add(r["original_line_number"])
        return picked

    for stratum, n_req in quotas.items():
        picked = take(stratum, n_req)
        stats["sampled"][stratum] = len(picked)
        if len(picked) < n_req:
            stats["shortfalls"][stratum] = n_req - len(picked)
        selected.extend(picked)

    # Backfill shortfall from largest remaining pools
    shortfall = sum(stats["shortfalls"].values())
    if shortfall > 0:
        remaining_pools = sorted(
            pools.keys(),
            key=lambda k: -len(
                [
                    r
                    for r in pools[k]
                    if r["text_sha256"] not in used_hashes
                    and r["original_line_number"] not in used_lines
                ]
            ),
        )
        for stratum in remaining_pools:
            if shortfall <= 0:
                break
            extra = take(stratum, shortfall)
            selected.extend(extra)
            stats["sampled"][stratum] = stats["sampled"].get(stratum, 0) + len(extra)
            shortfall -= len(extra)
        stats["backfill_remaining_shortfall"] = max(0, shortfall)

    return selected, stats


def build_holdout(
    config: dict[str, Any],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = config["paths"]
    raw_path = repo_root / paths["raw"]
    rem_path = repo_root / paths["removal_log"]
    tr_path = repo_root / paths["transform_log"]
    dev_path = repo_root / config["development_set_path"]

    raw_lines = read_utf8_text(raw_path).splitlines()
    removals = load_jsonl(rem_path)
    transforms = load_jsonl(tr_path)
    dev = load_jsonl(dev_path)
    dev_hashes, dev_lines, dev_ids, dev_line_hash = development_exclusion_sets(dev)

    source_id = config["source_id"]
    excerpt_len = int(config["excerpt_length"])
    seed = int(config["random_seed"])

    # URL-stripped line numbers that survived (transform strip_urls, not in removals)
    removed_set = {int(r["line_number"]) for r in removals}
    url_stripped = {
        int(t["line_number"])
        for t in transforms
        if t.get("rule_id") == "strip_urls"
        and int(t["line_number"]) not in removed_set
    }

    ny = build_term_pattern(config.get("chichewa_signal_terms", []))
    en = build_term_pattern(config.get("english_signal_terms", []))
    de = build_term_pattern(config.get("german_signal_terms", []))

    # --- removed pools by rule / alias ---
    aliases = config.get("removed_rule_aliases", {})
    rule_to_stratum: dict[str, str] = {}
    for stratum, rules in aliases.items():
        for rid in rules:
            rule_to_stratum[rid] = stratum

    removed_pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_removed = 0
    for rec in removals:
        ln = int(rec["line_number"])
        if ln < 1 or ln > len(raw_lines):
            continue
        text = raw_lines[ln - 1]
        if is_excluded(
            ln, text, dev_hashes=dev_hashes, dev_lines=dev_lines, dev_line_hash=dev_line_hash
        ):
            excluded_removed += 1
            continue
        rid = rec.get("rule_id") or "unknown"
        stratum = rule_to_stratum.get(rid, rid)
        candidate = build_candidate_record(
            source_id=source_id,
            line_number=ln,
            text=text,
            decision="removed",
            rule_id=rid,
            excerpt_len=excerpt_len,
            strata=[stratum],
        )
        removed_pools[stratum].append(candidate)

    # --- kept pools ---
    kept_pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_kept = 0
    for i, text in enumerate(raw_lines, start=1):
        if i in removed_set:
            continue
        if not text.strip():
            continue
        if is_excluded(
            i, text, dev_hashes=dev_hashes, dev_lines=dev_lines, dev_line_hash=dev_line_hash
        ):
            excluded_kept += 1
            continue
        strata = classify_kept_strata(
            text,
            i,
            config=config,
            ny_pat=ny,
            en_pat=en,
            de_pat=de,
            url_stripped_lines=url_stripped,
        )
        # place in each matching pool (for multi-stratum sampling)
        for s in strata:
            cand = build_candidate_record(
                source_id=source_id,
                line_number=i,
                text=text,
                decision="kept",
                rule_id=None,
                excerpt_len=excerpt_len,
                strata=strata,
            )
            kept_pools[s].append(cand)

    used_hashes: set[str] = set()
    used_lines: set[int] = set()

    removed_selected, removed_stats = fill_quotas(
        removed_pools,
        {k: int(v) for k, v in config["removed_strata_quotas"].items()},
        seed,
        "holdout_removed",
        used_hashes=used_hashes,
        used_lines=used_lines,
    )
    kept_selected, kept_stats = fill_quotas(
        kept_pools,
        {k: int(v) for k, v in config["kept_strata_quotas"].items()},
        seed,
        "holdout_kept",
        used_hashes=used_hashes,
        used_lines=used_lines,
    )

    # Deduplicate records by review_id (multi-stratum kept may duplicate before fill
    # but fill_quotas uses used sets — still collapse)
    by_id: dict[str, dict[str, Any]] = {}
    for r in removed_selected + kept_selected:
        by_id[r["review_id"]] = r
    records = list(by_id.values())
    records.sort(
        key=lambda r: (
            0 if r["v2_decision"] == "removed" else 1,
            r.get("v2_rule_id") or "",
            r["original_line_number"],
            r["review_id"],
        )
    )

    # Final overlap check
    holdout_hashes = {r["text_sha256"] for r in records}
    holdout_lines = {r["original_line_number"] for r in records}
    holdout_ids = {r["review_id"] for r in records}
    overlap = {
        "hash_overlap": len(holdout_hashes & dev_hashes),
        "line_overlap": len(holdout_lines & dev_lines),
        "review_id_overlap": len(holdout_ids & dev_ids),
    }
    if any(overlap.values()):
        raise RuntimeError(f"Holdout overlaps development set: {overlap}")

    manifest = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "config_version": config.get("version"),
        "dataset_role": "blind_holdout",
        "development_set": {
            "path": config["development_set_path"],
            "role": config.get("development_set_role", "development_validation"),
            "n_records": len(dev),
            "n_unique_hashes": len(dev_hashes),
        },
        "targets": config.get("targets"),
        "counts": {
            "total": len(records),
            "removed": sum(1 for r in records if r["v2_decision"] == "removed"),
            "kept": sum(1 for r in records if r["v2_decision"] == "kept"),
            "by_v2_rule": dict(
                Counter(r.get("v2_rule_id") or "kept" for r in records)
            ),
            "by_primary_stratum": dict(
                Counter((r.get("holdout_strata") or ["unknown"])[0] for r in records)
            ),
        },
        "removed_sampling": removed_stats,
        "kept_sampling": kept_stats,
        "exclusion": {
            "excluded_removed_candidates": excluded_removed,
            "excluded_kept_candidates": excluded_kept,
            "overlap_with_development": overlap,
        },
        "annotation_status": "pending_human_labels",
        "note": (
            "Original 367-record set is the development validation set only. "
            "This holdout is unlabeled and must be labeled before generalization claims."
        ),
    }
    return records, manifest


def render_instructions(
    config: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    lines: list[str] = []
    w = lines.append
    w("# Cleaning holdout — annotation instructions")
    w("")
    w("## Experimental role of this set")
    w("")
    w(
        "This is a **blind holdout** sample for Cleaning Policy **v2**. "
        "It was drawn **after** v2 was designed using the original 367-record review."
    )
    w("")
    w("| Dataset | Path | Role |")
    w("|---------|------|------|")
    w(
        f"| Development review (367) | `{config['development_set_path']}` | "
        f"**development validation only** — used to diagnose v1 and design v2 |"
    )
    w(
        f"| Blind holdout (~{manifest['counts']['total']}) | "
        f"`{config['paths']['sample_output']}` | "
        f"**independent generalization estimate** — do not tune v2 on these before labeling |"
    )
    w("| Final test set | *(not yet created)* | Future locked evaluation |")
    w("")
    w(
        "Evaluating and tuning on the **same** examples overestimates performance. "
        "The development set already informed v2 rule choices; only the holdout "
        "estimates how v2 behaves on unseen lines."
    )
    w("")
    w("## Goal")
    w("")
    w(
        "Label each record so we can compute removal precision, false-removal rate, "
        "useful-text retention, and leakage metrics for v2 on **unseen** data."
    )
    w("")
    w("## Labels")
    w("")
    for lab in config["allowed_labels"]:
        w(f"- `{lab}`")
    w("")
    w("| Label | Meaning |")
    w("|-------|---------|")
    w("| `valid_chichewa` | Usable Chichewa |")
    w("| `useful_mixed_chichewa` | Mostly Chichewa; minor foreign OK |")
    w("| `boilerplate_or_noise` | Nav, category, tables, junk |")
    w("| `foreign_language` | Mostly non-Chichewa |")
    w("| `duplicate` | Non-informative duplicate |")
    w("| `uncertain` | Cannot decide |")
    w("")
    w("### For `v2_decision=removed`")
    w("")
    w("- **keep-worthy content** (valid/useful) → label `valid_chichewa` or `useful_mixed_chichewa` (**false removal**)")
    w("- **noise/foreign** → `boilerplate_or_noise` / `foreign_language` / `duplicate` (**correct removal**)")
    w("")
    w("### For `v2_decision=kept`")
    w("")
    w("- Good text → `valid_chichewa` / `useful_mixed_chichewa`")
    w("- Noise that leaked through → `boilerplate_or_noise` / `foreign_language`")
    w("")
    w("## Sample composition")
    w("")
    c = manifest["counts"]
    w(f"- Total: **{c['total']}**")
    w(f"- v2 removed: **{c['removed']}**")
    w(f"- v2 kept: **{c['kept']}**")
    w("")
    w("By v2 rule / kept:")
    w("")
    for k, n in sorted(c["by_v2_rule"].items(), key=lambda kv: -kv[1]):
        w(f"- `{k}`: {n}")
    w("")
    w("## How to annotate")
    w("")
    w("1. Open `data/reports/cleaning_holdout_sample.jsonl`.")
    w("2. Set only `review_label` (and optional `review_notes`).")
    w("3. Do not change immutable fields.")
    w("4. Optionally use a review UI if extended for this path.")
    w("5. After full labeling:")
    w("")
    w("```bash")
    w("python3 scripts/data/summarize_cleaning_holdout.py \\")
    w("  --config configs/data/cleaning_holdout.json \\")
    w("  --sample data/reports/cleaning_holdout_sample.jsonl")
    w("```")
    w("")
    w("## Do not")
    w("")
    w("- Modify `configs/data/cleaning_v2.json` based on holdout impressions **before** labeling is complete")
    w("- Merge holdout into the development set")
    w("- Promote to `data/processed/` from this step alone")
    w("- Auto-label with an LLM as ground truth")
    w("")
    return "\n".join(lines) + "\n"


def write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            # public fields for annotators: strip internal multi-stratum only keep list
            out = {
                "review_id": rec["review_id"],
                "source_id": rec["source_id"],
                "original_line_number": rec["original_line_number"],
                "v2_decision": rec["v2_decision"],
                "v2_rule_id": rec["v2_rule_id"],
                "excerpt": rec["excerpt"],
                "text_sha256": rec["text_sha256"],
                "review_label": rec["review_label"],
                "review_notes": rec["review_notes"],
                "holdout_strata": rec.get("holdout_strata"),
                "dataset_role": rec.get("dataset_role", "blind_holdout"),
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build blind holdout sample for cleaning v2 (excludes development set)."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_holdout.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        config = load_json(config_path)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    paths = config["paths"]
    # checksum inputs
    try:
        raw_sha = sha256_file(root / paths["raw"])
        cfg_sha = sha256_file(root / paths["cleaning_config"])
        dev_sha = sha256_file(root / config["development_set_path"])
    except OSError as e:
        print(f"error: checksum failed: {e}", file=sys.stderr)
        return 1

    try:
        records, manifest = build_holdout(config, root)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    manifest["input_checksums"] = {
        "raw_wikipedia": raw_sha,
        "cleaning_v2_config": cfg_sha,
        "development_review_sample": dev_sha,
    }
    manifest["sample_path"] = paths["sample_output"]
    manifest["instructions_path"] = paths["instructions_output"]

    sample_out = root / paths["sample_output"]
    instr_out = root / paths["instructions_output"]
    man_out = root / paths["manifest_output"]

    # Atomic write sample
    sample_out.parent.mkdir(parents=True, exist_ok=True)
    tmp = sample_out.with_suffix(".jsonl.tmp")
    write_jsonl(tmp, records)
    # verify no overlap after write
    written = load_jsonl(tmp)
    if len(written) != len(records):
        print("error: write count mismatch", file=sys.stderr)
        return 1
    tmp.replace(sample_out)

    write_json(man_out, manifest)
    instr_out.write_text(render_instructions(config, manifest), encoding="utf-8")

    # Pending validation stubs
    val_json = root / paths["validation_json"]
    val_md = root / paths["validation_report"]
    pending = {
        "generated_at": utc_now_iso(),
        "annotation_status": "pending_human_labels",
        "dataset_role": "blind_holdout",
        "development_set_role": "development_validation",
        "n_records": len(records),
        "n_labeled": 0,
        "n_unlabeled": len(records),
        "note": "Run summarize_cleaning_holdout.py after human labeling.",
        "sample_path": paths["sample_output"],
        "manifest_path": paths["manifest_output"],
    }
    write_json(val_json, pending)
    val_md.parent.mkdir(parents=True, exist_ok=True)
    val_md.write_text(
        "# Cleaning holdout validation report\n\n"
        f"**Status:** `pending_human_labels`  \n"
        f"**Records:** {len(records)}  \n\n"
        "This set is a **blind holdout**. The original 367-record review is the "
        "**development validation set** only.\n\n"
        "Label `data/reports/cleaning_holdout_sample.jsonl`, then run:\n\n"
        "```bash\n"
        "python3 scripts/data/summarize_cleaning_holdout.py \\\n"
        "  --config configs/data/cleaning_holdout.json \\\n"
        "  --sample data/reports/cleaning_holdout_sample.jsonl\n"
        "```\n",
        encoding="utf-8",
    )

    # Post checksums
    post_raw = sha256_file(root / paths["raw"])
    post_cfg = sha256_file(root / paths["cleaning_config"])
    post_dev = sha256_file(root / config["development_set_path"])
    if (post_raw, post_cfg, post_dev) != (raw_sha, cfg_sha, dev_sha):
        print("error: input files changed during holdout build", file=sys.stderr)
        return 2

    c = manifest["counts"]
    print(
        f"Holdout sample: total={c['total']} removed={c['removed']} kept={c['kept']} "
        f"overlap={manifest['exclusion']['overlap_with_development']}"
    )
    print(f"  sample:       {sample_out}")
    print(f"  instructions: {instr_out}")
    print(f"  manifest:     {man_out}")
    for rid, n in sorted(c["by_v2_rule"].items(), key=lambda kv: -kv[1]):
        print(f"  {rid}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
