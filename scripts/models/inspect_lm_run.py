#!/usr/bin/env python3
"""Inspect a completed LM run / canary without launching training."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import load_json  # noqa: E402
from matrix_common import (  # noqa: E402
    enumerate_canary_runs,
    enumerate_full_runs,
    run_dir_for,
)


def inspect_run(
    run_dir: Path,
    *,
    matrix_cfg: dict[str, Any] | None = None,
    is_canary: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "run_dir": str(run_dir),
        "exists": run_dir.is_dir(),
        "canary_acceptance_criteria_passed": False,
    }
    if not run_dir.is_dir():
        out["error"] = "run_dir missing"
        return out

    man_path = run_dir / "manifest.json"
    if not man_path.is_file():
        out["error"] = "manifest.json missing"
        return out
    man = load_json(man_path)
    sel_path = run_dir / "selection_lock.json"
    sel = load_json(sel_path) if sel_path.is_file() else {}

    best = man.get("best_checkpoint") or {}
    exp = man.get("exposure") or {}
    rt = man.get("runtime") or {}
    reload_v = man.get("checkpoint_reload_verification") or {}
    initial = man.get("initial_validation") or {}

    out.update(
        {
            "run_id": man.get("run_id"),
            "status": man.get("status"),
            "tokenizer_id": man.get("tokenizer_id"),
            "seed": man.get("seed"),
            "track": man.get("track"),
            "budget_policy": man.get("budget_policy"),
            "validation_bpc": best.get("validation_bpc"),
            "validation_bpb": best.get("validation_bpb"),
            "characters_processed": exp.get("characters_processed"),
            "character_target": exp.get("character_target"),
            "character_overshoot": exp.get("character_overshoot"),
            "optimizer_steps": exp.get("optimizer_steps"),
            "tokens_processed": exp.get("tokens_processed"),
            "runtime_s": rt.get("wall_clock_s"),
            "peak_vram_gb": rt.get("peak_gpu_memory_gb"),
            "tokens_per_second": rt.get("tokens_per_second"),
            "characters_per_second": rt.get("characters_per_second"),
            "best_checkpoint": sel.get("selected_checkpoint") or "best.pt",
            "checkpoint_sha256": sel.get("checkpoint_sha256"),
            "checkpoint_reload_ok": reload_v.get("ok"),
            "reloaded_validation_bpc": reload_v.get("reloaded_validation_bpc"),
            "nan_or_inf_detected": man.get("nan_or_inf_detected"),
            "validation_improved_from_initial": man.get(
                "validation_improved_from_initial"
            ),
            "initial_validation_bpc": initial.get("bits_per_character"),
            "test_evaluated_during_training": man.get(
                "test_evaluated_during_training"
            ),
            "split_checksums_ok": bool(
                (man.get("split_verification") or {}).get("frozen")
            ),
            "parameter_counts": man.get("parameter_counts"),
            "selection_lock_present": sel_path.is_file(),
        }
    )

    # Character exposure tolerance
    tol = 0.02
    if matrix_cfg and man.get("budget_policy") == "fixed_characters":
        tol = float(
            (matrix_cfg.get("budgets") or {})
            .get("fixed_characters", {})
            .get("character_overshoot_tolerance", 0.02)
        )
    target = exp.get("character_target")
    processed = exp.get("characters_processed")
    exposure_ok = False
    if target and processed is not None:
        # must reach target; overshoot within tolerance
        exposure_ok = processed >= target * (1.0 - 1e-9) and processed <= target * (
            1.0 + tol
        )
    out["character_exposure_within_tolerance"] = exposure_ok

    criteria = {
        "training_completed": man.get("status") == "completed",
        "no_nan_inf": not bool(man.get("nan_or_inf_detected")),
        "character_exposure_ok": exposure_ok
        if man.get("budget_policy") == "fixed_characters"
        else True,
        "validation_improved": bool(man.get("validation_improved_from_initial")),
        "checkpoint_reload_ok": bool(reload_v.get("ok")),
        "checksums_ok": bool((man.get("split_verification") or {}).get("frozen"))
        and bool(man.get("tokenizer_verification")),
        "manifest_complete": all(
            k in man
            for k in (
                "run_id",
                "exposure",
                "best_checkpoint",
                "runtime",
                "parameter_counts",
                "selection_lock",
            )
        ),
        "selection_lock_present": sel_path.is_file(),
        "test_not_used": man.get("test_evaluated_during_training") is False,
    }
    out["criteria"] = criteria
    out["canary_acceptance_criteria_passed"] = all(criteria.values())
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect LM run / canary.")
    p.add_argument("--run-id", default=None)
    p.add_argument("--run-dir", type=Path, default=None)
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    cfg_path = args.config if args.config.is_absolute() else root / args.config
    matrix = load_json(cfg_path)

    run_dir = None
    is_canary = False
    if args.run_dir:
        run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    elif args.run_id:
        for sp in enumerate_full_runs(matrix) + enumerate_canary_runs(matrix):
            if sp.run_id == args.run_id:
                run_dir = run_dir_for(root, matrix, sp)
                is_canary = sp.run_id == enumerate_canary_runs(matrix)[0].run_id
                break
        if run_dir is None:
            print(f"error: unknown run_id {args.run_id}", file=sys.stderr)
            return 1
    else:
        # default: canary
        sp = enumerate_canary_runs(matrix)[0]
        run_dir = run_dir_for(root, matrix, sp)
        is_canary = True
        print(f"Using canary run_id={sp.run_id}")

    report = inspect_run(run_dir, matrix_cfg=matrix, is_canary=is_canary)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"run_id: {report.get('run_id')}")
        print(f"status: {report.get('status')}")
        print(f"val BPC: {report.get('validation_bpc')}")
        print(f"val BPB: {report.get('validation_bpb')}")
        print(
            f"chars: {report.get('characters_processed')} "
            f"(target {report.get('character_target')}, "
            f"overshoot {report.get('character_overshoot')})"
        )
        print(f"steps: {report.get('optimizer_steps')}")
        print(f"runtime_s: {report.get('runtime_s')}")
        print(f"peak_vram_gb: {report.get('peak_vram_gb')}")
        print(f"reload_ok: {report.get('checkpoint_reload_ok')}")
        print(f"nan_inf: {report.get('nan_or_inf_detected')}")
        print(f"criteria: {json.dumps(report.get('criteria'), indent=2)}")
        print(
            f"canary_acceptance_criteria_passed: "
            f"{report.get('canary_acceptance_criteria_passed')}"
        )
    return 0 if report.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
