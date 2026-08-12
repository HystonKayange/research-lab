#!/usr/bin/env python3
"""Migrate LM matrix status from r1 (4M canary) to r2 (30-epoch scientific matrix).

Does not train. Creates timestamped backups. Does not delete canary/calibration.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from matrix_common import enumerate_full_runs, load_json  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--matrix-config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix_r2.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--old-status",
        type=Path,
        default=Path("data/metadata/lm_baselines_v0_1_matrix_status.json"),
    )
    args = p.parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    matrix = load_json(
        args.matrix_config
        if args.matrix_config.is_absolute()
        else root / args.matrix_config
    )
    old_path = args.old_status if args.old_status.is_absolute() else root / args.old_status
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if old_path.is_file():
        bak = old_path.with_name(old_path.stem + f".pre_r2_migration_{ts}.json")
        shutil.copy2(old_path, bak)
        old = load_json(old_path)
        print(f"Backed up old status → {bak}")
    else:
        old = {}
        bak = None

    # Preserve canary acceptance as systems-only pointer (do not delete acceptance file)
    canary_acc_path = root / matrix["canary_acceptance_path"]
    canary_ok = canary_acc_path.is_file()
    if canary_ok:
        acc_bak = canary_acc_path.with_name(
            canary_acc_path.stem + f".pre_r2_{ts}.json"
        )
        if not acc_bak.is_file():
            shutil.copy2(canary_acc_path, acc_bak)
            print(f"Backed up canary acceptance → {acc_bak}")

    runs = {}
    for spec in enumerate_full_runs(matrix):
        runs[spec.run_id] = {
            "status": "pending",
            "matrix_id": matrix["matrix_id"],
            "tokenizer": spec.tokenizer,
            "seed": spec.seed,
            "track": spec.track,
            "budget_policy": spec.budget_policy,
            "budget_path_slug": spec.budget_path_slug,
            "run_dir": str(
                (root / matrix["output_root"] / spec.relative_run_dir()).relative_to(root)
            ),
        }

    new_status = {
        "matrix_id": matrix["matrix_id"],
        "supersedes": matrix.get("supersedes"),
        "updated_at": utc_now(),
        "canary_accepted": canary_ok,
        "canary_role": "systems_validation_only",
        "canary_excluded_from_final_statistics": True,
        "calibration_excluded_from_final_statistics": True,
        "currently_running": None,
        "scientific_run_count": len(runs),
        "completed_scientific_runs": 0,
        "runs": runs,
        "artifacts": {
            "accepted_systems_canary": matrix.get("canary"),
            "budget_calibration": matrix.get("calibration"),
        },
        "migration": {
            "at": utc_now(),
            "from_status": str(old_path.relative_to(root)) if old_path.is_file() else None,
            "from_status_backup": str(bak.relative_to(root)) if bak else None,
            "old_completed_not_carried_as_scientific": True,
            "reason": (
                "r2 calibrated fixed-character budget 30×4623799=138713970; "
                "old 4M canary is systems validation only"
            ),
            "old_status_snapshot_counts": {
                k: sum(1 for r in (old.get("runs") or {}).values() if r.get("status") == k)
                for k in ("pending", "completed", "failed", "running", "blocked")
            },
        },
        "failure_history": list(old.get("failure_history") or []),
    }

    out = root / matrix["status_path"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(new_status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote r2 status → {out}")
    print(f"scientific runs pending: {len(runs)}")
    print(f"canary_accepted (systems): {canary_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
