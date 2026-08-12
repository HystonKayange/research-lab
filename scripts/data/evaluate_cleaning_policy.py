#!/usr/bin/env python3
"""Evaluate a cleaning policy against the frozen 367-record human review set.

Does not modify labels, raw data, or interim corpora (except reading them).
Simulates the policy by running the same rule engine on full source text and
comparing per original_line_number decisions to human labels.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json, read_utf8_text, utc_now_iso  # noqa: E402
from build_inventory import sha256_file  # noqa: E402
from clean_sources import apply_rules  # noqa: E402

TOOL_NAME = "evaluate_cleaning_policy"
TOOL_VERSION = "1.0.0"

KEEP_LABELS = frozenset({"valid_chichewa", "useful_mixed_chichewa"})
REMOVE_LABELS = frozenset(
    {"boilerplate_or_noise", "foreign_language", "duplicate"}
)


def load_review(path: Path) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("review_label") is None:
            raise ValueError(f"Unlabeled record at JSONL line {i}: {rec.get('review_id')}")
        recs.append(rec)
    return recs


def simulate_removals(
    raw_path: Path,
    source_cfg: dict[str, Any],
    config: dict[str, Any],
) -> tuple[set[int], dict[int, str], dict[int, str]]:
    """Return (removed_line_numbers, rule_by_line, kept_text_by_line for survivors)."""
    text = read_utf8_text(raw_path)
    lines = text.splitlines()
    kept, removals, transforms, _counts = apply_rules(
        lines,
        source_cfg.get("rules", []),
        config,
        source_cfg.get("source_id", "wikipedia"),
    )
    removed: set[int] = set()
    rule_by: dict[int, str] = {}
    for rec in removals:
        ln = int(rec["line_number"])
        removed.add(ln)
        rule_by[ln] = rec["rule_id"]

    # Rebuild kept text by replaying (order preserved among kept)
    # Map line numbers that were kept
    kept_text: dict[int, str] = {}
    # Re-run tracking: lines not in removed are kept (after transforms applied)
    # Need final text — re-apply per line for survivors
    from clean_sources import compile_rule, _build_lang_patterns, RuleContext

    lang = _build_lang_patterns(config)
    compiled = [
        compile_rule(r, config, lang)
        for r in source_cfg.get("rules", [])
        if r.get("enabled", True)
    ]
    ctx = RuleContext()
    for i, original in enumerate(lines, start=1):
        if i in removed:
            # still advance dedupe state for lines that were dropped by non-dedupe?
            # apply_rules adds to seen only when reaching dedupe. For fidelity we
            # already have removed set from full apply_rules.
            continue
        line = original
        for rule in compiled:
            if "_transform" in rule:
                line = rule["_transform"](line)
                continue
            if rule["type"] == "dedupe_exact":
                if line.strip():
                    ctx.seen_exact.add(line)
                continue
            # drop predicates should not fire for kept lines
        if line.strip():
            kept_text[i] = line
    return removed, rule_by, kept_text


def evaluate(
    records: list[dict[str, Any]],
    removed_lines: set[int],
    rule_by_line: dict[int, str],
    *,
    policy_name: str,
    config_path: str,
) -> dict[str, Any]:
    """Compare policy decisions to frozen human labels."""
    # Counts
    # Human keep / policy remove = false removal
    # Human remove / policy keep = false keep (noise leak)
    # Human keep / policy keep = correct keep
    # Human remove / policy remove = correct removal

    cm = {
        "true_positive_removal": 0,  # human remove, policy remove
        "false_positive_removal": 0,  # human keep, policy remove
        "true_negative_keep": 0,  # human keep, policy keep
        "false_negative_keep": 0,  # human remove, policy keep
    }
    by_rule_fp: Counter[str] = Counter()
    by_rule_tp: Counter[str] = Counter()
    examples_fp: list[dict[str, Any]] = []
    examples_fn: list[dict[str, Any]] = []

    useful_total = 0
    useful_retained = 0
    noise_total = 0
    noise_removed = 0
    kept_sample = 0
    kept_noise = 0
    kept_foreign = 0
    kept_boilerplate = 0

    for rec in records:
        ln = int(rec["original_line_number"])
        lab = rec["review_label"]
        human_keep = lab in KEEP_LABELS
        human_remove = lab in REMOVE_LABELS
        policy_removed = ln in removed_lines
        rule = rule_by_line.get(ln)

        if human_keep:
            useful_total += 1
            if not policy_removed:
                useful_retained += 1
                cm["true_negative_keep"] += 1
            else:
                cm["false_positive_removal"] += 1
                if rule:
                    by_rule_fp[rule] += 1
                if len(examples_fp) < 15:
                    examples_fp.append(
                        {
                            "line": ln,
                            "label": lab,
                            "rule": rule,
                            "excerpt": rec.get("excerpt", "")[:160],
                        }
                    )
        elif human_remove:
            noise_total += 1
            if policy_removed:
                noise_removed += 1
                cm["true_positive_removal"] += 1
                if rule:
                    by_rule_tp[rule] += 1
            else:
                cm["false_negative_keep"] += 1
                if len(examples_fn) < 15:
                    examples_fn.append(
                        {
                            "line": ln,
                            "label": lab,
                            "excerpt": rec.get("excerpt", "")[:160],
                        }
                    )

        # Among human-labeled "kept" decision records that policy also kept
        if rec.get("decision") == "kept" and not policy_removed:
            kept_sample += 1
            if lab in ("boilerplate_or_noise", "duplicate"):
                kept_noise += 1
                kept_boilerplate += 1
            if lab == "foreign_language":
                kept_foreign += 1
                kept_noise += 1
            if lab == "boilerplate_or_noise":
                pass

    tp = cm["true_positive_removal"]
    fp = cm["false_positive_removal"]
    tn = cm["true_negative_keep"]
    fn = cm["false_negative_keep"]

    def rate(n: int, d: int) -> float | None:
        return round(n / d, 6) if d else None

    # Removal precision among policy removals that are in the labeled set
    labeled_policy_removals = tp + fp
    removal_precision = rate(tp, labeled_policy_removals)
    false_removal_rate = rate(fp, labeled_policy_removals)
    useful_retention = rate(useful_retained, useful_total)
    noise_recall = rate(noise_removed, noise_total)
    kept_noise_rate = rate(kept_noise, kept_sample) if kept_sample else None
    foreign_leak = rate(kept_foreign, kept_sample) if kept_sample else None
    bp_leak = rate(kept_boilerplate, kept_sample) if kept_sample else None

    return {
        "generated_at": utc_now_iso(),
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "policy_name": policy_name,
        "config_path": config_path,
        "n_validation_records": len(records),
        "confusion_matrix": cm,
        "metrics": {
            "removal_precision": removal_precision,
            "false_removal_rate": false_removal_rate,
            "useful_text_retention": useful_retention,
            "noise_removal_recall": noise_recall,
            "kept_noise_rate_on_human_kept_decision": kept_noise_rate,
            "foreign_language_leakage_on_human_kept_decision": foreign_leak,
            "boilerplate_leakage_on_human_kept_decision": bp_leak,
            "n_useful_labels": useful_total,
            "n_useful_retained": useful_retained,
            "n_noise_labels": noise_total,
            "n_noise_removed": noise_removed,
            "n_policy_removals_in_sample": labeled_policy_removals,
            "n_false_removals": fp,
            "n_correct_removals": tp,
        },
        "false_positives_by_rule": dict(by_rule_fp),
        "true_positives_by_rule": dict(by_rule_tp),
        "false_positive_examples": examples_fp,
        "false_negative_examples": examples_fn,
        "targets": {
            "removal_precision_ge": 0.90,
            "false_removal_rate_le": 0.10,
            "useful_text_retention_ge": 0.90,
        },
    }


def targets_met(metrics: dict[str, Any]) -> dict[str, bool]:
    m = metrics
    return {
        "removal_precision": (m.get("removal_precision") or 0) >= 0.90,
        "false_removal_rate": (m.get("false_removal_rate") or 1) <= 0.10,
        "useful_text_retention": (m.get("useful_text_retention") or 0) >= 0.90,
    }


def render_report(
    result: dict[str, Any],
    v1_metrics: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    w = lines.append
    m = result["metrics"]
    met = targets_met(m)
    w(f"# Cleaning policy validation — {result['policy_name']}")
    w("")
    w(f"**Generated:** {result['generated_at']}")
    w(f"**Config:** `{result['config_path']}`")
    w(f"**Validation records:** {result['n_validation_records']} (frozen labels)")
    w("")
    w("## Metrics")
    w("")
    w("| metric | value | target | met? |")
    w("|--------|------:|--------|:----:|")
    w(
        f"| removal_precision | {m['removal_precision']} | ≥ 0.90 | "
        f"{'yes' if met['removal_precision'] else 'no'} |"
    )
    w(
        f"| false_removal_rate | {m['false_removal_rate']} | ≤ 0.10 | "
        f"{'yes' if met['false_removal_rate'] else 'no'} |"
    )
    w(
        f"| useful_text_retention | {m['useful_text_retention']} | ≥ 0.90 | "
        f"{'yes' if met['useful_text_retention'] else 'no'} |"
    )
    w(f"| noise_removal_recall | {m['noise_removal_recall']} | — | — |")
    w(
        f"| kept_noise_rate (human kept-decision subset) | "
        f"{m['kept_noise_rate_on_human_kept_decision']} | — | — |"
    )
    w(
        f"| foreign_leakage (human kept-decision) | "
        f"{m['foreign_language_leakage_on_human_kept_decision']} | — | — |"
    )
    w("")
    w("## Confusion matrix (human keep vs policy remove)")
    w("")
    cm = result["confusion_matrix"]
    w("|  | policy remove | policy keep |")
    w("|--|--------------:|------------:|")
    w(
        f"| human remove (noise) | {cm['true_positive_removal']} (TP) | "
        f"{cm['false_negative_keep']} (FN) |"
    )
    w(
        f"| human keep (useful) | {cm['false_positive_removal']} (FP) | "
        f"{cm['true_negative_keep']} (TN) |"
    )
    w("")
    if v1_metrics:
        w("## v1 vs v2 comparison")
        w("")
        w("| metric | v1 | v2 |")
        w("|--------|---:|---:|")
        w(
            f"| removal_precision | {v1_metrics.get('removal_precision')} | "
            f"{m['removal_precision']} |"
        )
        w(
            f"| false_removal_rate | {v1_metrics.get('false_removal_rate')} | "
            f"{m['false_removal_rate']} |"
        )
        w(
            f"| useful retention / useful-text rate | "
            f"{v1_metrics.get('useful_text_rate')} | "
            f"{m['useful_text_retention']} |"
        )
        w("")
    w("## False removals by rule (v2)")
    w("")
    for rule, n in sorted(
        result["false_positives_by_rule"].items(), key=lambda kv: -kv[1]
    ):
        w(f"- `{rule}`: {n}")
    if not result["false_positives_by_rule"]:
        w("- (none)")
    w("")
    w("## Example false positives (useful text removed)")
    w("")
    for ex in result["false_positive_examples"][:8]:
        w(f"- L{ex['line']} rule=`{ex['rule']}` [{ex['label']}]: {ex['excerpt']}")
    w("")
    w("## Example false negatives (noise kept)")
    w("")
    for ex in result["false_negative_examples"][:8]:
        w(f"- L{ex['line']} [{ex['label']}]: {ex['excerpt']}")
    w("")
    all_met = all(met.values())
    w("## Promotion decision")
    w("")
    if all_met:
        w("Targets met on frozen set — promotion to `data/processed/` may be considered after license review.")
    else:
        w(
            "**Targets not fully met.** Do **not** promote to `data/processed/` "
            "based on this evaluation alone."
        )
    w("")
    w("Human labels were not modified.")
    w("")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate cleaning policy on frozen review set.")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument(
        "--sample",
        type=Path,
        default=Path("data/reports/cleaning_review_sample.jsonl"),
    )
    p.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/metadata/cleaning_v2_validation.json"),
    )
    p.add_argument(
        "--report-output",
        type=Path,
        default=Path("data/reports/cleaning_v2_validation_report.md"),
    )
    p.add_argument("--policy-name", default="cleaning_v2")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--v1-metrics-json",
        type=Path,
        default=Path("data/metadata/cleaning_validation.json"),
        help="Optional v1 validation JSON for comparison",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    sample_path = args.sample if args.sample.is_absolute() else root / args.sample

    try:
        config = load_json(config_path)
        records = load_review(sample_path)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    # Snapshot labels for immutability check after
    label_snapshot = {
        r["review_id"]: r["review_label"] for r in records
    }

    wiki_cfg = config.get("sources", {}).get("wikipedia")
    if not wiki_cfg:
        print("error: config missing sources.wikipedia", file=sys.stderr)
        return 1
    raw_path = root / wiki_cfg["input_path"]
    if not raw_path.is_file():
        print(f"error: raw missing {raw_path}", file=sys.stderr)
        return 1

    pre_sha = sha256_file(raw_path)
    try:
        removed, rule_by, _kept = simulate_removals(raw_path, wiki_cfg, config)
    except Exception as e:
        print(f"error: simulation failed: {e}", file=sys.stderr)
        return 1
    post_sha = sha256_file(raw_path)
    if pre_sha != post_sha:
        print("error: raw file changed during evaluation", file=sys.stderr)
        return 2

    # Verify labels unchanged
    reloaded = load_review(sample_path)
    for r in reloaded:
        if label_snapshot[r["review_id"]] != r["review_label"]:
            print("error: human labels were modified", file=sys.stderr)
            return 2

    result = evaluate(
        records,
        removed,
        rule_by,
        policy_name=args.policy_name,
        config_path=str(
            config_path.relative_to(root) if config_path.is_relative_to(root) else config_path
        ),
    )
    result["raw_sha256"] = pre_sha
    result["raw_files_unchanged"] = True
    result["human_labels_unchanged"] = True
    result["targets_met"] = targets_met(result["metrics"])
    result["all_targets_met"] = all(result["targets_met"].values())
    result["n_lines_removed_full_corpus"] = len(removed)

    v1_m = None
    v1_path = (
        args.v1_metrics_json
        if args.v1_metrics_json.is_absolute()
        else root / args.v1_metrics_json
    )
    if v1_path.is_file():
        try:
            v1 = json.loads(v1_path.read_text(encoding="utf-8"))
            ro = v1.get("removed", {}).get("overall", {})
            ko = v1.get("kept", {})
            v1_m = {
                "removal_precision": ro.get("removal_precision"),
                "false_removal_rate": ro.get("false_removal_rate"),
                "useful_text_rate": ko.get("useful_text_rate"),
            }
            result["v1_comparison"] = v1_m
        except (OSError, json.JSONDecodeError):
            pass

    report = render_report(result, v1_m)
    json_out = (
        args.json_output if args.json_output.is_absolute() else root / args.json_output
    )
    report_out = (
        args.report_output
        if args.report_output.is_absolute()
        else root / args.report_output
    )
    json_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report_out.write_text(report, encoding="utf-8")

    m = result["metrics"]
    print(
        f"Evaluation {args.policy_name}: "
        f"prec={m['removal_precision']} frr={m['false_removal_rate']} "
        f"useful_ret={m['useful_text_retention']} "
        f"targets_met={result['all_targets_met']}"
    )
    print(f"  json:   {json_out}")
    print(f"  report: {report_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
