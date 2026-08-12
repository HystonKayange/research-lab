#!/usr/bin/env python3
"""Apply completed human audit re-review decisions to a NEW full-200 file.

Does NOT overwrite the immutable pre-review snapshot:
  annotator_a_full_200.jsonl

Emits (when all 20 decisions are complete):
  annotator_a_full_200_reviewed_v0_1.jsonl

Rules:
- KEEP → leave item unchanged
- REVISE → set proposed_segmentation from revised_segmentation (must reconstruct)
- WHOLE → proposed_segmentation = surface; no_segmentation_required = true
- EXCLUDE → mark excluded / no_meaningful_segmentation; surface as WHOLE
- UNCERTAIN → uncertain=true; optional revised_segmentation if provided

Never loads holdout or LM test. Never invents decisions.

Usage (only after 20/20 decisions):
  python scripts/tokenizers/apply_morphology_human_review.py --require-complete
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import sha256_file, utc_now_iso, write_json, write_jsonl  # noqa: E402

TOOL_NAME = "apply_morphology_human_review"
TOOL_VERSION = "0.1.0"

VALID = {"KEEP", "REVISE", "WHOLE", "EXCLUDE", "UNCERTAIN"}


def refuse_forbidden(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked holdout path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def boundaries_csv(seg: str | None) -> str | None:
    if not seg or "+" not in seg:
        return None
    parts = seg.split("+")
    pos, cur = [], 0
    for p in parts[:-1]:
        cur += len(p)
        pos.append(str(cur))
    return ",".join(pos) if pos else None


def ensure_tags(tags: Any) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t) for t in tags]
    if isinstance(tags, str):
        return [t for t in tags.replace("|", ",").split(",") if t.strip()]
    return []


def add_tag(tags: list[str], tag: str) -> list[str]:
    if tag not in tags:
        tags = list(tags) + [tag]
    return tags


def apply_decision(row: dict[str, Any], dec: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(row)
    decision = str(dec["decision"]).upper()
    surface = str(out.get("surface_form") or "")
    note = dec.get("note")

    review_meta = {
        "human_review_decision": decision,
        "human_review_note": note,
        "human_review_updated_at": dec.get("updated_at"),
        "human_review_annotator_id": dec.get("annotator_id"),
        "pre_review_proposed_segmentation": out.get("proposed_segmentation"),
        "audit_review_v0_1": True,
    }

    if decision == "KEEP":
        out["human_review"] = {**review_meta, "changed": False}
        return out

    if decision == "REVISE":
        seg = dec.get("revised_segmentation") or dec.get("final_segmentation")
        if not seg:
            raise ValueError(f"{out['item_id']}: REVISE missing segmentation")
        if str(seg).replace("+", "") != surface:
            raise ValueError(
                f"{out['item_id']}: REVISE reconstruction fail "
                f"{seg!r} vs {surface!r}"
            )
        out["proposed_segmentation"] = seg
        out["boundary_positions"] = boundaries_csv(str(seg))
        out["no_segmentation_required"] = False
        out["uncertain"] = False
        out["human_review"] = {**review_meta, "changed": True}
        if note:
            prev = out.get("notes") or ""
            out["notes"] = (prev + " | " if prev else "") + f"audit_review REVISE: {note}"
        return out

    if decision == "WHOLE":
        out["proposed_segmentation"] = surface
        out["boundary_positions"] = None
        out["no_segmentation_required"] = True
        out["uncertain"] = False
        out["phenomenon_tags"] = add_tag(
            ensure_tags(out.get("phenomenon_tags")), "no_meaningful_segmentation"
        )
        out["human_review"] = {**review_meta, "changed": True}
        if note:
            prev = out.get("notes") or ""
            out["notes"] = (prev + " | " if prev else "") + f"audit_review WHOLE: {note}"
        return out

    if decision == "EXCLUDE":
        out["proposed_segmentation"] = surface
        out["boundary_positions"] = None
        out["no_segmentation_required"] = True
        out["mixed_language"] = True
        out["uncertain"] = False
        tags = ensure_tags(out.get("phenomenon_tags"))
        tags = add_tag(tags, "no_meaningful_segmentation")
        tags = add_tag(tags, "non_chichewa_or_mixed")
        out["phenomenon_tags"] = tags
        out["adjudication_status"] = "excluded_by_human_review"
        out["human_review"] = {
            **review_meta,
            "changed": True,
            "excluded": True,
        }
        if note:
            prev = out.get("notes") or ""
            out["notes"] = (prev + " | " if prev else "") + f"audit_review EXCLUDE: {note}"
        return out

    if decision == "UNCERTAIN":
        seg = dec.get("revised_segmentation") or dec.get("final_segmentation")
        if seg:
            if str(seg).replace("+", "") != surface:
                raise ValueError(
                    f"{out['item_id']}: UNCERTAIN reconstruction fail "
                    f"{seg!r} vs {surface!r}"
                )
            out["proposed_segmentation"] = seg
            out["boundary_positions"] = boundaries_csv(str(seg))
        out["uncertain"] = True
        tags = add_tag(ensure_tags(out.get("phenomenon_tags")), "unresolved_analysis")
        out["phenomenon_tags"] = tags
        out["human_review"] = {**review_meta, "changed": True}
        if note:
            prev = out.get("notes") or ""
            out["notes"] = (prev + " | " if prev else "") + f"audit_review UNCERTAIN: {note}"
        return out

    raise ValueError(f"unknown decision: {decision}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--full",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotations/"
            "annotator_a_full_200.jsonl"
        ),
        help="Immutable pre-review snapshot (never overwritten)",
    )
    p.add_argument(
        "--decisions",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20_decisions.jsonl"
        ),
    )
    p.add_argument(
        "--queue",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20.jsonl"
        ),
        help="Expected 20 item IDs",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/annotations/"
            "annotator_a_full_200_reviewed_v0_1.jsonl"
        ),
    )
    p.add_argument(
        "--report",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20_apply_report.json"
        ),
    )
    p.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit non-zero unless all 20 queue items have decisions",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only; do not write reviewed output",
    )
    args = p.parse_args()
    root = (args.repo_root or Path(__file__).resolve().parents[2]).resolve()

    def resolve(path: Path) -> Path:
        return (root / path).resolve() if not path.is_absolute() else path

    full_path = resolve(args.full)
    dec_path = resolve(args.decisions)
    queue_path = resolve(args.queue)
    out_path = resolve(args.out)
    report_path = resolve(args.report)

    for path in (full_path, dec_path, queue_path, out_path, report_path):
        refuse_forbidden(path)

    if out_path.resolve() == full_path.resolve():
        raise SystemExit("refusing to overwrite immutable full-200 path")

    queue = load_jsonl(queue_path)
    queue_ids = [str(r["item_id"]) for r in queue]
    if len(queue_ids) != 20:
        raise SystemExit(f"expected 20 queue items, found {len(queue_ids)}")

    decisions_list = load_jsonl(dec_path)
    decisions = {str(r["item_id"]): r for r in decisions_list}
    missing = [i for i in queue_ids if i not in decisions]
    extra = sorted(set(decisions) - set(queue_ids))

    if args.require_complete and missing:
        raise SystemExit(
            f"incomplete decisions: {len(missing)} missing "
            f"(e.g. {missing[:5]}). Not applying."
        )
    if missing and not args.dry_run:
        raise SystemExit(
            f"refusing partial apply ({len(missing)} missing). "
            "Use --require-complete after 20/20, or --dry-run."
        )

    for iid, d in decisions.items():
        if iid not in queue_ids:
            continue
        decision = str(d.get("decision") or "").upper()
        if decision not in VALID:
            raise SystemExit(f"{iid}: invalid decision {decision!r}")
        if decision in {"REVISE", "EXCLUDE", "UNCERTAIN"} and not (
            d.get("note") or ""
        ).strip():
            raise SystemExit(f"{iid}: note required for {decision}")

    full = load_jsonl(full_path)
    if len(full) != 200:
        raise SystemExit(f"expected 200 full annotations, found {len(full)}")
    full_by_id = {str(r["item_id"]): r for r in full}
    order = [str(r["item_id"]) for r in full]

    applied = []
    errors = []
    counts = {k: 0 for k in VALID}
    out_rows: list[dict[str, Any]] = []

    for iid in order:
        row = full_by_id[iid]
        if iid in decisions and iid in queue_ids:
            try:
                new_row = apply_decision(row, decisions[iid])
                counts[str(decisions[iid]["decision"]).upper()] += 1
                applied.append(iid)
                # reconstruction check for all non-empty segs
                seg = new_row.get("proposed_segmentation")
                surf = new_row.get("surface_form")
                if seg is not None and str(seg).replace("+", "") != surf:
                    errors.append(
                        {
                            "item_id": iid,
                            "error": "reconstruction_failure_after_apply",
                            "seg": seg,
                            "surface": surf,
                        }
                    )
                out_rows.append(new_row)
            except Exception as e:  # noqa: BLE001
                errors.append({"item_id": iid, "error": str(e)})
                out_rows.append(copy.deepcopy(row))
        else:
            out_rows.append(copy.deepcopy(row))

    if errors:
        raise SystemExit(f"apply errors ({len(errors)}): {errors[:3]}")

    # validate all recon
    recon_fail = []
    for r in out_rows:
        seg = r.get("proposed_segmentation")
        surf = r.get("surface_form")
        if seg is not None and str(seg).replace("+", "") != surf:
            recon_fail.append(r["item_id"])
    if recon_fail:
        raise SystemExit(f"reconstruction failures: {recon_fail}")

    report = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "immutable_full_path": str(full_path.relative_to(root)),
        "immutable_full_sha256": sha256_file(full_path),
        "decisions_path": str(dec_path.relative_to(root)),
        "decisions_sha256": sha256_file(dec_path) if dec_path.is_file() else None,
        "queue_ids": queue_ids,
        "n_decisions": len(decisions),
        "n_applied": len(applied),
        "missing_decisions": missing,
        "extra_decisions": extra,
        "decision_counts": counts,
        "dry_run": args.dry_run,
        "output_path": str(out_path.relative_to(root)),
        "output_written": False,
        "original_full_overwritten": False,
        "morphology_holdout_accessed": False,
        "lm_test_evaluations": 0,
        "status": "validated_ready" if not missing else "incomplete",
    }

    if args.dry_run:
        write_json(report_path, report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print("dry-run: no reviewed file written")
        return

    if missing:
        raise SystemExit("internal: missing decisions after checks")

    write_jsonl(out_path, out_rows)
    report["output_written"] = True
    report["output_sha256"] = sha256_file(out_path)
    report["n_output_rows"] = len(out_rows)
    report["status"] = "applied"
    write_json(report_path, report)

    # mark decisions as applied (optional side file note only — rewrite decisions with flag)
    # Do not mutate original decision meaning; append applied stamp via new write
    stamped = []
    for iid in queue_ids:
        d = dict(decisions[iid])
        d["applied_to_full_200"] = False  # still false: applied to NEW file only
        d["applied_to_reviewed_v0_1"] = True
        d["reviewed_output_path"] = str(out_path.relative_to(root))
        stamped.append(d)
    # keep decisions file content for non-queue keys if any
    for iid, d in decisions.items():
        if iid not in queue_ids:
            stamped.append(d)
    # preserve original decisions file; write stamp sidecar
    stamp_path = dec_path.with_name(dec_path.stem + "_applied_stamp.json")
    write_json(
        stamp_path,
        {
            "applied_at": utc_now_iso(),
            "reviewed_output": str(out_path.relative_to(root)),
            "item_ids": queue_ids,
        },
    )

    print(
        f"applied n={len(applied)}/20 → {out_path.relative_to(root)} "
        f"counts={counts} immutable_full_preserved=true"
    )


if __name__ == "__main__":
    main()
