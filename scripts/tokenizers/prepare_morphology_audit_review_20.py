#!/usr/bin/env python3
"""Prepare Annotator A human re-review queue from the audit report (20 items).

Read-only w.r.t. annotations: never modifies annotator_a_full_200.jsonl.
Does not load BPE/Unigram, holdout, or LM test.

Usage:
  python scripts/tokenizers/prepare_morphology_audit_review_20.py
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

from common import sha256_file, utc_now_iso, write_json, write_jsonl  # noqa: E402

TOOL_NAME = "prepare_morphology_audit_review_20"
TOOL_VERSION = "0.1.0"

QUEUE_FIELDS = [
    "item_id",
    "surface_form",
    "context",
    "source",
    "current_proposed_segmentation",
    "current_alternative_segmentation",
    "uncertain",
    "confidence",
    "no_segmentation_required",
    "mixed_language",
    "spelling_or_ocr_issue",
    "insufficient_context",
    "audit_priority",
    "audit_categories",
    "audit_reasons",
    "review_status",
]


def refuse_forbidden(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked holdout path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--audit",
        type=Path,
        default=Path("data/reports/morphology_annotation_audit_v0_1.json"),
    )
    p.add_argument(
        "--full-annotations",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotations/"
            "annotator_a_full_200.jsonl"
        ),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20.jsonl"
        ),
    )
    p.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20_manifest.json"
        ),
    )
    args = p.parse_args()
    root = (args.repo_root or Path(__file__).resolve().parents[2]).resolve()

    audit_path = (root / args.audit).resolve() if not args.audit.is_absolute() else args.audit
    full_path = (
        (root / args.full_annotations).resolve()
        if not args.full_annotations.is_absolute()
        else args.full_annotations
    )
    out_path = (root / args.out).resolve() if not args.out.is_absolute() else args.out
    man_path = (root / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest

    for path in (audit_path, full_path, out_path, man_path):
        refuse_forbidden(path)

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    recommended = audit.get("recommended_human_review") or []
    if len(recommended) != 20:
        raise SystemExit(
            f"expected 20 recommended_human_review items, found {len(recommended)}"
        )

    full_rows = load_jsonl(full_path)
    by_id = {str(r["item_id"]): r for r in full_rows}

    queue: list[dict[str, Any]] = []
    reason_counter: dict[str, int] = {}
    category_counter: dict[str, int] = {}

    for rec in recommended:
        iid = str(rec["item_id"])
        if iid not in by_id:
            raise SystemExit(f"audit item {iid} missing from full-200 annotations")
        src = by_id[iid]
        # Never copy model/tokenizer fields into the queue
        reasons = list(rec.get("reasons") or [])
        categories = list(rec.get("categories") or [])
        for reason in reasons:
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
        for cat in categories:
            category_counter[cat] = category_counter.get(cat, 0) + 1

        queue.append(
            {
                "item_id": iid,
                "surface_form": src.get("surface_form"),
                "context": src.get("context"),
                "source": src.get("source"),
                "current_proposed_segmentation": src.get("proposed_segmentation"),
                "current_alternative_segmentation": src.get("alternative_segmentation"),
                "uncertain": src.get("uncertain"),
                "confidence": src.get("confidence"),
                "no_segmentation_required": src.get("no_segmentation_required"),
                "mixed_language": src.get("mixed_language"),
                "spelling_or_ocr_issue": src.get("spelling_or_ocr_issue"),
                "insufficient_context": src.get("insufficient_context"),
                "audit_priority": rec.get("priority"),
                "audit_categories": categories,
                "audit_reasons": reasons,
                "review_status": "pending",
            }
        )

    # order: priority then item_id (same as audit)
    queue.sort(key=lambda r: (int(r.get("audit_priority") or 99), r["item_id"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, queue)

    # ensure no forbidden keys leaked
    forbidden_substrings = ("bpe", "unigram", "claude", "tokenizer")
    for row in queue:
        for k in row:
            kl = k.lower()
            if any(f in kl for f in forbidden_substrings):
                raise SystemExit(f"forbidden key in queue: {k}")

    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "n_items": len(queue),
        "item_ids": [r["item_id"] for r in queue],
        "audit_path": str(audit_path.relative_to(root)),
        "audit_sha256": sha256_file(audit_path),
        "full_annotations_path": str(full_path.relative_to(root)),
        "full_annotations_sha256": sha256_file(full_path),
        "full_annotations_immutable": True,
        "queue_path": str(out_path.relative_to(root)),
        "queue_sha256": sha256_file(out_path),
        "queue_fields": QUEUE_FIELDS,
        "excluded_from_queue": [
            "bpe_tokens",
            "unigram_tokens",
            "claude/AI annotations",
            "morphology holdout",
            "automatic correction suggestions",
        ],
        "category_counts": dict(sorted(category_counter.items(), key=lambda x: (-x[1], x[0]))),
        "reason_counts": dict(sorted(reason_counter.items(), key=lambda x: (-x[1], x[0]))),
        "decisions_path_target": (
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20_decisions.jsonl"
        ),
        "apply_script": "scripts/tokenizers/apply_morphology_human_review.py",
        "apply_executed": False,
        "original_annotations_modified": False,
        "morphology_holdout_accessed": False,
        "lm_test_evaluations": 0,
    }
    write_json(man_path, manifest)

    print(f"queue n={len(queue)} → {out_path.relative_to(root)}")
    print(f"manifest → {man_path.relative_to(root)}")
    print("category_counts:", json.dumps(manifest["category_counts"], ensure_ascii=False))
    print("original_annotations_modified: false")
    print("holdout_accessed: false")
    print("lm_test_evaluations: 0")


if __name__ == "__main__":
    main()
