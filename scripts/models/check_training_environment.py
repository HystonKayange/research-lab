#!/usr/bin/env python3
"""Verify training environment without launching training."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    build_gpt,
    env_metadata,
    load_json,
    resolve_arch,
    verify_frozen_split,
    verify_tokenizer_artifacts,
)
from matrix_common import enumerate_full_runs, make_run_id  # noqa: E402

TOOL_NAME = "check_training_environment"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check LM training environment.")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    cfg_path = args.config if args.config.is_absolute() else root / args.config
    matrix = load_json(cfg_path)
    parent = load_json(root / matrix.get("parent_config", "configs/models/lm_baselines_v0_1.json"))

    report: dict = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "ok": True,
        "errors": [],
        "warnings": [],
    }

    # env
    try:
        import torch

        report["torch_version"] = torch.__version__
        report["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            report["gpu_name"] = torch.cuda.get_device_name(0)
            free, total = torch.cuda.mem_get_info()
            report["vram_free_gb"] = free / (1024**3)
            report["vram_total_gb"] = total / (1024**3)
        else:
            report["warnings"].append("CUDA not available — real final training expects GPU")
    except ImportError:
        report["ok"] = False
        report["errors"].append("torch not installed")

    report["environment"] = env_metadata(root)
    report["python"] = sys.version

    # splits
    try:
        report["split_verification"] = verify_frozen_split(root / matrix["split_root"])
    except Exception as e:  # noqa: BLE001
        report["ok"] = False
        report["errors"].append(f"split: {e}")

    # tokenizers
    report["tokenizers"] = {}
    for tid, tcfg in parent["tokenizers"].items():
        try:
            report["tokenizers"][tid] = verify_tokenizer_artifacts(tcfg, root)
        except Exception as e:  # noqa: BLE001
            report["ok"] = False
            report["errors"].append(f"tokenizer {tid}: {e}")

    # parameter matching verification
    rows = []
    # character arch-matched as target
    arch_c = resolve_arch(
        {
            "architecture_matched": matrix["architecture_matched"],
            "parameter_matched": {
                **matrix["parameter_matched"],
                "overrides": matrix["parameter_matched"]["overrides"],
            },
        },
        "architecture_matched",
        "character",
    )
    # vocab sizes approximate
    vocabs = {"character": 915, "bpe_8000": 8000, "unigram_8000": 8000}
    m_char = build_gpt(
        vocab_size=vocabs["character"],
        n_layer=arch_c["n_layer"],
        n_embd=arch_c["n_embd"],
        n_head=arch_c["n_head"],
        n_inner=arch_c["n_inner"],
        context_length=arch_c["context_length"],
        dropout=0.0,
        tie_embeddings=True,
    )
    target_total = m_char.count_parameters()["total"]
    tol = float(matrix["parameter_matched"]["tolerance_fraction"])
    param_ok = True
    for tid in matrix["tokenizers"]:
        for track in matrix["tracks"]:
            arch = resolve_arch(
                {
                    "architecture_matched": matrix["architecture_matched"],
                    "parameter_matched": {
                        **matrix["parameter_matched"],
                        "overrides": matrix["parameter_matched"]["overrides"],
                    },
                },
                track,
                tid,
            )
            if arch["n_embd"] % arch["n_head"] != 0:
                report["errors"].append(f"{tid}/{track}: d_model not divisible by heads")
                param_ok = False
            m = build_gpt(
                vocab_size=vocabs[tid],
                n_layer=arch["n_layer"],
                n_embd=arch["n_embd"],
                n_head=arch["n_head"],
                n_inner=arch["n_inner"],
                context_length=arch["context_length"],
                dropout=0.0,
                tie_embeddings=True,
            )
            pc = m.count_parameters()
            pct = (pc["total"] - target_total) / target_total
            row = {
                "tokenizer": tid,
                "track": track,
                "total": pc["total"],
                "embedding": pc["embedding"],
                "non_embedding": pc["non_embedding"],
                "pct_diff_vs_char_arch": pct,
            }
            rows.append(row)
            if track == "parameter_matched" and abs(pct) > tol:
                param_ok = False
                report["warnings"].append(
                    f"parameter_matched {tid} off target by {pct*100:.2f}% (tol ±{tol*100:.1f}%)"
                )
    report["parameter_rows"] = rows
    report["parameter_matched_within_tolerance"] = param_ok
    if not param_ok:
        # not hard-fail environment if arch still valid — warn for operator
        report["warnings"].append(
            "Parameter-matched tolerance not fully met; review before --stage full"
        )

    # disk
    out = root / matrix["output_root"]
    out.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(out)
    report["disk_free_gb"] = usage.free / (1024**3)
    if usage.free < 20 * (1024**3):
        report["warnings"].append("Less than 20 GiB free disk")

    # matrix size
    full = enumerate_full_runs(matrix)
    report["planned_full_runs"] = len(full)
    report["expected_run_count"] = matrix.get("expected_run_count")
    if len(full) != int(matrix.get("expected_run_count", 36)):
        report["ok"] = False
        report["errors"].append(
            f"enumeration {len(full)} != expected {matrix.get('expected_run_count')}"
        )

    report["canary_run_id"] = make_run_id(
        matrix["canary"]["tokenizer"],
        matrix["canary"]["seed"],
        matrix["canary"]["track"],
        matrix["canary"]["budget_policy"],
        phase=matrix["canary"].get("phase", "final"),
        matrix_id=matrix["matrix_id"],
    )
    report["output_paths"] = {
        "output_root": matrix["output_root"],
        "status": matrix["status_path"],
        "canary_acceptance": matrix["canary_acceptance_path"],
    }

    # write parameter report
    lines = [
        "# Parameter matching report",
        "",
        f"Target (character architecture_matched) total params: **{target_total}**",
        f"Tolerance: ±{tol*100:.1f}%",
        "",
        "| tokenizer | track | total | embedding | non_embedding | % vs char-arch |",
        "|-----------|-------|------:|----------:|--------------:|---------------:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['tokenizer']} | {r['track']} | {r['total']} | {r['embedding']} | "
            f"{r['non_embedding']} | {r['pct_diff_vs_char_arch']*100:.2f}% |"
        )
    (root / matrix["parameter_report_path"]).parent.mkdir(parents=True, exist_ok=True)
    (root / matrix["parameter_report_path"]).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(json.dumps(report, indent=2, default=str))
    if report["errors"]:
        print("ENVIRONMENT CHECK: FAIL", file=sys.stderr)
        return 1
    print("ENVIRONMENT CHECK: OK (see warnings if any)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
