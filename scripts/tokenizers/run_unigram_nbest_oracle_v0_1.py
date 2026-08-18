#!/usr/bin/env python3
"""Unigram n-best morphology oracle + compat-alignment diagnostic.

Analysis only on the frozen 162-item Level-B development benchmark.

Gold is used solely to score already-generated Unigram n-best=16 candidates.
This script does not:
  - train or modify a tokenizer
  - select λ or α
  - open morphology holdout
  - open LM test or any BPC artifact
  - open validation/train text
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.tokenizers.statbound.boundary_stats import get_strength, load_boundary_stats  # noqa: E402
from src.tokenizers.statbound.metrics import (  # noqa: E402
    aggregate_boundary_metrics,
    boundaries_from_segments,
    boundary_metrics,
    parse_segments,
)
from src.tokenizers.statbound.nbest_oracle import (  # noqa: E402
    EPS,
    SC4_DEV_MARGIN,
    ScoredCandidate,
    assign_unigram_ranks,
    compare_f1,
    defined_correlations,
    family_decision,
    micro_boundary_metrics,
    official_f1,
    oracle_sort_key,
    pearson,
    pick_compat_oracle,
    pick_oracle,
    restricted_rank_oracle,
    sign_delta,
    spearman,
    summarize,
)
from src.tokenizers.statbound.reranker import boundary_compatibility  # noqa: E402
from src.tokenizers.statbound.unigram_adapter import UnigramAdapter  # noqa: E402

ACTIVE = (
    ROOT
    / "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl"
)
UNIGRAM_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
BOUNDARY_STATS = ROOT / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
STATBOUND_CONFIG = ROOT / "configs/tokenizers/statbound_unigram_v1.json"
PHASE_C_RESULTS = ROOT / "data/reports/phase_c_morphology_v0_2_results.json"

OUT_JSON = ROOT / "data/reports/unigram_nbest_oracle_v0_1.json"
OUT_MD = ROOT / "data/reports/unigram_nbest_oracle_v0_1.md"

EXPECTED_ACTIVE_SHA256 = "73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67"
NBEST_SIZE = 16
RANK_CAPS = (2, 4, 8, 16)
FORBIDDEN_INPUT_MARKERS = ("/test/", "/locked/", "holdout", "lm_test", "phase_f")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str | None:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return p.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def assert_analysis_inputs() -> None:
    for path in (ACTIVE, UNIGRAM_MODEL, BOUNDARY_STATS, STATBOUND_CONFIG, PHASE_C_RESULTS):
        s = str(path.resolve()).replace("\\", "/").lower()
        for bad in FORBIDDEN_INPUT_MARKERS:
            if bad in s:
                raise RuntimeError(f"forbidden analysis input path: {path} (matched {bad!r})")
        if not path.is_file():
            raise FileNotFoundError(path)
        if "/validation/" in s:
            raise RuntimeError(f"validation text must not be opened: {path}")
    digest = sha256_file(ACTIVE)
    if digest != EXPECTED_ACTIVE_SHA256:
        raise RuntimeError(f"frozen active benchmark hash mismatch: {digest}")


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pct(count: int, n: int) -> str:
    if n <= 0:
        return "—"
    return f"{count}/{n} ({100.0 * count / n:.2f}%)"


def build_candidates(
    word: str,
    gold: list[str],
    adapter: UnigramAdapter,
    stats: dict[str, Any],
) -> list[ScoredCandidate]:
    default_raw = tuple(adapter.encode_as_pieces(word))
    default_surf = tuple(p.lstrip("▁") for p in default_raw)
    raw_rows: list[tuple[tuple[str, ...], float, bool]] = []
    raw_keep: list[tuple[tuple[str, ...], tuple[str, ...], float, bool]] = []
    seen: set[tuple[str, ...]] = set()
    for cand in adapter.default_and_nbest(word, NBEST_SIZE):
        raw = tuple(cand.pieces)
        surf = tuple(p.lstrip("▁") for p in raw)
        if "".join(surf) != word or surf in seen:
            continue
        seen.add(surf)
        is_s0 = surf == default_surf
        raw_keep.append((raw, surf, float(cand.unigram_score), is_s0))
        raw_rows.append((surf, float(cand.unigram_score), is_s0))
    if default_surf not in seen:
        score = adapter.unigram_score(list(default_raw))
        raw_keep.insert(0, (default_raw, default_surf, score, True))
        raw_rows.insert(0, (default_surf, score, True))
    ranks = assign_unigram_ranks(raw_rows)
    out: list[ScoredCandidate] = []
    for (raw, surf, score, is_s0), rank in zip(raw_keep, ranks):
        compat = boundary_compatibility(word, list(raw), stats)
        metrics = boundary_metrics(gold, list(surf))
        out.append(
            ScoredCandidate(
                pieces=surf,
                raw_pieces=raw,
                unigram_score=score,
                unigram_rank=int(rank),
                is_s0=is_s0,
                compat=None if compat is None else float(compat),
                metrics=metrics,
            )
        )
    if not any(c.is_s0 for c in out):
        raise RuntimeError(f"Unigram default missing from candidate set: {word!r}")
    return out


def s0_of(cands: list[ScoredCandidate]) -> ScoredCandidate:
    for cand in cands:
        if cand.is_s0:
            return cand
    raise RuntimeError("S0 missing")


def candidate_record(cand: ScoredCandidate) -> dict[str, Any]:
    return {
        "pieces": list(cand.pieces),
        "segmentation": cand.segmentation,
        "unigram_score": cand.unigram_score,
        "unigram_rank": cand.unigram_rank,
        "is_s0": cand.is_s0,
        "compat": cand.compat,
        "boundary_precision": cand.metrics.get("boundary_precision"),
        "boundary_recall": cand.metrics.get("boundary_recall"),
        "boundary_f1": cand.metrics.get("boundary_f1"),
        "exact": bool(cand.metrics.get("exact_segmentation_match")),
    }


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


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


def render_report(result: dict[str, Any]) -> str:
    u = result["unigram"]
    o = result["f1_oracle"]
    c = result["compat_oracle"]
    a = result["alignment"]
    d = result["family_decision"]
    g = result["gains"]
    lines = [
        "# Unigram n-best candidate-set oracle v0.1",
        "",
        "Analysis only. Gold scores a frozen Unigram n-best=16 candidate set.",
        "This is not a tokenizer, not V2, and not a hyperparameter search.",
        "",
        "## Scope and locks",
        "",
        f"- Active development items: **{result['n_items']}**",
        f"- Active benchmark SHA-256: `{result['active_sha256']}`",
        f"- SHA verified: **{result['active_sha_ok']}**",
        f"- n-best size: **{result['nbest_size']}**",
        f"- Morphology holdout accessed: **{result['restricted']['morphology_holdout_accessed']}**",
        f"- LM test accessed: **{result['restricted']['lm_test_accessed']}**",
        f"- LM BPC accessed: **{result['restricted']['lm_bpc_accessed']}**",
        f"- Validation/train text opened: **{result['restricted']['corpus_text_opened']}**",
        f"- λ/α selected: **{result['restricted']['hyperparameter_selected']}**",
        "",
        "## Decision (pre-declared rule)",
        "",
        f"**`{d['code']}`**",
        "",
        d["reason"] + ".",
        "",
        "This decision chooses a *family*, not α. Gold was not used as a training signal.",
        "",
        "## Headline metrics",
        "",
        "| system | macro P | macro R | macro F1 | exact | micro P | micro R | micro F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| Unigram top-1 | {fmt(u['macro']['boundary_precision'])} | "
            f"{fmt(u['macro']['boundary_recall'])} | {fmt(u['macro']['boundary_f1'])} | "
            f"{fmt(u['macro']['exact_match_rate'])} | {fmt(u['micro']['boundary_precision'])} | "
            f"{fmt(u['micro']['boundary_recall'])} | {fmt(u['micro']['boundary_f1'])} |"
        ),
        (
            f"| F1 oracle | {fmt(o['macro']['boundary_precision'])} | "
            f"{fmt(o['macro']['boundary_recall'])} | {fmt(o['macro']['boundary_f1'])} | "
            f"{fmt(o['macro']['exact_match_rate'])} | {fmt(o['micro']['boundary_precision'])} | "
            f"{fmt(o['micro']['boundary_recall'])} | {fmt(o['micro']['boundary_f1'])} |"
        ),
        (
            f"| Compat oracle | {fmt(c['macro']['boundary_precision'])} | "
            f"{fmt(c['macro']['boundary_recall'])} | {fmt(c['macro']['boundary_f1'])} | "
            f"{fmt(c['macro']['exact_match_rate'])} | {fmt(c['micro']['boundary_precision'])} | "
            f"{fmt(c['micro']['boundary_recall'])} | {fmt(c['micro']['boundary_f1'])} |"
        ),
        "",
        f"- Official Unigram development F1 (Phase C): **{fmt(result['integrity']['phase_c_unigram_f1'])}**",
        f"- Recomputed Unigram F1: **{fmt(u['macro']['boundary_f1'])}**",
        f"- Match to Phase C Unigram F1: **{result['integrity']['unigram_f1_matches_phase_c']}**",
        "",
        "## Oracle gain over Unigram",
        "",
        f"- Macro ΔF1: **{fmt(g['macro_f1'])}**  (SC4 needs +{SC4_DEV_MARGIN:.2f})",
        f"- Macro ΔP: {fmt(g['macro_p'])}",
        f"- Macro ΔR: {fmt(g['macro_r'])}",
        f"- Δ exact rate: {fmt(g['exact_rate'])}  ({g['exact_count_oracle']} vs {g['exact_count_unigram']} items)",
        f"- Micro ΔF1: {fmt(g['micro_f1'])}",
        "",
        "## Availability",
        "",
        f"- Strictly higher-F1 candidate exists: **{pct(a['n_strictly_better_f1'], result['n_items'])}**",
        f"- Exact gold in n-best: **{pct(a['n_gold_in_nbest'], result['n_items'])}**",
        f"- Gold in n-best but Unigram is not gold: **{pct(a['n_gold_in_nbest_not_s0'], result['n_items'])}**",
        f"- Unigram already a best-F1 candidate: **{pct(a['n_s0_already_best_f1'], result['n_items'])}**",
        f"- F1 oracle ≠ Unigram top-1: **{pct(a['n_oracle_changes_s0'], result['n_items'])}**",
        f"- Unigram already exact gold: **{pct(u['macro']['exact_match_count'], result['n_items'])}**",
        "",
        "## Item-level F1 improvement magnitudes",
        "",
        "Computed only where both Unigram and oracle official item F1 are defined.",
        "",
        f"- n defined ΔF1 items: **{a['delta_f1']['count']}**",
        f"- mean / median / max ΔF1: **{fmt(a['delta_f1']['mean'])}** / {fmt(a['delta_f1']['median'])} / {fmt(a['delta_f1']['max'])}",
        f"- P10 / P90: {fmt(a['delta_f1']['p10'])} / {fmt(a['delta_f1']['p90'])}",
        f"- items with ΔF1 ≥ 0.10: **{pct(a['n_delta_f1_ge_0_10'], a['delta_f1']['count'] or 0)}**",
        f"- items with ΔF1 ≥ 0.25: **{pct(a['n_delta_f1_ge_0_25'], a['delta_f1']['count'] or 0)}**",
        "",
        "## Oracle choice rank distribution",
        "",
        "| Unigram rank of F1-oracle choice | n | % |",
        "|---:|---:|---:|",
    ]
    n = result["n_items"]
    for rank in range(1, NBEST_SIZE + 1):
        count = a["oracle_rank_histogram"].get(str(rank), 0)
        if count or rank <= 8:
            lines.append(f"| {rank} | {count} | {100.0 * count / n:.2f}% |")
    lines += [
        "",
        f"- Median oracle rank among changed items: **{fmt(a['median_oracle_rank_when_changed'], 1)}**",
        "",
        "## Ceiling if only shallow n-best ranks may be used",
        "",
        "| max Unigram rank | oracle macro F1 | ΔF1 vs Unigram | exact |",
        "|---:|---:|---:|---:|",
    ]
    for row in result["rank_restricted_oracles"]:
        lines.append(
            f"| {row['max_rank']} | {fmt(row['macro']['boundary_f1'])} | "
            f"{fmt(row['delta_macro_f1'])} | {fmt(row['macro']['exact_match_rate'])} |"
        )
    lines += [
        "",
        "## Compatibility alignment",
        "",
        "This is the measurement V1 could not make, because it never left top-1.",
        "",
        f"- Among items with a strictly better-F1 neighbour:",
        f"  - Δcompat > 0: **{pct(a['n_better_pos_compat'], a['n_strictly_better_f1'])}**",
        f"  - Δcompat = 0: **{pct(a['n_better_zero_compat'], a['n_strictly_better_f1'])}**",
        f"  - Δcompat < 0: **{pct(a['n_better_neg_compat'], a['n_strictly_better_f1'])}**",
        f"- Max-compat candidate equals max-F1 candidate: **{pct(a['n_max_compat_eq_max_f1'], n)}**",
        f"- Max-compat has higher official F1 than Unigram: **{pct(a['n_max_compat_better_f1_than_s0'], n)}**",
        f"- Max-compat has worse official F1 than Unigram: **{pct(a['n_max_compat_worse_f1_than_s0'], n)}**",
        f"- Compat-oracle macro F1: **{fmt(c['macro']['boundary_f1'])}** (Δ {fmt(c['delta_macro_f1_vs_unigram'])})",
        f"- Compat-oracle exact: **{fmt(c['macro']['exact_match_rate'])}**",
        "",
        "Among the better-F1 items with Δcompat = 0:",
        f"- all disputed boundary positions have V1 strength 0: "
        f"**{pct(a['n_zero_dcompat_all_disputed_bounds_unscored'], a['n_zero_dcompat_better_items'])}**",
        f"- disputed positions scored / total disputed: "
        f"**{a['n_zero_dcompat_disputed_bound_positions_scored']}/{a['n_zero_dcompat_disputed_bound_positions']}**",
        f"- entire word has no positive V1 strengths: "
        f"**{pct(a['n_zero_dcompat_word_all_strengths_zero'], a['n_zero_dcompat_better_items'])}**",
        "",
        "### Within-n-best correlation of compat vs official F1",
        "",
        f"- Items with a defined Spearman: **{a['item_spearman']['n_defined']}**",
        f"- Mean / median item Spearman: **{fmt(a['item_spearman']['mean'])}** / {fmt(a['item_spearman']['median'])}",
        f"- Pooled Pearson / Spearman over all defined (compat, F1) pairs: "
        f"**{fmt(a['pooled']['pearson'])}** / **{fmt(a['pooled']['spearman'])}** "
        f"(n={a['pooled']['n_pairs']})",
        "",
        "## Stratification (F1-oracle ΔF1 vs Unigram, defined items only)",
        "",
        "### source",
        "",
        "| source | n | Unigram F1 | oracle F1 | ΔF1 | better-F1 exists | better and Δcompat>0 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["by_source"]:
        lines.append(
            f"| {row['source']} | {row['n']} | {fmt(row['unigram_f1'])} | {fmt(row['oracle_f1'])} | "
            f"{fmt(row['delta_f1'])} | {row['n_better_f1']} | {row['n_better_pos_compat']} |"
        )
    lines += [
        "",
        "### gold piece count",
        "",
        "| gold pieces | n | Unigram F1 | oracle F1 | ΔF1 | better-F1 exists |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["by_gold_piece_count"]:
        lines.append(
            f"| {row['gold_piece_count']} | {row['n']} | {fmt(row['unigram_f1'])} | "
            f"{fmt(row['oracle_f1'])} | {fmt(row['delta_f1'])} | {row['n_better_f1']} |"
        )
    lines += [
        "",
        "## Largest oracle F1 gains (development examples)",
        "",
        "| item | word | Unigram | oracle | ΔF1 | Unigram rank | Δcompat |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in result["examples"]["largest_gains"]:
        lines.append(
            f"| `{row['item_id']}` | {row['surface_form']} | `{row['unigram_segmentation']}` | "
            f"`{row['oracle_segmentation']}` | {fmt(row['delta_f1'])} | {row['oracle_unigram_rank']} | "
            f"{fmt(row['delta_compat'])} |"
        )
    lines += [
        "",
        "## Better-F1 items where compat does **not** agree (Δcompat ≤ 0)",
        "",
        "| item | word | Unigram | better-F1 candidate | ΔF1 | Δcompat |",
        "|---|---|---|---|---:|---:|",
    ]
    disagree = result["examples"]["better_f1_nonpositive_compat"]
    if not disagree:
        lines.append("| — | — | — | — | — | — |")
    for row in disagree:
        lines.append(
            f"| `{row['item_id']}` | {row['surface_form']} | `{row['unigram_segmentation']}` | "
            f"`{row['better_segmentation']}` | {fmt(row['delta_f1'])} | {fmt(row['delta_compat'])} |"
        )
    lines += [
        "",
        "## Integrity",
        "",
        f"- Gold reconstruction failures: **{result['integrity']['gold_reconstruction_failures']}**",
        f"- Candidate reconstruction failures: **{result['integrity']['candidate_reconstruction_failures']}**",
        f"- Duplicate item IDs: **{result['integrity']['duplicate_ids']}**",
        f"- Candidate-set size min/median/max: "
        f"{result['integrity']['candidate_set_size']['min']} / "
        f"{result['integrity']['candidate_set_size']['median']} / "
        f"{result['integrity']['candidate_set_size']['max']}",
        f"- Git HEAD: `{result['git_head']}`",
        f"- Generated at: {result['generated_at']}",
        "",
        "## How this may and may not be used",
        "",
        "Permitted: decide whether RelBound-Unigram V2, a different auxiliary score, "
        "or abandoning this generator is the next family.",
        "",
        "Prohibited: using oracle choices, ranks, or ΔF1 to set α/λ, retrain Unigram, "
        "update boundary statistics, or filter vocabulary.",
        "",
        "V1 remains a completed negative experiment. This file does not change λ*.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    assert_analysis_inputs()
    rows = sorted(load_jsonl(ACTIVE), key=lambda r: str(r["item_id"]))
    if len(rows) != 162 or len({r.get("item_id") for r in rows}) != 162:
        raise RuntimeError("frozen active benchmark is not exactly 162 unique items")
    config = json.loads(STATBOUND_CONFIG.read_text(encoding="utf-8"))
    if int(config["reranking"]["nbest_size"]) != NBEST_SIZE:
        raise RuntimeError("frozen nbest_size mismatch")
    phase_c = json.loads(PHASE_C_RESULTS.read_text(encoding="utf-8"))
    phase_c_unigram_f1 = phase_c["systems"]["unigram_8000"]["morphology"]["aggregate"]["boundary_f1"]

    adapter = UnigramAdapter(UNIGRAM_MODEL)
    stats = load_boundary_stats(BOUNDARY_STATS)

    item_rows: list[dict[str, Any]] = []
    unigram_metrics: list[dict[str, Any]] = []
    oracle_metrics: list[dict[str, Any]] = []
    compat_metrics: list[dict[str, Any]] = []
    unigram_pairs: list[tuple[list[str], list[str]]] = []
    oracle_pairs: list[tuple[list[str], list[str]]] = []
    compat_pairs: list[tuple[list[str], list[str]]] = []
    rank_cap_metrics: dict[int, list[dict[str, Any]]] = {k: [] for k in RANK_CAPS}
    rank_cap_pairs: dict[int, list[tuple[list[str], list[str]]]] = {k: [] for k in RANK_CAPS}

    gold_fail = 0
    cand_fail = 0
    sizes: list[int] = []
    item_spearmans: list[float] = []
    pooled_compat: list[float] = []
    pooled_f1: list[float] = []
    delta_f1s: list[float] = []
    changed_ranks: list[int] = []
    oracle_rank_hist: Counter[str] = Counter()

    n_better = 0
    n_better_pos = 0
    n_better_zero = 0
    n_better_neg = 0
    n_gold_in = 0
    n_gold_not_s0 = 0
    n_s0_best = 0
    n_oracle_changes = 0
    n_maxc_eq_maxf = 0
    n_maxc_better = 0
    n_maxc_worse = 0
    n_delta_10 = 0
    n_delta_25 = 0
    n_zero_dcompat = 0
    n_zero_dcompat_all_diff_unscored = 0
    n_zero_dcompat_word_all_strength_zero = 0
    n_zero_dcompat_diff_bounds = 0
    n_zero_dcompat_diff_scored = 0

    examples_gain: list[dict[str, Any]] = []
    examples_disagree: list[dict[str, Any]] = []

    for row in rows:
        item_id = str(row["item_id"])
        word = str(row["surface_form"])
        gold = parse_segments(row.get("final_segmentation"))
        if not gold or "".join(gold) != word:
            gold_fail += 1
            raise RuntimeError(f"gold reconstruction failure: {item_id}")
        cands = build_candidates(word, gold, adapter, stats)
        if any("".join(c.pieces) != word for c in cands):
            cand_fail += 1
            raise RuntimeError(f"candidate reconstruction failure: {item_id}")
        sizes.append(len(cands))
        s0 = s0_of(cands)
        oracle = pick_oracle(cands)
        compat_choice = pick_compat_oracle(cands)
        best_f1 = oracle
        gold_hits = [c for c in cands if list(c.pieces) == gold]
        better = []
        s0_f1 = official_f1(s0.metrics)
        for cand in cands:
            f1 = official_f1(cand.metrics)
            if f1 is not None and s0_f1 is not None and f1 > s0_f1 + EPS:
                better.append(cand)
        better.sort(key=oracle_sort_key)

        unigram_metrics.append(s0.metrics)
        oracle_metrics.append(oracle.metrics)
        compat_metrics.append(compat_choice.metrics)
        unigram_pairs.append((gold, list(s0.pieces)))
        oracle_pairs.append((gold, list(oracle.pieces)))
        compat_pairs.append((gold, list(compat_choice.pieces)))
        for k in RANK_CAPS:
            capped = restricted_rank_oracle(cands, k)
            rank_cap_metrics[k].append(capped.metrics)
            rank_cap_pairs[k].append((gold, list(capped.pieces)))

        corr = defined_correlations(cands)
        if isinstance(corr["spearman"], float):
            item_spearmans.append(float(corr["spearman"]))
        for cand in cands:
            if cand.compat is None:
                continue
            f1 = official_f1(cand.metrics)
            if f1 is None:
                continue
            pooled_compat.append(float(cand.compat))
            pooled_f1.append(f1)

        oracle_rank_hist[str(oracle.unigram_rank)] += 1
        changed = list(oracle.pieces) != list(s0.pieces)
        if changed:
            n_oracle_changes += 1
            changed_ranks.append(oracle.unigram_rank)

        s0_already_best = official_f1(s0.metrics) is not None and all(
            official_f1(c.metrics) is None
            or official_f1(c.metrics) <= official_f1(s0.metrics) + EPS
            for c in cands
        )
        # also treat exact S0 as already-best when official F1 is undefined
        if s0.metrics.get("exact_segmentation_match"):
            s0_already_best = True
        if s0_already_best:
            n_s0_best += 1

        if gold_hits:
            n_gold_in += 1
            if not s0.metrics.get("exact_segmentation_match"):
                n_gold_not_s0 += 1

        if better:
            n_better += 1
            top_better = better[0]
            if s0.compat is None or top_better.compat is None:
                pass
            else:
                dcompat = float(top_better.compat) - float(s0.compat)
                sign = sign_delta(dcompat)
                if sign == "positive":
                    n_better_pos += 1
                elif sign == "zero":
                    n_better_zero += 1
                    n_zero_dcompat += 1
                    b0 = boundaries_from_segments(s0.pieces)
                    bb = boundaries_from_segments(top_better.pieces)
                    diff = (b0 | bb) - (b0 & bb)
                    n_zero_dcompat_diff_bounds += len(diff)
                    scored_diff = [i for i in diff if abs(get_strength(stats, word, i)) > EPS]
                    n_zero_dcompat_diff_scored += len(scored_diff)
                    if not scored_diff:
                        n_zero_dcompat_all_diff_unscored += 1
                    if all(
                        abs(get_strength(stats, word, i)) <= EPS for i in range(1, len(word))
                    ):
                        n_zero_dcompat_word_all_strength_zero += 1
                else:
                    n_better_neg += 1
                better_f1 = official_f1(top_better.metrics)
                if s0_f1 is not None and better_f1 is not None:
                    examples_disagree.append(
                        {
                            "item_id": item_id,
                            "surface_form": word,
                            "unigram_segmentation": s0.segmentation,
                            "better_segmentation": top_better.segmentation,
                            "delta_f1": better_f1 - s0_f1,
                            "delta_compat": dcompat,
                        }
                    )

        if list(compat_choice.pieces) == list(best_f1.pieces):
            n_maxc_eq_maxf += 1
        rel = compare_f1(official_f1(compat_choice.metrics), s0_f1)
        if rel == "better":
            n_maxc_better += 1
        elif rel == "worse":
            n_maxc_worse += 1

        oracle_f1 = official_f1(oracle.metrics)
        if s0_f1 is not None and oracle_f1 is not None:
            df1 = oracle_f1 - s0_f1
            delta_f1s.append(df1)
            if df1 >= 0.10 - EPS:
                n_delta_10 += 1
            if df1 >= 0.25 - EPS:
                n_delta_25 += 1
            examples_gain.append(
                {
                    "item_id": item_id,
                    "surface_form": word,
                    "unigram_segmentation": s0.segmentation,
                    "oracle_segmentation": oracle.segmentation,
                    "gold_segmentation": "+".join(gold),
                    "delta_f1": df1,
                    "oracle_unigram_rank": oracle.unigram_rank,
                    "delta_compat": (
                        None
                        if oracle.compat is None or s0.compat is None
                        else float(oracle.compat) - float(s0.compat)
                    ),
                }
            )

        item_rows.append(
            {
                "item_id": item_id,
                "surface_form": word,
                "source": row.get("source"),
                "gold_segmentation": "+".join(gold),
                "gold_piece_count": len(gold),
                "n_candidates": len(cands),
                "gold_in_nbest": bool(gold_hits),
                "higher_f1_exists": bool(better),
                "s0_already_best_f1": s0_already_best,
                "unigram": candidate_record(s0),
                "f1_oracle": candidate_record(oracle),
                "compat_oracle": candidate_record(compat_choice),
                "oracle_changes_unigram": changed,
                "delta_f1_official": (
                    None if s0_f1 is None or oracle_f1 is None else oracle_f1 - s0_f1
                ),
                "delta_compat_oracle_vs_s0": (
                    None
                    if oracle.compat is None or s0.compat is None
                    else float(oracle.compat) - float(s0.compat)
                ),
                "delta_compat_best_better_vs_s0": (
                    None
                    if not better or better[0].compat is None or s0.compat is None
                    else float(better[0].compat) - float(s0.compat)
                ),
                "item_compat_f1_correlation": corr,
                "candidates": [candidate_record(c) for c in cands],
            }
        )

    unigram_macro = aggregate_boundary_metrics(unigram_metrics)
    oracle_macro = aggregate_boundary_metrics(oracle_metrics)
    compat_macro = aggregate_boundary_metrics(compat_metrics)
    unigram_micro = micro_boundary_metrics(unigram_pairs)
    oracle_micro = micro_boundary_metrics(oracle_pairs)
    compat_micro = micro_boundary_metrics(compat_pairs)

    def delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return a - b

    gains = {
        "macro_f1": delta(oracle_macro["boundary_f1"], unigram_macro["boundary_f1"]),
        "macro_p": delta(oracle_macro["boundary_precision"], unigram_macro["boundary_precision"]),
        "macro_r": delta(oracle_macro["boundary_recall"], unigram_macro["boundary_recall"]),
        "exact_rate": delta(oracle_macro["exact_match_rate"], unigram_macro["exact_match_rate"]),
        "exact_count_oracle": oracle_macro["exact_match_count"],
        "exact_count_unigram": unigram_macro["exact_match_count"],
        "micro_f1": delta(oracle_micro["boundary_f1"], unigram_micro["boundary_f1"]),
    }

    # Keep only nonpositive-compat disagreements in the disagree example list.
    disagree_kept = [
        x
        for x in examples_disagree
        if x["delta_compat"] is not None and x["delta_compat"] <= EPS
    ]
    disagree_kept.sort(key=lambda x: (-(x["delta_f1"] or 0.0), x["item_id"]))
    examples_gain.sort(key=lambda x: (-(x["delta_f1"] or 0.0), x["item_id"]))

    decision = family_decision(
        oracle_delta_macro_f1=gains["macro_f1"],
        n_strictly_better_f1=n_better,
        n_better_with_pos_compat=n_better_pos,
    )

    rank_restricted = []
    for k in RANK_CAPS:
        macro = aggregate_boundary_metrics(rank_cap_metrics[k])
        rank_restricted.append(
            {
                "max_rank": k,
                "macro": macro,
                "micro": micro_boundary_metrics(rank_cap_pairs[k]),
                "delta_macro_f1": delta(macro["boundary_f1"], unigram_macro["boundary_f1"]),
            }
        )

    def group_rows(key_fn) -> list[dict[str, Any]]:
        groups: dict[Any, list[dict[str, Any]]] = {}
        for rec in item_rows:
            groups.setdefault(key_fn(rec), []).append(rec)
        out = []
        for key in sorted(groups, key=lambda x: (str(type(x)), x)):
            recs = groups[key]
            u_f1s = [r["unigram"]["boundary_f1"] for r in recs if r["unigram"]["boundary_f1"] is not None]
            o_f1s = [r["f1_oracle"]["boundary_f1"] for r in recs if r["f1_oracle"]["boundary_f1"] is not None]
            u_mean = mean_or_none(u_f1s)
            o_mean = mean_or_none(o_f1s)
            out.append(
                {
                    "key": key,
                    "n": len(recs),
                    "unigram_f1": u_mean,
                    "oracle_f1": o_mean,
                    "delta_f1": None if u_mean is None or o_mean is None else o_mean - u_mean,
                    "n_better_f1": sum(1 for r in recs if r["higher_f1_exists"]),
                    "n_better_pos_compat": sum(
                        1
                        for r in recs
                        if r["higher_f1_exists"]
                        and r["delta_compat_best_better_vs_s0"] is not None
                        and r["delta_compat_best_better_vs_s0"] > EPS
                    ),
                }
            )
        return out

    by_source_raw = group_rows(lambda r: r.get("source") or "unknown")
    by_source = [{"source": r["key"], **{k: v for k, v in r.items() if k != "key"}} for r in by_source_raw]
    by_gold_raw = group_rows(lambda r: int(r["gold_piece_count"]))
    by_gold = [
        {"gold_piece_count": r["key"], **{k: v for k, v in r.items() if k != "key"}}
        for r in by_gold_raw
    ]

    sizes_sorted = sorted(sizes)
    mid = len(sizes_sorted) // 2
    size_median = (
        sizes_sorted[mid]
        if len(sizes_sorted) % 2
        else 0.5 * (sizes_sorted[mid - 1] + sizes_sorted[mid])
    )
    unigram_f1_match = (
        abs(float(unigram_macro["boundary_f1"]) - float(phase_c_unigram_f1)) < 1e-6
    )

    result = {
        "schema_version": "unigram_nbest_oracle_v0_1",
        "analysis_type": "candidate_set_oracle_and_compat_alignment",
        "generated_at": now_iso(),
        "git_head": git_head(),
        "n_items": len(rows),
        "nbest_size": NBEST_SIZE,
        "active_benchmark": str(ACTIVE.relative_to(ROOT)),
        "active_sha256": sha256_file(ACTIVE),
        "active_sha_ok": True,
        "unigram_model": str(UNIGRAM_MODEL.relative_to(ROOT)),
        "boundary_stats": str(BOUNDARY_STATS.relative_to(ROOT)),
        "restricted": {
            "morphology_holdout_accessed": False,
            "lm_test_accessed": False,
            "lm_bpc_accessed": False,
            "corpus_text_opened": False,
            "hyperparameter_selected": False,
            "v1_lambda_modified": False,
            "gold_used_as": "scoring_function_over_frozen_unigram_nbest_only",
        },
        "unigram": {"macro": unigram_macro, "micro": unigram_micro},
        "f1_oracle": {"macro": oracle_macro, "micro": oracle_micro},
        "compat_oracle": {
            "macro": compat_macro,
            "micro": compat_micro,
            "delta_macro_f1_vs_unigram": delta(compat_macro["boundary_f1"], unigram_macro["boundary_f1"]),
        },
        "gains": gains,
        "alignment": {
            "n_strictly_better_f1": n_better,
            "n_better_pos_compat": n_better_pos,
            "n_better_zero_compat": n_better_zero,
            "n_better_neg_compat": n_better_neg,
            "n_zero_dcompat_better_items": n_zero_dcompat,
            "n_zero_dcompat_all_disputed_bounds_unscored": n_zero_dcompat_all_diff_unscored,
            "n_zero_dcompat_word_all_strengths_zero": n_zero_dcompat_word_all_strength_zero,
            "n_zero_dcompat_disputed_bound_positions": n_zero_dcompat_diff_bounds,
            "n_zero_dcompat_disputed_bound_positions_scored": n_zero_dcompat_diff_scored,
            "n_gold_in_nbest": n_gold_in,
            "n_gold_in_nbest_not_s0": n_gold_not_s0,
            "n_s0_already_best_f1": n_s0_best,
            "n_oracle_changes_s0": n_oracle_changes,
            "n_max_compat_eq_max_f1": n_maxc_eq_maxf,
            "n_max_compat_better_f1_than_s0": n_maxc_better,
            "n_max_compat_worse_f1_than_s0": n_maxc_worse,
            "delta_f1": summarize(delta_f1s),
            "n_delta_f1_ge_0_10": n_delta_10,
            "n_delta_f1_ge_0_25": n_delta_25,
            "oracle_rank_histogram": dict(sorted(oracle_rank_hist.items(), key=lambda kv: int(kv[0]))),
            "median_oracle_rank_when_changed": (
                None
                if not changed_ranks
                else summarize(changed_ranks)["median"]
            ),
            "item_spearman": {
                "n_defined": len(item_spearmans),
                "mean": mean_or_none(item_spearmans),
                "median": summarize(item_spearmans)["median"],
            },
            "pooled": {
                "n_pairs": len(pooled_compat),
                "pearson": pearson(pooled_compat, pooled_f1) if len(pooled_compat) >= 2 else None,
                "spearman": spearman(pooled_compat, pooled_f1) if len(pooled_compat) >= 2 else None,
            },
        },
        "family_decision": decision,
        "rank_restricted_oracles": rank_restricted,
        "by_source": by_source,
        "by_gold_piece_count": by_gold,
        "examples": {
            "largest_gains": examples_gain[:12],
            "better_f1_nonpositive_compat": disagree_kept[:12],
        },
        "integrity": {
            "gold_reconstruction_failures": gold_fail,
            "candidate_reconstruction_failures": cand_fail,
            "duplicate_ids": 0,
            "candidate_set_size": {
                "min": min(sizes),
                "median": size_median,
                "max": max(sizes),
            },
            "phase_c_unigram_f1": phase_c_unigram_f1,
            "unigram_f1_matches_phase_c": unigram_f1_match,
        },
        "items": item_rows,
    }

    write_json(OUT_JSON, result)
    write_text(OUT_MD, render_report(result))
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    print(f"decision: {decision['code']}")
    print(f"unigram_f1={unigram_macro['boundary_f1']}")
    print(f"oracle_f1={oracle_macro['boundary_f1']}")
    print(f"delta_f1={gains['macro_f1']}")
    print(
        f"better={n_better} pos_compat={n_better_pos} "
        f"zero={n_better_zero} neg={n_better_neg}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
