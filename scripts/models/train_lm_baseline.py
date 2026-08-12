#!/usr/bin/env python3
"""Train a controlled decoder-only LM baseline for one tokenizer × seed × track × budget.

Budgets: fixed_characters | fixed_updates.
Checkpoint selection: validation BPC only. Test never used during training.
Default: print plan and require confirmation unless --yes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    bits_per_byte,
    bits_per_character,
    build_gpt,
    effective_epochs,
    ensure_run_dir_free,
    env_metadata,
    frozen_train_character_count,
    load_json,
    load_tokenizer,
    pack_lines_to_sequences,
    resolve_arch,
    sequences_to_tensors,
    sha256_file,
    token_perplexity_from_nll,
    utc_now_iso,
    verify_frozen_split,
    verify_tokenizer_artifacts,
    write_json,
    write_text,
)
from matrix_common import make_run_id  # noqa: E402

TOOL_NAME = "train_lm_baseline"
TOOL_VERSION = "0.3.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train LM baseline (one run).")
    p.add_argument("--config", type=Path, default=Path("configs/models/lm_baselines_v0_1.json"))
    p.add_argument(
        "--matrix-config",
        type=Path,
        default=None,
        help="Optional final matrix config for budget/schedule overrides",
    )
    p.add_argument(
        "--calibration-config",
        type=Path,
        default=None,
        help="Budget-calibration config (sets phase=calibration defaults)",
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--phase",
        choices=["pilot", "final", "calibration"],
        default=None,
        help="Required unless --calibration-config is provided",
    )
    p.add_argument(
        "--tokenizer",
        choices=["character", "bpe_8000", "unigram_8000"],
        default=None,
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--track",
        choices=["architecture_matched", "parameter_matched"],
        default=None,
    )
    p.add_argument(
        "--budget-policy",
        choices=["fixed_characters", "fixed_updates"],
        default=None,
    )
    p.add_argument("--device", default=None, help="cuda|cpu (default: auto)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--cpu-smoke", action="store_true")
    p.add_argument("--yes", action="store_true", help="Skip interactive confirmation")
    p.add_argument(
        "--dry-run-plan",
        action="store_true",
        help="Print resolved plan and exit without training",
    )
    return p.parse_args(argv)


def apply_calibration_config(
    args: argparse.Namespace, calib: dict[str, Any]
) -> argparse.Namespace:
    """Fill args from calibration config when not explicitly provided."""
    run = calib.get("run") or {}
    if args.phase is None:
        args.phase = calib.get("phase", "calibration")
    if args.tokenizer is None:
        args.tokenizer = run.get("tokenizer")
    if args.seed is None:
        args.seed = int(run.get("seed", 42))
    if args.track is None:
        args.track = run.get("track", "architecture_matched")
    if args.budget_policy is None:
        args.budget_policy = run.get("budget_policy", "fixed_characters")
    return args


def set_seed(seed: int) -> None:
    import random

    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate_split(
    model,
    sequences: list[list[int]],
    *,
    pad_id: int,
    device,
    batch_size: int,
    source_text: str,
    amp: bool,
    dtype,
) -> dict[str, Any]:
    import torch

    model.eval()
    total_nll = 0.0
    total_tok = 0
    n_chars = len(source_text)
    n_bytes = len(source_text.encode("utf-8"))
    if not sequences:
        return {
            "bits_per_character": None,
            "bits_per_byte": None,
            "token_nll_nats": 0.0,
            "n_pred_tokens": 0,
            "token_perplexity_not_cross_comparable": None,
            "n_chars": n_chars,
            "n_bytes": n_bytes,
            "nan_detected": False,
        }

    x_all, y_all = sequences_to_tensors(sequences, pad_id)
    nan_detected = False
    with torch.no_grad():
        for i in range(0, x_all.size(0), batch_size):
            xb = x_all[i : i + batch_size].to(device)
            yb = y_all[i : i + batch_size].to(device)
            if amp and device.type == "cuda":
                with torch.autocast(device_type="cuda", dtype=dtype):
                    _logits, _loss, nll_sum, n_tok = model(xb, yb, pad_id=pad_id)
            else:
                _logits, _loss, nll_sum, n_tok = model(xb, yb, pad_id=pad_id)
            v = float(nll_sum.item())
            if math.isnan(v) or math.isinf(v):
                nan_detected = True
            total_nll += v
            total_tok += int(n_tok)

    return {
        "bits_per_character": bits_per_character(total_nll, n_chars),
        "bits_per_byte": bits_per_byte(total_nll, n_bytes),
        "token_nll_nats": total_nll,
        "n_pred_tokens": total_tok,
        "token_perplexity_not_cross_comparable": token_perplexity_from_nll(
            total_nll, total_tok
        ),
        "n_chars": n_chars,
        "n_bytes": n_bytes,
        "mean_token_nll_nats": total_nll / max(total_tok, 1),
        "nan_detected": nan_detected,
    }


def merge_matrix_budget(config: dict[str, Any], matrix: dict[str, Any] | None) -> dict[str, Any]:
    """Return config with matrix budget/training overrides when provided."""
    if not matrix:
        return config
    out = json.loads(json.dumps(config))
    out["matrix_id"] = matrix.get("matrix_id")
    out["budgets"] = matrix.get("budgets")
    if "training" in matrix:
        out["training"] = {**out.get("training", {}), **matrix["training"]}
    if "architecture_matched" in matrix:
        out["architecture_matched"] = matrix["architecture_matched"]
    if "parameter_matched" in matrix:
        # keep structure expected by resolve_arch
        pm = matrix["parameter_matched"]
        out["parameter_matched"] = {
            "tolerance_fraction": pm.get("tolerance_fraction", 0.05),
            "overrides": pm["overrides"],
            "context_length": pm.get("context_length", 256),
            "dropout": pm.get("dropout", 0.1),
            "pre_ln": pm.get("pre_ln", True),
            "tie_embeddings": pm.get("tie_embeddings", True),
            "positional_encoding": pm.get("positional_encoding", "learned"),
        }
    return out


def resolve_budget(
    config: dict[str, Any],
    phase: str,
    budget_policy: str,
    matrix: dict[str, Any] | None,
    calibration: dict[str, Any] | None = None,
    *,
    frozen_chars: int | None = None,
) -> dict[str, Any]:
    if calibration and phase == "calibration":
        bsrc = calibration.get("budget") or {}
        es = calibration.get("early_stopping") or {}
        corpus = calibration.get("corpus") or {}
        denom = int(
            corpus.get("frozen_training_corpus_character_count")
            or frozen_chars
            or 0
        )
        epoch_ckpts = list(bsrc.get("validation_effective_epoch_checkpoints") or [])
        char_ckpts = []
        if denom > 0:
            char_ckpts = [int(round(e * denom)) for e in epoch_ckpts]
        return {
            "policy": "fixed_characters",
            "train_characters": int(bsrc.get("train_characters_max", 185_000_000)),
            "max_optimizer_steps_cap": int(bsrc.get("max_optimizer_steps_cap", 500_000)),
            "validation_character_checkpoints": char_ckpts,
            "validation_effective_epoch_checkpoints": epoch_ckpts,
            "character_overshoot_tolerance": float(
                bsrc.get("character_overshoot_tolerance", 0.02)
            ),
            "frozen_training_corpus_character_count": denom,
            "early_stopping": es,
            "stop_policy": bsrc.get("stop_policy", "stop_when_characters_ge_max_or_early_stop"),
        }
    if matrix and "budgets" in matrix and phase == "final":
        b = dict(matrix["budgets"][budget_policy])
        b["policy"] = budget_policy
        denom = int(
            b.get("frozen_training_corpus_character_count")
            or frozen_chars
            or 0
        )
        if frozen_chars:
            b["frozen_training_corpus_character_count"] = frozen_chars
            denom = frozen_chars
        # Prefer exact integer character checkpoints when epoch list provided
        epoch_ckpts = list(b.get("validation_effective_epoch_checkpoints") or [])
        if epoch_ckpts and denom > 0:
            # exact integer multiplication; use configured list if present and matching
            derived = [int(e) * int(denom) for e in epoch_ckpts]
            configured = list(b.get("validation_character_checkpoints") or [])
            if configured and configured != derived:
                # Prefer exact derived from integer epochs × corpus chars
                b["validation_character_checkpoints"] = derived
                b["validation_character_checkpoints_note"] = (
                    "Recomputed as epoch × frozen_training_corpus_character_count "
                    "for exact integer checkpoints"
                )
            elif not configured:
                b["validation_character_checkpoints"] = derived
        # Final scientific runs: do not use patience early-stop to shorten exposure
        es = b.get("early_stopping")
        if es is None:
            b["early_stopping"] = {"enabled": False}
        return b
    # pilot / legacy parent config
    base = dict(config.get("budget", {}).get(phase, {}))
    if budget_policy == "fixed_characters":
        return {
            "policy": "fixed_characters",
            "train_characters": int(base.get("train_characters", 200000)),
            "max_optimizer_steps_cap": int(base.get("max_optimizer_steps", 400)),
            "validation_character_checkpoints": [],
            "character_overshoot_tolerance": 0.05,
            "frozen_training_corpus_character_count": frozen_chars,
            "early_stopping": {"enabled": False},
        }
    return {
        "policy": "fixed_updates",
        "optimizer_updates": int(base.get("max_optimizer_steps", 400)),
        "validation_update_checkpoints": [],
        "frozen_training_corpus_character_count": frozen_chars,
        "early_stopping": {"enabled": False},
    }


def confirm_or_abort(plan: dict[str, Any], *, yes: bool) -> bool:
    print("=== RESOLVED TRAINING PLAN (no test access) ===")
    for k in (
        "run_id",
        "tokenizer",
        "seed",
        "track",
        "budget_policy",
        "phase",
        "architecture",
        "parameter_count_estimate_note",
        "budget",
        "output_dir",
        "device",
        "exists",
        "test_set_inaccessible_during_training",
    ):
        print(f"  {k}: {plan.get(k)}")
    if yes:
        return True
    if not sys.stdin.isatty():
        print(
            "error: non-interactive session requires --yes to start training",
            file=sys.stderr,
        )
        return False
    ans = input("Start this training run? [y/N] ").strip().lower()
    return ans in ("y", "yes")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    matrix = None
    matrix_path = None
    calibration = None
    calibration_path = None
    if args.calibration_config is not None:
        calibration_path = (
            args.calibration_config
            if args.calibration_config.is_absolute()
            else root / args.calibration_config
        )
        calibration = load_json(calibration_path)
        args = apply_calibration_config(args, calibration)
        # Architecture from calibration if provided
        if "architecture" in calibration:
            config = json.loads(json.dumps(config))
            config["architecture_matched"] = {
                **config.get("architecture_matched", {}),
                **calibration["architecture"],
            }
        if "training" in calibration:
            config = json.loads(json.dumps(config))
            config["training"] = {**config.get("training", {}), **calibration["training"]}
    if args.matrix_config is not None:
        matrix_path = (
            args.matrix_config
            if args.matrix_config.is_absolute()
            else root / args.matrix_config
        )
        matrix = load_json(matrix_path)
        config = merge_matrix_budget(config, matrix)

    if args.phase is None or args.tokenizer is None or args.seed is None:
        print(
            "error: --phase, --tokenizer, and --seed are required "
            "(or provide --calibration-config)",
            file=sys.stderr,
        )
        return 1
    if args.track is None:
        args.track = "architecture_matched"
    if args.budget_policy is None:
        args.budget_policy = "fixed_characters"

    try:
        import torch
    except ImportError:
        print(
            "error: torch is required. Install with:\n"
            "  .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu128",
            file=sys.stderr,
        )
        return 2

    split_root = root / config["split_root"]
    try:
        split_info = verify_frozen_split(split_root)
        tok_cfg = config["tokenizers"][args.tokenizer]
        tok_info = verify_tokenizer_artifacts(tok_cfg, root)
    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"error: integrity check failed: {e}", file=sys.stderr)
        return 1

    # Measure frozen train character count (content definition) before budget resolve
    train_path_early = split_root / "train" / "combined.txt"
    train_text_early = train_path_early.read_text(encoding="utf-8")
    frozen_chars = frozen_train_character_count(train_text_early)
    if calibration and (calibration.get("corpus") or {}).get(
        "frozen_training_corpus_character_count"
    ):
        documented = int(calibration["corpus"]["frozen_training_corpus_character_count"])
        if documented != frozen_chars:
            print(
                f"warning: documented frozen char count {documented} != "
                f"measured {frozen_chars}; using measured for epochs",
                file=sys.stderr,
            )

    budget = resolve_budget(
        config,
        args.phase,
        args.budget_policy,
        matrix,
        calibration,
        frozen_chars=frozen_chars,
    )
    arch = resolve_arch(config, args.track, args.tokenizer)
    _budget_slug = args.budget_policy
    if matrix and (matrix.get("budget_path_slugs") or {}).get(args.budget_policy):
        _budget_slug = matrix["budget_path_slugs"][args.budget_policy]
    run_id = make_run_id(
        args.tokenizer,
        args.seed,
        args.track,
        args.budget_policy,
        phase=args.phase,
        matrix_id=(
            (calibration or {}).get("calibration_id")
            or (matrix or {}).get("matrix_id")
            or "lm_baselines_v0_1"
        ),
        budget_path_slug=_budget_slug,
    )
    if calibration and (calibration.get("output") or {}).get("run_dir"):
        run_dir = root / calibration["output"]["run_dir"]
    else:
        budget_slug = args.budget_policy
        if matrix and (matrix.get("budget_path_slugs") or {}).get(args.budget_policy):
            budget_slug = matrix["budget_path_slugs"][args.budget_policy]
        run_dir = (
            root
            / config["output_root"]
            / args.track
            / args.tokenizer
            / f"seed_{args.seed}"
            / args.phase
            / budget_slug
        )

    if args.device:
        device_s = args.device
    elif args.cpu_smoke:
        device_s = "cpu"
    elif config.get("device", {}).get("prefer_cuda", True):
        device_s = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device_s = "cpu"

    # lightweight param estimate without building full model on wrong device yet
    tmp = build_gpt(
        vocab_size=8000 if args.tokenizer != "character" else 915,
        n_layer=int(arch["n_layer"]),
        n_embd=int(arch["n_embd"]),
        n_head=int(arch["n_head"]),
        n_inner=int(arch["n_inner"]),
        context_length=int(arch["context_length"]),
        dropout=0.0,
        tie_embeddings=bool(arch["tie_embeddings"]),
        pre_ln=bool(arch.get("pre_ln", True)),
    )
    # fix vocab for character after loading tokenizer later; estimate only
    est_params = tmp.count_parameters()
    del tmp

    plan = {
        "run_id": run_id,
        "tokenizer": args.tokenizer,
        "seed": args.seed,
        "track": args.track,
        "budget_policy": args.budget_policy,
        "phase": args.phase,
        "architecture": arch,
        "parameter_count_estimate_note": est_params,
        "budget": budget,
        "frozen_training_corpus_character_count": frozen_chars,
        "effective_epochs_formula": (
            "cumulative_original_characters_processed / "
            "frozen_training_corpus_character_count"
        ),
        "max_effective_epochs_approx": (
            float(budget.get("train_characters", 0)) / frozen_chars
            if frozen_chars and budget.get("train_characters")
            else None
        ),
        "output_dir": str(
            run_dir.relative_to(root) if run_dir.is_relative_to(root) else run_dir
        ),
        "device": device_s,
        "exists": run_dir.exists() and any(run_dir.iterdir()) if run_dir.exists() else False,
        "test_set_inaccessible_during_training": True,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    if args.dry_run_plan:
        print(json.dumps(plan, indent=2))
        return 0
    if not confirm_or_abort(plan, yes=bool(args.yes)):
        print("aborted: confirmation not given")
        return 0

    try:
        ensure_run_dir_free(run_dir, force=args.force)
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.force and run_dir.exists():
        import shutil

        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(device_s)
    set_seed(args.seed)
    train_cfg = config["training"]

    tokenizer = load_tokenizer(tok_cfg, root)
    train_path = split_root / "train" / "combined.txt"
    val_path = split_root / "validation" / "combined.txt"
    # Explicit: never open test here
    train_text = train_text_early
    val_text = val_path.read_text(encoding="utf-8")
    train_lines = train_text.splitlines()
    val_lines = val_text.splitlines()

    train_seqs, train_meta, _, train_char_credits = pack_lines_to_sequences(
        train_lines,
        tokenizer,
        context_length=int(arch["context_length"]),
        eos_between_lines=bool(train_cfg["packing"]["eos_between_lines"]),
    )
    val_seqs, val_meta, _, _ = pack_lines_to_sequences(
        val_lines,
        tokenizer,
        context_length=int(arch["context_length"]),
        eos_between_lines=bool(train_cfg["packing"]["eos_between_lines"]),
    )

    model = build_gpt(
        vocab_size=tokenizer.vocab_size,
        n_layer=int(arch["n_layer"]),
        n_embd=int(arch["n_embd"]),
        n_head=int(arch["n_head"]),
        n_inner=int(arch["n_inner"]),
        context_length=int(arch["context_length"]),
        dropout=float(arch["dropout"]),
        tie_embeddings=bool(arch["tie_embeddings"]),
        pre_ln=bool(arch.get("pre_ln", True)),
    ).to(device)
    param_counts = model.count_parameters()
    print(f"Actual parameter counts: {param_counts}")

    opt = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg["learning_rate"]),
        betas=(float(train_cfg["beta1"]), float(train_cfg["beta2"])),
        weight_decay=float(train_cfg["weight_decay"]),
    )

    if budget["policy"] == "fixed_characters":
        target_chars = int(budget["train_characters"])
        max_steps = int(budget.get("max_optimizer_steps_cap", 50000))
        val_char_ckpts = set(int(x) for x in budget.get("validation_character_checkpoints") or [])
        val_update_ckpts: set[int] = set()
    else:
        target_chars = None
        max_steps = int(budget["optimizer_updates"])
        val_char_ckpts = set()
        val_update_ckpts = set(int(x) for x in budget.get("validation_update_checkpoints") or [])

    warmup = int(train_cfg.get("warmup_steps", 50))

    def lr_at(step: int) -> float:
        base = float(train_cfg["learning_rate"])
        if step < warmup:
            return base * (step + 1) / max(warmup, 1)
        progress = (step - warmup) / max(max_steps - warmup, 1)
        progress = min(max(progress, 0.0), 1.0)
        return base * (0.1 + 0.9 * 0.5 * (1.0 + math.cos(math.pi * progress)))

    micro = int(train_cfg["micro_batch_size"])
    accum = int(train_cfg["grad_accum_steps"])
    use_amp = bool(train_cfg.get("amp")) and device.type == "cuda"
    dtype = torch.bfloat16 if train_cfg.get("dtype") == "bfloat16" else torch.float16
    if device.type == "cpu":
        use_amp = False
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and dtype == torch.float16)

    x_all, y_all = sequences_to_tensors(train_seqs, tokenizer.pad_id)
    char_credits = torch.tensor(train_char_credits, dtype=torch.float64)
    n_seq = x_all.size(0)
    if n_seq == 0:
        print("error: no training sequences", file=sys.stderr)
        return 1

    # Initial validation (for improvement check)
    initial_metrics = evaluate_split(
        model,
        val_seqs,
        pad_id=tokenizer.pad_id,
        device=device,
        batch_size=int(config.get("evaluation", {}).get("eval_batch_size", 16)),
        source_text=val_text,
        amp=use_amp,
        dtype=dtype,
    )
    write_json(run_dir / "initial_validation.json", initial_metrics)

    log_path = run_dir / "train_log.jsonl"
    curve_path = run_dir / "learning_curve.jsonl"
    log_f = log_path.open("w", encoding="utf-8")
    curve_f = curve_path.open("w", encoding="utf-8")
    best: dict[str, Any] = {
        "step": -1,
        "validation_bpc": float("inf"),
        "validation_bpb": None,
        "characters_processed": 0,
        "wall_time_s": None,
    }
    history: list[dict[str, Any]] = []
    nan_or_inf = False
    next_char_ckpt = sorted(val_char_ckpts)
    char_ckpt_i = 0
    es_cfg = budget.get("early_stopping") or {"enabled": False}
    es_enabled = bool(es_cfg.get("enabled"))
    es_min_delta = float(es_cfg.get("min_delta", 0.01))
    es_patience = int(es_cfg.get("patience_evaluations", 3))
    es_min_epochs = float(es_cfg.get("min_effective_epochs_before_stop", 0))
    es_bad_evals = 0
    early_stop_triggered = False
    early_stop_reason: str | None = None

    step = 0
    chars_processed = 0.0
    tokens_processed = 0
    t0 = time.perf_counter()
    peak_mem = 0.0
    model.train()
    seq_idx = 0
    order = torch.arange(n_seq)

    def maybe_eval(force: bool = False) -> None:
        nonlocal best, char_ckpt_i, nan_or_inf, es_bad_evals
        nonlocal early_stop_triggered, early_stop_reason
        do = force
        if not do and budget["policy"] == "fixed_updates" and step in val_update_ckpts:
            do = True
        if not do and budget["policy"] == "fixed_characters":
            while (
                char_ckpt_i < len(next_char_ckpt)
                and chars_processed >= next_char_ckpt[char_ckpt_i]
            ):
                do = True
                char_ckpt_i += 1
                break
        if not do:
            return
        metrics = evaluate_split(
            model,
            val_seqs,
            pad_id=tokenizer.pad_id,
            device=device,
            batch_size=int(config.get("evaluation", {}).get("eval_batch_size", 16)),
            source_text=val_text,
            amp=use_amp,
            dtype=dtype,
        )
        epochs = effective_epochs(chars_processed, frozen_chars)
        elapsed = time.perf_counter() - t0
        metrics["step"] = step
        metrics["characters_processed"] = chars_processed
        metrics["tokens_processed"] = tokens_processed
        metrics["elapsed_s"] = elapsed
        metrics["learning_rate"] = lr_at(max(step - 1, 0))
        metrics["effective_epochs"] = epochs
        metrics["frozen_training_corpus_character_count"] = frozen_chars
        metrics["characters_per_second"] = chars_processed / max(elapsed, 1e-6)
        metrics["tokens_per_second"] = tokens_processed / max(elapsed, 1e-6)
        if metrics.get("nan_detected"):
            nan_or_inf = True
        history.append(metrics)
        write_json(run_dir / "validation_history.json", history)
        curve_f.write(json.dumps(metrics) + "\n")
        curve_f.flush()
        bpc = metrics["bits_per_character"]
        print(
            f"  val BPC={bpc} BPB={metrics['bits_per_byte']} "
            f"chars={chars_processed:.0f} epochs={epochs} step={step}"
        )
        improved = False
        if bpc is not None and math.isfinite(bpc):
            # improvement vs best by at least min_delta
            if bpc < best["validation_bpc"] - (es_min_delta if es_enabled else 0.0):
                improved = True
            # always save absolute best even if delta tiny when early stop off
            if bpc < best["validation_bpc"]:
                best = {
                    "step": step,
                    "validation_bpc": bpc,
                    "validation_bpb": metrics["bits_per_byte"],
                    "characters_processed": chars_processed,
                    "effective_epochs": epochs,
                    "wall_time_s": metrics["elapsed_s"],
                }
                torch.save(
                    {
                        "model": model.state_dict(),
                        "optimizer": opt.state_dict(),
                        "step": step,
                        "best": best,
                        "arch": arch,
                        "tokenizer_id": args.tokenizer,
                        "seed": args.seed,
                        "vocab_size": tokenizer.vocab_size,
                        "budget_policy": args.budget_policy,
                        "run_id": run_id,
                    },
                    run_dir / "best.pt",
                )
        if es_enabled and not force:
            # only count scheduled evals after min epochs
            if epochs is not None and epochs >= es_min_epochs:
                if improved:
                    es_bad_evals = 0
                else:
                    es_bad_evals += 1
                if es_bad_evals >= es_patience:
                    early_stop_triggered = True
                    early_stop_reason = (
                        f"no val BPC improvement >= {es_min_delta} for "
                        f"{es_patience} consecutive evals after "
                        f"{es_min_epochs} effective epochs"
                    )
                    print(f"early stopping: {early_stop_reason}")
        model.train()

    try:
        while step < max_steps:
            if budget["policy"] == "fixed_characters" and chars_processed >= float(
                target_chars  # type: ignore[arg-type]
            ):
                break
            opt.zero_grad(set_to_none=True)
            step_loss = 0.0
            step_chars = 0.0
            for _micro in range(accum):
                if seq_idx + micro > n_seq:
                    g = torch.Generator()
                    g.manual_seed(args.seed + step + 17)
                    order = torch.randperm(n_seq, generator=g)
                    seq_idx = 0
                idx = order[seq_idx : seq_idx + micro]
                seq_idx += micro
                xb = x_all[idx].to(device)
                yb = y_all[idx].to(device)
                batch_chars = float(char_credits[idx].sum().item())
                step_chars += batch_chars
                tokens_processed += int(xb.numel())

                for pg in opt.param_groups:
                    pg["lr"] = lr_at(step)

                if use_amp:
                    with torch.autocast(device_type="cuda", dtype=dtype):
                        _logits, loss, _nll, _nt = model(
                            xb, yb, pad_id=tokenizer.pad_id
                        )
                        loss = loss / accum
                    if dtype == torch.float16:
                        scaler.scale(loss).backward()
                    else:
                        loss.backward()
                else:
                    _logits, loss, _nll, _nt = model(xb, yb, pad_id=tokenizer.pad_id)
                    loss = loss / accum
                    loss.backward()
                lv = float(loss.item())
                if math.isnan(lv) or math.isinf(lv):
                    nan_or_inf = True
                step_loss += lv

            if use_amp and dtype == torch.float16:
                scaler.unscale_(opt)
            gnorm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(train_cfg["grad_clip"])
            )
            gnorm_f = float(gnorm)
            if math.isnan(gnorm_f) or math.isinf(gnorm_f):
                nan_or_inf = True
            if use_amp and dtype == torch.float16:
                scaler.step(opt)
                scaler.update()
            else:
                opt.step()

            chars_processed += step_chars
            if device.type == "cuda":
                peak_mem = max(
                    peak_mem, torch.cuda.max_memory_allocated() / (1024**3)
                )

            step += 1
            if step % int(train_cfg.get("log_every", 20)) == 0 or step == 1:
                row = {
                    "step": step,
                    "train_loss": step_loss,
                    "lr": lr_at(step - 1),
                    "grad_norm": gnorm_f,
                    "characters_processed": chars_processed,
                    "tokens_processed": tokens_processed,
                    "elapsed_s": time.perf_counter() - t0,
                }
                log_f.write(json.dumps(row) + "\n")
                log_f.flush()
                print(
                    f"step {step} loss={step_loss:.4f} chars={chars_processed:.0f} "
                    f"lr={row['lr']:.2e} gnorm={gnorm_f:.3f}"
                )
            maybe_eval(force=False)
            if nan_or_inf:
                print("error: NaN/Inf detected — stopping run", file=sys.stderr)
                break
            if early_stop_triggered:
                break

    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            msg = (
                "CUDA OOM. Do not silently reduce architecture. "
                "Create a new run identity with different micro_batch/grad_accum."
            )
            write_text(run_dir / "OOM.txt", msg + "\n" + str(e) + "\n")
            print(f"error: {msg}", file=sys.stderr)
            log_f.close()
            curve_f.close()
            return 3
        raise

    # Final validation
    maybe_eval(force=True)
    log_f.close()
    curve_f.close()

    # Restore best weights into final.pt path when requested
    if (
        early_stop_triggered
        and (budget.get("early_stopping") or {}).get("restore_best_checkpoint", True)
        and (run_dir / "best.pt").is_file()
    ):
        ckpt_best = torch.load(run_dir / "best.pt", map_location=device, weights_only=False)
        model.load_state_dict(ckpt_best["model"])
        print("restored best checkpoint weights after early stop")

    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": opt.state_dict(),
            "step": step,
            "arch": arch,
            "tokenizer_id": args.tokenizer,
            "seed": args.seed,
            "vocab_size": tokenizer.vocab_size,
            "budget_policy": args.budget_policy,
            "run_id": run_id,
        },
        run_dir / "final.pt",
    )
    if not (run_dir / "best.pt").is_file():
        import shutil

        shutil.copy(run_dir / "final.pt", run_dir / "best.pt")

    # Selection lock (immutable after write unless force+documented)
    sel_path = run_dir / "selection_lock.json"
    if sel_path.is_file() and not args.force:
        print("error: selection_lock.json already exists", file=sys.stderr)
        return 1
    best_ckpt = "best.pt"
    selection = {
        "run_id": run_id,
        "selected_checkpoint": best_ckpt,
        "selected_step": best["step"],
        "selected_character_exposure": best["characters_processed"],
        "validation_bpc": best["validation_bpc"],
        "validation_bpb": best["validation_bpb"],
        "checkpoint_sha256": sha256_file(run_dir / best_ckpt),
        "selection_timestamp": utc_now_iso(),
        "statement": "Test data was not used for checkpoint selection.",
        "primary_metric": "validation_bits_per_character",
        "confirmation_metric": "validation_bits_per_byte",
    }
    write_json(sel_path, selection)

    elapsed = time.perf_counter() - t0
    overshoot = None
    if budget["policy"] == "fixed_characters" and target_chars:
        overshoot = chars_processed - float(target_chars)

    improved = (
        initial_metrics.get("bits_per_character") is not None
        and best["validation_bpc"] is not None
        and best["validation_bpc"] < initial_metrics["bits_per_character"]
    )

    # Checkpoint reload verification
    reload_ok = False
    reload_bpc = None
    try:
        ckpt = torch.load(run_dir / "best.pt", map_location=device, weights_only=False)
        m2 = build_gpt(
            vocab_size=tokenizer.vocab_size,
            n_layer=int(arch["n_layer"]),
            n_embd=int(arch["n_embd"]),
            n_head=int(arch["n_head"]),
            n_inner=int(arch["n_inner"]),
            context_length=int(arch["context_length"]),
            dropout=0.0,
            tie_embeddings=bool(arch["tie_embeddings"]),
            pre_ln=bool(arch.get("pre_ln", True)),
        ).to(device)
        m2.load_state_dict(ckpt["model"])
        rem = evaluate_split(
            m2,
            val_seqs,
            pad_id=tokenizer.pad_id,
            device=device,
            batch_size=int(config.get("evaluation", {}).get("eval_batch_size", 16)),
            source_text=val_text,
            amp=False,
            dtype=torch.float32,
        )
        reload_bpc = rem["bits_per_character"]
        if (
            reload_bpc is not None
            and best["validation_bpc"] is not None
            and math.isfinite(reload_bpc)
            and abs(reload_bpc - best["validation_bpc"]) < 1e-3
        ):
            reload_ok = True
    except Exception as e:  # noqa: BLE001
        write_text(run_dir / "reload_error.txt", str(e) + "\n")

    status = "failed" if nan_or_inf else "completed"
    if best["validation_bpc"] == float("inf"):
        status = "failed"

    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "status": status,
        "created_at": utc_now_iso(),
        "run_id": run_id,
        "phase": args.phase,
        "track": args.track,
        "tokenizer_id": args.tokenizer,
        "seed": args.seed,
        "budget_policy": args.budget_policy,
        "budget": budget,
        "pilot_label": args.phase == "pilot",
        "architecture": arch,
        "parameter_counts": param_counts,
        "training": train_cfg,
        "device": str(device),
        "train_input": str(train_path.relative_to(root)),
        "train_input_sha256": sha256_file(train_path),
        "val_input": str(val_path.relative_to(root)),
        "val_input_sha256": sha256_file(val_path),
        "test_evaluated_during_training": False,
        "test_set_inaccessible_during_training": True,
        "tokenizer_verification": tok_info,
        "split_verification": {"frozen": True, "n_checksums": split_info["n_ok"]},
        "data_packing": {
            **train_meta.__dict__,
            "character_accounting": train_cfg["packing"].get(
                "character_accounting",
                "proportional_per_content_token_plus_zero_for_eos_pad",
            ),
            "val_packing": val_meta.__dict__,
        },
        "exposure": {
            "characters_processed": chars_processed,
            "character_target": target_chars,
            "character_overshoot": overshoot,
            "tokens_processed": tokens_processed,
            "optimizer_steps": step,
            "frozen_training_corpus_character_count": frozen_chars,
            "effective_epochs": effective_epochs(chars_processed, frozen_chars),
            "effective_epochs_formula": (
                "cumulative_original_characters_processed / "
                "frozen_training_corpus_character_count"
            ),
            "bytes_processed_approx": int(
                chars_processed
                * (
                    train_meta.n_bytes_in_source_text
                    / max(train_meta.n_characters_in_source_text, 1)
                )
            ),
        },
        "early_stopping": {
            "enabled": es_enabled,
            "triggered": early_stop_triggered,
            "reason": early_stop_reason,
            "config": es_cfg,
            "restore_best_checkpoint": bool(
                es_cfg.get("restore_best_checkpoint", True)
            ),
        },
        "initial_validation": initial_metrics,
        "best_checkpoint": best,
        "final_budget_metrics": history[-1] if history else None,
        "validation_improved_from_initial": improved,
        "nan_or_inf_detected": nan_or_inf,
        "checkpoint_reload_verification": {
            "ok": reload_ok,
            "reloaded_validation_bpc": reload_bpc,
            "tolerance": 1e-3,
        },
        "selection_lock": selection,
        "runtime": {
            "wall_clock_s": elapsed,
            "peak_gpu_memory_gb": peak_mem,
            "tokens_per_second": tokens_processed / max(elapsed, 1e-6),
            "characters_per_second": chars_processed / max(elapsed, 1e-6),
        },
        "validation_history": history,
        "environment": env_metadata(root),
        "config_sha256": sha256_file(config_path),
        "matrix_config_sha256": sha256_file(matrix_path) if matrix_path else None,
        "hypotheses": config.get("hypotheses"),
        "artifacts": {},
    }
    for name in (
        "best.pt",
        "final.pt",
        "train_log.jsonl",
        "learning_curve.jsonl",
        "selection_lock.json",
    ):
        p = run_dir / name
        if p.is_file():
            manifest["artifacts"][name] = sha256_file(p)

    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "config_snapshot.json", config)
    write_json(run_dir / "validation_metrics.json", history[-1] if history else {})
    write_text(
        run_dir / "README.md",
        f"# {run_id}\n\n"
        f"status={status}\n"
        f"best val BPC={best['validation_bpc']}\n"
        f"chars={chars_processed} steps={step}\n"
        "Test not used.\n",
    )

    print(
        f"Done status={status} {args.tokenizer} seed={args.seed} "
        f"budget={args.budget_policy} best_val_BPC={best['validation_bpc']} "
        f"steps={step} chars={chars_processed:.0f} time={elapsed:.1f}s "
        f"peak_mem={peak_mem:.2f}GB reload_ok={reload_ok}"
    )
    print(f"  run_dir={run_dir}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
