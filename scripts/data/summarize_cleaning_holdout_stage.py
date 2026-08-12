#!/usr/bin/env python3
"""Summarize stage-1 (or later stage) holdout labels and apply sequential stopping logic.

Does not modify Cleaning Policy v2. Does not auto-release extension records into
an active sample unless --release-next is passed after a release recommendation.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json, utc_now_iso  # noqa: E402
from build_inventory import sha256_file  # noqa: E402
from summarize_cleaning_holdout import (  # noqa: E402
    load_sample,
    render_report,
    summarize,
    wilson_interval,
)

TOOL_NAME = "summarize_cleaning_holdout_stage"
TOOL_VERSION = "1.0.0"


def apply_stopping_logic(
    metrics: dict[str, Any],
    intervals: dict[str, Any],
    stopping: dict[str, Any],
) -> dict[str, Any]:
    """Return stop/release recommendation from config rules."""
    checks: list[dict[str, Any]] = []
    all_clear = True

    for rule in stopping.get("stop_if_all", []):
        metric = rule["metric"]
        op = rule["op"]
        value = float(rule["value"])
        point = metrics.get(metric)
        ci = intervals.get(metric) or {}
        ok_point = False
        ok_ci = True
        detail: dict[str, Any] = {
            "metric": metric,
            "point": point,
            "required_op": op,
            "required_value": value,
        }

        if point is None:
            ok_point = False
        elif op == "ge":
            ok_point = point >= value
        elif op == "le":
            ok_point = point <= value
        else:
            raise ValueError(f"Unknown op {op}")

        if "ci_low_ge" in rule:
            low = ci.get("low")
            ok_ci = low is not None and low >= float(rule["ci_low_ge"])
            detail["ci_low"] = low
            detail["ci_low_ge"] = rule["ci_low_ge"]
        if "ci_high_le" in rule:
            high = ci.get("high")
            ok_ci = high is not None and high <= float(rule["ci_high_le"])
            detail["ci_high"] = high
            detail["ci_high_le"] = rule["ci_high_le"]

        ok = bool(ok_point and ok_ci)
        detail["passed"] = ok
        checks.append(detail)
        if not ok:
            all_clear = False

    if all_clear:
        decision = "stop"
        action = (
            "Stage-1 conclusions are sufficiently clear on preferred targets. "
            "Do not label the full remaining pool. Optionally archive extension "
            "as unused. Do not modify cleaning_v2 based on this alone without "
            "documented v3 design on the development set if needed."
        )
    else:
        decision = "release_next_chunk"
        chunk = int(
            stopping.get("chunk_size")
            or 40
        )
        action = (
            f"Targets unclear or missed. Release the next {chunk} records from "
            f"the locked extension pool (not the entire remainder). "
            f"Do not modify Cleaning Policy v2. Re-evaluate after the new chunk "
            f"is labeled."
        )

    return {
        "decision": decision,
        "action": action,
        "checks": checks,
        "all_stop_criteria_passed": all_clear,
        "never_release_full_250_at_once": bool(
            stopping.get("never_release_full_250_at_once", True)
        ),
    }


def discover_existing_stages(reports_dir: Path) -> list[int]:
    """Return sorted stage numbers from cleaning_holdout_stageN_sample.jsonl files."""
    stages: list[int] = []
    if not reports_dir.is_dir():
        return stages
    for p in reports_dir.glob("cleaning_holdout_stage*_sample.jsonl"):
        name = p.name
        # cleaning_holdout_stage3_sample.jsonl
        try:
            mid = name.removeprefix("cleaning_holdout_stage").removesuffix(
                "_sample.jsonl"
            )
            n = int(mid)
            if n >= 1:
                stages.append(n)
        except ValueError:
            continue
    return sorted(set(stages))


def next_stage_number(reports_dir: Path) -> int:
    existing = discover_existing_stages(reports_dir)
    if not existing:
        return 1
    return max(existing) + 1


def stage_sample_path(reports_dir: Path, stage_number: int) -> Path:
    return reports_dir / f"cleaning_holdout_stage{stage_number}_sample.jsonl"


def stage_manifest_path(reports_dir: Path, stage_number: int) -> Path:
    return reports_dir / f"cleaning_holdout_stage{stage_number}_manifest.json"


def stage_is_fully_labeled(sample_path: Path) -> bool:
    if not sample_path.is_file():
        return False
    records = load_sample(sample_path)
    if not records:
        return False
    return all(
        r.get("review_label") not in (None, "")
        for r in records
    )


def require_prior_stages_labeled(
    reports_dir: Path,
    next_stage: int,
    *,
    allow_partial_override: bool = False,
) -> None:
    """Block release if any prior stage sample exists but is not fully labeled."""
    if allow_partial_override:
        return
    for n in range(1, next_stage):
        p = stage_sample_path(reports_dir, n)
        if p.is_file() and not stage_is_fully_labeled(p):
            raise ValueError(
                f"Stage {n} is not fully labeled ({p}). "
                "Finish labeling or pass --allow-partial-prior-stage."
            )


def backup_file(path: Path, backup_dir: Path) -> Path | None:
    if not path.is_file():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_now_iso().replace(":", "").replace(".", "")[:20]
    dest = backup_dir / f"{path.name}.{ts}.bak"
    n = 1
    while dest.exists():
        dest = backup_dir / f"{path.name}.{ts}.{n}.bak"
        n += 1
    import shutil

    shutil.copy2(path, dest)
    return dest


def release_next_chunk(
    *,
    extension_path: Path,
    reports_dir: Path,
    chunk_size: int,
    backup_dir: Path,
    allow_partial_prior: bool = False,
) -> dict[str, Any]:
    """Release next stage from locked extension without overwriting prior stages.

    Creates cleaning_holdout_stage{N}_sample.jsonl where N is next free stage.
    Atomically updates extension pool after backup. Never overwrites prior stages.
    """
    if not extension_path.is_file():
        raise ValueError(f"Extension pool not found: {extension_path}")

    prior_stages = discover_existing_stages(reports_dir)
    next_n = next_stage_number(reports_dir)
    out_path = stage_sample_path(reports_dir, next_n)
    if out_path.exists():
        raise ValueError(
            f"Refusing to overwrite existing stage sample: {out_path}"
        )

    require_prior_stages_labeled(
        reports_dir, next_n, allow_partial_override=allow_partial_prior
    )

    records = load_sample(extension_path)
    if not records:
        raise ValueError("Extension pool is empty — no records to release")

    # Deterministic order already expected in pool; take head
    chunk = records[:chunk_size]
    rest = records[chunk_size:]
    if not chunk:
        raise ValueError("Extension pool is empty — no records to release")

    released_chunk: list[dict[str, Any]] = []
    for r in chunk:
        rec = dict(r)
        rec["evaluation_stage"] = next_n
        rec["sequential_role"] = f"stage{next_n}_active"
        # New stages start unlabeled; do not invent labels
        if rec.get("review_label") is None:
            rec["review_label"] = None
            rec["review_notes"] = None
        released_chunk.append(rec)

    # Backup extension before mutation
    bak = backup_file(extension_path, backup_dir)

    # Atomic write stage sample (must not exist)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out_path.with_suffix(".jsonl.tmp")
    try:
        with tmp_out.open("w", encoding="utf-8") as f:
            for r in released_chunk:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        # refuse if race created target
        if out_path.exists():
            tmp_out.unlink(missing_ok=True)
            raise ValueError(f"Stage sample appeared concurrently: {out_path}")
        tmp_out.replace(out_path)
    except Exception:
        tmp_out.unlink(missing_ok=True)
        raise

    # Atomic rewrite extension pool
    tmp_ext = extension_path.with_suffix(".jsonl.tmp")
    try:
        with tmp_ext.open("w", encoding="utf-8") as f:
            for r in rest:
                er = dict(r)
                er["sequential_role"] = "extension_locked"
                er["evaluation_stage"] = None
                f.write(json.dumps(er, ensure_ascii=False) + "\n")
        tmp_ext.replace(extension_path)
    except Exception:
        tmp_ext.unlink(missing_ok=True)
        # Leave stage file in place if extension rewrite fails — operator can recover
        # from backup. Do not delete stage sample automatically.
        raise

    manifest = {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "role": f"stage{next_n}_active",
        "stage_number": next_n,
        "sample_path": str(out_path),
        "n_records": len(released_chunk),
        "review_ids": [r["review_id"] for r in released_chunk],
        "text_sha256s": [r["text_sha256"] for r in released_chunk],
        "original_line_numbers": [
            r["original_line_number"] for r in released_chunk
        ],
        "parent_holdout_ids": [r["review_id"] for r in released_chunk],
        "extension_remaining": len(rest),
        "extension_backup": str(bak) if bak else None,
        "v2_decision_counts": {
            "removed": sum(
                1 for r in released_chunk if r.get("v2_decision") == "removed"
            ),
            "kept": sum(
                1 for r in released_chunk if r.get("v2_decision") == "kept"
            ),
        },
        "annotation_status": "pending_human_labels",
        "immutable_prior_stages": prior_stages,
    }
    man_path = stage_manifest_path(reports_dir, next_n)
    man_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "released": len(released_chunk),
        "stage_number": next_n,
        "extension_remaining": len(rest),
        "stage_sample": str(out_path),
        "manifest_path": str(man_path),
        "extension_backup": str(bak) if bak else None,
        "review_ids": [r["review_id"] for r in released_chunk],
        "parent_holdout_ids": [r["review_id"] for r in released_chunk],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Summarize holdout stage labels and apply sequential stopping logic."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_holdout_sequential.json"),
    )
    p.add_argument(
        "--sample",
        type=Path,
        default=None,
        help="Stage sample JSONL (default: stage1 sample from config)",
    )
    p.add_argument("--json-output", type=Path, default=None)
    p.add_argument("--report-output", type=Path, default=None)
    p.add_argument(
        "--release-next",
        action="store_true",
        help=(
            "Release the next chunk from the locked extension pool into a new "
            "immutable stageN sample (never overwrites prior stages)"
        ),
    )
    p.add_argument(
        "--allow-partial-prior-stage",
        action="store_true",
        help=(
            "Override: allow release even if a prior stage sample is not fully "
            "labeled (default: block)"
        ),
    )
    p.add_argument(
        "--force-release",
        action="store_true",
        help=(
            "Release even if stopping logic does not recommend release_next_chunk "
            "(still requires empty labels check on the active sample when used "
            "via normal flow; for tests/ops only)"
        ),
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

    s1 = config["stage1"]
    sample_path = (
        args.sample
        if args.sample is not None
        else root / s1["sample_output"]
    )
    if not Path(sample_path).is_absolute():
        sample_path = root / sample_path
    sample_path = Path(sample_path)

    json_out = (
        Path(args.json_output)
        if args.json_output
        else root / s1["validation_json"]
    )
    if args.json_output and not Path(args.json_output).is_absolute():
        json_out = root / args.json_output
    report_out = (
        Path(args.report_output)
        if args.report_output
        else root / s1["validation_report"]
    )
    if args.report_output and not Path(args.report_output).is_absolute():
        report_out = root / args.report_output

    # Integrity: v2 config unchanged (read-only check)
    try:
        v2_sha = sha256_file(root / config["cleaning_policy"])
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not sample_path.is_file():
        print(f"error: sample not found: {sample_path}", file=sys.stderr)
        return 1

    try:
        records = load_sample(sample_path)
        # Map holdout schema: summarize expects v2_decision
        for r in records:
            if "v2_decision" not in r and "decision" in r:
                r["v2_decision"] = r["decision"]
            if "v2_rule_id" not in r and "rule_id" in r:
                r["v2_rule_id"] = r.get("rule_id")
        result = summarize(records, config)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    stopping = dict(config.get("stopping_logic", {}))
    stopping["chunk_size"] = config.get("extension_pool", {}).get("chunk_size", 40)
    recommendation = {
        "decision": "pending_labels",
        "action": "Complete human labels on the active stage sample first.",
        "checks": [],
        "all_stop_criteria_passed": False,
    }
    if result["annotation_status"] == "complete":
        recommendation = apply_stopping_logic(
            result["metrics"],
            result.get("confidence_intervals", {}),
            stopping,
        )

    result["tool"] = {"name": TOOL_NAME, "version": TOOL_VERSION}
    result["stage"] = 1
    result["sequential_evaluation"] = True
    result["cleaning_policy"] = config["cleaning_policy"]
    result["cleaning_policy_sha256"] = v2_sha
    result["stopping_recommendation"] = recommendation
    result["sample_path"] = str(
        sample_path.relative_to(root) if sample_path.is_relative_to(root) else sample_path
    )

    # Augment report
    base_report = render_report(result, result["sample_path"])
    extra = [
        "",
        "## Sequential stopping recommendation",
        "",
        f"**Decision:** `{recommendation['decision']}`",
        "",
        recommendation["action"],
        "",
    ]
    if recommendation.get("checks"):
        extra.append("| criterion | passed | detail |")
        extra.append("|-----------|:------:|--------|")
        for c in recommendation["checks"]:
            extra.append(
                f"| {c['metric']} | {'yes' if c['passed'] else 'no'} | "
                f"point={c.get('point')} |"
            )
        extra.append("")
    reports_dir = root / "data" / "reports"
    next_n_preview = next_stage_number(reports_dir)
    if recommendation["decision"] == "release_next_chunk":
        next_sample = stage_sample_path(reports_dir, next_n_preview)
        extra.append(
            "To release the next chunk into a **new** immutable stage file "
            "(never overwrites prior stages):\n\n"
            "```bash\n"
            "python3 scripts/data/summarize_cleaning_holdout_stage.py \\\n"
            "  --config configs/data/cleaning_holdout_sequential.json \\\n"
            f"  --sample {result['sample_path']} \\\n"
            "  --release-next\n"
            "```\n\n"
            f"Next stage number will be **{next_n_preview}** → "
            f"`{next_sample.relative_to(root) if next_sample.is_relative_to(root) else next_sample}`.\n"
        )
    extra.append(
        f"Cleaning Policy v2 SHA-256 (must remain unchanged): `{v2_sha}`\n"
    )
    report = base_report.rstrip() + "\n" + "\n".join(extra) + "\n"

    json_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report_out.write_text(report, encoding="utf-8")

    release_info = None
    if args.release_next:
        if result["annotation_status"] != "complete" and not args.force_release:
            print(
                "error: cannot release next chunk before the evaluated sample "
                "is fully labeled (or pass --force-release for ops)",
                file=sys.stderr,
            )
            return 1
        if (
            recommendation["decision"] != "release_next_chunk"
            and not args.force_release
        ):
            print(
                "error: stopping logic does not recommend release "
                f"(decision={recommendation['decision']}); "
                "pass --force-release to override",
                file=sys.stderr,
            )
            return 1
        ext_path = root / config["extension_pool"]["path"]
        chunk = int(config["extension_pool"].get("chunk_size", 40))
        backup_dir = root / "data" / "reports" / "cleaning_holdout_backups"
        try:
            release_info = release_next_chunk(
                extension_path=ext_path,
                reports_dir=reports_dir,
                chunk_size=chunk,
                backup_dir=backup_dir,
                allow_partial_prior=bool(args.allow_partial_prior_stage),
            )
        except (ValueError, OSError) as e:
            print(f"error: release failed: {e}", file=sys.stderr)
            return 1
        print(
            f"Released {release_info['released']} records → "
            f"stage{release_info['stage_number']} "
            f"({release_info['stage_sample']}) "
            f"(extension remaining {release_info['extension_remaining']})"
        )
        print(f"  manifest: {release_info['manifest_path']}")
        if release_info.get("extension_backup"):
            print(f"  extension backup: {release_info['extension_backup']}")

    print(
        f"Stage summary: status={result['annotation_status']} "
        f"labeled={result['n_labeled']}/{result['n_records']} "
        f"stop_decision={recommendation['decision']}"
    )
    print(f"  json:   {json_out}")
    print(f"  report: {report_out}")
    if result["annotation_status"] == "complete":
        m = result["metrics"]
        print(
            f"  prec={m['removal_precision']} frr={m['false_removal_rate']} "
            f"useful_ret={m['useful_text_retention']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
