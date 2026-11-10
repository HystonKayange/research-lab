#!/usr/bin/env python3
"""Summarize stored development results for publication; never run a tokenizer."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "data/reports"
OUT = REPORTS / "publication_snapshot_v0_2.json"
FIGURES = REPORTS / "figures/paper_v0_2"
EXPECTED_GOLD = "73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67"
INPUTS = {
    "phase_c": "data/reports/phase_c_morphology_v0_2_results.json",
    "phase_f": "data/reports/phase_f_lm_results_v0_1.json",
    "oracle": "data/reports/unigram_nbest_oracle_v0_1.json",
    "diagnostic": "data/reports/phase_c_statbound_failure_diagnostic_v0_1.json",
    "adjudication": "data/reports/morphology_level_b_final_adjudication_v0_2.json",
    "canonical": "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200_canonical_v0_1.jsonl",
    "active_v01": "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl",
    "gold": "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_input(key: str):
    # An explicit allowlist prevents accidental corpus, test, or holdout access.
    path = ROOT / INPUTS[key]
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return json.loads(path.read_text())


def boundaries(pieces: list[str]) -> set[int]:
    offset = 0
    cuts = set()
    for piece in pieces[:-1]:
        offset += len(piece)
        cuts.add(offset)
    return cuts


def zone(word: str, cut: int) -> str:
    # Describe the existing oracle's coordinate bins; these are not morpheme tags.
    if cut <= 4:
        return "left_edge"
    if len(word) - cut <= 2:
        return "right_edge"
    return "internal"


def summarize_candidates(items: list[dict]) -> dict:
    misses = {name: Counter() for name in ("unigram", "selected_oracle", "absent_from_union")}
    denominators = {}
    for system in ("unigram", "f1_oracle", "compat_oracle"):
        denominators[system] = {
            metric: sum(row[system][metric] is not None for row in items)
            for metric in ("boundary_precision", "boundary_recall", "boundary_f1")
        }
    changes = Counter()
    classes = Counter()
    only_add = 0
    n_gold = 0
    for row in items:
        word = row["surface_form"]
        gold = boundaries(row["gold_segmentation"].split("+"))
        uni = boundaries(row["unigram"]["pieces"])
        selected = boundaries(row["f1_oracle"]["pieces"])
        union = set().union(*(boundaries(c["pieces"]) for c in row["candidates"]))
        n_gold += len(gold)
        for key, cuts in (("unigram", uni), ("selected_oracle", selected), ("absent_from_union", union)):
            for cut in gold - cuts:
                misses[key][zone(word, cut)] += 1
        if row["unigram"]["pieces"] == row["f1_oracle"]["pieces"]:
            continue
        a = row["unigram"]["boundary_f1"]
        b = row["f1_oracle"]["boundary_f1"]
        changes["undefined_comparison" if a is None or b is None else "strictly_improved" if b > a else "tied" if a == b else "worsened"] += 1
        added = selected - uni
        removed = uni - selected
        if added - gold:
            classes["adds_non_gold_boundary"] += 1
        elif not removed and added and all(zone(word, b) == "left_edge" for b in added):
            classes["only_gold_left_edge_additions"] += 1
        else:
            classes["other_changes_without_new_non_gold_cuts"] += 1
        only_add += bool(added) and not removed
    return {
        "coordinate_bins": {"left_edge": "offset <= 4 (takes precedence)", "right_edge": "remaining characters <= 2", "internal": "all other internal offsets"},
        "n_gold_boundaries": n_gold,
        "misses": {name: {z: counts[z] for z in ("left_edge", "right_edge", "internal")} for name, counts in misses.items()},
        "macro_defined_item_counts": denominators,
        "changed_item_f1_status": dict(changes),
        "changed_item_classes": dict(classes),
        "changed_items_only_add_boundaries": only_add,
        "warning": "Union availability does not establish that all desired boundaries coexist in one candidate. Selected-oracle misses are not a measure of absence from the candidate union.",
    }


def build_snapshot() -> dict:
    before = {name: sha(ROOT / path) for name, path in INPUTS.items()}
    assert before["gold"] == EXPECTED_GOLD, "Frozen gold hash mismatch"
    data = {name: read_input(name) for name in INPUTS}
    c, f, o = data["phase_c"], data["phase_f"], data["oracle"]
    assert len(data["gold"]) == len(o["items"]) == c["evaluated_item_count"] == 162
    assert len({r["item_id"] for r in data["gold"]}) == 162
    for row in data["gold"]:
        pieces = row["final_segmentation"]
        if isinstance(pieces, str):
            pieces = pieces.split("+")
        assert pieces and all(pieces) and "".join(pieces) == row["surface_form"]
    active = {r["item_id"] for r in data["active_v01"]}
    already_excluded = [r["item_id"] for r in data["canonical"] if r["item_id"] not in active]
    assert len(data["canonical"]) == 200 and len(active) == 195 and len(already_excluded) == 5
    anatomy = summarize_candidates(o["items"])
    assert anatomy["misses"]["unigram"] == {"left_edge": 129, "right_edge": 93, "internal": 70}
    assert anatomy["misses"]["selected_oracle"] == {"left_edge": 2, "right_edge": 71, "internal": 41}
    assert anatomy["misses"]["absent_from_union"] == {"left_edge": 0, "right_edge": 27, "internal": 22}
    result = {
        "schema_version": "publication_snapshot_v0_2",
        "scope": "Publication summaries and descriptive set counts from already stored outputs; no new tokenization, model inference, candidate selection, or metric rescoring.",
        "input_files": INPUTS,
        "input_sha256": before,
        "benchmark_flow": {"canonical": 200, "excluded_before_level_b": 5, "previously_excluded_ids": already_excluded, "level_b_source": 195, "level_b_excluded": 33, "final_active": 162, "original_keeps": 18, "accepted_policy_revisions": 133, "native_speaker_cases": 11},
        "morphology": {name: c["systems"][name]["morphology"] for name in ("bpe_8000", "unigram_8000", "statbound_lambda_0_25")},
        "efficiency": {name: c["systems"][name]["efficiency"] for name in ("bpe_8000", "unigram_8000", "statbound_lambda_0_25")},
        "lambda_star": 0.25,
        "selected_lambda_unchanged": True,
        "oracle": {"unigram": o["unigram"], "f1_oracle": o["f1_oracle"], "compat_oracle": o["compat_oracle"], "gains": o["gains"], "alignment": o["alignment"], "rank_restricted_oracles": o["rank_restricted_oracles"]},
        "candidate_descriptives": anatomy,
        "lm_conditions": f["conditions"],
        "success_criteria": f["success_criteria"],
        "publication_corrections": [
            {"issue": "adjudication_coverage", "resolution": "Distinguish original native-speaker annotation, 133 accepted policy revisions, and explicit native-speaker adjudication of 11 exceptions. Do not imply a second independent human reannotation of all revisions."},
            {"issue": "incomplete_sample_flow", "resolution": "200 canonical -> five already excluded -> 195 Level-B source -> 33 further exclusions -> 162 active."},
            {"issue": "oracle_selection_vs_candidate_union", "resolution": "Selected-oracle misses 2/71/41 do not imply candidate absence. Candidate-union misses are 0/27/22 for left/right/internal bins."},
            {"issue": "metric_denominators", "resolution": "Macro metrics omit undefined item values. Unigram P/R/F1 n=152/160/150; oracle n=162/160/160. Exact match uses all 162. Frozen scores remain unchanged."},
            {"issue": "oracle_changed_vs_improved", "resolution": "125 paths change, but 115 comparisons strictly improve defined F1; 10 have undefined baseline F1."},
            {"issue": "extra_cuts_vs_linguistic_judgment", "resolution": "31 selected paths add non-gold boundaries. This mechanical category is not 31 independent native-speaker judgments."},
            {"issue": "empty_piece_warnings", "resolution": "Frozen Phase C records one BPE and three Unigram empty-piece warnings despite exact surface reconstruction. Retain and disclose; do not silently alter the scorer."},
            {"issue": "blanket_test_secrecy", "resolution": "Report validation-only scientific scope and disclose prior public artifacts. The procedural locks do not establish historical confidentiality."},
            {"issue": "compatibility_overclaim", "resolution": "Max-compat performs worse; this does not prove every possible mixed weighting would fail. V1 remains closed under its original decisions."},
        ],
        "historical_measurements": {"exact_agreement": 0.52, "boundary_f1": 0.841, "recomputed": False},
        "restricted_access": {"morphology_holdout": False, "lm_test": False, "corpus_text": False, "new_scientific_evaluation": False},
        "original_inputs_unchanged": before == {name: sha(ROOT / path) for name, path in INPUTS.items()},
    }
    assert result["original_inputs_unchanged"]
    return result


def plot(snapshot: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "publication-v0.2"})
    FIGURES.mkdir(parents=True, exist_ok=True)
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(FIGURES / (name + ".png"), dpi=190)
        fig.savefig(FIGURES / (name + ".svg"), metadata={"Date": None})
        plt.close(fig)
    a = snapshot["candidate_descriptives"]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    zones = ["left_edge", "right_edge", "internal"]
    for j, (key, label, color) in enumerate([
        ("unigram", "Missed by Unigram top-1", "#0072B2"),
        ("selected_oracle", "Missed by selected F1 oracle", "#D55E00"),
        ("absent_from_union", "Absent from every candidate", "#009E73"),
    ]):
        xs = [i + (j - 1) * .25 for i in range(3)]
        values = [a["misses"][key][z] for z in zones]
        bars = ax.bar(xs, values, .24, color=color, label=label)
        ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xticks(range(3), ["Left edge (offset ≤4)", "Right edge (≤2 remain)", "Internal"])
    ax.set_ylim(0, 166)
    ax.set_ylabel("Gold boundaries")
    ax.set_title("Selection misses differ from candidate-set absence", fontsize=12)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    save(fig, "f1_candidate_availability")
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    classes = a["changed_item_classes"]
    values = [classes[k] for k in ["only_gold_left_edge_additions", "other_changes_without_new_non_gold_cuts", "adds_non_gold_boundary"]]
    bars = ax.bar(["Only gold left-edge\nadditions", "Other changes without\nnew non-gold cuts", "At least one added\nnon-gold boundary"], values, color=["#009E73", "#0072B2", "#D55E00"])
    ax.bar_label(bars, padding=4)
    ax.set_ylim(0, 82)
    ax.set_ylabel("Changed paths (n=125)")
    ax.set_title("Oracle changes classified against frozen gold", fontsize=12)
    save(fig, "f2_oracle_changes")
    fig, ax = plt.subplots(figsize=(7.4, 3.5))
    primary = snapshot["lm_conditions"]["parameter_matched_x_fixed_characters"]
    rows = primary["statbound"]["per_seed"]
    for j, (name, key, color) in enumerate([("Unigram8k", "unigram_validation_bpc", "#0072B2"), ("StatBound λ=0.25", "statbound_validation_bpc", "#D55E00")]):
        vals = [r[key] for r in rows]
        ax.scatter([i + (j-.5)*.14 for i in range(3)], vals, color=color, s=45, label=name, zorder=3)
        stats = primary["unigram_8000" if j == 0 else "statbound"]["validation_bpc"]
        ax.errorbar([3 + (j-.5)*.14], [stats["mean"]], yerr=[stats.get("std", stats.get("stdev"))], fmt="o", color=color, capsize=4)
    for i, row in enumerate(rows):
        ax.plot([i-.07, i+.07], [row["unigram_validation_bpc"], row["statbound_validation_bpc"]], color=".7", lw=1)
    ax.set_xticks(range(4), [str(r["seed"]) for r in rows]+["Mean ± sample SD"])
    ax.set_ylabel("Validation bits per character ↓")
    ax.set_title("Primary LM regime: parameter-matched × fixed characters", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=.2)
    save(fig, "f3_primary_lm")


def main() -> int:
    result = build_snapshot()
    plot(result)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"snapshot": str(OUT.relative_to(ROOT)), "figures": str(FIGURES.relative_to(ROOT)), "original_inputs_unchanged": result["original_inputs_unchanged"], "new_evaluation": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
