#!/usr/bin/env python3
"""Deterministic run enumeration and status helpers for LM baseline matrix."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lm_common import load_json, sha256_file, utc_now_iso, write_json

TOKENIZERS = ("character", "bpe_8000", "unigram_8000")
TRACKS = ("architecture_matched", "parameter_matched")
BUDGETS = ("fixed_characters", "fixed_updates")
STATUSES = ("pending", "running", "completed", "failed", "blocked")


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    tokenizer: str
    seed: int
    track: str
    budget_policy: str
    phase: str = "final"
    budget_path_slug: str | None = None

    def relative_run_dir(self) -> str:
        slug = self.budget_path_slug or self.budget_policy
        return (
            f"{self.track}/{self.tokenizer}/seed_{self.seed}/"
            f"{self.phase}/{slug}"
        )


def budget_slug(matrix_cfg: dict[str, Any], budget_policy: str) -> str:
    slugs = matrix_cfg.get("budget_path_slugs") or {}
    return str(slugs.get(budget_policy, budget_policy))


def make_run_id(
    tokenizer: str,
    seed: int,
    track: str,
    budget_policy: str,
    *,
    phase: str = "final",
    matrix_id: str = "lm_baselines_v0_1_final_matrix",
    budget_path_slug: str | None = None,
) -> str:
    track_short = {
        "architecture_matched": "arch",
        "parameter_matched": "param",
    }.get(track, track)
    budget_short = {
        "fixed_characters": "chars",
        "fixed_updates": "updates",
        "fixed_characters_e30": "chars_e30",
        "fixed_updates_u4000": "updates_u4000",
    }.get(budget_path_slug or budget_policy, budget_path_slug or budget_policy)
    return f"{matrix_id}__{phase}__{track_short}__{tokenizer}__seed{seed}__{budget_short}"


def enumerate_full_runs(matrix_cfg: dict[str, Any]) -> list[RunSpec]:
    tokenizers = list(matrix_cfg.get("tokenizers") or TOKENIZERS)
    seeds = list(matrix_cfg.get("seeds") or [42, 1337, 2026])
    tracks = list(matrix_cfg.get("tracks") or TRACKS)
    budgets = list(matrix_cfg.get("budget_policies") or BUDGETS)
    matrix_id = str(matrix_cfg.get("matrix_id") or "lm_baselines_v0_1_final_matrix")
    runs: list[RunSpec] = []
    # Deterministic nested order
    for track in tracks:
        for tokenizer in tokenizers:
            for seed in seeds:
                for budget in budgets:
                    slug = budget_slug(matrix_cfg, budget)
                    rid = make_run_id(
                        tokenizer,
                        int(seed),
                        track,
                        budget,
                        phase="final",
                        matrix_id=matrix_id,
                        budget_path_slug=slug,
                    )
                    runs.append(
                        RunSpec(
                            run_id=rid,
                            tokenizer=tokenizer,
                            seed=int(seed),
                            track=track,
                            budget_policy=budget,
                            phase="final",
                            budget_path_slug=slug,
                        )
                    )
    return runs


def enumerate_canary_runs(matrix_cfg: dict[str, Any]) -> list[RunSpec]:
    """Systems canary only when matrix still defines a launchable canary.

    r2 matrices mark canary as systems_validation_only with canary_run_count=0;
    they do not re-launch the old 4M canary.
    """
    if int(matrix_cfg.get("canary_run_count", 1)) == 0:
        return []
    c = matrix_cfg["canary"]
    if c.get("role") == "systems_validation_only" and not c.get("launchable", False):
        return []
    matrix_id = str(matrix_cfg.get("matrix_id") or "lm_baselines_v0_1_final_matrix")
    slug = budget_slug(matrix_cfg, c["budget_policy"])
    rid = make_run_id(
        c["tokenizer"],
        int(c["seed"]),
        c["track"],
        c["budget_policy"],
        phase=c.get("phase", "final"),
        matrix_id=matrix_id,
        budget_path_slug=slug,
    )
    return [
        RunSpec(
            run_id=rid,
            tokenizer=c["tokenizer"],
            seed=int(c["seed"]),
            track=c["track"],
            budget_policy=c["budget_policy"],
            phase=c.get("phase", "final"),
            budget_path_slug=slug,
        )
    ]


def enumerate_stage(matrix_cfg: dict[str, Any], stage: str) -> list[RunSpec]:
    if stage == "canary":
        return enumerate_canary_runs(matrix_cfg)
    if stage == "full":
        return enumerate_full_runs(matrix_cfg)
    raise ValueError(f"Unknown stage: {stage}")


def run_dir_for(repo_root: Path, matrix_cfg: dict[str, Any], spec: RunSpec) -> Path:
    return repo_root / matrix_cfg["output_root"] / spec.relative_run_dir()


def load_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "matrix_id": None,
            "updated_at": None,
            "runs": {},
            "canary_accepted": False,
            "currently_running": None,
        }
    return load_json(path)


def save_status(path: Path, status: dict[str, Any]) -> None:
    status["updated_at"] = utc_now_iso()
    write_json(path, status)


def is_run_completed_valid(run_dir: Path) -> bool:
    man = run_dir / "manifest.json"
    lock = run_dir / "selection_lock.json"
    if not man.is_file() or not lock.is_file():
        return False
    try:
        m = load_json(man)
        s = load_json(lock)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    if m.get("status") == "failed":
        return False
    if not s.get("selected_checkpoint"):
        return False
    ckpt = run_dir / s["selected_checkpoint"]
    if not ckpt.is_file():
        return False
    exp = s.get("checkpoint_sha256")
    if exp and sha256_file(ckpt) != exp:
        return False
    return True


def canary_acceptance_valid(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        a = load_json(path)
    except (OSError, ValueError):
        return False
    return bool(a.get("accepted") is True)


class FileLock:
    """Simple exclusive lock using O_EXCL create."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(
                self._fd,
                f"pid={os.getpid()}\ncreated={utc_now_iso()}\n".encode("utf-8"),
            )
            return True
        except FileExistsError:
            return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> "FileLock":
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock: {self.path}")
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()


def filter_specs(
    specs: list[RunSpec],
    *,
    tokenizer: str | None = None,
    seed: int | None = None,
    track: str | None = None,
    budget_policy: str | None = None,
) -> list[RunSpec]:
    out = []
    for s in specs:
        if tokenizer and s.tokenizer != tokenizer:
            continue
        if seed is not None and s.seed != seed:
            continue
        if track and s.track != track:
            continue
        if budget_policy and s.budget_policy != budget_policy:
            continue
        out.append(s)
    return out


def execution_plan_markdown(
    matrix_cfg: dict[str, Any],
    stage: str,
    specs: list[RunSpec],
    *,
    canary_ok: bool,
) -> str:
    lines = [
        f"# LM baselines v0.1 execution plan — stage `{stage}`",
        "",
        f"_Generated at {utc_now_iso()}_",
        "",
        f"- Matrix ID: `{matrix_cfg.get('matrix_id')}`",
        f"- Expected full runs: **{matrix_cfg.get('expected_run_count', 36)}**",
        f"- This stage run count: **{len(specs)}**",
        f"- Canary accepted: **{canary_ok}**",
        "",
        "## Enumerated runs",
        "",
        "| # | run_id | tokenizer | seed | track | budget |",
        "|--:|--------|-----------|-----:|-------|--------|",
    ]
    for i, s in enumerate(specs, 1):
        lines.append(
            f"| {i} | `{s.run_id}` | {s.tokenizer} | {s.seed} | {s.track} | {s.budget_policy} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Dry-run does not train.",
            "- Full stage blocked until canary acceptance manifest exists.",
            "- Pilot results are excluded from final aggregation.",
            "",
        ]
    )
    return "\n".join(lines)
