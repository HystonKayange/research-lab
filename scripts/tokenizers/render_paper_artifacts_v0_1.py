#!/usr/bin/env python3
"""Build the six paper-facing tables/figures from existing result files.

No new training, no V2, no holdout/test/validation-corpus access.
Gold is not used here except as already stored in the frozen oracle JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.tokenizers.statbound.nbest_oracle import (  # noqa: E402
    classify_oracle_change,
    gold_miss_zone_counts,
)

PHASE_C = ROOT / "data/reports/phase_c_morphology_v0_2_results.json"
PHASE_F = ROOT / "data/reports/phase_f_lm_results_v0_1.json"
ORACLE = ROOT / "data/reports/unigram_nbest_oracle_v0_1.json"
OUT_JSON = ROOT / "data/reports/paper_artifacts_v0_1.json"
OUT_MD = ROOT / "data/reports/paper_artifacts_v0_1.md"
FIG_DIR = ROOT / "data/reports/figures/paper_v0_1"

FORBIDDEN = ("/test/", "/locked/", "holdout", "lm_test")


def load(path: Path) -> Any:
    s = str(path.resolve()).replace("\\", "/").lower()
    for bad in FORBIDDEN:
        if bad in s:
            raise RuntimeError(f"forbidden input: {path}")
    if "/validation/" in s and path.suffix == ".txt":
        raise RuntimeError(f"must not open corpus text: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def r4(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def morph_row(name: str, agg: dict[str, Any], tpc: float | None) -> dict[str, Any]:
    return {
        "system": name,
        "boundary_precision": agg["boundary_precision"],
        "boundary_recall": agg["boundary_recall"],
        "boundary_f1": agg["boundary_f1"],
        "exact_match_rate": agg["exact_match_rate"],
        "exact_match_count": agg.get("exact_match_count"),
        "tokens_per_character": tpc,
    }


def anatomy_from_oracle(oracle: dict[str, Any]) -> dict[str, Any]:
    unigram_miss = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
    oracle_miss = {"left_edge": 0, "right_edge": 0, "internal": 0, "total": 0}
    change_counts = {"unchanged": 0, "clean_prefix": 0, "mixed_gold": 0, "junk_fp": 0}
    only_add = 0
    changed = 0
    for item in oracle["items"]:
        word = item["surface_form"]
        gold = item["gold_segmentation"].split("+")
        uni = item["unigram"]["pieces"]
        ora = item["f1_oracle"]["pieces"]
        um = gold_miss_zone_counts(word, gold, uni)
        om = gold_miss_zone_counts(word, gold, ora)
        for key in ("left_edge", "right_edge", "internal", "total"):
            unigram_miss[key] += um[key]
            oracle_miss[key] += om[key]
        label = classify_oracle_change(word, gold, uni, ora)
        change_counts[label] += 1
        if label != "unchanged":
            changed += 1
            if len(ora) >= len(uni):
                only_add += 1
    return {
        "unigram_gold_misses": unigram_miss,
        "oracle_gold_misses": oracle_miss,
        "change_classes": change_counts,
        "n_oracle_differs": changed,
        "n_oracle_adds_or_keeps_piece_count": only_add,
        "definitions": {
            "left_edge": "cut offset <= 4",
            "right_edge": "remaining characters <= 2",
            "clean_prefix": "only left-edge gold cuts added; no removals; no false-positive cuts",
            "junk_fp": "at least one added cut is not gold",
            "mixed_gold": "other gold-improving oracle changes",
        },
    }


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "figure.dpi": 140,
            "savefig.dpi": 160,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    return plt


def plot_f1(plt, anatomy: dict[str, Any], dest: Path) -> None:
    labels = [
        "Left edge\n(prefix / TAM / NEG)",
        "Right edge\n(mostly final -a/-e)",
        "Internal\n(extensions etc.)",
    ]
    keys = ["left_edge", "right_edge", "internal"]
    uni = [anatomy["unigram_gold_misses"][k] for k in keys]
    ora = [anatomy["oracle_gold_misses"][k] for k in keys]
    x = list(range(len(labels)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar([i - width / 2 for i in x], uni, width, label="Missed by Unigram top-1", color="#4C72B0")
    ax.bar([i + width / 2 for i in x], ora, width, label="Still missed after best-of-16", color="#DD8452")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Missed gold boundaries")
    ax.set_title("F1. Unigram gold-boundary misses by location")
    ax.legend(frameon=False)
    for i, (a, b) in enumerate(zip(uni, ora)):
        ax.text(i - width / 2, a + 2, str(a), ha="center", va="bottom", fontsize=9)
        ax.text(i + width / 2, b + 2, str(b), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(dest.with_suffix(".png"))
    fig.savefig(dest.with_suffix(".svg"))
    plt.close(fig)


def plot_f2(plt, anatomy: dict[str, Any], dest: Path) -> None:
    labels = [
        "Clean prefix-only\ngold adds",
        "Other gold-improving\nchanges",
        "F1 gain with\nfalse-positive cuts",
    ]
    values = [
        anatomy["change_classes"]["clean_prefix"],
        anatomy["change_classes"]["mixed_gold"],
        anatomy["change_classes"]["junk_fp"],
    ]
    colors = ["#55A868", "#4C72B0", "#C44E52"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Words (oracle ≠ Unigram)")
    ax.set_title("F2. What the n-best F1-oracle actually changes")
    ymax = max(values) * 1.18
    ax.set_ylim(0, ymax)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1.2, str(val), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(dest.with_suffix(".png"))
    fig.savefig(dest.with_suffix(".svg"))
    plt.close(fig)


def plot_f3(plt, primary: dict[str, Any], dest: Path) -> None:
    seeds = [str(s["seed"]) for s in primary["per_seed"]] + ["mean"]
    uni = [s["unigram_bpc"] for s in primary["per_seed"]] + [primary["unigram_bpc"]]
    sb = [s["statbound_bpc"] for s in primary["per_seed"]] + [primary["statbound_bpc"]]
    x = list(range(len(seeds)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.bar([i - width / 2 for i in x], uni, width, label="Unigram8k", color="#4C72B0")
    ax.bar([i + width / 2 for i in x], sb, width, label="StatBound λ*=0.25", color="#C44E52")
    ax.set_xticks(x, seeds)
    ax.set_xlabel("Seed")
    ax.set_ylabel("Validation BPC (lower is better)")
    ax.set_title("F3. Primary LM: parameter-matched × fixed characters")
    lo = min(uni + sb) - 0.0015
    hi = max(uni + sb) + 0.0015
    ax.set_ylim(lo, hi)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(dest.with_suffix(".png"))
    fig.savefig(dest.with_suffix(".svg"))
    plt.close(fig)


def render_md(art: dict[str, Any]) -> str:
    t1 = art["T1_standard_tokenizers"]
    t2 = art["T2_statbound_v1"]
    t3 = art["T3_nbest_oracle"]
    a = art["anatomy"]
    lines = [
        "# Paper-facing artifacts v0.1",
        "",
        "Generated from frozen Phase C, Phase F, and n-best oracle reports.",
        "No new training. Morphology holdout and LM test were not opened.",
        "",
        "## T1. Standard tokenizers on Level-B development",
        "",
        "| system | P | R | F1 | exact | TPC |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in t1["rows"]:
        lines.append(
            f"| {row['system']} | {fmt(row['boundary_precision'])} | {fmt(row['boundary_recall'])} | "
            f"{fmt(row['boundary_f1'])} | {fmt(row['exact_match_rate'])} | {fmt(row['tokens_per_character'])} |"
        )
    lines += [
        "",
        f"Source: `{t1['source']}`. Character is omitted (descriptive only, not a morphology baseline).",
        "",
        "## T2. StatBound V1 vs Unigram",
        "",
        "| | Unigram8k | StatBound λ*=0.25 |",
        "|---|---:|---:|",
        f"| development boundary F1 | {fmt(t2['unigram_f1'])} | {fmt(t2['statbound_f1'])} |",
        f"| benchmark words changed | 0 | {t2['benchmark_words_changed']} |",
        f"| primary validation BPC | {fmt(t2['unigram_bpc'], 6)} ± {fmt(t2['unigram_bpc_std'], 6)} | "
        f"{fmt(t2['statbound_bpc'], 6)} ± {fmt(t2['statbound_bpc_std'], 6)} |",
        f"| ΔBPC (SB − Unigram) | — | {fmt(t2['delta_bpc'], 6)} |",
        f"| seeds beating Unigram | — | {t2['seeds_beating_unigram']}/{t2['n_seeds']} |",
        f"| SC4 | — | {t2['sc4']} |",
        f"| SC1 | — | {t2['sc1']} |",
        "",
        f"Sources: `{t2['morphology_source']}`, `{t2['lm_source']}`.",
        "",
        "## T3. Unigram n-best=16 F1 oracle",
        "",
        "| system | P | R | F1 | exact |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in t3["rows"]:
        lines.append(
            f"| {row['system']} | {fmt(row['boundary_precision'])} | {fmt(row['boundary_recall'])} | "
            f"{fmt(row['boundary_f1'])} | {fmt(row['exact_match_rate'])} |"
        )
    lines += [
        "",
        f"- Oracle ΔF1: **{fmt(t3['delta_f1'])}**",
        f"- Exact gold in n-best: **{t3['gold_in_nbest']}/162**",
        f"- The 0.79 F1 is an analysis ceiling, not a method target.",
        f"- Source: `{t3['source']}`",
        "",
        "## F1–F3",
        "",
        "![F1 missed boundaries](figures/paper_v0_1/f1_missed_boundaries_by_location.png)",
        "",
        f"- Unigram misses: left {a['unigram_gold_misses']['left_edge']}, "
        f"right {a['unigram_gold_misses']['right_edge']}, "
        f"internal {a['unigram_gold_misses']['internal']} "
        f"(total {a['unigram_gold_misses']['total']})",
        f"- Still missing after oracle: left {a['oracle_gold_misses']['left_edge']}, "
        f"right {a['oracle_gold_misses']['right_edge']}, "
        f"internal {a['oracle_gold_misses']['internal']} "
        f"(total {a['oracle_gold_misses']['total']})",
        "",
        "![F2 oracle change types](figures/paper_v0_1/f2_oracle_change_types.png)",
        "",
        f"- Clean prefix: **{a['change_classes']['clean_prefix']}**",
        f"- Mixed gold: **{a['change_classes']['mixed_gold']}**",
        f"- Junk FP: **{a['change_classes']['junk_fp']}**",
        f"- Unchanged: {a['change_classes']['unchanged']}",
        f"- Oracle differs on {a['n_oracle_differs']}; "
        f"{a['n_oracle_adds_or_keeps_piece_count']} add or keep piece count",
        "",
        "![F3 primary LM](figures/paper_v0_1/f3_primary_lm_bpc.png)",
        "",
        "Lower BPC is better. Primary condition: parameter-matched × fixed characters.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    for path in (PHASE_C, PHASE_F, ORACLE):
        if not path.is_file():
            raise FileNotFoundError(path)
    phase_c = load(PHASE_C)
    phase_f = load(PHASE_F)
    oracle = load(ORACLE)

    bpe = phase_c["systems"]["bpe_8000"]
    uni = phase_c["systems"]["unigram_8000"]
    sb = phase_c["systems"]["statbound_lambda_0_25"]
    t1 = {
        "source": str(PHASE_C.relative_to(ROOT)),
        "n_items": 162,
        "rows": [
            morph_row(
                "BPE8k",
                bpe["morphology"]["aggregate"],
                bpe["efficiency"]["sequence_efficiency"]["tokens_per_character"],
            ),
            morph_row(
                "Unigram8k",
                uni["morphology"]["aggregate"],
                uni["efficiency"]["sequence_efficiency"]["tokens_per_character"],
            ),
        ],
    }

    primary = phase_f["conditions"]["parameter_matched_x_fixed_characters"]
    per_seed = []
    for rec in primary["statbound"]["per_seed"]:
        per_seed.append(
            {
                "seed": rec["seed"],
                "unigram_bpc": rec["unigram_validation_bpc"],
                "statbound_bpc": rec["statbound_validation_bpc"],
                "delta_bpc": rec["delta_bpc_statbound_minus_unigram"],
                "statbound_beats_unigram": rec["seed_beats_unigram"],
            }
        )
    t2 = {
        "morphology_source": str(PHASE_C.relative_to(ROOT)),
        "lm_source": str(PHASE_F.relative_to(ROOT)),
        "unigram_f1": uni["morphology"]["aggregate"]["boundary_f1"],
        "statbound_f1": sb["morphology"]["aggregate"]["boundary_f1"],
        "benchmark_words_changed": 0,
        "unigram_bpc": primary["unigram_8000"]["validation_bpc"]["mean"],
        "unigram_bpc_std": primary["unigram_8000"]["validation_bpc"]["stdev"],
        "statbound_bpc": primary["statbound"]["validation_bpc"]["mean"],
        "statbound_bpc_std": primary["statbound"]["validation_bpc"]["std"],
        "delta_bpc": primary["delta"]["mean_bpc_statbound_minus_unigram"],
        "seeds_beating_unigram": primary["delta"]["seeds_beating_unigram"],
        "n_seeds": primary["delta"]["n_seeds"],
        "sc4": "FAIL",
        "sc1": "FAIL",
        "per_seed": per_seed,
    }

    t3 = {
        "source": str(ORACLE.relative_to(ROOT)),
        "nbest_size": 16,
        "delta_f1": oracle["gains"]["macro_f1"],
        "gold_in_nbest": oracle["alignment"]["n_gold_in_nbest"],
        "rows": [
            morph_row("Unigram top-1", oracle["unigram"]["macro"], None),
            morph_row("Best-of-16 F1 oracle", oracle["f1_oracle"]["macro"], None),
        ],
        "note": "Oracle uses gold only to score frozen Unigram candidates. It is not a tokenizer.",
    }

    anatomy = anatomy_from_oracle(oracle)
    artifacts = {
        "schema_version": "paper_artifacts_v0_1",
        "restricted": {
            "morphology_holdout_accessed": False,
            "lm_test_accessed": False,
            "new_training": False,
            "v2_authorized": False,
        },
        "T1_standard_tokenizers": t1,
        "T2_statbound_v1": t2,
        "T3_nbest_oracle": t3,
        "anatomy": anatomy,
        "figures": {
            "F1": "data/reports/figures/paper_v0_1/f1_missed_boundaries_by_location.png",
            "F2": "data/reports/figures/paper_v0_1/f2_oracle_change_types.png",
            "F3": "data/reports/figures/paper_v0_1/f3_primary_lm_bpc.png",
        },
    }

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt = setup_matplotlib()
    plot_f1(plt, anatomy, FIG_DIR / "f1_missed_boundaries_by_location")
    plot_f2(plt, anatomy, FIG_DIR / "f2_oracle_change_types")
    plot_f3(plt, t2, FIG_DIR / "f3_primary_lm_bpc")

    write_json(OUT_JSON, artifacts)
    write_text(OUT_MD, render_md(artifacts))
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    print("anatomy", json.dumps(anatomy["unigram_gold_misses"]), json.dumps(anatomy["change_classes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
