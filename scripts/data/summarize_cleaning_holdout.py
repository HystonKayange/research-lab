#!/usr/bin/env python3
"""Summarize human labels on the blind cleaning holdout sample.

Computes precision/recall-style metrics with Wilson score intervals.
Does not modify cleaning_v2, raw data, or human labels (read-only except outputs).

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json, utc_now_iso  # noqa: E402

TOOL_NAME = "summarize_cleaning_holdout"
TOOL_VERSION = "1.0.0"

ALLOWED_DEFAULT = [
    "valid_chichewa",
    "useful_mixed_chichewa",
    "boilerplate_or_noise",
    "foreign_language",
    "duplicate",
    "uncertain",
]


def load_sample(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL {path}:{i}: {e}") from e
    return records


def rate(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(num / den, 6)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> dict[str, float | None]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return {"low": None, "high": None, "n": 0, "p": None}
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    low = (centre - margin) / denom
    high = (centre + margin) / denom
    return {
        "p": round(p, 6),
        "low": round(max(0.0, low), 6),
        "high": round(min(1.0, high), 6),
        "n": n,
        "successes": successes,
        "z": z,
    }


def summarize(records: Sequence[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    allowed = set(config.get("allowed_labels", ALLOWED_DEFAULT))
    false_rm = set(config.get("false_removal_labels", ["valid_chichewa", "useful_mixed_chichewa"]))
    correct_rm = set(
        config.get(
            "correct_removal_labels",
            ["boilerplate_or_noise", "foreign_language", "duplicate"],
        )
    )
    useful = set(config.get("useful_kept_labels", ["valid_chichewa", "useful_mixed_chichewa"]))
    noise = set(config.get("noise_kept_labels", ["boilerplate_or_noise", "duplicate"]))
    foreign = set(config.get("foreign_kept_labels", ["foreign_language"]))
    boilerplate = set(config.get("boilerplate_kept_labels", ["boilerplate_or_noise"]))
    include_uncertain = bool(config.get("include_uncertain_in_precision", False))
    z = float(config.get("wilson_z", 1.96))

    invalid: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    unlabeled = 0

    def lab_of(rec: dict[str, Any]) -> str | None:
        nonlocal unlabeled
        lab = rec.get("review_label")
        if lab is None or lab == "":
            unlabeled += 1
            return None
        if lab not in allowed:
            invalid.append({"review_id": rec.get("review_id"), "review_label": lab})
            return None
        label_counts[lab] += 1
        return lab

    # Policy decision from v2 fields
    removed = [r for r in records if r.get("v2_decision") == "removed"]
    kept = [r for r in records if r.get("v2_decision") == "kept"]

    # Confusion relative to human useful vs noise
    # For removed records: correct removal vs false removal
    # For kept: useful retention vs leakage

    def decisive(lab: str | None) -> bool:
        if lab is None:
            return False
        if lab == "uncertain":
            return include_uncertain
        return True

    # Overall removal metrics among v2-removed with decisive labels
    rm_correct = rm_false = rm_uncertain = 0
    by_rule: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0, "false": 0, "uncertain": 0, "unlabeled": 0}
    )

    for r in removed:
        lab = lab_of(r)
        rid = r.get("v2_rule_id") or "unknown"
        by_rule[rid]["n"] += 1
        if lab is None:
            by_rule[rid]["unlabeled"] += 1
            continue
        if lab == "uncertain":
            rm_uncertain += 1
            by_rule[rid]["uncertain"] += 1
            if not include_uncertain:
                continue
        if lab in correct_rm:
            rm_correct += 1
            by_rule[rid]["correct"] += 1
        elif lab in false_rm:
            rm_false += 1
            by_rule[rid]["false"] += 1

    den_rm = rm_correct + rm_false
    removal_precision = rate(rm_correct, den_rm)
    false_removal_rate = rate(rm_false, den_rm)

    # Useful retention: among all records human-labeled useful, share with v2_decision=kept
    useful_total = useful_kept_by_v2 = 0
    noise_total = noise_removed_by_v2 = 0
    foreign_total = foreign_removed = 0
    bp_total = bp_removed = 0

    # Reset label counting for kept path — lab_of already counted all
    # Re-walk all records for global useful/noise
    for r in records:
        lab = r.get("review_label")
        if lab is None or lab == "" or lab not in allowed:
            continue
        if lab == "uncertain" and not include_uncertain:
            continue
        v2_rm = r.get("v2_decision") == "removed"
        if lab in useful:
            useful_total += 1
            if not v2_rm:
                useful_kept_by_v2 += 1
        if lab in correct_rm:
            noise_total += 1
            if v2_rm:
                noise_removed_by_v2 += 1
        if lab in foreign:
            foreign_total += 1
            if v2_rm:
                foreign_removed += 1
        if lab in boilerplate:
            bp_total += 1
            if v2_rm:
                bp_removed += 1

    # Kept-sample leakage (v2 kept + labeled)
    kept_labeled = []
    for r in kept:
        lab = r.get("review_label")
        if lab is None or lab == "" or lab not in allowed:
            continue
        if lab == "uncertain" and not include_uncertain:
            continue
        kept_labeled.append(lab)

    n_kept_lab = len(kept_labeled)
    n_useful_kept = sum(1 for x in kept_labeled if x in useful)
    n_noise_kept = sum(1 for x in kept_labeled if x in noise or x in foreign)
    n_foreign_kept = sum(1 for x in kept_labeled if x in foreign)
    n_bp_kept = sum(1 for x in kept_labeled if x in boilerplate)

    # Confusion matrix 2x2: human useful vs noise × v2 remove vs keep
    cm = {
        "human_useful_v2_remove": 0,
        "human_useful_v2_keep": 0,
        "human_noise_v2_remove": 0,
        "human_noise_v2_keep": 0,
    }
    for r in records:
        lab = r.get("review_label")
        if lab is None or lab not in allowed:
            continue
        if lab == "uncertain" and not include_uncertain:
            continue
        v2_rm = r.get("v2_decision") == "removed"
        if lab in useful:
            if v2_rm:
                cm["human_useful_v2_remove"] += 1
            else:
                cm["human_useful_v2_keep"] += 1
        elif lab in correct_rm:
            if v2_rm:
                cm["human_noise_v2_remove"] += 1
            else:
                cm["human_noise_v2_keep"] += 1

    total = len(records)
    labeled_total = sum(
        1 for r in records if r.get("review_label") not in (None, "")
    )
    status = (
        "complete"
        if labeled_total == total and total > 0 and not invalid
        else ("partial" if labeled_total > 0 else "pending_human_labels")
    )

    targets = config.get("generalization_targets", {})
    metrics = {
        "removal_precision": removal_precision,
        "false_removal_rate": false_removal_rate,
        "useful_text_retention": rate(useful_kept_by_v2, useful_total),
        "noise_removal_recall": rate(noise_removed_by_v2, noise_total),
        "foreign_language_removal_recall": rate(foreign_removed, foreign_total),
        "boilerplate_removal_recall": rate(bp_removed, bp_total),
        "kept_noise_rate": rate(n_noise_kept, n_kept_lab),
        "foreign_language_leakage": rate(n_foreign_kept, n_kept_lab),
        "boilerplate_leakage": rate(n_bp_kept, n_kept_lab),
        "useful_text_rate_among_kept_labeled": rate(n_useful_kept, n_kept_lab),
        "n_removed_reviewed": len(removed),
        "n_kept_reviewed": len(kept),
        "n_rm_correct": rm_correct,
        "n_rm_false": rm_false,
        "n_rm_uncertain": rm_uncertain,
        "n_useful_labels": useful_total,
        "n_useful_retained": useful_kept_by_v2,
        "n_noise_labels": noise_total,
        "n_noise_removed": noise_removed_by_v2,
    }

    intervals = {
        "removal_precision": wilson_interval(rm_correct, den_rm, z),
        "false_removal_rate": wilson_interval(rm_false, den_rm, z),
        "useful_text_retention": wilson_interval(useful_kept_by_v2, useful_total, z),
        "noise_removal_recall": wilson_interval(noise_removed_by_v2, noise_total, z),
    }

    rule_metrics = {}
    for rid, st in sorted(by_rule.items()):
        d = st["correct"] + st["false"]
        rule_metrics[rid] = {
            **st,
            "removal_precision": rate(st["correct"], d),
            "false_removal_rate": rate(st["false"], d),
            "precision_ci": wilson_interval(st["correct"], d, z),
        }

    met = {
        "removal_precision": (metrics["removal_precision"] or 0)
        >= float(targets.get("removal_precision_ge", 0.9)),
        "false_removal_rate": (metrics["false_removal_rate"] or 1)
        <= float(targets.get("false_removal_rate_le", 0.1)),
        "useful_text_retention": (metrics["useful_text_retention"] or 0)
        >= float(targets.get("useful_text_retention_ge", 0.9)),
    }

    return {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "dataset_role": "blind_holdout",
        "development_set_role": "development_validation",
        "annotation_status": status,
        "n_records": total,
        "n_labeled": labeled_total,
        "n_unlabeled": total - labeled_total,
        "n_invalid_labels": len(invalid),
        "invalid_labels": invalid,
        "overall_label_counts": dict(label_counts),
        "metrics": metrics,
        "confidence_intervals": intervals,
        "confusion_matrix": cm,
        "rule_metrics": rule_metrics,
        "targets": targets,
        "targets_met": met,
        "all_targets_met": all(met.values()) if status == "complete" else False,
        "note": (
            "Development set (original 367) informed v2 design. "
            "Holdout estimates generalization; do not retune v2 on holdout before labeling is complete."
        ),
    }


def render_report(summary: dict[str, Any], sample_path: str) -> str:
    lines: list[str] = []
    w = lines.append
    w("# Cleaning holdout validation report")
    w("")
    w(f"**Generated:** {summary['generated_at']}")
    w(f"**Sample:** `{sample_path}`")
    w(f"**Dataset role:** `{summary['dataset_role']}` (blind holdout)")
    w(
        f"**Development set role:** `{summary['development_set_role']}` "
        "(original 367 — not independent final validation)"
    )
    w(f"**Annotation status:** `{summary['annotation_status']}`")
    w("")
    w(
        f"Records: {summary['n_records']}; labeled {summary['n_labeled']}; "
        f"unlabeled {summary['n_unlabeled']}."
    )
    w("")
    if summary["annotation_status"] != "complete":
        w("> **Pending human labels.** Metrics below may be null or partial.")
        w("")
    w("## Metrics")
    w("")
    m = summary["metrics"]
    ci = summary.get("confidence_intervals", {})
    w("| metric | value | 95% Wilson CI |")
    w("|--------|------:|---------------|")
    for key in (
        "removal_precision",
        "false_removal_rate",
        "useful_text_retention",
        "noise_removal_recall",
        "foreign_language_removal_recall",
        "boilerplate_removal_recall",
        "kept_noise_rate",
        "foreign_language_leakage",
        "boilerplate_leakage",
    ):
        val = m.get(key)
        interval = ci.get(key)
        if interval and interval.get("low") is not None:
            cis = f"[{interval['low']}, {interval['high']}] n={interval['n']}"
        else:
            cis = "—"
        w(f"| {key} | {val} | {cis} |")
    w("")
    w("## Confusion matrix")
    w("")
    cm = summary["confusion_matrix"]
    w("|  | v2 remove | v2 keep |")
    w("|--|---------:|--------:|")
    w(
        f"| human useful | {cm['human_useful_v2_remove']} | {cm['human_useful_v2_keep']} |"
    )
    w(
        f"| human noise | {cm['human_noise_v2_remove']} | {cm['human_noise_v2_keep']} |"
    )
    w("")
    w("## Rule-specific removal metrics")
    w("")
    w("| rule | n | correct | false | precision | FRR |")
    w("|------|--:|--------:|------:|----------:|----:|")
    for rid, st in summary.get("rule_metrics", {}).items():
        w(
            f"| `{rid}` | {st['n']} | {st['correct']} | {st['false']} | "
            f"{st['removal_precision']} | {st['false_removal_rate']} |"
        )
    w("")
    w("## Targets (generalization)")
    w("")
    if summary["annotation_status"] == "complete":
        for k, ok in summary.get("targets_met", {}).items():
            w(f"- `{k}`: **{'met' if ok else 'not met'}**")
        w("")
        if summary.get("all_targets_met"):
            w("All preferred targets met on this **holdout**.")
        else:
            w(
                "Targets missed on holdout. **Do not** quietly retune v2 on these "
                "examples; design v3 on the development set and re-evaluate on holdout."
            )
    else:
        w("Targets evaluated after complete labeling.")
    w("")
    w(summary.get("note", ""))
    w("")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize cleaning holdout labels.")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_holdout.json"),
    )
    p.add_argument("--sample", type=Path, default=None)
    p.add_argument("--json-output", type=Path, default=None)
    p.add_argument("--report-output", type=Path, default=None)
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
    sample_path = (
        args.sample
        if args.sample is not None
        else root / paths["sample_output"]
    )
    if not sample_path.is_absolute():
        sample_path = root / sample_path
    json_out = (
        args.json_output
        if args.json_output is not None
        else root / paths["validation_json"]
    )
    if args.json_output is not None and not Path(args.json_output).is_absolute():
        json_out = root / args.json_output
    report_out = (
        args.report_output
        if args.report_output is not None
        else root / paths["validation_report"]
    )
    if args.report_output is not None and not Path(args.report_output).is_absolute():
        report_out = root / args.report_output

    if not sample_path.is_file():
        print(f"error: sample not found: {sample_path}", file=sys.stderr)
        return 1

    try:
        records = load_sample(sample_path)
        # immutability: only read labels
        summary = summarize(records, config)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    summary["sample_path"] = str(
        sample_path.relative_to(root) if sample_path.is_relative_to(root) else sample_path
    )
    report = render_report(summary, summary["sample_path"])
    json_out = Path(json_out)
    report_out = Path(report_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report_out.write_text(report, encoding="utf-8")

    print(
        f"Holdout summary: status={summary['annotation_status']} "
        f"labeled={summary['n_labeled']}/{summary['n_records']}"
    )
    print(f"  json:   {json_out}")
    print(f"  report: {report_out}")
    if summary["annotation_status"] == "complete":
        m = summary["metrics"]
        print(
            f"  prec={m['removal_precision']} frr={m['false_removal_rate']} "
            f"useful_ret={m['useful_text_retention']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
