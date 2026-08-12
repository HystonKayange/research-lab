#!/usr/bin/env python3
"""Compare multiple LM runs / tokenizers from manifests (no training).

Supports post-matrix comparisons when multiple completed runs exist.
Does not fabricate missing seed points.
"""

from __future__ import annotations

import argparse
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

from lm_common import load_json  # noqa: E402

TOOL_NAME = "plot_lm_comparisons"
TOOL_VERSION = "0.1.0"


def discover_runs(root: Path, base: Path) -> list[Path]:
    runs = []
    if not base.is_dir():
        return runs
    for man in base.rglob("manifest.json"):
        # skip pilot unless requested later
        runs.append(man.parent)
    return sorted(runs)


def load_run(run_dir: Path) -> dict[str, Any] | None:
    man_path = run_dir / "manifest.json"
    if not man_path.is_file():
        return None
    m = load_json(man_path)
    m["_run_dir"] = str(run_dir)
    lock = run_dir / "selection_lock.json"
    if lock.is_file():
        m["_selection_lock"] = load_json(lock)
    curve = run_dir / "learning_curve.jsonl"
    if curve.is_file():
        rows = []
        for line in curve.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        m["_curve"] = rows
    return m


def mean_std(vals: list[float]) -> dict[str, float | None]:
    if not vals:
        return {"n": 0, "mean": None, "stdev": None}
    return {
        "n": len(vals),
        "mean": statistics.mean(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
        "median": statistics.median(vals),
    }


def bar_compare(
    labels: list[str],
    values: list[float],
    *,
    yerr: list[float] | None,
    title: str,
    ylabel: str,
    out_base: Path,
) -> list[Path]:
    import matplotlib.pyplot as plt
    import numpy as np

    if not labels or not values:
        return []
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(labels))
    ax.bar(x, values, yerr=yerr, capsize=4, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    paths = []
    for ext in ("png", "svg"):
        p = out_base.with_suffix(f".{ext}")
        fig.savefig(p, dpi=150 if ext == "png" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def multi_curve(
    series: dict[str, tuple[list[float], list[float]]],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    out_base: Path,
) -> list[Path]:
    import matplotlib.pyplot as plt

    if not series:
        return []
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for name, (xs, ys) in series.items():
        if not xs:
            continue
        ax.plot(xs, ys, marker="o", label=name, linewidth=1.4, markersize=4)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    paths = []
    for ext in ("png", "svg"):
        p = out_base.with_suffix(f".{ext}")
        fig.savefig(p, dpi=150 if ext == "png" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def generate_comparisons(
    runs: list[dict[str, Any]],
    out_dir: Path,
    *,
    exclude_pilot: bool = True,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    filtered = []
    for m in runs:
        if exclude_pilot and (m.get("pilot_label") or m.get("phase") == "pilot"):
            continue
        filtered.append(m)

    # Group by tokenizer × track × budget
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in filtered:
        key = f"{m.get('tokenizer_id')}|{m.get('track')}|{m.get('budget_policy')}"
        groups[key].append(m)

    summary_rows = []
    bar_labels, bar_means, bar_stds = [], [], []
    for key, items in sorted(groups.items()):
        bpcs = []
        for m in items:
            b = (m.get("best_checkpoint") or {}).get("validation_bpc")
            if isinstance(b, (int, float)) and math.isfinite(float(b)):
                bpcs.append(float(b))
        st = mean_std(bpcs)
        tok, track, budget = key.split("|")
        row = {
            "tokenizer": tok,
            "track": track,
            "budget_policy": budget,
            "seeds": [m.get("seed") for m in items],
            "validation_bpc": st,
            "n_runs": len(items),
        }
        summary_rows.append(row)
        if st["mean"] is not None:
            bar_labels.append(f"{tok}\n{track[:4]}/{budget[:5]}")
            bar_means.append(st["mean"])
            bar_stds.append(st["stdev"] or 0.0)

    written: list[str] = []
    if bar_means:
        paths = bar_compare(
            bar_labels,
            bar_means,
            yerr=bar_stds,
            title="Validation BPC by tokenizer/track/budget (mean±std over available seeds)",
            ylabel="Validation BPC (lower better)",
            out_base=out_dir / "val_bpc_mean_by_group",
        )
        written.extend(str(p) for p in paths)

    # Learning curves overlay for groups with curves
    series_epochs: dict[str, tuple[list[float], list[float]]] = {}
    series_chars: dict[str, tuple[list[float], list[float]]] = {}
    for m in filtered:
        curve = m.get("_curve") or []
        if not curve:
            continue
        label = f"{m.get('tokenizer_id')}_s{m.get('seed')}"
        xs_e, ys_e, xs_c, ys_c = [], [], [], []
        for r in curve:
            bpc = r.get("bits_per_character")
            if bpc is None or not math.isfinite(float(bpc)):
                continue
            if r.get("effective_epochs") is not None:
                xs_e.append(float(r["effective_epochs"]))
                ys_e.append(float(bpc))
            if r.get("characters_processed") is not None:
                xs_c.append(float(r["characters_processed"]))
                ys_c.append(float(bpc))
        if xs_e:
            series_epochs[label] = (xs_e, ys_e)
        if xs_c:
            series_chars[label] = (xs_c, ys_c)

    written.extend(
        str(p)
        for p in multi_curve(
            series_epochs,
            title="Validation BPC vs effective epochs (available runs)",
            xlabel="Effective epochs",
            ylabel="Validation BPC",
            out_base=out_dir / "val_bpc_curves_vs_epochs",
        )
    )
    written.extend(
        str(p)
        for p in multi_curve(
            series_chars,
            title="Validation BPC vs characters (available runs)",
            xlabel="Characters processed",
            ylabel="Validation BPC",
            out_base=out_dir / "val_bpc_curves_vs_characters",
        )
    )

    # Parameter / runtime / VRAM bars if present
    for metric_key, title, fname, ylabel in [
        (("parameter_counts", "total"), "Total parameters", "params_total", "Parameters"),
        (("runtime", "wall_clock_s"), "Wall-clock time", "runtime_s", "Seconds"),
        (("runtime", "peak_gpu_memory_gb"), "Peak VRAM", "peak_vram_gb", "GiB"),
    ]:
        labels, vals = [], []
        for m in filtered:
            a, b = metric_key
            v = (m.get(a) or {}).get(b)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                labels.append(f"{m.get('tokenizer_id')}_s{m.get('seed')}")
                vals.append(float(v))
        if vals:
            paths = bar_compare(
                labels,
                vals,
                yerr=None,
                title=title,
                ylabel=ylabel,
                out_base=out_dir / fname,
            )
            written.extend(str(p) for p in paths)

    # Paired seed differences when same seed across tokenizers (arch+chars)
    paired = []
    by_seed_tok: dict[tuple[Any, str], float] = {}
    for m in filtered:
        if m.get("track") != "architecture_matched":
            continue
        if m.get("budget_policy") not in (None, "fixed_characters"):
            continue
        bpc = (m.get("best_checkpoint") or {}).get("validation_bpc")
        if isinstance(bpc, (int, float)) and math.isfinite(float(bpc)):
            by_seed_tok[(m.get("seed"), m.get("tokenizer_id"))] = float(bpc)
    seeds = sorted({s for s, _t in by_seed_tok})
    toks = sorted({t for _s, t in by_seed_tok})
    for s in seeds:
        row = {"seed": s}
        for t in toks:
            row[t] = by_seed_tok.get((s, t))
        if "bpe_8000" in row and "character" in row and row["bpe_8000"] and row["character"]:
            row["bpe_minus_char_bpc"] = row["bpe_8000"] - row["character"]
        if "unigram_8000" in row and "bpe_8000" in row and row["unigram_8000"] and row["bpe_8000"]:
            row["uni_minus_bpe_bpc"] = row["unigram_8000"] - row["bpe_8000"]
        paired.append(row)

    summary = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "n_runs_loaded": len(filtered),
        "groups": summary_rows,
        "paired_seed_diffs_architecture_matched_fixed_characters": paired,
        "plots": written,
        "notes": [
            "No fabricated points; missing seeds simply reduce n.",
            "Mean±std over available seeds only — not significance claims.",
            "Bible vs Wikipedia require eval_metrics with source splits.",
        ],
    }
    (out_dir / "comparison_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot LM run comparisons.")
    p.add_argument(
        "--runs-root",
        type=Path,
        default=Path("data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"),
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/reports/figures/lm_baselines_v0.1/comparisons"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--include-pilot", action="store_true")
    p.add_argument(
        "--run-dir",
        action="append",
        default=None,
        help="Optional explicit run dir(s); can repeat",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("error: matplotlib required", file=sys.stderr)
        return 2

    runs: list[dict[str, Any]] = []
    if args.run_dir:
        for rd in args.run_dir:
            p = Path(rd) if Path(rd).is_absolute() else root / rd
            m = load_run(p)
            if m:
                runs.append(m)
    else:
        base = args.runs_root if args.runs_root.is_absolute() else root / args.runs_root
        for rd in discover_runs(root, base):
            m = load_run(rd)
            if m:
                runs.append(m)

    out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    summary = generate_comparisons(
        runs, out_dir, exclude_pilot=not args.include_pilot
    )
    print(json.dumps({"n_runs": summary["n_runs_loaded"], "plots": summary["plots"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
