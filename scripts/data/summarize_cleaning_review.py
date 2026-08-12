#!/usr/bin/env python3
"""Summarize human labels on the Wikipedia cleaning review sample.

Computes removal precision / false-removal rates and kept-text quality rates.
Does not modify cleaning rules, raw data, or interim cleaned corpora.

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

from audit_sources import load_json, utc_now_iso  # noqa: E402

TOOL_NAME = "summarize_cleaning_review"
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
        line = line.strip()
        if not line:
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


def summarize(
    records: Sequence[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    allowed = set(config.get("allowed_labels", ALLOWED_DEFAULT))
    false_rm = set(config.get("false_removal_labels", ["valid_chichewa", "useful_mixed_chichewa"]))
    correct_rm = set(
        config.get(
            "correct_removal_labels",
            ["boilerplate_or_noise", "foreign_language", "duplicate"],
        )
    )
    useful_kept = set(
        config.get("useful_kept_labels", ["valid_chichewa", "useful_mixed_chichewa"])
    )
    noise_kept = set(
        config.get("noise_kept_labels", ["boilerplate_or_noise", "duplicate"])
    )
    foreign_kept = set(config.get("foreign_kept_labels", ["foreign_language"]))
    boilerplate_kept = set(
        config.get("boilerplate_kept_labels", ["boilerplate_or_noise"])
    )
    include_uncertain = bool(config.get("include_uncertain_in_precision", False))

    invalid_labels: list[dict[str, Any]] = []
    unlabeled = 0
    label_counts: Counter[str] = Counter()

    removed = [r for r in records if r.get("decision") == "removed"]
    kept = [r for r in records if r.get("decision") == "kept"]

    def normalize_label(rec: dict[str, Any]) -> str | None:
        nonlocal unlabeled
        lab = rec.get("review_label")
        if lab is None or lab == "":
            unlabeled += 1
            return None
        if lab not in allowed:
            invalid_labels.append(
                {"review_id": rec.get("review_id"), "review_label": lab}
            )
            return None
        label_counts[lab] += 1
        return lab

    # --- Removed metrics ---
    rm_by_rule: dict[str, list[str | None]] = defaultdict(list)
    rm_labels: list[str | None] = []
    for rec in removed:
        lab = normalize_label(rec)
        rm_labels.append(lab)
        rm_by_rule[rec.get("rule_id") or "unknown"].append(lab)

    def removal_stats(labs: Sequence[str | None]) -> dict[str, Any]:
        labeled = [x for x in labs if x is not None]
        uncertain = sum(1 for x in labeled if x == "uncertain")
        if include_uncertain:
            decisive = labeled
            # treat uncertain as neither correct nor false → still exclude from num
            correct = sum(1 for x in decisive if x in correct_rm)
            false = sum(1 for x in decisive if x in false_rm)
            denom = correct + false
        else:
            decisive = [x for x in labeled if x != "uncertain"]
            correct = sum(1 for x in decisive if x in correct_rm)
            false = sum(1 for x in decisive if x in false_rm)
            denom = correct + false
        other = sum(
            1
            for x in decisive
            if x not in correct_rm and x not in false_rm and x != "uncertain"
        )
        return {
            "n_records": len(labs),
            "n_labeled": len(labeled),
            "n_unlabeled": sum(1 for x in labs if x is None),
            "n_uncertain": uncertain,
            "n_decisive": len(decisive) if not include_uncertain else (correct + false),
            "n_correct_removal": correct,
            "n_false_removal": false,
            "n_other_decisive": other,
            "removal_precision": rate(correct, denom),
            "false_removal_rate": rate(false, denom),
            "label_counts": dict(Counter(x for x in labeled)),
        }

    removed_overall = removal_stats(rm_labels)
    removed_by_rule = {
        rid: removal_stats(labs) for rid, labs in sorted(rm_by_rule.items())
    }

    # --- Kept metrics ---
    kp_labels: list[str | None] = []
    for rec in kept:
        kp_labels.append(normalize_label(rec))

    kp_labeled = [x for x in kp_labels if x is not None]
    kp_uncertain = sum(1 for x in kp_labeled if x == "uncertain")
    if include_uncertain:
        kp_decisive = [x for x in kp_labeled if x != "uncertain"]
    else:
        kp_decisive = [x for x in kp_labeled if x != "uncertain"]
    n_useful = sum(1 for x in kp_decisive if x in useful_kept)
    n_noise = sum(1 for x in kp_decisive if x in noise_kept)
    n_foreign = sum(1 for x in kp_decisive if x in foreign_kept)
    n_boilerplate = sum(1 for x in kp_decisive if x in boilerplate_kept)
    d = len(kp_decisive)

    kept_overall = {
        "n_records": len(kp_labels),
        "n_labeled": len(kp_labeled),
        "n_unlabeled": sum(1 for x in kp_labels if x is None),
        "n_uncertain": kp_uncertain,
        "n_decisive": d,
        "n_useful": n_useful,
        "n_noise": n_noise,
        "n_foreign": n_foreign,
        "n_boilerplate": n_boilerplate,
        "useful_text_rate": rate(n_useful, d),
        "kept_noise_rate": rate(n_noise, d),
        "foreign_language_leakage": rate(n_foreign, d),
        "boilerplate_leakage": rate(n_boilerplate, d),
        "label_counts": dict(Counter(kp_labeled)),
    }

    total = len(records)
    labeled_total = sum(1 for r in records if r.get("review_label") not in (None, ""))
    annotation_status = (
        "complete"
        if labeled_total == total and total > 0 and not invalid_labels
        else (
            "partial"
            if labeled_total > 0
            else "pending_human_labels"
        )
    )

    return {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "config_version": config.get("version"),
        "include_uncertain_in_precision": include_uncertain,
        "annotation_status": annotation_status,
        "n_records": total,
        "n_labeled": labeled_total,
        "n_unlabeled": total - labeled_total,
        "n_invalid_labels": len(invalid_labels),
        "invalid_labels": invalid_labels,
        "overall_label_counts": dict(label_counts),
        "removed": {
            "overall": removed_overall,
            "by_rule": removed_by_rule,
        },
        "kept": kept_overall,
        "human_annotation_remaining": max(0, total - labeled_total),
        "definitions": {
            "false_removal": sorted(false_rm),
            "correct_removal": sorted(correct_rm),
            "useful_kept": sorted(useful_kept),
            "noise_kept": sorted(noise_kept),
            "uncertain_handling": (
                "included_in_denominator"
                if include_uncertain
                else "excluded_from_precision"
            ),
        },
    }


def render_report(summary: dict[str, Any], sample_path: str) -> str:
    lines: list[str] = []
    w = lines.append

    w("# Cleaning validation report")
    w("")
    w(f"**Generated:** {summary['generated_at']}")
    w(f"**Tool:** {summary['tool']['name']} v{summary['tool']['version']}")
    w(f"**Sample:** `{sample_path}`")
    w(f"**Annotation status:** `{summary['annotation_status']}`")
    w("")
    w(
        f"Records: {summary['n_records']} total; "
        f"{summary['n_labeled']} labeled; "
        f"{summary['n_unlabeled']} unlabeled; "
        f"{summary['human_annotation_remaining']} remaining."
    )
    w("")

    if summary["annotation_status"] == "pending_human_labels":
        w("> **No human labels yet.** Metrics below are placeholders (null rates).")
        w("> Annotate `cleaning_review_sample.jsonl`, then re-run this script.")
        w("")

    w("## Definitions")
    w("")
    w(f"- False removal labels: `{summary['definitions']['false_removal']}`")
    w(f"- Correct removal labels: `{summary['definitions']['correct_removal']}`")
    w(f"- Useful kept labels: `{summary['definitions']['useful_kept']}`")
    w(f"- Noise kept labels: `{summary['definitions']['noise_kept']}`")
    w(
        f"- Uncertain handling: `{summary['definitions']['uncertain_handling']}`"
    )
    w("")

    w("## Removed samples")
    w("")
    ro = summary["removed"]["overall"]
    w("| metric | value |")
    w("|--------|------:|")
    for k in (
        "n_records",
        "n_labeled",
        "n_unlabeled",
        "n_uncertain",
        "n_correct_removal",
        "n_false_removal",
        "removal_precision",
        "false_removal_rate",
    ):
        w(f"| {k} | {ro.get(k)} |")
    w("")

    w("### Rule-specific removal metrics")
    w("")
    w(
        "| rule_id | n | labeled | correct | false | precision | false-removal rate |"
    )
    w("|---------|--:|--------:|--------:|------:|----------:|-------------------:|")
    for rid, st in summary["removed"]["by_rule"].items():
        w(
            f"| `{rid}` | {st['n_records']} | {st['n_labeled']} | "
            f"{st['n_correct_removal']} | {st['n_false_removal']} | "
            f"{st['removal_precision']} | {st['false_removal_rate']} |"
        )
    w("")

    w("## Kept samples")
    w("")
    ko = summary["kept"]
    w("| metric | value |")
    w("|--------|------:|")
    for k in (
        "n_records",
        "n_labeled",
        "n_unlabeled",
        "n_uncertain",
        "n_useful",
        "n_noise",
        "n_foreign",
        "n_boilerplate",
        "useful_text_rate",
        "kept_noise_rate",
        "foreign_language_leakage",
        "boilerplate_leakage",
    ):
        w(f"| {k} | {ko.get(k)} |")
    w("")

    w("## Label distribution (labeled only)")
    w("")
    w("| label | count |")
    w("|-------|------:|")
    for lab, n in sorted(summary.get("overall_label_counts", {}).items()):
        w(f"| `{lab}` | {n} |")
    if not summary.get("overall_label_counts"):
        w("| _(none)_ | 0 |")
    w("")

    w("## Next steps")
    w("")
    if summary["human_annotation_remaining"] > 0:
        w(
            f"1. Annotate remaining **{summary['human_annotation_remaining']}** "
            "records in the sample JSONL."
        )
        w("2. Re-run `summarize_cleaning_review.py`.")
        w("3. Only then consider cleaning-rule adjustments or promotion to processed.")
    else:
        w("1. Review precision / leakage metrics with a second annotator if possible.")
        w("2. Decide whether to adjust rules (manual config change) or promote interim → processed.")
    w("")
    w(
        "This report does **not** modify cleaning rules, promote data, create splits, "
        "or train models."
    )
    w("")
    return "\n".join(lines) + "\n"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Summarize human labels for Wikipedia cleaning review."
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/cleaning_review.json"),
    )
    p.add_argument(
        "--sample",
        type=Path,
        default=None,
        help="Annotated sample JSONL (default: paths.sample_output from config)",
    )
    p.add_argument(
        "--json-output",
        type=Path,
        default=None,
    )
    p.add_argument(
        "--report-output",
        type=Path,
        default=None,
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
    sample_path = (
        args.sample
        if args.sample is not None
        else repo_root / paths["sample_output"]
    )
    if not sample_path.is_absolute():
        sample_path = repo_root / sample_path
    json_out = (
        args.json_output
        if args.json_output is not None
        else repo_root / paths["validation_json"]
    )
    if args.json_output is not None and not json_out.is_absolute():
        json_out = repo_root / args.json_output
    report_out = (
        args.report_output
        if args.report_output is not None
        else repo_root / paths["validation_report"]
    )
    if args.report_output is not None and not report_out.is_absolute():
        report_out = repo_root / args.report_output

    if not sample_path.is_file():
        print(f"error: sample not found: {sample_path}", file=sys.stderr)
        return 1

    try:
        records = load_sample(sample_path)
        summary = summarize(records, config)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    summary["sample_path"] = str(
        sample_path.relative_to(repo_root)
        if sample_path.is_relative_to(repo_root)
        else sample_path
    )
    summary["source_id"] = config.get("source_id", "wikipedia")

    report = render_report(summary, summary["sample_path"])
    try:
        write_json(json_out, summary)
        write_text(report_out, report)
    except OSError as e:
        print(f"error: write failed: {e}", file=sys.stderr)
        return 1

    print(
        f"Validation summary: status={summary['annotation_status']} "
        f"labeled={summary['n_labeled']}/{summary['n_records']}"
    )
    print(f"  json:   {json_out}")
    print(f"  report: {report_out}")
    if summary["annotation_status"] != "pending_human_labels":
        ro = summary["removed"]["overall"]
        print(
            f"  removal_precision={ro['removal_precision']} "
            f"false_removal_rate={ro['false_removal_rate']}"
        )
        ko = summary["kept"]
        print(
            f"  useful_text_rate={ko['useful_text_rate']} "
            f"kept_noise_rate={ko['kept_noise_rate']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
