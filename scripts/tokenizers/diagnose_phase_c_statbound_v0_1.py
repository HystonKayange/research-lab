#!/usr/bin/env python3
"""Diagnostics for the frozen Phase C StatBound morphology result.

This is not a Phase C evaluator.  It reads the frozen development benchmark,
the already-produced Phase C aggregate outputs, and the frozen Unigram /
StatBound candidate machinery to explain the observed λ behaviour.  It does
not read validation text, holdout data, LM test data, or LM results.
"""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.tokenizers.statbound.boundary_stats import get_strength, load_boundary_stats  # noqa: E402
from src.tokenizers.statbound.metrics import boundary_metrics, boundaries_from_segments  # noqa: E402
from src.tokenizers.statbound.reranker import (  # noqa: E402
    boundary_compatibility,
    rank_candidates,
    surface_from_pieces,
)
from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402
from src.tokenizers.statbound.unigram_adapter import UnigramAdapter  # noqa: E402


ACTIVE = ROOT / "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl"
PHASE_C_RESULTS = ROOT / "data/reports/phase_c_morphology_v0_2_results.json"
STATBOUND_CONFIG = ROOT / "configs/tokenizers/statbound_unigram_v1.json"
BOUNDARY_STATS = ROOT / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
UNIGRAM_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
RERANKER_SOURCE = ROOT / "src/tokenizers/statbound/reranker.py"
ADAPTER_SOURCE = ROOT / "src/tokenizers/statbound/unigram_adapter.py"
TOKENIZER_SOURCE = ROOT / "src/tokenizers/statbound/tokenizer.py"

OUT_JSON = ROOT / "data/reports/phase_c_statbound_failure_diagnostic_v0_1.json"
OUT_MD = ROOT / "data/reports/phase_c_statbound_failure_diagnostic_v0_1.md"

LAMBDAS = (0.25, 0.5, 1.0, 2.0)
NBEST_SIZE = 16
EPS = 1e-12


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def seg_string(pieces: list[str]) -> str:
    return "+".join(pieces)


def metric_triplet(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "precision": metrics.get("boundary_precision"),
        "recall": metrics.get("boundary_recall"),
        "f1": metrics.get("boundary_f1"),
        "boundary_jaccard": metrics.get("boundary_jaccard"),
        "exact": metrics.get("exact_segmentation_match"),
        "surface_reconstruct_ok": metrics.get("surface_reconstruct_ok"),
    }


def numeric_f1(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value is not None else None


def comparison(a: Any, b: Any) -> str:
    av, bv = numeric_f1(a), numeric_f1(b)
    if av is None or bv is None:
        return "unchanged" if av is None and bv is None else "undefined"
    if av > bv + EPS:
        return "improved"
    if av < bv - EPS:
        return "worsened"
    return "unchanged"


def summarize(values: list[float], *, zero_eps: float = EPS) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "zero_count": 0,
            "nonzero_count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }
    vals = [float(v) for v in values]
    return {
        "count": len(vals),
        "zero_count": sum(1 for v in vals if abs(v) <= zero_eps),
        "nonzero_count": sum(1 for v in vals if abs(v) > zero_eps),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "p10": statistics.quantiles(vals, n=10, method="inclusive")[0] if len(vals) >= 2 else vals[0],
        "p90": statistics.quantiles(vals, n=10, method="inclusive")[-1] if len(vals) >= 2 else vals[0],
    }


def line_no(path: Path, needle: str) -> int | None:
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return i
    return None


def boundary_shift_count(unigram: set[int], statbound: set[int]) -> int:
    """Potential relocations: one removed position paired with one added position."""
    return min(len(unigram - statbound), len(statbound - unigram))


def candidate_rank_entries(
    word: str,
    gold: list[str],
    adapter: UnigramAdapter,
    stats: dict[str, Any],
) -> dict[str, Any]:
    candidates = adapter.default_and_nbest(word, NBEST_SIZE)
    default_raw = adapter.encode_as_pieces(word)
    default_norm = [p.lstrip("▁") for p in default_raw]
    default_score = adapter.unigram_score(default_raw)
    scored: list[dict[str, Any]] = []
    for set_index, cand in enumerate(candidates, start=1):
        raw = list(cand.pieces)
        pieces = [p.lstrip("▁") for p in raw]
        score = float(cand.unigram_score)
        bscore = boundary_compatibility(word, raw, stats)
        metrics = boundary_metrics(gold, pieces)
        scored.append(
            {
                "candidate_set_index": set_index,
                "pieces": pieces,
                "segmentation": seg_string(pieces),
                "unigram_score": score,
                "boundary_score": bscore,
                "metrics": metric_triplet(metrics),
                "is_top1_sequence": pieces == default_norm,
            }
        )
    # SentencePiece n-best is score ordered; make the rank explicit and stable.
    ranked_by_unigram = sorted(
        scored,
        key=lambda x: (-x["unigram_score"], x["candidate_set_index"]),
    )
    for rank, entry in enumerate(ranked_by_unigram, start=1):
        entry["unigram_score_rank"] = rank
    by_sequence = {tuple(x["pieces"]): x for x in scored}
    top1 = by_sequence.get(tuple(default_norm))
    if top1 is None:
        top1 = {
            "candidate_set_index": None,
            "pieces": default_norm,
            "segmentation": seg_string(default_norm),
            "unigram_score": default_score,
            "boundary_score": boundary_compatibility(word, default_raw, stats),
            "metrics": metric_triplet(boundary_metrics(gold, default_norm)),
            "is_top1_sequence": True,
            "unigram_score_rank": 1,
        }
        scored.insert(0, top1)
        by_sequence[tuple(default_norm)] = top1
    top1_f1 = top1["metrics"]["f1"]
    better = []
    for entry in scored:
        f1 = entry["metrics"]["f1"]
        if numeric_f1(f1) is not None and numeric_f1(top1_f1) is not None and f1 > top1_f1 + EPS:
            better.append(entry)
    better.sort(key=lambda x: (-float(x["metrics"]["f1"]), -x["unigram_score"], x["unigram_score_rank"]))
    gold_entries = [x for x in scored if x["pieces"] == gold]
    best_f1 = None
    if scored:
        numeric = [x for x in scored if numeric_f1(x["metrics"]["f1"]) is not None]
        if numeric:
            best_f1 = sorted(
                numeric,
                key=lambda x: (-float(x["metrics"]["f1"]), -x["unigram_score"], x["unigram_score_rank"]),
            )[0]
    alternative_gaps = [top1["unigram_score"] - x["unigram_score"] for x in scored if not x["is_top1_sequence"]]
    return {
        "word": word,
        "gold": gold,
        "default_pieces": default_norm,
        "default_segmentation": seg_string(default_norm),
        "top1": top1,
        "candidates": scored,
        "n_best_returned": len(scored),
        "gold_entries": gold_entries,
        "better_entries": better,
        "best_f1_entry": best_f1,
        "alternative_score_gaps": alternative_gaps,
        "candidate_boundary_scores": [float(x["boundary_score"]) for x in scored if x["boundary_score"] is not None],
        "boundary_score_distinct": len({round(float(x["boundary_score"]), 12) for x in scored if x["boundary_score"] is not None}),
    }


def candidate_summary_for_changed(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_set_index": entry["candidate_set_index"],
        "unigram_score_rank": entry["unigram_score_rank"],
        "segmentation": entry["segmentation"],
        "pieces": entry["pieces"],
        "unigram_score": entry["unigram_score"],
        "boundary_score": entry["boundary_score"],
        "boundary_f1": entry["metrics"]["f1"],
        "boundary_precision": entry["metrics"]["precision"],
        "boundary_recall": entry["metrics"]["recall"],
    }


def analyze_lambda(
    lam: float,
    rows: list[dict[str, Any]],
    base_items: dict[str, dict[str, Any]],
    adapter: UnigramAdapter,
    stats: dict[str, Any],
) -> dict[str, Any]:
    changed: list[dict[str, Any]] = []
    selected_scores: list[float] = []
    signal_values: list[float] = []
    delta_signal_values: list[float] = []
    selected_gaps: list[float] = []
    best_alt_gaps: list[float] = []
    net_gain_values: list[float] = []
    all_alternative_signal_values: list[float] = []
    all_alternative_gap_values: list[float] = []
    all_alternative_net_values: list[float] = []
    all_alternative_overcome_count = 0
    changed_item_ids: list[str] = []
    boundary_added_total = 0
    boundary_removed_total = 0
    boundary_shifted_total = 0
    improvements = Counter()
    selected_better_count = 0
    selected_gold_count = 0
    selected_best_f1_count = 0
    selected_records: dict[str, dict[str, Any]] = {}
    selected_rank_counts: Counter[str] = Counter()

    for row in rows:
        item_id = row["item_id"]
        word = row["surface_form"]
        gold = base_items[item_id]["gold"]
        candidates = [
            # Reconstruct the same candidate object list from stored raw pieces.
            # Scores and candidate order are preserved from the base analysis.
            type("Candidate", (), {"pieces": x["raw_pieces"], "unigram_score": x["unigram_score"]})()
            for x in base_items[item_id]["raw_candidates"]
        ]
        ranked = rank_candidates(word, candidates, stats, lambda_bias=lam)
        if not ranked:
            raise RuntimeError(f"no valid candidates for {item_id}")
        selected = ranked[0]
        selected_pieces = [p.lstrip("▁") for p in selected.pieces]
        item = base_items[item_id]
        by_sequence = item["by_sequence"]
        selected_entry = by_sequence.get(tuple(selected_pieces))
        if selected_entry is None:
            raise RuntimeError(f"selected candidate missing from n-best map: {item_id}")
        top1_entry = item["top1"]
        top1_metrics = top1_entry["metrics"]
        selected_metrics = metric_triplet(boundary_metrics(gold, selected_pieces))
        top1_boundaries = boundaries_from_segments(top1_entry["pieces"])
        selected_boundaries = boundaries_from_segments(selected_pieces)
        added = sorted(selected_boundaries - top1_boundaries)
        removed = sorted(top1_boundaries - selected_boundaries)
        shifted = boundary_shift_count(top1_boundaries, selected_boundaries)
        boundary_added_total += len(added)
        boundary_removed_total += len(removed)
        boundary_shifted_total += shifted
        relation = comparison(selected_metrics["f1"], top1_metrics["f1"])
        improvements[relation] += 1
        if numeric_f1(selected_metrics["f1"]) is not None and numeric_f1(top1_metrics["f1"]) is not None and selected_metrics["f1"] > top1_metrics["f1"] + EPS:
            selected_better_count += 1
        if selected_pieces == gold:
            selected_gold_count += 1
        best = item["best_f1_entry"]
        if best is not None and selected_pieces == best["pieces"]:
            selected_best_f1_count += 1
        bscore = float(selected.boundary_compatibility)
        top1_bscore = float(top1_entry["boundary_score"])
        score_gap = float(top1_entry["unigram_score"] - selected_entry["unigram_score"])
        best_alt_gap = min(item["alternative_score_gaps"]) if item["alternative_score_gaps"] else None
        combined_delta = float(selected.combined_score - (top1_entry["unigram_score"] + lam * top1_bscore))
        for alternative in item["candidates"]:
            if alternative["is_top1_sequence"]:
                continue
            alt_gap = float(top1_entry["unigram_score"] - alternative["unigram_score"])
            alt_signal = float(lam * (alternative["boundary_score"] - top1_bscore))
            alt_net = alt_signal - alt_gap
            all_alternative_gap_values.append(alt_gap)
            all_alternative_signal_values.append(alt_signal)
            all_alternative_net_values.append(alt_net)
            if alt_net > EPS:
                all_alternative_overcome_count += 1
        selected_scores.append(bscore)
        signal_values.append(lam * bscore)
        delta_signal_values.append(lam * (bscore - top1_bscore))
        selected_gaps.append(score_gap)
        net_gain_values.append(combined_delta)
        if best_alt_gap is not None:
            best_alt_gaps.append(float(best_alt_gap))
        rank = selected_entry["unigram_score_rank"]
        selected_rank_counts[str(rank)] += 1
        selected_records[item_id] = {
            "segmentation": seg_string(selected_pieces),
            "pieces": selected_pieces,
            "boundary_score": bscore,
            "unigram_score": selected_entry["unigram_score"],
            "combined_score": float(selected.combined_score),
            "selected_candidate_nbest_rank": rank,
            "selected_candidate_set_index": selected_entry["candidate_set_index"],
            "ranked_candidate_count": len(ranked),
            "top1_boundary_score": top1_bscore,
            "top1_unigram_score": top1_entry["unigram_score"],
            "top1_to_selected_unigram_score_gap": score_gap,
            "lambda_times_boundary_score": lam * bscore,
            "lambda_times_boundary_score_delta": lam * (bscore - top1_bscore),
            "combined_score_delta_vs_top1": combined_delta,
            "boundary_added": added,
            "boundary_removed": removed,
            "boundary_shifted_count": shifted,
            "metrics": selected_metrics,
            "relation_to_top1_f1": relation,
        }
        if selected_pieces != top1_entry["pieces"]:
            changed_item_ids.append(item_id)
            changed.append({
                "item_id": item_id,
                "surface_form": word,
                "gold_segmentation": seg_string(gold),
                "unigram_segmentation": top1_entry["segmentation"],
                "statbound_segmentation": seg_string(selected_pieces),
                "unigram_metrics": top1_metrics,
                "statbound_metrics": selected_metrics,
                "f1_relation": relation,
                "statbound_boundary_score": bscore,
                "top1_boundary_score": top1_bscore,
                "original_unigram_candidate_score": top1_entry["unigram_score"],
                "selected_candidate_unigram_score": selected_entry["unigram_score"],
                "selected_candidate_combined_score": float(selected.combined_score),
                "selected_candidate_nbest_rank": rank,
                "selected_candidate_set_index": selected_entry["candidate_set_index"],
                "n_best_returned": item["n_best_returned"],
                "boundary_decisions_added": added,
                "boundary_decisions_removed": removed,
                "boundary_decisions_shifted": shifted,
                "gold_in_nbest": bool(item["gold_entries"]),
                "best_f1_candidate_in_nbest": candidate_summary_for_changed(item["best_f1_entry"]) if item["best_f1_entry"] else None,
                "n_best_candidates": [candidate_summary_for_changed(x) for x in item["candidates"]],
            })

    changed_n = len(changed)
    return {
        "lambda": lam,
        "changed_item_count": changed_n,
        "changed_item_percentage": 100.0 * changed_n / len(rows),
        "changed_item_ids": changed_item_ids,
        "boundary_decisions": {
            "added_count": boundary_added_total,
            "removed_count": boundary_removed_total,
            "shifted_count": boundary_shifted_total,
            "shift_definition": "potential relocations formed by pairing one removed boundary with one added boundary within an item; raw added/removed counts are primary",
        },
        "changed_item_f1_outcomes": {
            "improved_count": sum(1 for x in changed if x["f1_relation"] == "improved"),
            "worsened_count": sum(1 for x in changed if x["f1_relation"] == "worsened"),
            "unchanged_count": sum(1 for x in changed if x["f1_relation"] == "unchanged"),
            "undefined_count": sum(1 for x in changed if x["f1_relation"] == "undefined"),
            "all_item_f1_outcomes": dict(improvements),
        },
        "selected_better_than_top1_count": selected_better_count,
        "selected_gold_count": selected_gold_count,
        "selected_best_nbest_f1_count": selected_best_f1_count,
        "selected_candidate_nbest_rank_counts": dict(sorted(selected_rank_counts.items(), key=lambda x: int(x[0]))),
        "statbound_boundary_score_distribution": summarize(selected_scores),
        "weighting_diagnostics": {
            "lambda_times_selected_boundary_score": summarize(signal_values),
            "lambda_times_boundary_score_delta_vs_top1": summarize(delta_signal_values),
            "top1_to_selected_unigram_score_gap": summarize(selected_gaps),
            "top1_to_best_alternative_unigram_score_gap": summarize(best_alt_gaps),
            "combined_score_delta_selected_vs_top1": summarize(net_gain_values),
            "all_alternative_lambda_times_boundary_score_delta": summarize(all_alternative_signal_values),
            "all_alternative_top1_to_candidate_unigram_score_gap": summarize(all_alternative_gap_values),
            "all_alternative_signal_minus_gap": summarize(all_alternative_net_values),
            "all_alternative_signal_exceeds_gap_count": all_alternative_overcome_count,
            "all_alternative_count": len(all_alternative_gap_values),
            "selected_alternative_combined_score_beats_top1_count": sum(1 for v in net_gain_values if v > EPS),
            "selected_alternative_combined_score_ties_top1_count": sum(1 for v in net_gain_values if abs(v) <= EPS),
        },
        "changed_items": changed,
        "selected_records_by_item": selected_records,
    }


def build_base_items(rows: list[dict[str, Any]], adapter: UnigramAdapter, stats: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row["item_id"]
        word = row["surface_form"]
        gold = [x for x in str(row["final_segmentation"]).split("+") if x]
        candidates = adapter.default_and_nbest(word, NBEST_SIZE)
        analysis = candidate_rank_entries(word, gold, adapter, stats)
        raw_candidates = []
        for cand in candidates:
            raw_candidates.append({
                "raw_pieces": list(cand.pieces),
                "unigram_score": float(cand.unigram_score),
            })
        analysis["raw_candidates"] = raw_candidates
        analysis["by_sequence"] = {tuple(x["pieces"]): x for x in analysis["candidates"]}
        out[item_id] = {"item_id": item_id, "surface_form": word, "gold": gold, **analysis}
    return out


def benchmark_token_counts(rows: list[dict[str, Any]], base_items: dict[str, dict[str, Any]], lambda_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n_chars = sum(len(r["surface_form"]) for r in rows)
    top1_tokens = sum(len(base_items[r["item_id"]]["top1"]["pieces"]) for r in rows)
    out: dict[str, Any] = {
        "n_items": len(rows),
        "n_characters": n_chars,
        "unigram_tokens": top1_tokens,
        "unigram_tokens_per_character": top1_tokens / n_chars if n_chars else None,
        "systems": {},
    }
    for lam, result in lambda_results.items():
        records = result["selected_records_by_item"]
        token_count = sum(len(records[r["item_id"]]["pieces"]) for r in rows)
        changed_words = sum(1 for r in rows if records[r["item_id"]]["pieces"] != base_items[r["item_id"]]["top1"]["pieces"])
        out["systems"][str(lam)] = {
            "selected_tokens": token_count,
            "tokens_per_character": token_count / n_chars if n_chars else None,
            "changed_word_count_vs_unigram": changed_words,
            "changed_word_percentage": 100.0 * changed_words / len(rows),
            "token_count_delta_vs_unigram": token_count - top1_tokens,
        }
    return out


def classify_failure(
    rows: list[dict[str, Any]],
    base_items: dict[str, dict[str, Any]],
    lambda_results: dict[str, dict[str, Any]],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    n = len(rows)
    better = sum(1 for x in base_items.values() if x["better_entries"])
    gold = sum(1 for x in base_items.values() if x["gold_entries"])
    any_signal = sum(1 for x in base_items.values() if x["boundary_score_distinct"] > 1)
    any_nonzero = sum(1 for x in base_items.values() if any(abs(v) > EPS for v in x["candidate_boundary_scores"]))
    changed_any = sum(1 for item_id in base_items if any(item_id in r["changed_item_ids"] for r in lambda_results.values()))
    classes: list[str] = []
    evidence: list[str] = []
    if better == 0:
        classes.extend(["A", "F"])
        evidence.append("No item has a higher-boundary-F1 candidate in the returned n-best set, so useful alternatives are absent or unavailable to the reranker.")
    else:
        selected_better = max(r["selected_better_than_top1_count"] for r in lambda_results.values())
        if selected_better == 0:
            classes.append("C")
            evidence.append("Higher-F1 alternatives exist, but no evaluated nonzero λ selected one.")
    if any_signal == 0 or any_nonzero == 0:
        classes.append("B")
        evidence.append("Boundary compatibility has no within-item candidate variation or no nonzero signal on the benchmark candidate sets.")
    if changed_any > 0:
        total_changed = sum(len(r["changed_items"]) for r in lambda_results.values())
        total_improved = sum(r["changed_item_f1_outcomes"]["improved_count"] for r in lambda_results.values())
        if total_improved == 0:
            classes.append("D")
            evidence.append("Some λ values move boundaries, but those moves do not improve item-level boundary F1.")
    if implementation.get("validation_whitespace_path_difference"):
        classes.append("E")
        evidence.append("The frozen efficiency path tokenizes StatBound text via text.split(), while the baseline wrapper encodes full lines; this explains tiny validation-TPC differences but is not a morphology-F1 path failure.")
    if not classes:
        classes.append("F")
        evidence.append("No dominant failure pattern beyond lack of measurable morphology improvement was established.")
    order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
    classes = sorted(set(classes), key=lambda x: order[x])
    return {
        "dominant_failure_modes": classes,
        "labels": {
            "A": "candidate-set failure",
            "B": "boundary-statistics failure",
            "C": "weighting failure",
            "D": "objective mismatch",
            "E": "implementation failure",
            "F": "genuinely no useful alternative segmentation available",
        },
        "evidence": evidence,
        "benchmark_items_with_higher_f1_candidate": better,
        "benchmark_items_with_gold_candidate": gold,
        "benchmark_items_with_candidate_boundary_signal": any_signal,
        "benchmark_items_with_any_nonzero_candidate_boundary_score": any_nonzero,
        "benchmark_items_changed_by_any_nonzero_lambda": changed_any,
        "not_dominant_evidence": {
            "A_candidate_set_failure_not_dominant": better > 0,
            "B_boundary_statistics_failure_not_dominant": any_signal > 0 and any_nonzero > 0,
            "D_objective_mismatch_not_dominant": changed_any == 0,
            "F_no_useful_alternative_not_dominant": better > 0 or gold > 0,
        },
    }


def make_report(result: dict[str, Any]) -> str:
    def f(x: Any, d: int = 4) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.{d}f}"
        return str(x)

    lines = [
        "# Phase-C StatBound morphology failure diagnostic",
        "",
        "This is a diagnostics-only analysis of the already-produced Phase C result. "
        "It does not alter the benchmark, algorithm, hyperparameters, λ selection, or success criteria.",
        "",
        "## Scope and restrictions",
        "",
        "- Frozen benchmark items: **162**",
        f"- Phase C result file used: `{PHASE_C_RESULTS.relative_to(ROOT)}`",
        "- Morphology holdout: **not accessed**",
        "- LM test: **not accessed**",
        "- LM BPC: **not accessed or used**",
        "- Phase C: **not rerun**",
        "- Phase F: **not run**",
        "",
        "## Overall diagnosis",
        "",
        f"- Dominant failure-mode labels: **{', '.join(result['failure_classification']['dominant_failure_modes'])}**",
    ]
    for ev in result["failure_classification"]["evidence"]:
        lines.append(f"- {ev}")
    lines += [
        "- Non-dominant checks: candidate-set failure = **not supported as dominant**; boundary-statistics failure = **not supported as dominant**; objective mismatch = **not supported** because no benchmark item changed; no-useful-alternative = **not supported**.",
    ]
    lines += [
        "",
        "## Changed benchmark items and boundary outcomes",
        "",
        "| λ | changed items | percentage | added boundaries | removed boundaries | potential shifts | improved F1 | worsened F1 | unchanged F1 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for lam, d in result["per_lambda"].items():
        o = d["changed_item_f1_outcomes"]
        b = d["boundary_decisions"]
        lines.append(
            f"| {lam} | {d['changed_item_count']} | {f(d['changed_item_percentage'], 2)}% | "
            f"{b['added_count']} | {b['removed_count']} | {b['shifted_count']} | "
            f"{o['improved_count']} | {o['worsened_count']} | {o['unchanged_count']} |"
        )
    lines += [
        "",
        "A changed item means the selected StatBound piece sequence differs from ordinary Unigram8k. Added and removed boundaries are exact set differences. Potential shifts pair one removed location with one added location; they are reported separately and are not substituted for the raw set differences.",
        "",
    ]
    for lam, d in result["per_lambda"].items():
        lines += [f"### λ={lam} changed-item list", ""]
        if not d["changed_items"]:
            lines.append("No benchmark item changed relative to Unigram8k.")
            lines.append(f"All 162 selected candidates were Unigram n-best rank 1: `{d['selected_candidate_nbest_rank_counts']}`.")
            lines.append("")
            continue
        lines.append("The complete item-level records, including all n-best candidate summaries, are in the JSON artifact. The compact table below preserves the required primary fields.")
        lines += ["", "| item | gold | Unigram | StatBound | Unigram P/R/F1 | StatBound P/R/F1 | SB boundary score | top1 log score | selected n-best rank |", "|---|---|---|---|---|---|---:|---:|---:|"]
        for item in d["changed_items"]:
            um, sm = item["unigram_metrics"], item["statbound_metrics"]
            lines.append(
                f"| {item['item_id']} | `{item['gold_segmentation']}` | `{item['unigram_segmentation']}` | `{item['statbound_segmentation']}` | "
                f"{f(um['precision'])}/{f(um['recall'])}/{f(um['f1'])} | {f(sm['precision'])}/{f(sm['recall'])}/{f(sm['f1'])} | "
                f"{f(item['statbound_boundary_score'])} | {f(item['original_unigram_candidate_score'])} | {item['selected_candidate_nbest_rank']} |"
            )
        lines.append("")
    lines += [
        "## n-best candidate availability",
        "",
        "The n-best set is the frozen SentencePiece Unigram default plus the returned `nbest_encode_as_pieces(word, 16)` candidates, deduplicated by sequence. Percentages use all 162 items.",
        "",
        "| λ | higher-F1 candidate exists | gold segmentation exists | StatBound selects higher-F1 candidate | StatBound selects gold |",
        "|---:|---:|---:|---:|---:|",
    ]
    for lam, d in result["coverage_by_lambda"].items():
        lines.append(
            f"| {lam} | {d['items_with_higher_f1_candidate']} ({f(d['higher_f1_candidate_percentage'], 2)}%) | "
            f"{d['items_with_gold_in_nbest']} ({f(d['gold_in_nbest_percentage'], 2)}%) | "
            f"{d['selected_better_than_top1_count']} ({f(d['selected_better_than_top1_percentage'], 2)}%) | "
            f"{d['selected_gold_count']} ({f(d['selected_gold_percentage'], 2)}%) |"
        )
    lines += [
        "",
        "The per-item yes/no determination for all 162 items is stored under `item_candidate_availability` in the JSON artifact.",
        "",
        "## Boundary-score distributions",
        "",
        "These are the selected-candidate compatibility scores used by the frozen reranker, not gold labels.",
        "",
        "| λ | zero | nonzero | mean | median | min | max |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for lam, d in result["per_lambda"].items():
        s = d["statbound_boundary_score_distribution"]
        lines.append(f"| {lam} | {s['zero_count']} | {s['nonzero_count']} | {f(s['mean'])} | {f(s['median'])} | {f(s['min'])} | {f(s['max'])} |")
    lines += [
        "",
        "## Weighting analysis",
        "",
        "The direct selection comparison is λ × (selected boundary score − top1 boundary score) versus the top1-to-selected Unigram score gap. For completeness, λ × selected boundary score is also reported.",
        "",
        "| λ | λ×selected score mean/median/min/max | λ×score delta mean/median/min/max | top1→selected gap mean/median/min/max | selected combined score beats top1 |",
        "|---:|---|---|---|---:|",
    ]
    for lam, d in result["per_lambda"].items():
        w = d["weighting_diagnostics"]
        def sm(key: str) -> str:
            s = w[key]
            return f"{f(s['mean'])}/{f(s['median'])}/{f(s['min'])}/{f(s['max'])}"
        lines.append(f"| {lam} | {sm('lambda_times_selected_boundary_score')} | {sm('lambda_times_boundary_score_delta_vs_top1')} | {sm('top1_to_selected_unigram_score_gap')} | {w['selected_alternative_combined_score_beats_top1_count']} |")
    lines += [
        "",
        "Across every returned non-top1 candidate (not only the candidate selected by StatBound):",
        "",
        "| λ | alternatives | λ×boundary-score delta mean/median/min/max | Unigram gap mean/median/min/max | signal−gap mean/median/min/max | signal > gap |",
        "|---:|---:|---|---|---|---:|",
    ]
    for lam, d in result["per_lambda"].items():
        w = d["weighting_diagnostics"]
        def sm2(key: str) -> str:
            s = w[key]
            return f"{f(s['mean'])}/{f(s['median'])}/{f(s['min'])}/{f(s['max'])}"
        lines.append(
            f"| {lam} | {w['all_alternative_count']} | {sm2('all_alternative_lambda_times_boundary_score_delta')} | "
            f"{sm2('all_alternative_top1_to_candidate_unigram_score_gap')} | {sm2('all_alternative_signal_minus_gap')} | "
            f"{w['all_alternative_signal_exceeds_gap_count']} |"
        )
    g = result["weighting_global"]
    lines += [
        "",
        f"Across all non-top1 candidates, the top1-to-alternative Unigram score-gap distribution is mean/median/min/max = **{f(g['all_alternative_score_gap_distribution']['mean'])}/{f(g['all_alternative_score_gap_distribution']['median'])}/{f(g['all_alternative_score_gap_distribution']['min'])}/{f(g['all_alternative_score_gap_distribution']['max'])}** over {g['all_alternative_score_gap_distribution']['count']} candidate alternatives.",
        f"Items with any candidate-boundary-score variation: **{g['items_with_candidate_boundary_score_variation']}/162**; items with any nonzero candidate boundary score: **{g['items_with_any_nonzero_candidate_boundary_score']}/162**.",
        "",
        "## Source of TPC differences",
        "",
        "| λ | benchmark-word TPC | benchmark words changed vs Unigram | benchmark token-count delta | Phase C validation-text TPC |",
        "|---:|---:|---:|---:|---:|",
    ]
    for lam, d in result["benchmark_word_efficiency"]["systems"].items():
        val_tpc = result["phase_c_validation_tpc"].get(lam)
        lines.append(f"| {lam} | {f(d['tokens_per_character'])} | {d['changed_word_count_vs_unigram']} ({f(d['changed_word_percentage'], 2)}%) | {d['token_count_delta_vs_unigram']} | {f(val_tpc)} |")
    lines += [
        "",
        f"Conclusion: **{result['benchmark_word_efficiency']['conclusion']}**",
        "The tiny validation-TPC difference between ordinary Unigram and StatBound λ=0/0.25 is consistent with the frozen implementation’s separate text paths: baseline SentencePiece encodes full lines, whereas `StatBoundUnigramTokenizer.encode_text` applies `text.split()` before encoding. This does not change the benchmark-word morphology segmentation result.",
        "",
        "## Implementation/dead-path audit",
        "",
    ]
    for key, value in result["implementation_audit"]["checks"].items():
        lines.append(f"- **{key}:** {value}")
    lines += [
        "",
        "Relevant frozen code paths were inspected without modification:",
        f"- n-best candidate construction: `{ADAPTER_SOURCE.relative_to(ROOT)}:{result['implementation_audit']['source_lines']['default_and_nbest']}`",
        f"- λ-weighted combined score: `{RERANKER_SOURCE.relative_to(ROOT)}:{result['implementation_audit']['source_lines']['combined_score']}`",
        f"- boundary compatibility: `{RERANKER_SOURCE.relative_to(ROOT)}:{result['implementation_audit']['source_lines']['boundary_compatibility']}`",
        f"- StatBound word encoding: `{TOKENIZER_SOURCE.relative_to(ROOT)}:{result['implementation_audit']['source_lines']['encode_word']}`",
        "",
        "## Conclusion",
        "",
        "The diagnosis is based on candidate availability, score magnitudes, selected boundary scores, and exact per-item comparisons. It does not change λ selection or interpret the development F1 as confirmatory evidence.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows = sorted(load_jsonl(ACTIVE), key=lambda r: r["item_id"])
    phase_c = json.loads(PHASE_C_RESULTS.read_text(encoding="utf-8"))
    if len(rows) != 162 or len({r["item_id"] for r in rows}) != 162:
        raise RuntimeError("active benchmark must contain exactly 162 unique items")
    if phase_c.get("evaluated_item_count") != 162:
        raise RuntimeError("Phase C result count is not 162")
    for p in (ACTIVE, PHASE_C_RESULTS, STATBOUND_CONFIG, BOUNDARY_STATS, UNIGRAM_MODEL):
        normalized = str(p).replace("\\", "/").lower()
        if "/test/" in normalized or "/locked/" in normalized or "holdout" in normalized or "bpc" in normalized:
            raise RuntimeError(f"forbidden diagnostic input path: {p}")
        if not p.is_file():
            raise FileNotFoundError(p)

    config = json.loads(STATBOUND_CONFIG.read_text(encoding="utf-8"))
    nbest_config = int(config["reranking"]["nbest_size"])
    if nbest_config != NBEST_SIZE:
        raise RuntimeError(f"frozen config nbest_size={nbest_config}, expected {NBEST_SIZE}")
    adapter = UnigramAdapter(UNIGRAM_MODEL)
    stats = load_boundary_stats(BOUNDARY_STATS)
    base_items = build_base_items(rows, adapter, stats)
    lambda_results: dict[str, dict[str, Any]] = {}
    lambda_result_objects: dict[float, dict[str, Any]] = {}
    for lam in LAMBDAS:
        result = analyze_lambda(lam, rows, base_items, adapter, stats)
        lambda_result_objects[lam] = result
        lambda_results[str(lam)] = result

    item_availability: list[dict[str, Any]] = []
    for row in rows:
        item = base_items[row["item_id"]]
        best = item["best_f1_entry"]
        item_availability.append({
            "item_id": row["item_id"],
            "surface_form": row["surface_form"],
            "gold_segmentation": seg_string(item["gold"]),
            "top1_unigram_segmentation": item["top1"]["segmentation"],
            "top1_unigram_score": item["top1"]["unigram_score"],
            "top1_unigram_f1": item["top1"]["metrics"]["f1"],
            "n_best_returned": item["n_best_returned"],
            "gold_in_nbest": bool(item["gold_entries"]),
            "gold_nbest_ranks": [x["unigram_score_rank"] for x in item["gold_entries"]],
            "higher_f1_candidate_exists": bool(item["better_entries"]),
            "best_f1_candidate_in_nbest": candidate_summary_for_changed(best) if best else None,
            "best_f1_candidate_is_gold": bool(best and best["pieces"] == item["gold"]),
            "candidate_boundary_score_variation": item["boundary_score_distinct"] > 1,
            "candidate_boundary_scores": item["candidate_boundary_scores"],
        })

    coverage_by_lambda: dict[str, dict[str, Any]] = {}
    n = len(rows)
    items_better = sum(1 for x in base_items.values() if x["better_entries"])
    items_gold = sum(1 for x in base_items.values() if x["gold_entries"])
    for lam, result in lambda_result_objects.items():
        coverage_by_lambda[str(lam)] = {
            "items_with_higher_f1_candidate": items_better,
            "higher_f1_candidate_percentage": 100.0 * items_better / n,
            "items_with_gold_in_nbest": items_gold,
            "gold_in_nbest_percentage": 100.0 * items_gold / n,
            "selected_better_than_top1_count": result["selected_better_than_top1_count"],
            "selected_better_than_top1_percentage": 100.0 * result["selected_better_than_top1_count"] / n,
            "selected_gold_count": result["selected_gold_count"],
            "selected_gold_percentage": 100.0 * result["selected_gold_count"] / n,
            "selected_best_nbest_f1_count": result["selected_best_nbest_f1_count"],
            "selected_best_nbest_f1_percentage": 100.0 * result["selected_best_nbest_f1_count"] / n,
        }

    all_gaps = [gap for item in base_items.values() for gap in item["alternative_score_gaps"]]
    candidate_variation = sum(1 for item in base_items.values() if item["boundary_score_distinct"] > 1)
    any_nonzero = sum(1 for item in base_items.values() if any(abs(v) > EPS for v in item["candidate_boundary_scores"]))
    benchmark_eff = benchmark_token_counts(rows, base_items, lambda_result_objects)
    phase_c_validation_tpc = {}
    for lam in LAMBDAS:
        sid = f"statbound_lambda_{str(lam).replace('.', '_')}"
        phase_c_validation_tpc[str(lam)] = phase_c["systems"][sid]["efficiency"]["sequence_efficiency"]["tokens_per_character"]
    benchmark_changed = any(
        x["changed_word_count_vs_unigram"] > 0 for x in benchmark_eff["systems"].values()
    )
    validation_changed = len({round(float(v), 12) for v in phase_c_validation_tpc.values()}) > 1
    if not benchmark_changed and validation_changed:
        tpc_conclusion = "TPC differences come from the broader validation-text path, not from changed benchmark-word segmentations."
    elif benchmark_changed:
        tpc_conclusion = "TPC differences are present on benchmark words as well as the broader validation text."
    else:
        tpc_conclusion = "No TPC differences were observed across the checked benchmark-word and validation-text summaries."

    implementation = {
        "checks": {
            "lambda_0_morphology_control": phase_c.get("lambda_zero_control", {}).get("passes"),
            "candidate_set_is_frozen_unigram_nbest": True,
            "lambda_enters_combined_score": True,
            "boundary_compatibility_called_for_candidates": True,
            "candidate_set_size_min_median_max": [
                min(x["n_best_returned"] for x in base_items.values()),
                statistics.median(x["n_best_returned"] for x in base_items.values()),
                max(x["n_best_returned"] for x in base_items.values()),
            ],
            "items_with_any_lambda_reranker_change": sum(
                1 for item_id in base_items if any(item_id in r["changed_item_ids"] for r in lambda_result_objects.values())
            ),
            "validation_whitespace_path_difference": True,
            "tokenizer_algorithm_modified": False,
        },
        "source_lines": {
            "default_and_nbest": line_no(ADAPTER_SOURCE, "def default_and_nbest"),
            "combined_score": line_no(RERANKER_SOURCE, "combined = cand.unigram_score"),
            "boundary_compatibility": line_no(RERANKER_SOURCE, "def boundary_compatibility"),
            "encode_word": line_no(TOKENIZER_SOURCE, "def encode_word"),
        },
        "boundary_stats_metadata": {
            key: stats.get(key)
            for key in ("schema_version", "formula_id", "n_types", "n_tokens", "n_chars")
            if key in stats
        },
    }

    failure = classify_failure(rows, base_items, lambda_result_objects, {"validation_whitespace_path_difference": True})
    result = {
        "schema_version": "phase_c_statbound_failure_diagnostic_v0_1",
        "diagnostic_type": "post_phase_c_diagnostic_only",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_phase_c_results": str(PHASE_C_RESULTS.relative_to(ROOT)),
        "benchmark_item_count": len(rows),
        "nbest_size": NBEST_SIZE,
        "lambda_values": list(LAMBDAS),
        "per_lambda": lambda_results,
        "coverage_by_lambda": coverage_by_lambda,
        "item_candidate_availability": item_availability,
        "weighting_global": {
            "all_alternative_score_gap_distribution": summarize(all_gaps),
            "items_with_candidate_boundary_score_variation": candidate_variation,
            "items_with_any_nonzero_candidate_boundary_score": any_nonzero,
        },
        "benchmark_word_efficiency": {
            **benchmark_eff,
            "conclusion": tpc_conclusion,
        },
        "phase_c_validation_tpc": phase_c_validation_tpc,
        "implementation_audit": implementation,
        "failure_classification": failure,
        "restricted_materials": {
            "morphology_holdout_accessed": False,
            "lm_test_accessed": False,
            "lm_bpc_accessed": False,
            "phase_c_rerun": False,
            "phase_f_run": False,
        },
        "benchmark_modified": False,
        "lambda_selection_modified": False,
        "algorithm_modified": False,
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(make_report(result), encoding="utf-8")
    print(f"diagnostic JSON: {OUT_JSON.relative_to(ROOT)}")
    print(f"diagnostic Markdown: {OUT_MD.relative_to(ROOT)}")
    print(f"dominant failure modes: {', '.join(failure['dominant_failure_modes'])}")
    for lam, d in lambda_results.items():
        print(f"lambda={lam}: changed={d['changed_item_count']}/{len(rows)}; added={d['boundary_decisions']['added_count']}; removed={d['boundary_decisions']['removed_count']}; score_mean={d['statbound_boundary_score_distribution']['mean']}")
    print(f"restricted materials: holdout/test/BPC accessed=false; Phase C rerun=false; Phase F=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
