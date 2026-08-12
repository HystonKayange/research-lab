#!/usr/bin/env python3
"""Split the 250-record blind holdout into stage-1 (80) + locked extension pool (170).

Risk-stratified sequential evaluation. Does not modify cleaning_v2 or parent holdout
records' identity fields. Parent holdout file is left intact.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import deterministic_sample, load_json, utc_now_iso  # noqa: E402
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "build_cleaning_holdout_stages"
TOOL_VERSION = "1.0.0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def primary_stratum(rec: dict[str, Any]) -> str:
    strata = rec.get("holdout_strata") or []
    if strata:
        return str(strata[0])
    if rec.get("v2_decision") == "removed":
        return str(rec.get("v2_rule_id") or "removed_unknown")
    return "kept_unknown"


def sample_quota(
    pool: list[dict[str, Any]],
    n: int,
    seed: int,
    salt: str,
    used: set[str],
) -> list[dict[str, Any]]:
    avail = [
        r
        for r in pool
        if r["review_id"] not in used
    ]
    avail = sorted(
        avail,
        key=lambda r: (r["original_line_number"], r["text_sha256"], r["review_id"]),
    )
    picked = deterministic_sample(avail, n, seed, salt=salt)
    for r in picked:
        used.add(r["review_id"])
    return picked


def select_stage1(
    parent: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    seed = int(config["random_seed"])
    s1 = config["stage1"]
    exclude_rules = set(s1.get("removed_exclude_rules", []))

    removed = [
        r
        for r in parent
        if r.get("v2_decision") == "removed"
        and r.get("v2_rule_id") not in exclude_rules
    ]
    # Optional: deprioritize pure "Category:X" short boilerplate for category pool
    # Keep some category for coverage via quota.

    kept = [r for r in parent if r.get("v2_decision") == "kept"]

    removed_by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in removed:
        removed_by_rule[str(r.get("v2_rule_id") or "unknown")].append(r)

    kept_by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in kept:
        # multi-stratum: add to each listed stratum for priority pools
        strata = r.get("holdout_strata") or [primary_stratum(r)]
        for s in strata:
            kept_by_stratum[str(s)].append(r)
        # also ensure primary
        kept_by_stratum[primary_stratum(r)].append(r)

    used: set[str] = set()
    stage_records: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "removed_requested": dict(s1["removed_priority_quotas"]),
        "kept_requested": dict(s1["kept_priority_quotas"]),
        "removed_sampled": {},
        "kept_sampled": {},
        "removed_shortfalls": {},
        "kept_shortfalls": {},
        "excluded_from_stage1_removed_rules": sorted(exclude_rules),
    }

    # Removed quotas
    for rule, n_req in s1["removed_priority_quotas"].items():
        n_req = int(n_req)
        pool = removed_by_rule.get(rule, [])
        # For category: prefer longer / non-trivial excerpts if available
        if rule == "drop_category":
            pool = sorted(
                pool,
                key=lambda r: (-len(r.get("excerpt") or ""), r["original_line_number"]),
            )
        picked = sample_quota(pool, n_req, seed, f"s1_rm:{rule}", used)
        stats["removed_sampled"][rule] = len(picked)
        if len(picked) < n_req:
            stats["removed_shortfalls"][rule] = n_req - len(picked)
        stage_records.extend(picked)

    # Backfill removed to hit 40 from remaining high-risk pools
    target_rm = int(s1["removed_total"])
    shortfall_rm = target_rm - sum(
        1 for r in stage_records if r["v2_decision"] == "removed"
    )
    if shortfall_rm > 0:
        risk_order = [
            "drop_high_confidence_foreign",
            "drop_short_conditional",
            "drop_url_only",
            "drop_wikimedia_chrome",
            "drop_long_table_dump",
            "drop_category",
        ]
        for rule in risk_order:
            if shortfall_rm <= 0:
                break
            extra = sample_quota(
                removed_by_rule.get(rule, []),
                shortfall_rm,
                seed,
                f"s1_rm_backfill:{rule}",
                used,
            )
            stage_records.extend(extra)
            stats["removed_sampled"][rule] = stats["removed_sampled"].get(rule, 0) + len(
                extra
            )
            shortfall_rm -= len(extra)
        stats["removed_backfill_shortfall"] = max(0, shortfall_rm)

    # Kept quotas
    for stratum, n_req in s1["kept_priority_quotas"].items():
        n_req = int(n_req)
        # dedupe pool by review_id
        pool_map = {r["review_id"]: r for r in kept_by_stratum.get(stratum, [])}
        pool = list(pool_map.values())
        picked = sample_quota(pool, n_req, seed, f"s1_kp:{stratum}", used)
        stats["kept_sampled"][stratum] = len(picked)
        if len(picked) < n_req:
            stats["kept_shortfalls"][stratum] = n_req - len(picked)
        stage_records.extend(picked)

    target_kp = int(s1["kept_total"])
    shortfall_kp = target_kp - sum(
        1 for r in stage_records if r["v2_decision"] == "kept"
    )
    if shortfall_kp > 0:
        for stratum in [
            "mixed_signal",
            "insufficient_signal",
            "english_names_institutions",
            "near_threshold",
            "chichewa_signal",
            "short_retained",
            "long_retained",
        ]:
            if shortfall_kp <= 0:
                break
            pool_map = {r["review_id"]: r for r in kept_by_stratum.get(stratum, [])}
            extra = sample_quota(
                list(pool_map.values()),
                shortfall_kp,
                seed,
                f"s1_kp_backfill:{stratum}",
                used,
            )
            stage_records.extend(extra)
            stats["kept_sampled"][stratum] = stats["kept_sampled"].get(stratum, 0) + len(
                extra
            )
            shortfall_kp -= len(extra)
        stats["kept_backfill_shortfall"] = max(0, shortfall_kp)

    # Deduplicate stage by review_id
    stage_by_id = {r["review_id"]: r for r in stage_records}
    stage = list(stage_by_id.values())

    # Tag stage metadata (do not alter immutable core fields)
    for r in stage:
        r = dict(r)
        r["evaluation_stage"] = 1
        r["sequential_role"] = "stage1_active"
        stage_by_id[r["review_id"]] = r
    stage = list(stage_by_id.values())
    stage.sort(
        key=lambda r: (
            0 if r["v2_decision"] == "removed" else 1,
            r.get("v2_rule_id") or "",
            r["original_line_number"],
            r["review_id"],
        )
    )

    # Extension = parent not in stage
    stage_ids = {r["review_id"] for r in stage}
    extension = []
    for r in parent:
        if r["review_id"] in stage_ids:
            continue
        er = dict(r)
        er["evaluation_stage"] = None
        er["sequential_role"] = "extension_locked"
        extension.append(er)
    extension.sort(
        key=lambda r: (
            0 if r["v2_decision"] == "removed" else 1,
            r.get("v2_rule_id") or "",
            r["original_line_number"],
            r["review_id"],
        )
    )

    # Enforce counts if over-sampled
    rm = [r for r in stage if r["v2_decision"] == "removed"]
    kp = [r for r in stage if r["v2_decision"] == "kept"]
    if len(rm) > target_rm:
        rm = sorted(rm, key=lambda r: (r["original_line_number"], r["review_id"]))[
            :target_rm
        ]
    if len(kp) > target_kp:
        kp = sorted(kp, key=lambda r: (r["original_line_number"], r["review_id"]))[
            :target_kp
        ]
    stage = rm + kp
    stage.sort(
        key=lambda r: (
            0 if r["v2_decision"] == "removed" else 1,
            r.get("v2_rule_id") or "",
            r["original_line_number"],
            r["review_id"],
        )
    )

    # Rebuild extension after trim
    stage_ids = {r["review_id"] for r in stage}
    extension = []
    for r in parent:
        if r["review_id"] in stage_ids:
            continue
        er = dict(r)
        er["evaluation_stage"] = None
        er["sequential_role"] = "extension_locked"
        extension.append(er)

    stats["stage1_counts"] = {
        "total": len(stage),
        "removed": sum(1 for r in stage if r["v2_decision"] == "removed"),
        "kept": sum(1 for r in stage if r["v2_decision"] == "kept"),
        "by_rule": dict(Counter(r.get("v2_rule_id") or "kept" for r in stage)),
    }
    stats["extension_counts"] = {
        "total": len(extension),
        "removed": sum(1 for r in extension if r["v2_decision"] == "removed"),
        "kept": sum(1 for r in extension if r["v2_decision"] == "kept"),
    }

    if len(stage) != target_rm + target_kp:
        stats["warning"] = (
            f"Stage1 size {len(stage)} != {target_rm + target_kp}; "
            "pools may be too small."
        )

    # No overlap stage vs extension
    if stage_ids & {r["review_id"] for r in extension}:
        raise RuntimeError("stage1 and extension overlap")

    return stage, extension, stats


def render_stage1_instructions(config: dict[str, Any], stats: dict[str, Any]) -> str:
    s1 = config["stage1"]
    lines: list[str] = []
    w = lines.append
    w("# Holdout stage 1 — sequential evaluation (80 records)")
    w("")
    w("## Why sequential")
    w("")
    w(
        "Labeling all 250 holdout records at once is costly. "
        "Stage 1 concentrates effort on **ambiguous / high-risk** cases. "
        "The remaining records stay in a **locked extension pool** and are only "
        "released in chunks of 40 if stage-1 results are inconclusive."
    )
    w("")
    w("## Dataset roles")
    w("")
    w("| Set | Path | Role |")
    w("|-----|------|------|")
    w(
        f"| Development (367) | `{config['development_set_path']}` | "
        f"v1 diagnosis / v2 design — **not** independent final proof |"
    )
    w(
        f"| Parent holdout (250) | `{config['parent_holdout_path']}` | "
        f"Full blind pool (do not label all at once) |"
    )
    w(
        f"| **Stage 1 active (80)** | `{s1['sample_output']}` | "
        f"**Label these first** |"
    )
    w(
        f"| Extension locked (~170) | `{config['extension_pool']['path']}` | "
        f"**Do not open/label** until released |"
    )
    w(
        f"| Cleaning policy | `{config['cleaning_policy']}` | "
        f"**Do not modify** during this evaluation |"
    )
    w("")
    w("## Stage 1 composition")
    w("")
    c = stats["stage1_counts"]
    w(f"- Total: **{c['total']}** (target 40 removed + 40 kept)")
    w(f"- Removed: **{c['removed']}**")
    w(f"- Kept: **{c['kept']}**")
    w("")
    w("By v2 rule:")
    for k, n in sorted(c["by_rule"].items(), key=lambda kv: -kv[1]):
        w(f"- `{k}`: {n}")
    w("")
    w("Obvious `drop_blank` / `drop_digit_only` and bulk trivial Category lines are "
      "**deprioritized** (excluded or minimal coverage).")
    w("")
    w("## Labels")
    w("")
    for lab in config["allowed_labels"]:
        w(f"- `{lab}`")
    w("")
    w("Only edit `review_label` and optional `review_notes`.")
    w("")
    w("## After labeling stage 1")
    w("")
    w("```bash")
    w("python3 scripts/data/summarize_cleaning_holdout_stage.py \\")
    w("  --config configs/data/cleaning_holdout_sequential.json \\")
    w("  --sample data/reports/cleaning_holdout_stage1_sample.jsonl")
    w("```")
    w("")
    w("### Stopping logic")
    w("")
    w("The summarizer applies documented stop/release rules:")
    w("")
    w("- **Stop** if precision, false-removal rate, and useful retention are clearly "
      "on the good side of targets (point estimates + CI bounds).")
    w("- **Otherwise release the next 40** records from the locked extension pool "
      "(do not dump the remaining 170).")
    w("- **Never** expose the full 250 for simultaneous labeling as the default path.")
    w("")
    w("Do **not** change Cleaning Policy v2 to chase stage-1 scores.")
    w("")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build stage-1 holdout (80) + locked extension pool from parent 250."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_holdout_sequential.json"),
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

    parent_path = root / config["parent_holdout_path"]
    if not parent_path.is_file():
        print(f"error: parent holdout missing: {parent_path}", file=sys.stderr)
        return 1

    # Integrity snapshots
    try:
        parent_sha = sha256_file(parent_path)
        v2_sha = sha256_file(root / config["cleaning_policy"])
        dev_sha = sha256_file(root / config["development_set_path"])
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    parent = load_jsonl(parent_path)
    if len(parent) < 80:
        print(f"error: parent holdout too small: {len(parent)}", file=sys.stderr)
        return 1

    try:
        stage, extension, stats = select_stage1(parent, config)
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    s1 = config["stage1"]
    ext = config["extension_pool"]

    # Write outputs (do not modify parent file)
    write_jsonl(root / s1["sample_output"], stage)
    write_jsonl(root / ext["path"], extension)

    stage_manifest = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "role": "stage1_active",
        "parent_holdout_path": config["parent_holdout_path"],
        "parent_holdout_sha256": parent_sha,
        "cleaning_policy": config["cleaning_policy"],
        "cleaning_policy_sha256": v2_sha,
        "development_set_sha256": dev_sha,
        "stats": stats,
        "annotation_status": "pending_human_labels",
        "sequential_evaluation": True,
        "extension_pool_path": ext["path"],
        "extension_locked": True,
        "chunk_size": ext.get("chunk_size", 40),
    }
    write_json(root / s1["manifest_output"], stage_manifest)

    ext_manifest = {
        "generated_at": utc_now_iso(),
        "role": "extension_locked",
        "locked": True,
        "n_records": len(extension),
        "path": ext["path"],
        "chunk_size": ext.get("chunk_size", 40),
        "release_policy": config.get("stopping_logic"),
        "warning": (
            "Do not label this file until summarize_cleaning_holdout_stage.py "
            "recommends releasing the next chunk."
        ),
        "counts": stats["extension_counts"],
    }
    write_json(root / ext["manifest_output"], ext_manifest)

    instr = render_stage1_instructions(config, stats)
    (root / s1["instructions_output"]).write_text(instr, encoding="utf-8")

    # Pending validation stubs
    pending = {
        "generated_at": utc_now_iso(),
        "annotation_status": "pending_human_labels",
        "stage": 1,
        "n_records": len(stage),
        "n_labeled": 0,
        "n_unlabeled": len(stage),
        "sample_path": s1["sample_output"],
        "note": "Label stage1 only; then run summarize_cleaning_holdout_stage.py",
    }
    write_json(root / s1["validation_json"], pending)
    (root / s1["validation_report"]).write_text(
        "# Holdout stage-1 validation\n\n"
        f"**Status:** pending_human_labels  \n"
        f"**Records:** {len(stage)}  \n\n"
        "Label `data/reports/cleaning_holdout_stage1_sample.jsonl`, then:\n\n"
        "```bash\n"
        "python3 scripts/data/summarize_cleaning_holdout_stage.py \\\n"
        "  --config configs/data/cleaning_holdout_sequential.json \\\n"
        "  --sample data/reports/cleaning_holdout_stage1_sample.jsonl\n"
        "```\n",
        encoding="utf-8",
    )

    # Sequential eval doc
    seq_doc = root / "docs/data/CLEANING_HOLDOUT_SEQUENTIAL.md"
    seq_doc.parent.mkdir(parents=True, exist_ok=True)
    seq_doc.write_text(
        """# Sequential holdout evaluation (Cleaning Policy v2)

## Motivation

The original 367-record review set is a **development validation** set: it was used
to diagnose Cleaning Policy v1 and design v2. Metrics on that set overstate
independent generalization.

A **blind holdout** of 250 records was drawn with zero overlap. Labeling all 250
at once is expensive. This document defines **sequential, risk-stratified** labeling.

## Stages

| Stage | File | Size | Action |
|-------|------|-----:|--------|
| Stage 1 (active) | `data/reports/cleaning_holdout_stage1_sample.jsonl` | 80 | Label first |
| Extension (locked) | `data/reports/cleaning_holdout_extension_pool.jsonl` | ~170 | Do not label until released |
| Parent pool | `data/reports/cleaning_holdout_sample.jsonl` | 250 | Full pool; do not label wholesale |

Stage 1 prioritizes high-risk removed rules (foreign, short-conditional, URL-only,
wikimedia chrome, long-table dumps) and ambiguous kept strata (mixed, insufficient,
institutions, near-threshold). Obvious blank/digit-only and bulk trivial Category
lines are deprioritized.

## Workflow

1. Label **only** stage 1 (80 records).
2. Run `summarize_cleaning_holdout_stage.py`.
3. Read stop/release recommendation:
   - **Stop** if precision, FRR, and useful retention are clearly good (point + CI).
   - Else **release next 40** from the extension pool into a new stage file.
4. Never default to labeling all remaining records in one shot.
5. **Do not modify** `configs/data/cleaning_v2.json` to fit stage results mid-stream.

## Stopping criteria (defaults)

Stop if all hold:

- removal precision ≥ 0.90 and Wilson CI lower bound ≥ 0.80  
- false-removal rate ≤ 0.10 and Wilson CI upper bound ≤ 0.20  
- useful-text retention ≥ 0.90 and Wilson CI lower bound ≥ 0.80  

Otherwise release `chunk_size` (40) more records from the locked pool.

## Relation to development set

| Set | Use for tuning v2/v3? | Use for final claim? |
|-----|----------------------:|---------------------:|
| Development 367 | Yes (design only) | No |
| Holdout stage 1 / extensions | No (eval only) | Provisional generalization |
| Future final test set | No | Yes (when created) |

## Integrity

- Parent holdout file is not rewritten by the stage builder (identity of the 250 preserved).
- Cleaning Policy v2 is not modified by this workflow.
- Extension pool remains locked until the summarizer issues a release recommendation.
""",
        encoding="utf-8",
    )

    # Verify inputs unchanged
    if sha256_file(parent_path) != parent_sha:
        print("error: parent holdout changed", file=sys.stderr)
        return 2
    if sha256_file(root / config["cleaning_policy"]) != v2_sha:
        print("error: cleaning_v2 changed", file=sys.stderr)
        return 2

    print(
        f"Stage1: {stats['stage1_counts']['total']} "
        f"(rm={stats['stage1_counts']['removed']}, "
        f"kp={stats['stage1_counts']['kept']}); "
        f"extension locked: {stats['extension_counts']['total']}"
    )
    print(f"  stage1:    {root / s1['sample_output']}")
    print(f"  extension: {root / ext['path']}")
    print(f"  docs:      {seq_doc}")
    for rid, n in sorted(
        stats["stage1_counts"]["by_rule"].items(), key=lambda kv: -kv[1]
    ):
        print(f"  {rid}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
