#!/usr/bin/env python3
"""Aggregate pilot/final LM baseline runs and write comparison report sections."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import load_json, utc_now_iso, write_json, write_text  # noqa: E402

TOOL_NAME = "compare_lm_baselines"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare LM baseline runs.")
    p.add_argument("--config", type=Path, default=Path("configs/models/lm_baselines_v0_1.json"))
    p.add_argument(
        "--matrix-config",
        type=Path,
        default=Path("configs/models/lm_baselines_v0_1_final_matrix.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--phase", choices=["pilot", "final"], default="pilot")
    p.add_argument(
        "--track",
        default="architecture_matched",
        choices=["architecture_matched", "parameter_matched"],
    )
    p.add_argument(
        "--authorize-test-evaluation",
        action="store_true",
        help="Evaluate locked checkpoints on test (only after all final runs locked).",
    )
    return p.parse_args(argv)

def stats(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0}
    return {
        "n": len(vals),
        "mean": statistics.mean(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "values": vals,
    }


def collect_runs(root: Path, config: dict[str, Any], track: str, phase: str) -> list[dict[str, Any]]:
    base = root / config["output_root"] / track
    runs = []
    if not base.is_dir():
        return runs
    # Paths excluded from final scientific stats
    exclude_path_parts = {
        "calibration",
        "fixed_characters",  # pre-r2 4M canary path slug (not fixed_characters_e30)
        "pilot",
    }
    for tok_dir in sorted(base.iterdir()):
        if not tok_dir.is_dir():
            continue
        for seed_dir in sorted(tok_dir.glob("seed_*")):
            phase_dir = seed_dir / phase
            # New layout: phase/budget_policy/manifest.json
            candidates = []
            if (phase_dir / "manifest.json").is_file():
                candidates.append(phase_dir)
            if phase_dir.is_dir():
                for sub in sorted(phase_dir.iterdir()):
                    if sub.is_dir() and (sub / "manifest.json").is_file():
                        candidates.append(sub)
            for run_dir in candidates:
                m = load_json(run_dir / "manifest.json")
                # Exclude pilot / calibration / pre-calibration canary from final stats
                if phase == "final":
                    if m.get("pilot_label") or m.get("phase") in ("pilot", "calibration"):
                        continue
                    # Old canary: budget target 4e6 or path ends with /fixed_characters
                    path_s = str(run_dir).replace("\\", "/")
                    if path_s.rstrip("/").endswith("/final/fixed_characters"):
                        m["_excluded_reason"] = "pre_calibration_systems_canary"
                        continue
                    if m.get("budget_policy") == "fixed_characters":
                        tgt = (m.get("budget") or {}).get("train_characters") or (
                            m.get("exposure") or {}
                        ).get("character_target")
                        if tgt is not None and int(tgt) == 4_000_000:
                            continue
                if phase == "pilot" and not m.get("pilot_label") and m.get("phase") != "pilot":
                    if m.get("phase") and m.get("phase") != "pilot":
                        continue
                m["_path"] = str(run_dir.relative_to(root))
                lock = run_dir / "selection_lock.json"
                if lock.is_file():
                    m["_selection_lock"] = load_json(lock)
                ev = run_dir / "eval_metrics.json"
                if ev.is_file():
                    m["_eval"] = load_json(ev)
                # Retain both best and final-budget metrics when present
                m["_best_checkpoint"] = m.get("best_checkpoint")
                m["_final_budget_metrics"] = m.get("final_budget_metrics") or (
                    (m.get("validation_history") or [None])[-1]
                )
                runs.append(m)
    return runs

def render_report(
    config: dict[str, Any],
    runs: list[dict[str, Any]],
    phase: str,
    track: str,
) -> str:
    lines = [
        f"# LM baselines v0.1 — {phase} ({track})",
        "",
        f"_Generated at {utc_now_iso()} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "## 1. Research question",
        "",
        "Under the same data and controlled training budget, which tokenizer "
        "(character, BPE-8000, Unigram-8000) achieves better validation/test BPC, "
        "sample efficiency, stability, generation quality, and compute efficiency?",
        "",
        "## 2. Hypotheses (locked before training)",
        "",
        f"- **H1 character:** {config['hypotheses']['H1_character']}",
        f"- **H2 BPE-8000:** {config['hypotheses']['H2_bpe_8000']}",
        f"- **H3 Unigram-8000:** {config['hypotheses']['H3_unigram_8000']}",
        "",
        "## 3. Corpus and split identity",
        "",
        f"- Corpus: `{config['corpus_version']}`",
        f"- Split: `{config['split_version']}` at `{config['split_root']}`",
        "",
        "## 4. Tokenizers",
        "",
        "- character, bpe_8000, unigram_8000 from `baselines_v0.1`",
        "",
        "## 5. Architecture",
        "",
        f"```json\n{json.dumps(config['architecture_matched'], indent=2)}\n```",
        "",
        "## 6. Parameter fairness",
        "",
        f"Track: **{track}**. Embedding parameter differences are reported per run.",
        "",
        "## 7. Compute-budget policy",
        "",
        f"Primary: fixed characters. Phase `{phase}` budget: "
        f"`{json.dumps(config['budget'][phase])}`",
        "",
        "## 8. Training configuration",
        "",
        f"```json\n{json.dumps(config['training'], indent=2)}\n```",
        "",
        f"## 9. {'Pilot' if phase=='pilot' else 'Final multi-seed'} results",
        "",
        "**Pilot results are not final multi-seed evidence.**" if phase == "pilot" else "",
        "",
        "| tokenizer | seed | params | emb | non-emb | steps | chars | val BPC | val BPB | time_s | peak_GB |",
        "|-----------|-----:|-------:|----:|--------:|------:|------:|--------:|--------:|-------:|--------:|",
    ]
    by_tok: dict[str, list[float]] = {}
    for m in runs:
        best = m.get("best_checkpoint") or {}
        pc = m.get("parameter_counts") or {}
        exp = m.get("exposure") or {}
        rt = m.get("runtime") or {}
        bpc = best.get("validation_bpc")
        bpb = best.get("validation_bpb")
        wall = rt.get("wall_clock_s")
        mem = rt.get("peak_gpu_memory_gb")
        bpc_s = "—" if bpc is None else f"{bpc:.4f}"
        bpb_s = "—" if bpb is None else f"{bpb:.4f}"
        wall_s = "—" if wall is None else f"{wall:.1f}"
        mem_s = "—" if mem is None else f"{mem:.2f}"
        lines.append(
            f"| {m.get('tokenizer_id')} | {m.get('seed')} | {pc.get('total')} | "
            f"{pc.get('embedding')} | {pc.get('non_embedding')} | "
            f"{exp.get('optimizer_steps')} | {exp.get('characters_processed')} | "
            f"{bpc_s} | {bpb_s} | {wall_s} | {mem_s} |"
        )
        if isinstance(bpc, (int, float)) and math.isfinite(bpc):
            by_tok.setdefault(m["tokenizer_id"], []).append(float(bpc))

    lines.extend(["", "### Multi-seed summary (validation BPC)", ""])
    for tok, vals in sorted(by_tok.items()):
        s = stats(vals)
        lines.append(
            f"- **{tok}:** mean={s.get('mean'):.4f} ± {s.get('stdev'):.4f} "
            f"(n={s.get('n')}, min={s.get('min'):.4f}, max={s.get('max'):.4f})"
            if s.get("n")
            else f"- **{tok}:** no data"
        )

    lines.extend(
        [
            "",
            "## 10–12. Validation / test BPC-BPB",
            "",
            "Validation BPC is primary for checkpoint selection. "
            "Test metrics appear only if `eval_metrics.json` contains test splits "
            "(after `--allow-test`).",
            "",
        ]
    )
    for m in runs:
        ev = m.get("_eval") or {}
        splits = ev.get("splits") or {}
        if not splits:
            continue
        lines.append(f"### {m.get('tokenizer_id')} seed {m.get('seed')}")
        for sn, met in splits.items():
            lines.append(
                f"- {sn}: BPC={met.get('bits_per_character')} BPB={met.get('bits_per_byte')}"
            )
        lines.append("")

    lines.extend(
        [
            "## 13. Source-specific results",
            "",
            "See per-run `eval_metrics.json` for bible_* and wikipedia_* splits when evaluated.",
            "",
            "## 14. Learning curves",
            "",
            "See each run's `validation_history.json` and `train_log.jsonl`.",
            "",
            "## 15. Throughput and memory",
            "",
            "See table peak_GB and runtime characters_per_second in manifests.",
            "",
            "## 16. Generation samples",
            "",
            f"Human-review scaffold: `{config.get('generation_review_path')}` (labels null).",
            "",
            "## 17. Human-review status",
            "",
            "Not filled automatically.",
            "",
            "## 18. Memorization diagnostics",
            "",
            "See per-run `memorization.json` when generated.",
            "",
            "## 19. Limitations",
            "",
            "- Small model / limited pilot character budget.",
            "- Architecture-matched track gives subword models more embedding parameters.",
            "- Token perplexity is not cross-comparable.",
            "- Generation quality is qualitative only.",
            "",
            "## 20. Conclusion",
            "",
            (
                "Pilot pipeline verification only — not final evidence."
                if phase == "pilot"
                else "See multi-seed means above; further replication may be needed."
            ),
            "",
            "## 21. Exact evidence motivating MthandiziTokenizer",
            "",
            "MthandiziTokenizer is **not** motivated by this pilot alone. "
            "Motivation requires final multi-seed BPC gaps, morphology probe review, "
            "and generation/memorization patterns. Do not implement morphology-aware "
            "tokenizers until final baselines complete.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config = load_json(
        args.config if args.config.is_absolute() else root / args.config
    )
    if args.authorize_test_evaluation:
        print(
            "error: test evaluation authorization requires all final runs locked "
            "and is intentionally not auto-chained. Use evaluate_lm_baseline.py "
            "--allow-test per locked run after formal completion.",
            file=sys.stderr,
        )
        print(
            "Refusing automatic test evaluation from compare for safety. "
            "Provide a dedicated test-eval pass only after matrix completion."
        )
        return 2

    runs = collect_runs(root, config, args.track, args.phase)
    out_dir = root / config["output_root"] / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        out_dir / f"{args.phase}_{args.track}_summary.json",
        {"phase": args.phase, "track": args.track, "n_runs": len(runs), "runs": runs},
    )
    report = render_report(config, runs, args.phase, args.track)
    write_text(out_dir / f"{args.phase}_{args.track}_report.md", report)
    if args.phase == "pilot":
        write_text(root / config["report_path"], report)
    print(f"Compared {len(runs)} runs → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
