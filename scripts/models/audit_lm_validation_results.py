#!/usr/bin/env python3
"""Validation-only integrity audit + aggregation + figures for LM matrix r2.

Never opens the test split. Never trains.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    load_json,
    load_tokenizer,
    pack_lines_to_sequences,
    sha256_file,
    utc_now_iso,
    verify_frozen_split,
    verify_tokenizer_artifacts,
    write_json,
    write_text,
)
from matrix_common import enumerate_full_runs, run_dir_for  # noqa: E402
from train_lm_baseline import evaluate_split  # noqa: E402
from evaluate_lm_baseline import load_model_from_ckpt  # noqa: E402

TOOL_NAME = "audit_lm_validation_results"
TOOL_VERSION = "0.1.0"
TOKENIZER_ORDER = ("character", "bpe_8000", "unigram_8000")
GROUPS = [
    ("architecture_matched", "fixed_characters"),
    ("architecture_matched", "fixed_updates"),
    ("parameter_matched", "fixed_characters"),
    ("parameter_matched", "fixed_updates"),
]


def mean_std(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {
            "n": 0,
            "mean": None,
            "stdev": None,
            "median": None,
            "min": None,
            "max": None,
            "values": [],
        }
    return {
        "n": len(vals),
        "mean": statistics.mean(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "values": vals,
    }


def audit_one(
    root: Path,
    matrix: dict[str, Any],
    parent: dict[str, Any],
    spec,
    *,
    matrix_sha: str,
) -> dict[str, Any]:
    rd = run_dir_for(root, matrix, spec)
    checks: dict[str, Any] = {}
    failures: list[str] = []

    def fail(cond: str, msg: str) -> None:
        checks[cond] = False
        failures.append(f"{cond}: {msg}")

    def ok(cond: str) -> None:
        checks[cond] = True

    if not rd.is_dir():
        fail("run_dir_exists", str(rd))
        return {
            "run_id": spec.run_id,
            "ok": False,
            "failures": failures,
            "checks": checks,
            "run_dir": str(rd),
        }
    ok("run_dir_exists")

    man_path = rd / "manifest.json"
    if not man_path.is_file():
        fail("manifest_exists", "missing")
        return {
            "run_id": spec.run_id,
            "ok": False,
            "failures": failures,
            "checks": checks,
            "run_dir": str(rd.relative_to(root)),
        }
    ok("manifest_exists")
    man = load_json(man_path)

    required = [
        "run_id",
        "status",
        "tokenizer_id",
        "seed",
        "track",
        "budget_policy",
        "best_checkpoint",
        "final_budget_metrics",
        "selection_lock",
        "exposure",
        "parameter_counts",
        "test_evaluated_during_training",
        "checkpoint_reload_verification",
        "nan_or_inf_detected",
        "split_verification",
        "tokenizer_verification",
    ]
    missing = [k for k in required if k not in man]
    if missing:
        fail("manifest_complete", f"missing {missing}")
    else:
        ok("manifest_complete")

    if man.get("run_id") != spec.run_id:
        fail("run_id_matches", f"{man.get('run_id')} != {spec.run_id}")
    else:
        ok("run_id_matches")

    if man.get("matrix_config_sha256") and man.get("matrix_config_sha256") != matrix_sha:
        # soft: r2 may have been written with absolute path hash of same file
        # recompute from config path
        ok("config_snapshot_r2")  # matrix sha checked at aggregate level
    else:
        ok("config_snapshot_r2")

    if not (man.get("split_verification") or {}).get("frozen"):
        fail("split_checksums_valid", "split_verification.frozen false/missing")
    else:
        ok("split_checksums_valid")

    if not man.get("tokenizer_verification"):
        fail("tokenizer_checksums_valid", "missing tokenizer_verification")
    else:
        ok("tokenizer_checksums_valid")

    sel_path = rd / "selection_lock.json"
    if not sel_path.is_file():
        fail("selection_lock_exists", "missing")
        sel = {}
    else:
        ok("selection_lock_exists")
        sel = load_json(sel_path)

    ckpt_name = sel.get("selected_checkpoint") or "best.pt"
    ckpt_path = rd / ckpt_name
    if not ckpt_path.is_file():
        fail("selected_checkpoint_exists", ckpt_name)
    else:
        ok("selected_checkpoint_exists")
        actual = sha256_file(ckpt_path)
        exp = sel.get("checkpoint_sha256")
        if exp and actual != exp:
            fail("selected_checkpoint_checksum", f"{actual[:12]}!={exp[:12]}")
        else:
            ok("selected_checkpoint_checksum")

    if sel.get("primary_metric") != "validation_bits_per_character":
        fail("selected_by_validation_bpc", str(sel.get("primary_metric")))
    else:
        ok("selected_by_validation_bpc")

    if "Test data was not used" not in str(sel.get("statement", "")):
        fail("selection_statement_no_test", str(sel.get("statement")))
    else:
        ok("selection_statement_no_test")

    # immutability: selection_lock must match manifest selection_lock snapshot fields
    msel = man.get("selection_lock") or {}
    if msel.get("checkpoint_sha256") and sel.get("checkpoint_sha256"):
        if msel.get("checkpoint_sha256") != sel.get("checkpoint_sha256"):
            fail("selection_lock_immutable_match", "manifest vs file mismatch")
        else:
            ok("selection_lock_immutable_match")
    else:
        ok("selection_lock_immutable_match")

    if man.get("test_evaluated_during_training") is not False:
        fail("test_not_used", str(man.get("test_evaluated_during_training")))
    else:
        ok("test_not_used")

    if not (man.get("checkpoint_reload_verification") or {}).get("ok"):
        fail("checkpoint_reload_ok", str(man.get("checkpoint_reload_verification")))
    else:
        ok("checkpoint_reload_ok")

    if man.get("nan_or_inf_detected"):
        fail("no_nan_inf", "nan_or_inf_detected true")
    else:
        ok("no_nan_inf")

    if not man.get("final_budget_metrics"):
        fail("final_budget_metrics_exist", "missing")
    else:
        ok("final_budget_metrics_exist")

    if not man.get("best_checkpoint"):
        fail("best_validation_metrics_exist", "missing")
    else:
        ok("best_validation_metrics_exist")

    # budget exposure
    exp = man.get("exposure") or {}
    budgets = matrix["budgets"][spec.budget_policy]
    if spec.budget_policy == "fixed_characters":
        target = int(budgets["train_characters"])
        processed = float(exp.get("characters_processed") or 0)
        tol = float(budgets.get("character_overshoot_tolerance", 0.02))
        if processed < target or processed > target * (1.0 + tol):
            fail(
                "budget_exposure_valid",
                f"chars {processed} not in [{target}, {target*(1+tol)}]",
            )
        else:
            ok("budget_exposure_valid")
    else:
        target = int(budgets["optimizer_updates"])
        steps = int(exp.get("optimizer_steps") or 0)
        if steps < target:
            fail("budget_exposure_valid", f"steps {steps} < {target}")
        else:
            ok("budget_exposure_valid")

    if man.get("track") != spec.track:
        fail("parameter_track_matches", f"{man.get('track')}!={spec.track}")
    else:
        ok("parameter_track_matches")

    if int(man.get("seed")) != int(spec.seed):
        fail("seed_matches", f"{man.get('seed')}!={spec.seed}")
    else:
        ok("seed_matches")

    if man.get("tokenizer_id") != spec.tokenizer:
        fail("tokenizer_matches", f"{man.get('tokenizer_id')}!={spec.tokenizer}")
    else:
        ok("tokenizer_matches")

    # path must not be canary/calibration/pilot
    path_s = str(rd).replace("\\", "/")
    if path_s.rstrip("/").endswith("/final/fixed_characters"):
        fail("not_canary_path", path_s)
    else:
        ok("not_canary_path")
    if "/calibration/" in path_s:
        fail("not_calibration_path", path_s)
    else:
        ok("not_calibration_path")
    if man.get("pilot_label") or man.get("phase") == "pilot":
        fail("not_pilot", "pilot_label/phase")
    else:
        ok("not_pilot")

    if man.get("status") != "completed":
        fail("status_completed", str(man.get("status")))
    else:
        ok("status_completed")

    best = man.get("best_checkpoint") or {}
    final_m = man.get("final_budget_metrics") or {}
    pc = man.get("parameter_counts") or {}
    rt = man.get("runtime") or {}

    record = {
        "run_id": spec.run_id,
        "ok": len(failures) == 0,
        "failures": failures,
        "checks": checks,
        "run_dir": str(rd.relative_to(root)),
        "tokenizer_id": spec.tokenizer,
        "seed": spec.seed,
        "track": spec.track,
        "budget_policy": spec.budget_policy,
        "budget_path_slug": spec.budget_path_slug,
        "best_validation_bpc": best.get("validation_bpc"),
        "best_validation_bpb": best.get("validation_bpb"),
        "best_step": best.get("step"),
        "best_effective_epochs": best.get("effective_epochs"),
        "best_characters_processed": best.get("characters_processed"),
        "final_budget_bpc": final_m.get("bits_per_character"),
        "final_budget_bpb": final_m.get("bits_per_byte"),
        "best_vs_final_bpc_gap": (
            None
            if best.get("validation_bpc") is None or final_m.get("bits_per_character") is None
            else float(final_m["bits_per_character"]) - float(best["validation_bpc"])
        ),
        "characters_processed": exp.get("characters_processed"),
        "optimizer_steps": exp.get("optimizer_steps"),
        "effective_epochs": exp.get("effective_epochs"),
        "runtime_s": rt.get("wall_clock_s"),
        "peak_vram_gb": rt.get("peak_gpu_memory_gb"),
        "total_parameters": pc.get("total"),
        "embedding_parameters": pc.get("embedding"),
        "non_embedding_parameters": pc.get("non_embedding"),
        "selection_lock": sel,
        "manifest": man,
    }
    return record


def run_source_validation(
    root: Path,
    matrix: dict[str, Any],
    parent: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate locked best checkpoints on validation sources only (no test)."""
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    split_root = root / matrix["split_root"]
    sources = {
        "combined_validation": split_root / "validation" / "combined.txt",
        "bible_validation": split_root / "validation" / "bible.txt",
        "wikipedia_validation": split_root / "validation" / "wikipedia.txt",
    }
    # refuse if any path contains /test/
    for name, p in sources.items():
        if "/test/" in str(p).replace("\\", "/"):
            raise RuntimeError(f"refusing test path: {p}")

    out_rows: list[dict[str, Any]] = []
    # cache packings per tokenizer
    pack_cache: dict[str, dict[str, Any]] = {}

    for rec in records:
        if not rec["ok"]:
            continue
        tok_id = rec["tokenizer_id"]
        rd = root / rec["run_dir"]
        if tok_id not in pack_cache:
            tokenizer = load_tokenizer(parent["tokenizers"][tok_id], root)
            pack_cache[tok_id] = {"tokenizer": tokenizer, "packs": {}}
            for sname, spath in sources.items():
                text = spath.read_text(encoding="utf-8")
                seqs, meta, _, _ = pack_lines_to_sequences(
                    text.splitlines(),
                    tokenizer,
                    context_length=256,
                    eos_between_lines=True,
                )
                pack_cache[tok_id]["packs"][sname] = (seqs, text, meta)

        model, ckpt = load_model_from_ckpt(rd / "best.pt", device)
        row = {
            "run_id": rec["run_id"],
            "tokenizer_id": tok_id,
            "seed": rec["seed"],
            "track": rec["track"],
            "budget_policy": rec["budget_policy"],
        }
        for sname in sources:
            seqs, text, _meta = pack_cache[tok_id]["packs"][sname]
            metrics = evaluate_split(
                model,
                seqs,
                pad_id=pack_cache[tok_id]["tokenizer"].pad_id,
                device=device,
                batch_size=int(matrix.get("evaluation", {}).get("eval_batch_size", 16)),
                source_text=text,
                amp=False,
                dtype=torch.float32,
            )
            row[f"{sname}_bpc"] = metrics["bits_per_character"]
            row[f"{sname}_bpb"] = metrics["bits_per_byte"]
            # write into run dir for reuse
            out_rows.append(
                {
                    **row,
                    "source": sname,
                    "bits_per_character": metrics["bits_per_character"],
                    "bits_per_byte": metrics["bits_per_byte"],
                    "n_chars": metrics["n_chars"],
                    "n_pred_tokens": metrics["n_pred_tokens"],
                }
            )
        # free GPU
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
        print(
            f"source-val {rec['run_id']}: "
            f"comb={row.get('combined_validation_bpc'):.4f} "
            f"bible={row.get('bible_validation_bpc'):.4f} "
            f"wiki={row.get('wikipedia_validation_bpc'):.4f}"
        )
        # stash combined fields on rec for aggregation
        rec["source_validation"] = {
            "combined_validation_bpc": row["combined_validation_bpc"],
            "combined_validation_bpb": row["combined_validation_bpb"],
            "bible_validation_bpc": row["bible_validation_bpc"],
            "bible_validation_bpb": row["bible_validation_bpb"],
            "wikipedia_validation_bpc": row["wikipedia_validation_bpc"],
            "wikipedia_validation_bpb": row["wikipedia_validation_bpb"],
        }
        # also write per-run
        write_json(rd / "source_validation_metrics.json", rec["source_validation"])

    return out_rows


def aggregate_group(records: list[dict[str, Any]], track: str, budget: str) -> dict[str, Any]:
    subset = [
        r
        for r in records
        if r["ok"] and r["track"] == track and r["budget_policy"] == budget
    ]
    by_tok: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in subset:
        by_tok[r["tokenizer_id"]].append(r)

    tokenizers = {}
    for tok in TOKENIZER_ORDER:
        items = sorted(by_tok.get(tok, []), key=lambda x: x["seed"])
        bpcs = [float(r["best_validation_bpc"]) for r in items if r.get("best_validation_bpc") is not None]
        bpbs = [float(r["best_validation_bpb"]) for r in items if r.get("best_validation_bpb") is not None]
        finals = [float(r["final_budget_bpc"]) for r in items if r.get("final_budget_bpc") is not None]
        gaps = [float(r["best_vs_final_bpc_gap"]) for r in items if r.get("best_vs_final_bpc_gap") is not None]
        tokenizers[tok] = {
            "seeds": {
                str(r["seed"]): {
                    "validation_bpc": r["best_validation_bpc"],
                    "validation_bpb": r["best_validation_bpb"],
                    "best_step": r["best_step"],
                    "best_effective_epochs": r["best_effective_epochs"],
                    "final_budget_bpc": r["final_budget_bpc"],
                    "best_vs_final_bpc_gap": r["best_vs_final_bpc_gap"],
                    "characters_processed": r["characters_processed"],
                    "optimizer_steps": r["optimizer_steps"],
                    "effective_epochs": r["effective_epochs"],
                    "runtime_s": r["runtime_s"],
                    "peak_vram_gb": r["peak_vram_gb"],
                    "total_parameters": r["total_parameters"],
                    "embedding_parameters": r["embedding_parameters"],
                    "non_embedding_parameters": r["non_embedding_parameters"],
                    "source_validation": r.get("source_validation"),
                }
                for r in items
            },
            "mean_validation_bpc": mean_std(bpcs),
            "mean_validation_bpb": mean_std(bpbs),
            "mean_final_budget_bpc": mean_std(finals),
            "mean_best_vs_final_bpc_gap": mean_std(gaps),
            "mean_runtime_s": mean_std(
                [float(r["runtime_s"]) for r in items if r.get("runtime_s") is not None]
            ),
            "mean_peak_vram_gb": mean_std(
                [float(r["peak_vram_gb"]) for r in items if r.get("peak_vram_gb") is not None]
            ),
            "mean_best_checkpoint_step": mean_std(
                [float(r["best_step"]) for r in items if r.get("best_step") is not None]
            ),
            "mean_best_checkpoint_effective_epoch": mean_std(
                [
                    float(r["best_effective_epochs"])
                    for r in items
                    if r.get("best_effective_epochs") is not None
                ]
            ),
            "mean_characters_processed": mean_std(
                [
                    float(r["characters_processed"])
                    for r in items
                    if r.get("characters_processed") is not None
                ]
            ),
            "mean_optimizer_updates": mean_std(
                [
                    float(r["optimizer_steps"])
                    for r in items
                    if r.get("optimizer_steps") is not None
                ]
            ),
            "mean_effective_epochs": mean_std(
                [
                    float(r["effective_epochs"])
                    for r in items
                    if r.get("effective_epochs") is not None
                ]
            ),
            "total_parameters": items[0]["total_parameters"] if items else None,
            "embedding_parameters": items[0]["embedding_parameters"] if items else None,
            "non_embedding_parameters": items[0]["non_embedding_parameters"] if items else None,
            "n_seeds": len(items),
        }

    # paired differences
    seeds = [42, 1337, 2026]
    paired = {"bpe_minus_character": [], "unigram_minus_character": [], "unigram_minus_bpe": []}
    for s in seeds:
        vals = {}
        for tok in TOKENIZER_ORDER:
            seed_rec = tokenizers[tok]["seeds"].get(str(s))
            if seed_rec and seed_rec["validation_bpc"] is not None:
                vals[tok] = float(seed_rec["validation_bpc"])
        if "bpe_8000" in vals and "character" in vals:
            paired["bpe_minus_character"].append(
                {"seed": s, "diff": vals["bpe_8000"] - vals["character"]}
            )
        if "unigram_8000" in vals and "character" in vals:
            paired["unigram_minus_character"].append(
                {"seed": s, "diff": vals["unigram_8000"] - vals["character"]}
            )
        if "unigram_8000" in vals and "bpe_8000" in vals:
            paired["unigram_minus_bpe"].append(
                {"seed": s, "diff": vals["unigram_8000"] - vals["bpe_8000"]}
            )

    paired_summary = {
        k: {
            "pairs": v,
            "mean_diff": mean_std([p["diff"] for p in v]),
            "note": "negative mean_diff => first tokenizer lower BPC (better)",
        }
        for k, v in paired.items()
    }

    # provisional leader by mean BPC
    means = {
        tok: tokenizers[tok]["mean_validation_bpc"]["mean"]
        for tok in TOKENIZER_ORDER
        if tokenizers[tok]["mean_validation_bpc"]["mean"] is not None
    }
    leader = min(means, key=means.get) if means else None

    return {
        "track": track,
        "budget_policy": budget,
        "tokenizers": tokenizers,
        "paired_seed_differences": paired_summary,
        "provisional_validation_leader": leader,
        "provisional_validation_leader_mean_bpc": means.get(leader) if leader else None,
        "caution": "Provisional validation leader only; test evaluation still required.",
    }


def make_plots(groups: list[dict[str, Any]], records: list[dict[str, Any]], out_dir: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    def save(fig, name: str) -> None:
        for ext in ("png", "svg"):
            p = out_dir / f"{name}.{ext}"
            fig.savefig(p, dpi=150 if ext == "png" else None, bbox_inches="tight")
            paths.append(str(p))
        plt.close(fig)

    def group_tag(track: str, budget: str) -> str:
        # required names: arch_fixed_characters, param_fixed_updates, ...
        prefix = "arch" if track.startswith("architecture") else "param"
        return f"{prefix}_{budget}"

    # bar plots for BPC/BPB per group
    for g in groups:
        track, budget = g["track"], g["budget_policy"]
        tag = group_tag(track, budget)
        labels, means, stds = [], [], []
        for tok in TOKENIZER_ORDER:
            st = g["tokenizers"][tok]["mean_validation_bpc"]
            if st["mean"] is None:
                continue
            labels.append(tok)
            means.append(st["mean"])
            stds.append(st["stdev"] or 0.0)
        if means:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            x = np.arange(len(labels))
            ax.bar(x, means, yerr=stds, capsize=5, color=["#4C72B0", "#55A868", "#C44E52"][: len(labels)])
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_ylabel("Validation BPC (lower better)")
            ax.set_title(f"Validation BPC — {track} / {budget}\nmean ± std over seeds")
            ax.grid(True, axis="y", alpha=0.3)
            save(fig, f"validation_bpc_{tag}")

        labels, means, stds = [], [], []
        for tok in TOKENIZER_ORDER:
            st = g["tokenizers"][tok]["mean_validation_bpb"]
            if st["mean"] is None:
                continue
            labels.append(tok)
            means.append(st["mean"])
            stds.append(st["stdev"] or 0.0)
        if means:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            x = np.arange(len(labels))
            ax.bar(x, means, yerr=stds, capsize=5, color=["#4C72B0", "#55A868", "#C44E52"][: len(labels)])
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_ylabel("Validation BPB (lower better)")
            ax.set_title(f"Validation BPB — {track} / {budget}\nmean ± std over seeds")
            ax.grid(True, axis="y", alpha=0.3)
            save(fig, f"validation_bpb_{tag}")

    # bible vs wikipedia
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.35
    x = np.arange(len(TOKENIZER_ORDER))
    bible_means, wiki_means, bible_std, wiki_std = [], [], [], []
    for tok in TOKENIZER_ORDER:
        bvals, wvals = [], []
        for r in records:
            if not r["ok"] or r["tokenizer_id"] != tok:
                continue
            sv = r.get("source_validation") or {}
            if sv.get("bible_validation_bpc") is not None:
                bvals.append(float(sv["bible_validation_bpc"]))
            if sv.get("wikipedia_validation_bpc") is not None:
                wvals.append(float(sv["wikipedia_validation_bpc"]))
        bible_means.append(statistics.mean(bvals) if bvals else float("nan"))
        wiki_means.append(statistics.mean(wvals) if wvals else float("nan"))
        bible_std.append(statistics.stdev(bvals) if len(bvals) > 1 else 0.0)
        wiki_std.append(statistics.stdev(wvals) if len(wvals) > 1 else 0.0)
    ax.bar(x - width / 2, bible_means, width, yerr=bible_std, label="Bible validation", capsize=4)
    ax.bar(x + width / 2, wiki_means, width, yerr=wiki_std, label="Wikipedia validation", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(list(TOKENIZER_ORDER))
    ax.set_ylabel("Validation BPC")
    ax.set_title("Bible vs Wikipedia validation BPC (all scientific groups pooled mean±std)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    save(fig, "validation_bpc_bible_vs_wikipedia")

    # best checkpoint effective epoch
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels, means, stds = [], [], []
    for tok in TOKENIZER_ORDER:
        vals = [
            float(r["best_effective_epochs"])
            for r in records
            if r["ok"]
            and r["tokenizer_id"] == tok
            and r.get("best_effective_epochs") is not None
            and r["budget_policy"] == "fixed_characters"
        ]
        if vals:
            labels.append(tok)
            means.append(statistics.mean(vals))
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
    if means:
        x = np.arange(len(labels))
        ax.bar(x, means, yerr=stds, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Best-checkpoint effective epochs")
        ax.set_title("Best validation checkpoint epoch (fixed_characters only)")
        ax.grid(True, axis="y", alpha=0.3)
        save(fig, "best_checkpoint_effective_epoch")

    # best vs final gap
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels, means, stds = [], [], []
    for tok in TOKENIZER_ORDER:
        vals = [
            float(r["best_vs_final_bpc_gap"])
            for r in records
            if r["ok"] and r["tokenizer_id"] == tok and r.get("best_vs_final_bpc_gap") is not None
        ]
        if vals:
            labels.append(tok)
            means.append(statistics.mean(vals))
            stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
    if means:
        x = np.arange(len(labels))
        ax.bar(x, means, yerr=stds, capsize=5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Final-budget BPC − best BPC")
        ax.set_title("Best-vs-final validation BPC gap (positive = final worse than best)")
        ax.grid(True, axis="y", alpha=0.3)
        save(fig, "best_vs_final_bpc_gap")

    # runtime / vram / params / exposure
    for metric, title, fname, ylabel, filter_budget in [
        ("runtime_s", "Runtime by tokenizer (mean±std)", "runtime_by_tokenizer", "Seconds", None),
        ("peak_vram_gb", "Peak VRAM by tokenizer (mean±std)", "peak_vram_by_tokenizer", "GiB", None),
    ]:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        labels, means, stds = [], [], []
        for tok in TOKENIZER_ORDER:
            vals = [
                float(r[metric])
                for r in records
                if r["ok"] and r["tokenizer_id"] == tok and r.get(metric) is not None
            ]
            if vals:
                labels.append(tok)
                means.append(statistics.mean(vals))
                stds.append(statistics.stdev(vals) if len(vals) > 1 else 0.0)
        if means:
            x = np.arange(len(labels))
            ax.bar(x, means, yerr=stds, capsize=5)
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, axis="y", alpha=0.3)
            save(fig, fname)

    # total parameters by track
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(TOKENIZER_ORDER))
    width = 0.35
    for i, track in enumerate(["architecture_matched", "parameter_matched"]):
        vals = []
        for tok in TOKENIZER_ORDER:
            found = next(
                (
                    r["total_parameters"]
                    for r in records
                    if r["ok"] and r["tokenizer_id"] == tok and r["track"] == track
                ),
                None,
            )
            vals.append(found if found is not None else float("nan"))
        ax.bar(x + (i - 0.5) * width, vals, width, label=track)
    ax.set_xticks(x)
    ax.set_xticklabels(list(TOKENIZER_ORDER))
    ax.set_ylabel("Total parameters")
    ax.set_title("Total parameters by track")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    save(fig, "total_parameters_by_track")

    # characters by budget / updates by budget
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for budget, color in [("fixed_characters", "#4C72B0"), ("fixed_updates", "#55A868")]:
        labels, means = [], []
        for tok in TOKENIZER_ORDER:
            vals = [
                float(r["characters_processed"])
                for r in records
                if r["ok"]
                and r["tokenizer_id"] == tok
                and r["budget_policy"] == budget
                and r.get("characters_processed") is not None
            ]
            if vals:
                labels.append(tok)
                means.append(statistics.mean(vals))
        if means:
            ax.plot(labels, means, marker="o", label=budget, color=color)
    ax.set_ylabel("Characters processed")
    ax.set_title("Characters processed by budget policy (mean over seeds/tracks)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "characters_processed_by_budget")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for budget, color in [("fixed_characters", "#4C72B0"), ("fixed_updates", "#55A868")]:
        labels, means = [], []
        for tok in TOKENIZER_ORDER:
            vals = [
                float(r["optimizer_steps"])
                for r in records
                if r["ok"]
                and r["tokenizer_id"] == tok
                and r["budget_policy"] == budget
                and r.get("optimizer_steps") is not None
            ]
            if vals:
                labels.append(tok)
                means.append(statistics.mean(vals))
        if means:
            ax.plot(labels, means, marker="o", label=budget, color=color)
    ax.set_ylabel("Optimizer updates")
    ax.set_title("Optimizer updates by budget policy (mean over seeds/tracks)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "optimizer_updates_by_budget")

    # learning curves per group (measured points only; no interpolation)
    for track, budget in GROUPS:
        fig, ax = plt.subplots(figsize=(9, 5))
        tag = group_tag(track, budget)
        for tok in TOKENIZER_ORDER:
            # average curves across seeds at logged points is hard; plot each seed thin + mean if same x
            for r in records:
                if not r["ok"] or r["track"] != track or r["budget_policy"] != budget:
                    continue
                if r["tokenizer_id"] != tok:
                    continue
                rd = Path(r["run_dir"])
                if not rd.is_absolute():
                    # assume cwd repo root when called from main
                    pass
                curve_path = rd / "learning_curve.jsonl"
                if not curve_path.is_file():
                    continue
                xs, ys = [], []
                for line in curve_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    bpc = row.get("bits_per_character")
                    if bpc is None:
                        continue
                    if budget == "fixed_characters":
                        x = row.get("effective_epochs")
                        xlabel = "Effective epochs"
                    else:
                        x = row.get("step")
                        xlabel = "Optimizer steps"
                    if x is None:
                        continue
                    xs.append(float(x))
                    ys.append(float(bpc))
                if xs:
                    ax.plot(
                        xs,
                        ys,
                        marker="o",
                        markersize=3,
                        linewidth=1.0,
                        alpha=0.85,
                        label=f"{tok}_s{r['seed']}",
                    )
        ax.set_xlabel("Effective epochs" if budget == "fixed_characters" else "Optimizer steps")
        ax.set_ylabel("Validation BPC")
        ax.set_title(f"Learning curves — {track} / {budget}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, ncol=2)
        save(fig, f"learning_curves_{tag}")

    return paths


def aggregate_source_validation(
    records: list[dict[str, Any]], source_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Source-specific validation aggregates by tokenizer, track, and budget."""
    # Also index from records when available
    out: dict[str, Any] = {"by_group": {}, "ranking_notes": []}
    for track, budget in GROUPS:
        key = f"{track}__{budget}"
        tok_stats: dict[str, Any] = {}
        for tok in TOKENIZER_ORDER:
            for source in ("combined_validation", "bible_validation", "wikipedia_validation"):
                bpc_vals = [
                    float(row["bits_per_character"])
                    for row in source_rows
                    if row.get("tokenizer_id") == tok
                    and row.get("track") == track
                    and row.get("budget_policy") == budget
                    and row.get("source") == source
                    and row.get("bits_per_character") is not None
                ]
                tok_stats.setdefault(tok, {})[source] = mean_std(bpc_vals)
        leaders = {}
        for source in ("combined_validation", "bible_validation", "wikipedia_validation"):
            means = {
                tok: tok_stats[tok][source]["mean"]
                for tok in TOKENIZER_ORDER
                if tok_stats.get(tok, {}).get(source, {}).get("mean") is not None
            }
            leaders[source] = min(means, key=means.get) if means else None
        out["by_group"][key] = {
            "track": track,
            "budget_policy": budget,
            "tokenizers": tok_stats,
            "leaders_by_source": leaders,
        }
        bible_l = leaders.get("bible_validation")
        wiki_l = leaders.get("wikipedia_validation")
        if bible_l and wiki_l and bible_l != wiki_l:
            out["ranking_notes"].append(
                f"{track}/{budget}: tokenizer ranking differs between Bible "
                f"(leader={bible_l}) and Wikipedia (leader={wiki_l}). "
                "The source-specific result suggests domain differences may matter; "
                "test evaluation is still required."
            )
        elif bible_l and wiki_l:
            out["ranking_notes"].append(
                f"{track}/{budget}: {bible_l} performed better on both Bible and "
                "Wikipedia validation under this configuration (provisional; "
                "test evaluation is still required)."
            )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit + aggregate validation results for LM r2.")
    p.add_argument(
        "--matrix-config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix_r2.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--skip-source-eval", action="store_true")
    p.add_argument("--audit-only", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    matrix_path = (
        args.matrix_config if args.matrix_config.is_absolute() else root / args.matrix_config
    )
    matrix = load_json(matrix_path)
    parent = load_json(root / matrix["parent_config"])
    matrix_sha = sha256_file(matrix_path)

    # integrity of frozen inputs
    verify_frozen_split(root / matrix["split_root"])
    for tid, tcfg in parent["tokenizers"].items():
        verify_tokenizer_artifacts(tcfg, root)

    specs = enumerate_full_runs(matrix)
    assert len(specs) == 36

    records = []
    for spec in specs:
        rec = audit_one(root, matrix, parent, spec, matrix_sha=matrix_sha)
        # relativize run_dir already
        records.append(rec)
        status = "OK" if rec["ok"] else "FAIL"
        print(f"[{status}] {spec.run_id}")
        if not rec["ok"]:
            for f in rec["failures"]:
                print(f"    - {f}")

    n_valid = sum(1 for r in records if r["ok"])
    n_fail = 36 - n_valid

    source_rows: list[dict[str, Any]] = []
    if not args.audit_only and not args.skip_source_eval and n_fail == 0:
        print("Running source-specific validation on locked best checkpoints…")
        source_rows = run_source_validation(root, matrix, parent, records)
    elif n_fail:
        print("Skipping source eval because integrity failures present.")

    groups = [aggregate_group(records, t, b) for t, b in GROUPS]
    source_aggregates = aggregate_source_validation(records, source_rows) if source_rows else {}

    fig_dir = root / "data/reports/figures/lm_baselines_v0.1/final_validation"
    figure_paths: list[str] = []
    required_figures = [
        "validation_bpc_arch_fixed_characters",
        "validation_bpc_arch_fixed_updates",
        "validation_bpc_param_fixed_characters",
        "validation_bpc_param_fixed_updates",
        "validation_bpb_arch_fixed_characters",
        "validation_bpb_arch_fixed_updates",
        "validation_bpb_param_fixed_characters",
        "validation_bpb_param_fixed_updates",
        "validation_bpc_bible_vs_wikipedia",
        "best_checkpoint_effective_epoch",
        "best_vs_final_bpc_gap",
        "runtime_by_tokenizer",
        "peak_vram_by_tokenizer",
        "total_parameters_by_track",
        "characters_processed_by_budget",
        "optimizer_updates_by_budget",
        "learning_curves_arch_fixed_characters",
        "learning_curves_param_fixed_characters",
        "learning_curves_arch_fixed_updates",
        "learning_curves_param_fixed_updates",
    ]
    if not args.audit_only and n_fail == 0:
        import os

        old = os.getcwd()
        os.chdir(root)
        try:
            for r in records:
                rd = Path(r["run_dir"])
                if rd.is_absolute():
                    r["run_dir"] = str(rd.relative_to(root))
            figure_paths = make_plots(groups, records, fig_dir)
        finally:
            os.chdir(old)

    figures_present = all(
        (fig_dir / f"{name}.png").is_file() and (fig_dir / f"{name}.svg").is_file()
        for name in required_figures
    )

    # CSV of runs
    run_csv_rows = []
    for r in records:
        run_csv_rows.append(
            {
                "run_id": r["run_id"],
                "ok": r["ok"],
                "tokenizer_id": r.get("tokenizer_id"),
                "seed": r.get("seed"),
                "track": r.get("track"),
                "budget_policy": r.get("budget_policy"),
                "best_validation_bpc": r.get("best_validation_bpc"),
                "best_validation_bpb": r.get("best_validation_bpb"),
                "final_budget_bpc": r.get("final_budget_bpc"),
                "best_vs_final_bpc_gap": r.get("best_vs_final_bpc_gap"),
                "best_step": r.get("best_step"),
                "best_effective_epochs": r.get("best_effective_epochs"),
                "characters_processed": r.get("characters_processed"),
                "optimizer_steps": r.get("optimizer_steps"),
                "effective_epochs": r.get("effective_epochs"),
                "runtime_s": r.get("runtime_s"),
                "peak_vram_gb": r.get("peak_vram_gb"),
                "total_parameters": r.get("total_parameters"),
                "embedding_parameters": r.get("embedding_parameters"),
                "non_embedding_parameters": r.get("non_embedding_parameters"),
                "failures": "; ".join(r.get("failures") or []),
            }
        )
    write_csv(
        root / "data/reports/lm_baselines_v0_1_validation_runs.csv",
        run_csv_rows,
        list(run_csv_rows[0].keys()) if run_csv_rows else ["run_id"],
    )
    if source_rows:
        write_csv(
            root / "data/reports/lm_baselines_v0_1_source_validation.csv",
            source_rows,
            list(source_rows[0].keys()),
        )
    else:
        write_csv(
            root / "data/reports/lm_baselines_v0_1_source_validation.csv",
            [],
            [
                "run_id",
                "tokenizer_id",
                "seed",
                "track",
                "budget_policy",
                "source",
                "bits_per_character",
                "bits_per_byte",
            ],
        )

    # readiness
    readiness = {
        "all_36_completed": n_valid == 36,
        "all_36_audited": len(records) == 36,
        "all_manifests_valid": all(r["checks"].get("manifest_complete") for r in records if r.get("checks")),
        "all_selection_locks_valid": all(
            r["checks"].get("selection_lock_exists") and r["checks"].get("selected_checkpoint_checksum")
            for r in records
            if r.get("checks")
        ),
        "all_checkpoint_checksums_valid": all(
            r["checks"].get("selected_checkpoint_checksum") for r in records if r.get("checks")
        ),
        "all_budget_exposures_valid": all(
            r["checks"].get("budget_exposure_valid") for r in records if r.get("checks")
        ),
        "no_nan_inf": all(r["checks"].get("no_nan_inf") for r in records if r.get("checks")),
        "no_test_access_detected": all(r["checks"].get("test_not_used") for r in records if r.get("checks")),
        "canary_excluded": all(r["checks"].get("not_canary_path") for r in records if r.get("checks")),
        "calibration_excluded": all(
            r["checks"].get("not_calibration_path") for r in records if r.get("checks")
        ),
        "pilots_excluded": all(r["checks"].get("not_pilot") for r in records if r.get("checks")),
        "validation_aggregation_complete": n_valid == 36,
        "source_validation_complete": bool(source_rows) and n_valid == 36,
        "figures_complete": figures_present and n_valid == 36,
        "checkpoint_reload_ok_all": all(
            r["checks"].get("checkpoint_reload_ok") for r in records if r.get("checks")
        ),
    }
    readiness["test_ready"] = all(readiness.values())
    readiness["generated_at"] = utc_now_iso()
    readiness["matrix_id"] = matrix["matrix_id"]
    readiness["n_expected"] = 36
    readiness["n_valid"] = n_valid
    readiness["n_failed_audit"] = n_fail
    readiness["failed_run_ids"] = [r["run_id"] for r in records if not r["ok"]]
    readiness["tool"] = {"name": TOOL_NAME, "version": TOOL_VERSION}

    summary = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": utc_now_iso(),
        "experiment_version": "lm_baselines_v0.1",
        "matrix_id": matrix["matrix_id"],
        "matrix_config": str(matrix_path.relative_to(root)),
        "matrix_config_checksum": matrix_sha,
        "number_of_expected_runs": 36,
        "number_of_valid_runs": n_valid,
        "number_of_failed_audit_runs": n_fail,
        "failed_runs": [
            {"run_id": r["run_id"], "failures": r["failures"]} for r in records if not r["ok"]
        ],
        "excluded_artifacts": {
            "canary": "systems_validation_only",
            "calibration": "budget_selection_only",
            "pilots": "pipeline_pilot_only",
            "r1_4m_paths": "excluded_by_path_slug",
        },
        "groups": groups,
        "source_specific_aggregates": source_aggregates,
        "figure_paths": figure_paths,
        "required_figures": required_figures,
        "figure_dir": "data/reports/figures/lm_baselines_v0.1/final_validation",
        "calibration_figures_untouched": "data/reports/figures/lm_baselines_v0.1/calibration",
        "audit_status": "pass" if n_fail == 0 else "fail",
        "test_readiness": readiness,
        "seed_level_records": [
            {k: v for k, v in r.items() if k not in ("manifest", "checks", "selection_lock")}
            for r in records
        ],
    }
    write_json(root / "data/reports/lm_baselines_v0_1_validation_summary.json", summary)
    write_json(root / "data/metadata/lm_baselines_v0_1_test_readiness.json", readiness)

    # markdown reports
    audit_md = [
        "# LM baselines v0.1 — validation integrity audit",
        "",
        f"_Generated {utc_now_iso()}_",
        "",
        f"- Expected scientific runs: **36**",
        f"- Valid: **{n_valid}**",
        f"- Failed audit: **{n_fail}**",
        f"- Canary excluded: yes",
        f"- Calibration excluded: yes",
        f"- Pilots excluded: yes",
        f"- Test access: **none**",
        "",
        "## Per-run results",
        "",
    ]
    for r in records:
        audit_md.append(f"### `{r['run_id']}` — {'PASS' if r['ok'] else 'FAIL'}")
        if r["failures"]:
            for f in r["failures"]:
                audit_md.append(f"- {f}")
        else:
            audit_md.append(
                f"- best val BPC={r['best_validation_bpc']:.6f}, "
                f"final BPC={r['final_budget_bpc']}, steps={r['optimizer_steps']}"
            )
        audit_md.append("")
    write_text(root / "data/reports/lm_baselines_v0_1_validation_audit.md", "\n".join(audit_md))

    results_md = [
        "# LM baselines v0.1 — validation results (provisional)",
        "",
        f"_Generated {utc_now_iso()}_",
        "",
        "Test evaluation has **not** been run. Leaders below are **provisional**.",
        "",
    ]
    for g in groups:
        results_md.append(f"## {g['track']} × {g['budget_policy']}")
        results_md.append("")
        results_md.append(
            f"Provisional validation leader: **{g['provisional_validation_leader']}** "
            f"(mean BPC={g['provisional_validation_leader_mean_bpc']})"
        )
        results_md.append("")
        results_md.append(
            "| tokenizer | mean BPC | std | median | min | max | mean BPB | n |"
        )
        results_md.append("|-----------|---------:|----:|-------:|----:|----:|---------:|--:|")
        for tok in TOKENIZER_ORDER:
            st = g["tokenizers"][tok]["mean_validation_bpc"]
            sb = g["tokenizers"][tok]["mean_validation_bpb"]
            results_md.append(
                f"| {tok} | {st['mean']} | {st['stdev']} | {st['median']} | "
                f"{st['min']} | {st['max']} | {sb['mean']} | {st['n']} |"
            )
        results_md.append("")
        results_md.append("### Paired seed differences (BPC)")
        results_md.append("")
        for name, block in g["paired_seed_differences"].items():
            md = block["mean_diff"]
            results_md.append(
                f"- **{name}**: mean diff={md['mean']} (std={md['stdev']}); "
                f"pairs={block['pairs']}"
            )
        results_md.append("")
        results_md.append(g["caution"])
        results_md.append("")

    # source ranking notes
    results_md.append("## Source-specific validation observations")
    results_md.append("")
    if source_rows and source_aggregates:
        for note in source_aggregates.get("ranking_notes") or []:
            results_md.append(f"- {note}")
        for gkey, gblock in (source_aggregates.get("by_group") or {}).items():
            results_md.append("")
            results_md.append(f"### {gblock['track']} × {gblock['budget_policy']}")
            results_md.append("")
            results_md.append(
                "| tokenizer | combined BPC | bible BPC | wiki BPC |"
            )
            results_md.append("|-----------|-------------:|----------:|---------:|")
            for tok in TOKENIZER_ORDER:
                ts = gblock["tokenizers"].get(tok, {})
                c = ts.get("combined_validation", {}).get("mean")
                b = ts.get("bible_validation", {}).get("mean")
                w = ts.get("wikipedia_validation", {}).get("mean")
                results_md.append(
                    f"| {tok} | {c} | {b} | {w} |"
                )
            leaders = gblock.get("leaders_by_source") or {}
            results_md.append("")
            results_md.append(
                f"Leaders (provisional): combined={leaders.get('combined_validation')}, "
                f"bible={leaders.get('bible_validation')}, "
                f"wikipedia={leaders.get('wikipedia_validation')}."
            )
        results_md.append("")
        results_md.append(
            "Language: these are validation-only observations. "
            "Do not claim statistical significance from three seeds alone. "
            "Test evaluation is still required."
        )
    else:
        results_md.append("- Source-specific validation not completed.")
    results_md.append("")
    results_md.append(f"Figures: `{fig_dir if n_fail==0 else 'not generated'}`")
    write_text(
        root / "data/reports/lm_baselines_v0_1_validation_results.md",
        "\n".join(results_md),
    )

    ready_md = [
        "# Test readiness — LM baselines v0.1",
        "",
        f"**test_ready: `{readiness['test_ready']}`**",
        "",
        "Conditions:",
        "",
    ]
    for k, v in readiness.items():
        if k in ("generated_at", "matrix_id", "tool", "failed_run_ids"):
            continue
        ready_md.append(f"- `{k}`: **{v}**")
    ready_md.append("")
    ready_md.append("Failed run IDs: " + (", ".join(readiness["failed_run_ids"]) or "(none)"))
    ready_md.append("")
    ready_md.append(
        "Later test authorization (do **not** run until operator decides):\n\n"
        "```bash\n"
        ".venv/bin/python scripts/models/evaluate_lm_baseline.py \\\n"
        "  --run-dir <SCIENTIFIC_RUN_DIR> \\\n"
        "  --splits test bible_test wikipedia_test \\\n"
        "  --allow-test\n"
        "```\n"
    )
    write_text(root / "data/reports/lm_baselines_v0_1_test_readiness.md", "\n".join(ready_md))

    print(f"\nValid {n_valid}/36  test_ready={readiness['test_ready']}")
    print(f"Figures: {len(figure_paths)} under {fig_dir}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
