#!/usr/bin/env python3
"""Self-consistency for single-annotator delayed re-annotation (25 items).

Compares pass1 (original Annotator A) vs pass2 (self-review re-annotation).
Does not run comparison if pass2 is missing.
Does not use locked holdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import utc_now_iso, write_json, write_text  # noqa: E402
from evaluate_morphology_boundaries import (  # noqa: E402
    boundary_scores,
    boundaries_from_segments,
    parse_segments,
)
from measure_morphology_annotation_agreement import (  # noqa: E402
    jaccard,
    normalize_annotation,
    parse_bool,
    parse_tags,
)

TOOL_NAME = "measure_annotation_self_consistency"
TOOL_VERSION = "0.1.0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_ann_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    if path.suffix.lower() == ".csv":
        out: dict[str, dict[str, Any]] = {}
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("item_id"):
                    out[str(row["item_id"])] = dict(row)
        return out
    out = {}
    for r in load_jsonl(path):
        out[str(r["item_id"])] = r
    return out


def needs_reconsideration(n1: dict[str, Any], n2: dict[str, Any]) -> bool:
    s1, s2 = n1.get("segments"), n2.get("segments")
    if s1 != s2:
        return True
    if n1.get("uncertain") != n2.get("uncertain"):
        return True
    if n1.get("phenomenon_tags") != n2.get("phenomenon_tags"):
        return True
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Measure single-annotator self-consistency")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--self-review-ids",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/self_review_25_blinded.jsonl"
        ),
    )
    p.add_argument(
        "--pass1",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200.jsonl"
        ),
        help="Original Annotator A labels (full 200 or pilot+remaining merge)",
    )
    p.add_argument(
        "--pass2",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_self_review_25_annotations.jsonl"
        ),
        help="Delayed re-annotation of the 25 items",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/morphology_single_annotator_quality_v0_1.json"),
    )
    p.add_argument(
        "--report-md",
        type=Path,
        default=Path("data/reports/morphology_single_annotator_quality_v0_1.md"),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()

    def resolve(p: Path) -> Path:
        return p if p.is_absolute() else root / p

    review_path = resolve(args.self_review_ids)
    pass1_path = resolve(args.pass1)
    pass2_path = resolve(args.pass2)
    out_json = resolve(args.output)
    out_md = resolve(args.report_md)

    if not review_path.is_file():
        print(f"missing self-review list: {review_path}", file=sys.stderr)
        return 1

    review_rows = load_jsonl(review_path)
    review_ids = [str(r["item_id"]) for r in review_rows]
    if len(review_ids) != 25:
        print(f"expected 25 self-review ids, got {len(review_ids)}", file=sys.stderr)
        return 1
    for iid in review_ids:
        if iid.startswith("morph_hold_"):
            print(f"holdout id in self-review: {iid}", file=sys.stderr)
            return 1
        # blinded file must not carry original answers
        for r in review_rows:
            if str(r["item_id"]) != iid:
                continue
            for bad in (
                "proposed_segmentation",
                "bpe_tokens",
                "unigram_tokens",
                "automatic_tags",
            ):
                if bad in r:
                    print(f"self-review not blinded: {iid} has {bad}", file=sys.stderr)
                    return 1

    pass1 = load_ann_map(pass1_path)
    pass2 = load_ann_map(pass2_path)

    framing = {
        "development_benchmark": "single_native_speaker_annotation",
        "annotator_count": 1,
        "annotator_id": "annotator_a",
        "human_ai_pilot": "exploratory_only_not_gold",
        "human_human_iaa_claim": False,
        "morphology_holdout_locked": True,
        "multi_annotator_validation": "future_work",
    }

    if not pass2_path.is_file() or len(pass2) == 0:
        report = {
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "generated_at": utc_now_iso(),
            "status": "awaiting_pass2_reannotation",
            "n_self_review_items": 25,
            "self_review_item_ids": review_ids,
            "pass1_path": str(pass1_path),
            "pass2_path": str(pass2_path),
            "pass2_present": False,
            "comparison_run": False,
            "note": (
                "Do not run self-consistency comparison before Annotator A "
                "re-annotates the 25 blinded items."
            ),
            "framing": framing,
            "metrics": None,
        }
        write_json(out_json, report)
        write_text(
            out_md,
            "\n".join(
                [
                    "# Morphology single-annotator quality v0.1",
                    "",
                    f"_Generated {report['generated_at']}_",
                    "",
                    "## Research framing",
                    "",
                    "- Development benchmark: **single native-speaker annotation** (`annotator_a`)",
                    "- Annotator count: **1**",
                    "- Human–AI pilot (chat / Claude assist): **exploratory only**, not gold",
                    "- **No human–human IAA claim** in this phase",
                    "- Morphology holdout: **locked**",
                    "- Stronger multi-annotator validation: **future work**",
                    "",
                    "## Self-consistency review",
                    "",
                    f"- Blinded re-annotation set: **25** items (`self_review_25_blinded.jsonl`)",
                    "- Status: **awaiting pass-2 re-annotation**",
                    "- Comparison **not run** (pass-2 file missing or empty)",
                    "",
                    "After Annotator A completes pass-2, re-run:",
                    "",
                    "```bash",
                    ".venv/bin/python scripts/tokenizers/measure_annotation_self_consistency.py",
                    "```",
                    "",
                ]
            ),
        )
        print("status=awaiting_pass2 n=25 comparison_skipped")
        return 0

    # Compare
    per_item = []
    exact = 0
    both_seg = 0
    f1s: list[float] = []
    precs: list[float] = []
    recs: list[float] = []
    tag_jacs: list[float] = []
    unc_agree = 0
    unc_n = 0
    reconsider = []

    missing_p1 = []
    missing_p2 = []
    for iid in review_ids:
        if iid not in pass1:
            missing_p1.append(iid)
            continue
        if iid not in pass2:
            missing_p2.append(iid)
            continue
        n1 = normalize_annotation(pass1[iid])
        n2 = normalize_annotation(pass2[iid])
        s1, s2 = n1["segments"], n2["segments"]
        item: dict[str, Any] = {"item_id": iid}
        if s1 is not None and s2 is not None:
            both_seg += 1
            item["exact_segmentation_agreement"] = s1 == s2
            if s1 == s2:
                exact += 1
            sc = boundary_scores(s1, s2)
            item["boundary"] = {
                "precision": sc["boundary_precision"],
                "recall": sc["boundary_recall"],
                "f1": sc["boundary_f1"],
            }
            if sc["boundary_f1"] is not None:
                f1s.append(float(sc["boundary_f1"]))
            if sc["boundary_precision"] is not None:
                precs.append(float(sc["boundary_precision"]))
            if sc["boundary_recall"] is not None:
                recs.append(float(sc["boundary_recall"]))
            b1, b2 = boundaries_from_segments(s1), boundaries_from_segments(s2)
            item["boundary_set_jaccard"] = (
                1.0 if not b1 and not b2 else len(b1 & b2) / len(b1 | b2)
            )
        else:
            item["exact_segmentation_agreement"] = s1 is None and s2 is None
            if item["exact_segmentation_agreement"]:
                exact += 1
            item["boundary"] = None

        tj = jaccard(n1["phenomenon_tags"], n2["phenomenon_tags"])
        item["phenomenon_tag_jaccard"] = tj
        if tj is not None:
            tag_jacs.append(tj)

        u1, u2 = n1.get("uncertain"), n2.get("uncertain")
        if u1 is not None and u2 is not None:
            unc_n += 1
            if u1 == u2:
                unc_agree += 1
            item["uncertainty_agreement"] = u1 == u2
        else:
            item["uncertainty_agreement"] = None

        recon = needs_reconsideration(n1, n2)
        item["requires_manual_reconsideration"] = recon
        if recon:
            reconsider.append(iid)
        per_item.append(item)

    n_common = len(per_item)
    metrics = {
        "n_self_review_items": 25,
        "n_compared": n_common,
        "missing_pass1": missing_p1,
        "missing_pass2": missing_p2,
        "exact_segmentation_agreement": {
            "n_agree": exact,
            "n_compared": n_common,
            "rate": exact / n_common if n_common else None,
        },
        "boundary_when_both_segmented": {
            "n_pairs": both_seg,
            "mean_precision": sum(precs) / len(precs) if precs else None,
            "mean_recall": sum(recs) / len(recs) if recs else None,
            "mean_f1": sum(f1s) / len(f1s) if f1s else None,
        },
        "uncertainty_consistency": {
            "n_agree": unc_agree,
            "n_compared": unc_n,
            "rate": unc_agree / unc_n if unc_n else None,
        },
        "tag_consistency": {
            "mean_jaccard": sum(tag_jacs) / len(tag_jacs) if tag_jacs else None,
            "n": len(tag_jacs),
        },
        "manual_reconsideration": {
            "n": len(reconsider),
            "percentage": (100.0 * len(reconsider) / n_common) if n_common else None,
            "item_ids": reconsider,
        },
        "per_item": per_item,
    }

    report = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "status": "compared",
        "comparison_run": True,
        "pass1_path": str(pass1_path),
        "pass2_path": str(pass2_path),
        "framing": framing,
        "metrics": metrics,
        "note": (
            "Self-consistency is not human–human IAA. "
            "Human–AI pilot labels are not used as gold."
        ),
    }
    write_json(out_json, report)
    m = metrics
    write_text(
        out_md,
        "\n".join(
            [
                "# Morphology single-annotator quality v0.1",
                "",
                f"_Generated {report['generated_at']}_",
                "",
                "## Research framing",
                "",
                "- Development benchmark: **single native-speaker annotation**",
                "- Annotator count: **1** (`annotator_a`)",
                "- Human–AI pilot: **exploratory only** (not gold)",
                "- **No human–human IAA claim**",
                "- Morphology holdout: **locked**",
                "- Multi-annotator validation: **future work**",
                "",
                "## Self-consistency (pass1 vs delayed pass2)",
                "",
                f"- Items compared: **{m['n_compared']}** / 25",
                f"- Exact segmentation agreement: **{m['exact_segmentation_agreement']['rate']}**",
                f"- Mean boundary F1 (both segmented): **{m['boundary_when_both_segmented']['mean_f1']}**",
                f"- Uncertainty consistency: **{m['uncertainty_consistency']['rate']}**",
                f"- Mean tag Jaccard: **{m['tag_consistency']['mean_jaccard']}**",
                f"- Requiring manual reconsideration: **{m['manual_reconsideration']['n']}** "
                f"({m['manual_reconsideration']['percentage']}%)",
                "",
            ]
        ),
    )
    print(
        f"compared={m['n_compared']} exact={m['exact_segmentation_agreement']['rate']} "
        f"recon%={m['manual_reconsideration']['percentage']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
