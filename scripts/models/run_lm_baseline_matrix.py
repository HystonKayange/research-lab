#!/usr/bin/env python3
"""Resumable LM baseline matrix launcher (canary → full).

Does not evaluate test. Full stage blocked until canary acceptance.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import load_json, sha256_file, utc_now_iso, write_json, write_text  # noqa: E402
from matrix_common import (  # noqa: E402
    FileLock,
    canary_acceptance_valid,
    enumerate_stage,
    execution_plan_markdown,
    filter_specs,
    is_run_completed_valid,
    load_status,
    run_dir_for,
    save_status,
)

TOOL_NAME = "run_lm_baseline_matrix"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LM baseline matrix launcher.")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--stage",
        choices=["canary", "full"],
        default=None,
        help="canary or full (not required for --status/--dry-run with stage)",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--resume", action="store_true", help="Alias for continuing full/canary")
    p.add_argument("--yes", action="store_true", help="Pass --yes to train_lm_baseline")
    p.add_argument("--tokenizer", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--track", default=None)
    p.add_argument("--budget-policy", default=None)
    p.add_argument(
        "--accept-canary",
        action="store_true",
        help="Write canary acceptance after validating canary run (no training).",
    )
    p.add_argument(
        "--mark-canary-failed",
        action="store_true",
        help="Record canary failure and keep full blocked.",
    )
    return p.parse_args(argv)


def train_command(
    repo_root: Path,
    parent_config: str,
    matrix_config: Path,
    spec,
    *,
    yes: bool,
) -> list[str]:
    py = sys.executable
    cmd = [
        py,
        str(repo_root / "scripts/models/train_lm_baseline.py"),
        "--config",
        parent_config,
        "--matrix-config",
        str(matrix_config),
        "--phase",
        spec.phase,
        "--tokenizer",
        spec.tokenizer,
        "--seed",
        str(spec.seed),
        "--track",
        spec.track,
        "--budget-policy",
        spec.budget_policy,
    ]
    if yes:
        cmd.append("--yes")
    return cmd


def status_summary(status: dict[str, Any], specs: list) -> dict[str, Any]:
    counts = {s: 0 for s in ("pending", "running", "completed", "failed", "blocked")}
    for sp in specs:
        st = (status.get("runs") or {}).get(sp.run_id, {}).get("status", "pending")
        counts[st] = counts.get(st, 0) + 1
    return {
        "counts": counts,
        "currently_running": status.get("currently_running"),
        "canary_accepted": status.get("canary_accepted"),
        "n_planned": len(specs),
    }


def write_execution_plan(
    repo_root: Path, matrix: dict[str, Any], stage: str, specs: list, canary_ok: bool
) -> Path:
    md = execution_plan_markdown(matrix, stage, specs, canary_ok=canary_ok)
    path = repo_root / matrix["execution_plan_path"]
    write_text(path, md)
    return path


def accept_canary(repo_root: Path, matrix: dict[str, Any]) -> int:
    from inspect_lm_run import inspect_run  # local

    specs = enumerate_stage(matrix, "canary")
    if len(specs) != 1:
        print("error: canary must be exactly one run", file=sys.stderr)
        return 1
    spec = specs[0]
    run_dir = run_dir_for(repo_root, matrix, spec)
    report = inspect_run(run_dir, matrix_cfg=matrix, is_canary=True)
    acc_path = repo_root / matrix["canary_acceptance_path"]
    if not report.get("canary_acceptance_criteria_passed"):
        write_json(
            acc_path,
            {
                "accepted": False,
                "run_id": spec.run_id,
                "inspected_at": utc_now_iso(),
                "report": report,
            },
        )
        print("error: canary acceptance criteria NOT met", file=sys.stderr)
        return 1
    write_json(
        acc_path,
        {
            "accepted": True,
            "run_id": spec.run_id,
            "accepted_at": utc_now_iso(),
            "report_summary": {
                k: report.get(k)
                for k in (
                    "status",
                    "validation_bpc",
                    "validation_bpb",
                    "characters_processed",
                    "character_overshoot",
                    "optimizer_steps",
                    "runtime_s",
                    "peak_vram_gb",
                    "checkpoint_reload_ok",
                    "nan_or_inf_detected",
                )
            },
            "statement": "Canary accepted; --stage full may proceed.",
        },
    )
    # also write canary report
    write_text(
        repo_root / matrix["canary_report_path"],
        "# Canary report\n\n"
        f"Accepted: **true**\n\n```json\n{json.dumps(report, indent=2)}\n```\n",
    )
    print(f"Canary ACCEPTED → {acc_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    cfg_path = args.config if args.config.is_absolute() else root / args.config
    matrix = load_json(cfg_path)
    status_path = root / matrix["status_path"]
    status = load_status(status_path)
    status["matrix_id"] = matrix.get("matrix_id")
    canary_ok = canary_acceptance_valid(root / matrix["canary_acceptance_path"])
    status["canary_accepted"] = canary_ok

    if args.accept_canary:
        return accept_canary(root, matrix)
    if args.mark_canary_failed:
        write_json(
            root / matrix["canary_acceptance_path"],
            {"accepted": False, "marked_at": utc_now_iso()},
        )
        print("Canary marked failed; full remains blocked.")
        return 0

    stage = args.stage
    if args.status and stage is None:
        stage = "full"
    if stage is None:
        print("error: --stage required unless --status/--accept-canary", file=sys.stderr)
        return 1

    if stage == "full" and matrix["launcher"].get("require_canary_acceptance_for_full", True):
        # r2: systems canary may already be accepted under r1 path; still required
        if not canary_ok and not args.dry_run and not args.status:
            print(
                "error: full stage blocked — canary not accepted. "
                f"Missing/invalid {matrix['canary_acceptance_path']}",
                file=sys.stderr,
            )
            return 2
    if stage == "canary" and int(matrix.get("canary_run_count", 1)) == 0:
        print(
            "note: this matrix version has canary_run_count=0 "
            "(systems canary already accepted under prior version). "
            "Use --stage full for scientific runs.",
            file=sys.stderr,
        )
        if not args.dry_run and not args.status:
            return 0

    specs = enumerate_stage(matrix, stage)
    specs = filter_specs(
        specs,
        tokenizer=args.tokenizer,
        seed=args.seed,
        track=args.track,
        budget_policy=args.budget_policy,
    )
    plan_path = write_execution_plan(root, matrix, stage, specs, canary_ok)

    if args.status:
        # refresh completion from disk
        for sp in enumerate_stage(matrix, "full"):
            rd = run_dir_for(root, matrix, sp)
            entry = status.setdefault("runs", {}).setdefault(sp.run_id, {})
            if is_run_completed_valid(rd):
                entry["status"] = "completed"
                entry["run_dir"] = str(rd.relative_to(root))
            elif (rd / "manifest.json").is_file():
                m = load_json(rd / "manifest.json")
                entry["status"] = m.get("status", "failed")
            else:
                entry.setdefault("status", "pending")
        save_status(status_path, status)
        summ = status_summary(status, enumerate_stage(matrix, "full"))
        print(json.dumps(summ, indent=2))
        # remaining estimate
        completed = summ["counts"].get("completed", 0)
        pending = summ["counts"].get("pending", 0) + summ["counts"].get("blocked", 0)
        # use canary runtime if present
        est = status.get("canary_runtime_s")
        if est and pending:
            print(f"estimated_remaining_s_if_canary_like: {est * pending:.0f}")
        print(f"execution_plan: {plan_path}")
        return 0

    if args.dry_run:
        print(f"DRY-RUN stage={stage} n_runs={len(specs)}")
        for s in specs:
            print(f"  {s.run_id}")
            print(
                "   ",
                " ".join(
                    train_command(
                        root,
                        matrix.get("parent_config", "configs/models/lm_baselines_v0_1.json"),
                        cfg_path,
                        s,
                        yes=True,
                    )
                ),
            )
        print(f"Wrote plan: {plan_path}")
        print("No training launched.")
        return 0

    parent = matrix.get("parent_config", "configs/models/lm_baselines_v0_1.json")
    consecutive_fail = 0
    max_fail = int(matrix["launcher"].get("max_consecutive_systemic_failures", 3))

    for spec in specs:
        rd = run_dir_for(root, matrix, spec)
        if is_run_completed_valid(rd):
            status.setdefault("runs", {})[spec.run_id] = {
                "status": "completed",
                "run_dir": str(rd.relative_to(root)),
                "skipped_resume": True,
            }
            save_status(status_path, status)
            print(f"skip completed: {spec.run_id}")
            continue

        # Lock beside the run dir, never inside it — an in-dir lock would make
        # train_lm_baseline refuse the non-empty run directory mid-launch.
        lock_name = matrix["launcher"].get("lock_file_name", ".run.lock")
        lock_path = rd.parent / f"{rd.name}{lock_name if lock_name.startswith('.') else '.' + lock_name}"
        lock = FileLock(lock_path)
        if not lock.acquire():
            print(f"blocked concurrent: {spec.run_id}", file=sys.stderr)
            status.setdefault("runs", {})[spec.run_id] = {"status": "blocked"}
            save_status(status_path, status)
            continue

        status["currently_running"] = spec.run_id
        status.setdefault("runs", {})[spec.run_id] = {
            "status": "running",
            "started_at": utc_now_iso(),
            "run_dir": str(rd.relative_to(root)),
        }
        save_status(status_path, status)

        cmd = train_command(root, parent, cfg_path, spec, yes=bool(args.yes))
        print("Launching:", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, cwd=str(root), check=False)
            code = proc.returncode
        except KeyboardInterrupt:
            lock.release()
            status["runs"][spec.run_id] = {"status": "failed", "error": "interrupted"}
            status["currently_running"] = None
            save_status(status_path, status)
            raise
        finally:
            lock.release()

        if code == 0 and is_run_completed_valid(rd):
            consecutive_fail = 0
            man = load_json(rd / "manifest.json")
            status["runs"][spec.run_id] = {
                "status": "completed",
                "finished_at": utc_now_iso(),
                "run_dir": str(rd.relative_to(root)),
                "validation_bpc": (man.get("best_checkpoint") or {}).get(
                    "validation_bpc"
                ),
                "runtime_s": (man.get("runtime") or {}).get("wall_clock_s"),
            }
            if stage == "canary":
                status["canary_runtime_s"] = (man.get("runtime") or {}).get(
                    "wall_clock_s"
                )
            status["currently_running"] = None
            save_status(status_path, status)
            print(f"completed: {spec.run_id}")
        else:
            consecutive_fail += 1
            status["runs"][spec.run_id] = {
                "status": "failed",
                "finished_at": utc_now_iso(),
                "exit_code": code,
                "run_dir": str(rd.relative_to(root)),
            }
            status["currently_running"] = None
            save_status(status_path, status)
            print(f"failed: {spec.run_id} code={code}", file=sys.stderr)
            if not matrix["launcher"].get("allow_isolated_seed_failure", True):
                return 1
            if consecutive_fail >= max_fail:
                print(
                    f"error: {consecutive_fail} consecutive failures — stopping matrix",
                    file=sys.stderr,
                )
                return 1

    print(f"Stage {stage} finished. Plan: {plan_path}")
    if stage == "canary":
        print(
            "Next: inspect canary, then:\n"
            f"  {sys.executable} scripts/models/run_lm_baseline_matrix.py "
            f"--config {cfg_path} --accept-canary"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
