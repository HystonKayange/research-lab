#!/usr/bin/env python3
"""Publication-quality figures for the empirical paper. Frozen results only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.tokenizers.statbound.nbest_oracle import (  # noqa: E402
    classify_oracle_change,
    gold_miss_zone_counts,
)

PHASE_C = ROOT / "data/reports/phase_c_morphology_v0_2_results.json"
PHASE_F = ROOT / "data/reports/phase_f_lm_results_v0_1.json"
ORACLE = ROOT / "data/reports/unigram_nbest_oracle_v0_1.json"
FIG = ROOT / "data/reports/figures/paper_v0_1"

# Okabe–Ito, colorblind-safe
C_BLUE = "#0072B2"
C_VERM = "#D55E00"
C_GREEN = "#009E73"
C_SKY = "#56B4E9"
C_GOLD = "#E69F00"
C_PURPLE = "#CC79A7"
C_INK = "#222222"
C_GRID = "#E6E2DA"
C_BG = "#FFFcf7"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "semibold",
            "axes.labelsize": 11,
            "axes.edgecolor": C_INK,
            "axes.labelcolor": C_INK,
            "axes.facecolor": C_BG,
            "figure.facecolor": C_BG,
            "xtick.color": C_INK,
            "ytick.color": C_INK,
            "text.color": C_INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "savefig.bbox": "tight",
            "savefig.facecolor": C_BG,
            "legend.frameon": False,
        }
    )
    return plt


def save(fig, plt, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png")
    fig.savefig(FIG / f"{name}.svg")
    plt.close(fig)


def annotate_bars(ax, bars, fmt="{:.0f}", dy=0.015):
    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + span * dy,
            fmt.format(h),
            ha="center",
            va="bottom",
            fontsize=9,
        )


def fig_prf(plt, phase_c, oracle) -> None:
    systems = [
        ("BPE8k", phase_c["systems"]["bpe_8000"]["morphology"]["aggregate"], C_GOLD),
        ("Unigram8k", phase_c["systems"]["unigram_8000"]["morphology"]["aggregate"], C_BLUE),
        ("StatBound V1", phase_c["systems"]["statbound_lambda_0_25"]["morphology"]["aggregate"], C_VERM),
        ("Best-of-16 oracle", oracle["f1_oracle"]["macro"], C_GREEN),
    ]
    metrics = [("boundary_precision", "Precision"), ("boundary_recall", "Recall"), ("boundary_f1", "F1")]
    x = list(range(len(metrics)))
    width = 0.18
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    for i, (name, agg, color) in enumerate(systems):
        vals = [agg[k] for k, _ in metrics]
        offs = [j + (i - 1.5) * width for j in x]
        bars = ax.bar(offs, vals, width, label=name, color=color, zorder=3)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x, [lab for _, lab in metrics])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.set_title("Unigram beats BPE on morphology; StatBound copies Unigram; the oracle gains recall")
    ax.axhline(0.5551, color=C_BLUE, ls=":", lw=0.8, alpha=0.5)
    ax.legend(ncol=2, loc="upper left", fontsize=9)
    ax.yaxis.grid(True, color=C_GRID, zorder=0)
    save(fig, plt, "fig01_prf_comparison")


def fig_miss_location(plt, uni_miss, ora_miss) -> None:
    labels = ["Left edge\nprefix / TAM / NEG", "Right edge\nmostly final -a / -e", "Internal\nextensions etc."]
    keys = ["left_edge", "right_edge", "internal"]
    u = [uni_miss[k] for k in keys]
    o = [ora_miss[k] for k in keys]
    x = list(range(3))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    b1 = ax.bar([i - w / 2 for i in x], u, w, label="Missed by Unigram top-1", color=C_BLUE, zorder=3)
    b2 = ax.bar([i + w / 2 for i in x], o, w, label="Still missing after best-of-16", color=C_VERM, zorder=3)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Missed gold boundaries")
    ax.set_title("Prefixes are already in the n-best list; final vowels mostly are not")
    ax.legend(loc="upper right")
    ax.yaxis.grid(True, color=C_GRID, zorder=0)
    annotate_bars(ax, list(b1) + list(b2), dy=0.012)
    # recovery callouts
    for i, (a, b) in enumerate(zip(u, o)):
        rec = a - b
        ax.annotate(
            f"−{rec} recovered",
            xy=(i, (a + b) / 2),
            xytext=(i + 0.42, (a + b) / 2 + 8),
            fontsize=8,
            color=C_GREEN,
            arrowprops=dict(arrowstyle="-", color=C_GREEN, lw=0.7),
        )
    save(fig, plt, "fig02_missed_boundaries_by_location")


def fig_oracle_types(plt, classes) -> None:
    labels = [
        "Clean prefix-only\ngold adds",
        "Other gold-\nimproving changes",
        "F1 gain with\nfalse-positive cuts",
    ]
    vals = [classes["clean_prefix"], classes["mixed_gold"], classes["junk_fp"]]
    colors = [C_GREEN, C_BLUE, C_VERM]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    bars = ax.bar(labels, vals, color=colors, zorder=3)
    ax.set_ylabel("Words where oracle ≠ Unigram")
    ax.set_title("The +0.24 F1 oracle mixes legitimate prefix harvests with metric-lucky junk")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.yaxis.grid(True, color=C_GRID, zorder=0)
    annotate_bars(ax, bars, dy=0.02)
    ax.text(0.98, 0.96, "n = 125 changed words", transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#555")
    save(fig, plt, "fig03_oracle_change_types")


def fig_rank_hist(plt, hist: dict) -> None:
    ranks = list(range(1, 17))
    counts = [int(hist.get(str(r), 0)) for r in ranks]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    colors = [C_BLUE if r == 1 else C_SKY if r <= 4 else C_GOLD if r <= 8 else C_VERM for r in ranks]
    bars = ax.bar(ranks, counts, color=colors, zorder=3)
    ax.set_xlabel("Unigram n-best rank of the F1-oracle choice")
    ax.set_ylabel("Development items")
    ax.set_title("Most unused morphology sits near the top of the n-best list (median rank 4)")
    ax.set_xticks(ranks)
    ax.yaxis.grid(True, color=C_GRID, zorder=0)
    # cumulative line
    ax2 = ax.twinx()
    cum = []
    s = 0
    total = sum(counts)
    for c in counts:
        s += c
        cum.append(100.0 * s / total)
    ax2.plot(ranks, cum, color=C_PURPLE, marker="o", ms=4, lw=1.6, label="cumulative %")
    ax2.set_ylabel("Cumulative % of items")
    ax2.set_ylim(0, 105)
    ax2.spines["top"].set_visible(False)
    ax2.legend(loc="center right")
    save(fig, plt, "fig04_oracle_rank_histogram")


def fig_by_gold_pieces(plt, rows) -> None:
    # rows: list of {gold_piece_count, n, unigram_f1, oracle_f1}
    xs, u, o, ns = [], [], [], []
    for r in rows:
        if r["unigram_f1"] is None:
            continue
        xs.append(int(r["gold_piece_count"]))
        u.append(r["unigram_f1"])
        o.append(r["oracle_f1"])
        ns.append(r["n"])
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    ax.plot(xs, u, "o-", color=C_BLUE, lw=2, ms=7, label="Unigram top-1")
    ax.plot(xs, o, "s-", color=C_GREEN, lw=2, ms=7, label="Best-of-16 oracle")
    ax.fill_between(xs, u, o, color=C_GREEN, alpha=0.12)
    for x, n, yu, yo in zip(xs, ns, u, o):
        ax.text(x, min(yu, yo) - 0.045, f"n={n}", ha="center", fontsize=8, color="#666")
    ax.set_xlabel("Gold morpheme count (Level-B)")
    ax.set_ylabel("Macro boundary F1")
    ax.set_ylim(0.35, 0.95)
    ax.set_xticks(xs)
    ax.set_title("Unigram collapses on longer words; n-best room grows with morphological complexity")
    ax.legend(loc="lower left")
    ax.yaxis.grid(True, color=C_GRID)
    save(fig, plt, "fig05_f1_by_gold_piece_count")


def fig_compat(plt) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4))
    ax = axes[0]
    sizes = [41, 73, 1]
    labels = ["Higher compat\n41/115", "Equal compat\n73/115", "Lower compat\n1/115"]
    colors = [C_GREEN, C_GOLD, C_VERM]
    wedges, *_ = ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.52, edgecolor=C_BG, linewidth=2),
    )
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(-0.15, 0.5), fontsize=8.5)
    ax.set_title("Does compat point at the better-F1 candidate?", fontsize=11)
    ax2 = axes[1]
    names = ["Unigram\ntop-1", "Max-compat\noracle", "Best-F1\noracle"]
    vals = [0.5551, 0.5169, 0.7913]
    cols = [C_BLUE, C_VERM, C_GREEN]
    bars = ax2.bar(names, vals, color=cols, zorder=3)
    ax2.set_ylim(0, 1.0)
    ax2.set_ylabel("Macro boundary F1")
    ax2.set_title("Picking max-compat would hurt F1", fontsize=11)
    ax2.yaxis.grid(True, color=C_GRID, zorder=0)
    annotate_bars(ax2, bars, fmt="{:.2f}", dy=0.02)
    fig.suptitle("V1’s productivity score is the wrong auxiliary signal", fontsize=13, fontweight="semibold", y=1.02)
    fig.tight_layout()
    save(fig, plt, "fig06_compat_alignment")


def fig_lm(plt, phase_f) -> None:
    primary = phase_f["conditions"]["parameter_matched_x_fixed_characters"]
    seeds, uni, sb = [], [], []
    for rec in primary["statbound"]["per_seed"]:
        seeds.append(str(rec["seed"]))
        uni.append(rec["unigram_validation_bpc"])
        sb.append(rec["statbound_validation_bpc"])
    seeds.append("mean")
    uni.append(primary["unigram_8000"]["validation_bpc"]["mean"])
    sb.append(primary["statbound"]["validation_bpc"]["mean"])
    x = list(range(len(seeds)))
    w = 0.34
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    ax.bar([i - w / 2 for i in x], uni, w, label="Unigram8k", color=C_BLUE, zorder=3)
    ax.bar([i + w / 2 for i in x], sb, w, label="StatBound λ*=0.25", color=C_VERM, zorder=3)
    ax.set_xticks(x, seeds)
    ax.set_xlabel("Random seed")
    ax.set_ylabel("Validation BPC  (lower is better)")
    ax.set_title("Primary LM comparison: StatBound ≈ Unigram (SC1 fail; 1/3 seeds better)")
    lo = min(uni + sb) - 0.0012
    hi = max(uni + sb) + 0.0014
    ax.set_ylim(lo, hi)
    ax.legend(loc="upper right")
    ax.yaxis.grid(True, color=C_GRID, zorder=0)
    save(fig, plt, "fig07_primary_lm_bpc")


def fig_schematic(plt) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("Two different problems, one n-best list", loc="left", pad=8)

    def box(x, y, w, h, text, fc, ec):
        from matplotlib.patches import FancyBboxPatch

        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12", facecolor=fc, edgecolor=ec, lw=1.4)
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.2, color=C_INK)

    box(0.3, 3.6, 2.6, 1.6, "Unigram top-1\nundersegments\nAnali+gawa", "#E8F1F8", C_BLUE)
    box(3.7, 4.35, 2.6, 1.15, "SELECTION\nprefix stacks already\nin n-best ranks 2–8", "#E5F4EE", C_GREEN)
    box(3.7, 2.7, 2.6, 1.15, "GENERATION\nmany FV / extensions\nabsent from n-best=16", "#F8E8E2", C_VERM)
    box(7.1, 4.35, 2.6, 1.15, "A+na+li+gawa\n(clean prefix harvest)", "#E5F4EE", C_GREEN)
    box(7.1, 2.7, 2.6, 1.15, "teng+a  often missing\n(ndi+te+ng+a is junk)", "#F8E8E2", C_VERM)
    ax.annotate("", xy=(3.65, 4.9), xytext=(2.95, 4.6), arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.6))
    ax.annotate("", xy=(3.65, 3.2), xytext=(2.95, 4.0), arrowprops=dict(arrowstyle="->", color=C_VERM, lw=1.6))
    ax.annotate("", xy=(7.05, 4.9), xytext=(6.35, 4.9), arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.6))
    ax.annotate("", xy=(7.05, 3.25), xytext=(6.35, 3.25), arrowprops=dict(arrowstyle="->", color=C_VERM, lw=1.6))
    ax.text(
        5.0,
        1.85,
        "Reranking can only solve selection.  A productivity score that does not fire on those prefix cuts solves neither.",
        ha="center",
        va="center",
        fontsize=10,
        style="italic",
        color="#444",
    )
    box(3.7, 0.25, 2.6, 1.15, "StatBound V1\n0/162 changes\nmax-compat hurts F1", "#F3F0EA", "#888")
    save(fig, plt, "fig08_selection_vs_generation")


def fig_examples(plt) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 5.2))
    rows_clean = [
        ("Analigawa", "Anali + gawa", "A + na + li + gawa", "A + na + li + gaw + a"),
        ("silingathe", "sili + ngathe", "si + li + nga + the", "si + li + nga + th + e"),
        ("mudzamumvera", "mudza + mumvera", "mu + dza + mu + mvera", "mu + dza + mu + mver + a"),
        ("adapita", "ada + pita", "a + da + pit + a", "a + da + pit + a"),
    ]
    rows_junk = [
        ("nditenga", "ndi + tenga", "ndi + te + ng + a", "ndi + teng + a"),
        ("Nena", "Ne + na", "N + en + a", "Nen + a"),
        ("Matimu", "M + atimu", "Ma + ti + mu", "Ma + timu"),
        ("cholimbana", "cho + limbana", "cho + limba + n + a", "cho + limban + a"),
    ]

    def draw(ax, title, rows, color):
        ax.set_xlim(0, 10)
        ax.set_ylim(-0.4, len(rows) + 0.7)
        ax.axis("off")
        ax.set_title(title, loc="left", fontsize=12, color=color)
        ax.text(0.05, len(rows) + 0.25, "word", fontsize=8, color="#666")
        ax.text(2.0, len(rows) + 0.25, "Unigram", fontsize=8, color="#666")
        ax.text(5.0, len(rows) + 0.25, "F1-oracle", fontsize=8, color="#666")
        ax.text(7.7, len(rows) + 0.25, "Level-B gold", fontsize=8, color="#666")
        for i, (w, u, o, g) in enumerate(rows[::-1]):
            y = i
            ax.text(0.05, y, w, fontsize=9.2, fontweight="semibold")
            ax.text(2.0, y, u, fontsize=8.6, family="DejaVu Sans Mono")
            ax.text(5.0, y, o, fontsize=8.6, family="DejaVu Sans Mono", color=color)
            ax.text(7.7, y, g, fontsize=8.6, family="DejaVu Sans Mono")

    draw(axes[0], "Clean prefix harvest — oracle adds gold left-edge cuts", rows_clean, C_GREEN)
    draw(axes[1], "Metric-lucky junk — F1 rises via syllable-like extra cuts", rows_junk, C_VERM)
    fig.tight_layout()
    save(fig, plt, "fig09_segmentation_examples")


def anatomy(oracle):
    uni = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
    ora = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
    ch = {"unchanged": 0, "clean_prefix": 0, "mixed_gold": 0, "junk_fp": 0}
    for item in oracle["items"]:
        word = item["surface_form"]
        gold = item["gold_segmentation"].split("+")
        u = item["unigram"]["pieces"]
        o = item["f1_oracle"]["pieces"]
        um = gold_miss_zone_counts(word, gold, u)
        om = gold_miss_zone_counts(word, gold, o)
        for k in uni:
            uni[k] += um[k]
            ora[k] += om[k]
        ch[classify_oracle_change(word, gold, u, o)] += 1
    return uni, ora, ch


def main() -> int:
    phase_c = load(PHASE_C)
    phase_f = load(PHASE_F)
    oracle = load(ORACLE)
    uni, ora, ch = anatomy(oracle)
    plt = setup()
    fig_prf(plt, phase_c, oracle)
    fig_miss_location(plt, uni, ora)
    fig_oracle_types(plt, ch)
    fig_rank_hist(plt, oracle["alignment"]["oracle_rank_histogram"])
    fig_by_gold_pieces(plt, oracle["by_gold_piece_count"])
    fig_compat(plt)
    fig_lm(plt, phase_f)
    fig_schematic(plt)
    fig_examples(plt)
    print(f"wrote figures in {FIG.relative_to(ROOT)}")
    print("misses", uni, "remaining", ora, "classes", ch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
