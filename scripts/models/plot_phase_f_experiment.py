#!/usr/bin/env python3
"""Create a presentation-ready graph from frozen Phase-F results only."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data/reports/phase_f_lm_results_v0_1.json"
OUT_DIR = ROOT / "data/reports/figures/phase_f"


def main() -> int:
    import matplotlib.pyplot as plt
    import numpy as np

    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    conditions = result["conditions"]
    keys = [
        ("parameter_matched_x_fixed_characters", "Param. × fixed char"),
        ("architecture_matched_x_fixed_characters", "Arch. × fixed char"),
        ("parameter_matched_x_fixed_updates", "Param. × fixed updates"),
        ("architecture_matched_x_fixed_updates", "Arch. × fixed updates"),
    ]

    unigram = [conditions[k]["unigram_8000"]["validation_bpc"]["mean"] for k, _ in keys]
    unigram_std = [conditions[k]["unigram_8000"]["validation_bpc"]["stdev"] for k, _ in keys]
    statbound = [conditions[k]["statbound"]["validation_bpc"]["mean"] for k, _ in keys]
    statbound_std = [conditions[k]["statbound"]["validation_bpc"]["std"] for k, _ in keys]
    labels = [label for _, label in keys]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, (ax_mean, ax_delta) = plt.subplots(
        1,
        2,
        figsize=(15, 8.4),
        gridspec_kw={"width_ratios": [1.15, 1]},
        facecolor="#f8fafc",
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.83, bottom=0.22, wspace=0.25)

    blue = "#2563eb"
    orange = "#ea580c"
    green = "#059669"
    ink = "#0f172a"
    muted = "#475569"
    grid = "#cbd5e1"

    # Panel A: aggregate BPC with seed standard deviations.
    x = np.arange(len(labels))
    width = 0.34
    ax_mean.bar(
        x - width / 2,
        unigram,
        width,
        yerr=unigram_std,
        capsize=4,
        color=blue,
        alpha=0.9,
        label="Unigram8k",
        error_kw={"ecolor": ink, "elinewidth": 1, "capthick": 1},
    )
    ax_mean.bar(
        x + width / 2,
        statbound,
        width,
        yerr=statbound_std,
        capsize=4,
        color=orange,
        alpha=0.9,
        label="StatBound λ=0.25",
        error_kw={"ecolor": ink, "elinewidth": 1, "capthick": 1},
    )
    ax_mean.set_title("Validation BPC by frozen LM regime", loc="left", color=ink, pad=12)
    ax_mean.set_ylabel("Validation BPC (lower is better)", color=muted)
    ax_mean.set_xticks(x, labels, rotation=18, ha="right")
    ax_mean.set_ylim(min(unigram + statbound) - 0.0045, max(unigram + statbound) + 0.0045)
    ax_mean.grid(axis="y", color=grid, linewidth=0.8, alpha=0.7)
    ax_mean.set_axisbelow(True)
    ax_mean.spines[["top", "right"]].set_visible(False)
    ax_mean.legend(frameon=False, loc="upper left", fontsize=9)

    # Panel B: each seed's paired difference, where negative favors StatBound.
    for idx, (key, label) in enumerate(keys):
        rows = conditions[key]["statbound"]["per_seed"]
        deltas = [row["delta_bpc_statbound_minus_unigram"] for row in rows]
        jitter = np.linspace(-0.09, 0.09, len(deltas))
        colors = [green if value < 0 else orange for value in deltas]
        ax_delta.scatter(
            np.full(len(deltas), idx) + jitter,
            deltas,
            s=65,
            c=colors,
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
        )
        ax_delta.plot([idx - 0.1, idx + 0.1], [sum(deltas) / len(deltas)] * 2, color=ink, linewidth=2.2, zorder=2)
        for seed_idx, (row, delta) in enumerate(zip(rows, deltas)):
            ax_delta.annotate(
                str(row["seed"]),
                (idx + jitter[seed_idx], delta),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=7,
                color=muted,
            )
    ax_delta.axhline(0, color=ink, linewidth=1.1)
    ax_delta.set_title("Per-seed change: StatBound − Unigram", loc="left", color=ink, pad=12)
    ax_delta.set_ylabel("Δ validation BPC (negative is better)", color=muted)
    ax_delta.set_xticks(x, labels, rotation=18, ha="right")
    ax_delta.grid(axis="y", color=grid, linewidth=0.8, alpha=0.7)
    ax_delta.set_axisbelow(True)
    ax_delta.spines[["top", "right"]].set_visible(False)
    ax_delta.text(
        0.02,
        0.98,
        "green = StatBound better\norange = StatBound worse\nblack line = mean",
        transform=ax_delta.transAxes,
        va="top",
        fontsize=8,
        color=muted,
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": grid, "alpha": 0.9},
    )

    primary = conditions["parameter_matched_x_fixed_characters"]
    primary_delta = primary["delta"]["mean_bpc_statbound_minus_unigram"]
    seeds_better = primary["delta"]["seeds_beating_unigram"]
    fig.suptitle(
        "StatBound V1 (λ=0.25): Phase-F validation experiment",
        x=0.07,
        y=0.96,
        ha="left",
        fontsize=20,
        fontweight="bold",
        color=ink,
    )
    fig.text(
        0.07,
        0.905,
        "Frozen protocol • 3 seeds • lower BPC is better • error bars show seed standard deviation",
        fontsize=10,
        color=muted,
    )
    fig.text(
        0.07,
        0.075,
        f"PRIMARY SC1: FAIL — Δ {primary_delta:+.6f} BPC; {seeds_better}/3 seeds improved.   |   SC2: PASS   |   SC4 morphology: FAIL (frozen Phase C)",
        fontsize=10,
        color=ink,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#e2e8f0", "edgecolor": "none"},
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / "phase_f_statbound_v1_experiment_v0_1.png"
    svg = OUT_DIR / "phase_f_statbound_v1_experiment_v0_1.svg"
    fig.savefig(png, dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(svg, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(json.dumps({"png": str(png.relative_to(ROOT)), "svg": str(svg.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
