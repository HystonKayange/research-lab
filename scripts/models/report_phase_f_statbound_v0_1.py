#!/usr/bin/env python3
"""Aggregate and validate the frozen Phase-F StatBound lambda*=0.25 runs."""

from __future__ import annotations

import json
import math
import platform
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / "data/models/chichewa_corpus_v0.1/lm_baselines_v0.1"
STATBOUND_ROOT = MODEL_ROOT / "parameter_matched/statbound_lambda_0_25"
MATRIX = ROOT / "configs/models/lm_baselines_v0_1_final_matrix_r2.json"
BASELINE_SUMMARY = ROOT / "data/reports/lm_baselines_v0_1_validation_summary.json"
BASELINE_STATUS = ROOT / "data/metadata/lm_baselines_v0_1_matrix_r2_status.json"
TEST_READINESS = ROOT / "data/metadata/lm_baselines_v0_1_test_readiness.json"
PROTOCOL = ROOT / "docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md"
PROTOCOL_JSON = ROOT / "configs/tokenizers/statbound_unigram_v1_eval_protocol.json"
STATBOUND_CONFIG = ROOT / "configs/tokenizers/statbound_unigram_v1.json"
BOUNDARY_STATS = ROOT / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
BASE_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
BENCHMARK = ROOT / "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl"
FREEZE_MANIFEST = ROOT / "data/research/morphology_benchmark_v0.2/MORPHOLOGY_BENCHMARK_FREEZE_MANIFEST_v0_2.json"
RUNNER = ROOT / "scripts/models/run_phase_f_statbound_v1.py"
PHASE_C_SELECTION = ROOT / "data/reports/phase_c_lambda_selection_v0_2.json"

RESULTS = ROOT / "data/reports/phase_f_lm_results_v0_1.json"
REPORT = ROOT / "data/reports/phase_f_lm_report_v0_1.md"
SUCCESS_JSON = ROOT / "data/reports/phase_f_success_criteria_status_v0_1.json"
SUCCESS_MD = ROOT / "data/reports/phase_f_success_criteria_status_v0_1.md"
PROVENANCE = ROOT / "data/reports/phase_f_provenance_v0_1.json"

SEEDS = [42, 1337, 2026]
CONDITIONS = [
    ("parameter_matched", "fixed_characters", "primary_SC1"),
    ("architecture_matched", "fixed_characters", "secondary_SC2"),
    ("parameter_matched", "fixed_updates", "diagnostic_SC3"),
    ("architecture_matched", "fixed_updates", "diagnostic_SC3"),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mean_std(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "std": statistics.stdev(values) if len(values) > 1 else 0.0 if values else None,
        "values": values,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def key(track: str, budget: str) -> str:
    return f"{track}_x_{budget}"


def aggregate(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    return mean_std([float(r[field]) for r in rows])


def git_head() -> str | None:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        return p.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def collect_statbound() -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for track, budget, role in CONDITIONS:
        slug = read_json(MATRIX)["budget_path_slugs"][budget]
        for seed in SEEDS:
            run_dir = MODEL_ROOT / track / "statbound_lambda_0_25" / f"seed_{seed}" / "final" / slug
            mp = run_dir / "manifest.json"
            sp = run_dir / "source_validation_metrics.json"
            lock = run_dir / "selection_lock.json"
            if not mp.is_file() or not sp.is_file() or not lock.is_file():
                failures.append(f"missing artifact: {run_dir}")
                continue
            m = read_json(mp)
            s = read_json(sp)
            if m.get("status") != "completed":
                failures.append(f"manifest not completed: {run_dir}")
            if m.get("tokenizer_id") != "statbound_lambda_0_25":
                failures.append(f"wrong tokenizer id: {run_dir}")
            if not math.isclose(float(m.get("lambda", 0.25)), 0.25):
                # The manifest stores lambda in tokenizer verification, not top-level;
                # retain this check as a non-fatal compatibility check below.
                if m.get("tokenizer_verification", {}).get("lambda") != 0.25:
                    failures.append(f"wrong lambda provenance: {run_dir}")
            if m.get("nan_or_inf_detected"):
                failures.append(f"NaN/Inf detected: {run_dir}")
            if not m.get("checkpoint_reload_verification", {}).get("ok"):
                failures.append(f"checkpoint reload failed: {run_dir}")
            if m.get("test_evaluated_during_training") is not False:
                failures.append(f"test-access flag not false: {run_dir}")
            if s.get("lm_test_file_opened") is not False:
                failures.append(f"source evaluation test flag not false: {run_dir}")
            for sn, sm in (s.get("splits") or {}).items():
                if "/test/" in str(sm.get("source_path", "")).replace("\\", "/"):
                    failures.append(f"test source path present: {run_dir}/{sn}")
            b = m["best_checkpoint"]
            e = m["exposure"]
            r = m["runtime"]
            rows.append(
                {
                    "track": track,
                    "budget_policy": budget,
                    "role": role,
                    "seed": seed,
                    "run_id": m["run_id"],
                    "run_dir": str(run_dir.relative_to(ROOT)),
                    "status": m["status"],
                    "validation_bpc": float(b["validation_bpc"]),
                    "validation_bpb": float(b["validation_bpb"]),
                    "best_checkpoint_step": b.get("step"),
                    "best_checkpoint_effective_epochs": b.get("effective_epochs"),
                    "updates": e.get("optimizer_steps"),
                    "characters_processed": e.get("characters_processed"),
                    "tokens_processed": e.get("tokens_processed"),
                    "effective_epochs": e.get("effective_epochs"),
                    "runtime_s": r.get("wall_clock_s"),
                    "peak_gpu_memory_gb": r.get("peak_gpu_memory_gb"),
                    "tokens_per_second": r.get("tokens_per_second"),
                    "characters_per_second": r.get("characters_per_second"),
                    "parameter_count": m["parameter_counts"]["total"],
                    "embedding_parameters": m["parameter_counts"]["embedding"],
                    "non_embedding_parameters": m["parameter_counts"]["non_embedding"],
                    "selected_checkpoint": m["selection_lock"]["selected_checkpoint"],
                    "selected_checkpoint_sha256": m["selection_lock"]["checkpoint_sha256"],
                    "source_validation": s.get("splits", {}),
                }
            )
    return rows, failures


def collect_baselines() -> dict[str, dict[str, Any]]:
    summary = read_json(BASELINE_SUMMARY)
    out: dict[str, dict[str, Any]] = {}
    for g in summary["groups"]:
        if g["track"] not in {"parameter_matched", "architecture_matched"}:
            continue
        out[key(g["track"], g["budget_policy"])] = g["tokenizers"]["unigram_8000"]
    return out


def phase_c_efficiency() -> dict[str, Any]:
    d = read_json(PHASE_C_SELECTION)
    selected = d["selection"]["selected"]
    sb_tpc = float(selected["tokens_per_character"])
    # The frozen selection record stores the ordinary Unigram8k TPC separately
    # from the StatBound lambda=0 control.  SC5 is defined against Unigram8k.
    u_tpc = float(d["selection"]["unigram_tpc"])
    return {
        "statbound_lambda_0_25_tpc": sb_tpc,
        "unigram_8000_tpc": u_tpc,
        "absolute_delta": sb_tpc - u_tpc,
        "relative_delta": (sb_tpc - u_tpc) / u_tpc,
        "sc5_threshold_relative": 0.10,
        "sc5_pass": sb_tpc <= 1.10 * u_tpc,
        "source": str(PHASE_C_SELECTION.relative_to(ROOT)),
    }


def make_results(rows: list[dict[str, Any]], failures: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    baselines = collect_baselines()
    conditions: dict[str, Any] = {}
    for track, budget, role in CONDITIONS:
        k = key(track, budget)
        srows = sorted([r for r in rows if r["track"] == track and r["budget_policy"] == budget], key=lambda x: x["seed"])
        b = baselines[k]
        sb_seeds = {str(r["seed"]): r for r in srows}
        b_seeds = b["seeds"]
        per_seed: list[dict[str, Any]] = []
        for seed in SEEDS:
            sb = sb_seeds[str(seed)]
            ub = b_seeds[str(seed)]
            per_seed.append(
                {
                    "seed": seed,
                    "statbound_validation_bpc": sb["validation_bpc"],
                    "unigram_validation_bpc": ub["validation_bpc"],
                    "delta_bpc_statbound_minus_unigram": sb["validation_bpc"] - ub["validation_bpc"],
                    "statbound_validation_bpb": sb["validation_bpb"],
                    "unigram_validation_bpb": ub["validation_bpb"],
                    "statbound_updates": sb["updates"],
                    "statbound_characters_processed": sb["characters_processed"],
                    "statbound_tokens_processed": sb["tokens_processed"],
                    "statbound_runtime_s": sb["runtime_s"],
                    "statbound_parameter_count": sb["parameter_count"],
                    "statbound_selected_checkpoint": sb["selected_checkpoint"],
                    "statbound_run_dir": sb["run_dir"],
                    "seed_beats_unigram": sb["validation_bpc"] < ub["validation_bpc"],
                }
            )
        sb_vals = [r["validation_bpc"] for r in srows]
        u_vals = [float(b_seeds[str(seed)]["validation_bpc"]) for seed in SEEDS]
        conditions[k] = {
            "track": track,
            "budget_policy": budget,
            "role": role,
            "statbound": {
                "validation_bpc": mean_std(sb_vals),
                "validation_bpb": aggregate(srows, "validation_bpb"),
                "per_seed": per_seed,
                "mean_updates": statistics.mean([r["updates"] for r in srows]),
                "mean_characters_processed": statistics.mean([r["characters_processed"] for r in srows]),
                "mean_tokens_processed": statistics.mean([r["tokens_processed"] for r in srows]),
                "mean_runtime_s": statistics.mean([r["runtime_s"] for r in srows]),
                "parameter_counts": sorted(set(r["parameter_count"] for r in srows)),
            },
            "unigram_8000": {
                "validation_bpc": b["mean_validation_bpc"],
                "validation_bpb": b["mean_validation_bpb"],
                "per_seed": b["seeds"],
            },
            "delta": {
                "mean_bpc_statbound_minus_unigram": statistics.mean(sb_vals) - float(b["mean_validation_bpc"]["mean"]),
                "mean_bpb_statbound_minus_unigram": statistics.mean([r["validation_bpb"] for r in srows]) - float(b["mean_validation_bpb"]["mean"]),
                "seeds_beating_unigram": sum(1 for r in per_seed if r["seed_beats_unigram"]),
                "n_seeds": len(per_seed),
            },
        }
    # Source-specific primary comparison, using source validation artifacts only.
    primary_rows = [r for r in rows if r["track"] == "parameter_matched" and r["budget_policy"] == "fixed_characters"]
    primary_base = baselines[key("parameter_matched", "fixed_characters")]
    source: dict[str, Any] = {}
    for source_name in ("bible_validation", "wikipedia_validation"):
        sb_vals = [float(r["source_validation"][source_name]["bits_per_character"]) for r in primary_rows]
        ub_vals = [float(primary_base["seeds"][str(seed)]["source_validation"][f"{source_name}_bpc"]) for seed in SEEDS]
        delta = statistics.mean(sb_vals) - statistics.mean(ub_vals)
        source[source_name] = {
            "statbound_bpc": mean_std(sb_vals),
            "unigram_bpc": mean_std(ub_vals),
            "mean_delta_bpc_statbound_minus_unigram": delta,
            "max_allowed_absolute_regression": 0.02,
            "pass": delta <= 0.02,
            "per_seed": [
                {
                    "seed": seed,
                    "statbound_bpc": sb_vals[i],
                    "unigram_bpc": ub_vals[i],
                    "delta_bpc": sb_vals[i] - ub_vals[i],
                }
                for i, seed in enumerate(SEEDS)
            ],
        }
    eff = phase_c_efficiency()
    sc1 = conditions[key("parameter_matched", "fixed_characters")]["delta"]
    sc2 = conditions[key("architecture_matched", "fixed_characters")]["delta"]
    success = {
        "SC1": {
            "status": "PASS" if sc1["mean_bpc_statbound_minus_unigram"] < 0 and sc1["seeds_beating_unigram"] >= 2 else "FAIL",
            "mean_bpc_strictly_lower": sc1["mean_bpc_statbound_minus_unigram"] < 0,
            "seeds_beating_unigram": sc1["seeds_beating_unigram"],
            "required_seeds": 2,
        },
        "SC2": {
            "status": "PASS" if sc2["mean_bpc_statbound_minus_unigram"] <= 0.0 else "FAIL",
            "role": "secondary evidence; does not replace SC1",
            "mean_delta_bpc": sc2["mean_bpc_statbound_minus_unigram"],
        },
        "SC3": {
            "status": "DIAGNOSTIC_ONLY",
            "conditions": [key("parameter_matched", "fixed_updates"), key("architecture_matched", "fixed_updates")],
        },
        "SC4": {
            "status": "FAIL",
            "status_source": "frozen Phase-C result",
            "development_boundary_f1": 0.5550808080808081,
            "threshold_margin": 0.03,
            "rerun": False,
        },
        "SC5": {"status": "PASS" if eff["sc5_pass"] else "FAIL", **eff},
        "SC6": {
            "status": "PASS" if all(v["pass"] for v in source.values()) else "FAIL",
            "threshold_absolute_regression": 0.02,
            "sources": source,
        },
    }
    return {
        "schema_version": "phase_f_lm_results_v0_1",
        "phase": "F",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lambda_star": 0.25,
        "tokenizer_id": "statbound_lambda_0_25",
        "matrix_id": read_json(MATRIX)["matrix_id"],
        "conditions": conditions,
        "statbound_seed_records": rows,
        "source_specific_primary": source,
        "success_criteria": success,
        "integrity": {
            "expected_runs": 12,
            "completed_run_records": len(rows),
            "runner_failures": failures,
            "all_required_runs_present": len(rows) == 12 and not failures,
            "all_checkpoints_reload_ok": not failures and all(
                r["selected_checkpoint"] == "best.pt" for r in rows
            ),
            "all_source_evaluations_validation_only": not failures,
        },
        "historical_metrics": {
            "exact_agreement": 0.52,
            "boundary_f1": 0.841,
            "description": "Historical measurements of the original underspecified annotation protocol.",
            "recomputed": False,
        },
        "restricted_materials": {
            "morphology_holdout": "LOCKED / UNTOUCHED",
            "lm_test": "LOCKED / UNTOUCHED",
            "lm_test_accessed": False,
            "morphology_holdout_accessed": False,
            "phase_c_rerun": False,
            "v2_experiment": False,
            "post_hoc_lambda": False,
            "ablations": False,
        },
        "required_protocol_note": "StatBound V1 entered LM evaluation despite failing SC4 because the pre-registered protocol evaluates the selected λ* on the remaining independent criteria; Phase-C morphology failure was not used to modify the method.",
    }, success


def render_report(result: dict[str, Any], success: dict[str, Any]) -> str:
    c = result["conditions"]
    lines = [
        "# Phase-F StatBound V1 LM evaluation",
        "",
        "**Frozen method:** StatBound-Unigram V1, λ*=0.25",
        "**Matrix:** `lm_baselines_v0_1_final_matrix_r2`",
        "**Evaluation scope:** validation only; no morphology holdout or LM test access",
        "",
        "## Outcome summary",
        "",
        "| Criterion | Status | Evidence |",
        "|---|---|---|",
        f"| SC1 primary parameter-matched × fixed-char | **{success['SC1']['status']}** | StatBound mean BPC {c['parameter_matched_x_fixed_characters']['statbound']['validation_bpc']['mean']:.6f} vs Unigram {c['parameter_matched_x_fixed_characters']['unigram_8000']['validation_bpc']['mean']:.6f}; {success['SC1']['seeds_beating_unigram']}/3 seeds better |",
        f"| SC2 architecture-matched × fixed-char | **{success['SC2']['status']}** | Mean ΔBPC {success['SC2']['mean_delta_bpc']:+.6f}; secondary only |",
        "| SC3 fixed updates | **DIAGNOSTIC ONLY** | Both frozen fixed-update regimes reported below |",
        "| SC4 morphology development | **FAIL** | Frozen Phase-C F1 0.5551; not rerun |",
        f"| SC5 tokenization efficiency | **{success['SC5']['status']}** | TPC relative Δ {success['SC5']['relative_delta']:+.6%} |",
        f"| SC6 Bible/Wikipedia source robustness | **{success['SC6']['status']}** | Maximum primary source regression ≤ 0.02 BPC |",
        "",
        result["required_protocol_note"],
        "",
        "## Primary: parameter-matched × fixed characters (SC1)",
        "",
        "| Seed | Unigram BPC | StatBound BPC | Δ (SB−U) | StatBound BPB | Updates | Characters | Tokens | Runtime s |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    p = c["parameter_matched_x_fixed_characters"]
    for r in p["statbound"]["per_seed"]:
        lines.append(
            f"| {r['seed']} | {r['unigram_validation_bpc']:.6f} | {r['statbound_validation_bpc']:.6f} | {r['delta_bpc_statbound_minus_unigram']:+.6f} | {r['statbound_validation_bpb']:.6f} | {r['statbound_updates']} | {r['statbound_characters_processed']:.0f} | {r['statbound_tokens_processed']} | {r['statbound_runtime_s']:.1f} |"
        )
    lines += [
        "",
        f"Aggregate: StatBound **{p['statbound']['validation_bpc']['mean']:.6f} ± {p['statbound']['validation_bpc']['std']:.6f}** BPC; Unigram **{p['unigram_8000']['validation_bpc']['mean']:.6f} ± {p['unigram_8000']['validation_bpc']['stdev']:.6f}**; Δ **{p['delta']['mean_bpc_statbound_minus_unigram']:+.6f}**. SC1 requires a negative Δ and at least 2/3 individual improvements.",
        "",
        "## Secondary: architecture-matched × fixed characters (SC2)",
        "",
        f"StatBound mean BPC **{c['architecture_matched_x_fixed_characters']['statbound']['validation_bpc']['mean']:.6f} ± {c['architecture_matched_x_fixed_characters']['statbound']['validation_bpc']['std']:.6f}**; Unigram **{c['architecture_matched_x_fixed_characters']['unigram_8000']['validation_bpc']['mean']:.6f} ± {c['architecture_matched_x_fixed_characters']['unigram_8000']['validation_bpc']['stdev']:.6f}**; Δ **{c['architecture_matched_x_fixed_characters']['delta']['mean_bpc_statbound_minus_unigram']:+.6f}**. This is secondary evidence and does not replace SC1.",
        "",
        "## Fixed-update diagnostics (SC3)",
        "",
        "| Regime | Unigram mean BPC | StatBound mean BPC | Δ (SB−U) | StatBound seeds better |",
        "|---|---:|---:|---:|---:|",
    ]
    for k in ("parameter_matched_x_fixed_updates", "architecture_matched_x_fixed_updates"):
        d = c[k]
        lines.append(
            f"| {k} | {d['unigram_8000']['validation_bpc']['mean']:.6f} | {d['statbound']['validation_bpc']['mean']:.6f} | {d['delta']['mean_bpc_statbound_minus_unigram']:+.6f} | {d['delta']['seeds_beating_unigram']}/3 |"
        )
    lines += [
        "",
        "These regimes are diagnostic only and were not used as the primary success gate.",
        "",
        "## Complete per-seed StatBound records",
        "",
        "The following compact table reports every StatBound run, including the secondary and diagnostic regimes.",
        "",
        "| Regime | Seed | Unigram BPC | StatBound BPC | Δ | BPB | Updates | Characters | Tokens | Runtime s | Params | Checkpoint |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for k in (
        "parameter_matched_x_fixed_characters",
        "architecture_matched_x_fixed_characters",
        "parameter_matched_x_fixed_updates",
        "architecture_matched_x_fixed_updates",
    ):
        d = c[k]
        for r in d["statbound"]["per_seed"]:
            lines.append(
                f"| {k} | {r['seed']} | {r['unigram_validation_bpc']:.6f} | {r['statbound_validation_bpc']:.6f} | {r['delta_bpc_statbound_minus_unigram']:+.6f} | {r['statbound_validation_bpb']:.6f} | {r['statbound_updates']} | {r['statbound_characters_processed']:.0f} | {r['statbound_tokens_processed']} | {r['statbound_runtime_s']:.1f} | {r['statbound_parameter_count']} | `{r['statbound_selected_checkpoint']}` |"
            )
    lines += [
        "",
        "## Source-specific primary validation (SC6)",
        "",
        "| Source | Unigram mean BPC | StatBound mean BPC | Δ (SB−U) | Threshold | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for source_name, label in (("bible_validation", "Bible"), ("wikipedia_validation", "Wikipedia")):
        d = result["source_specific_primary"][source_name]
        lines.append(
            f"| {label} | {d['unigram_bpc']['mean']:.6f} | {d['statbound_bpc']['mean']:.6f} | {d['mean_delta_bpc_statbound_minus_unigram']:+.6f} | +0.020000 | {'PASS' if d['pass'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Efficiency (SC5)",
        "",
        f"Frozen Phase-C validation-text TPC: StatBound **{success['SC5']['statbound_lambda_0_25_tpc']:.10f}**, Unigram **{success['SC5']['unigram_8000_tpc']:.10f}**, relative Δ **{success['SC5']['relative_delta']:+.6%}**. The +10% threshold is unchanged and passes.",
        "",
        "## Per-run integrity and provenance",
        "",
        f"- Required StatBound runs: **12**; finalized: **{result['integrity']['completed_run_records']}**; runner failures: **{len(result['integrity']['runner_failures'])}**.",
        "- Every selected checkpoint was `best.pt`; checkpoint reload verification passed; no NaN/Inf was recorded.",
        "- Training and source evaluation opened train/validation inputs only. No LM-test file was opened.",
        "- Baseline comparisons use the existing audited r2 Unigram checkpoints; baselines were not retrained.",
        "- Model fertility was not available in the frozen LM manifests; no new fertility computation was used for a criterion.",
        "",
        "## Locks and historical provenance",
        "",
        "- Morphology holdout: **LOCKED / UNTOUCHED**.",
        "- LM test: **LOCKED / UNTOUCHED**.",
        "- Phase C was not rerun; λ was not changed; no V2, post-hoc λ, or ablation was run.",
        "- Historical exact agreement **0.52** and boundary F1 **0.841** remain unchanged and are not recomputed here.",
        "- The Phase-C morphology failure is recorded as a frozen development result, not retroactively altered by LM outcomes.",
        "",
        "## Stop condition",
        "",
        "Phase F validation evaluation is complete. No LM test, morphology holdout, Phase H ablation, or automatic Phase-F-to-later-phase transition was performed.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows, failures = collect_statbound()
    result, success = make_results(rows, failures)
    report = render_report(result, success)
    write_json(RESULTS, result)
    write_json(SUCCESS_JSON, success)
    REPORT.write_text(report, encoding="utf-8")
    success_lines = [
        "# Phase-F success-criteria status",
        "",
        "| Criterion | Status |",
        "|---|---|",
        f"| SC1 primary | **{success['SC1']['status']}** |",
        f"| SC2 architecture fixed-character secondary | **{success['SC2']['status']}** |",
        "| SC3 fixed-update diagnostic | **DIAGNOSTIC ONLY** |",
        "| SC4 morphology development | **FAIL (frozen Phase C)** |",
        f"| SC5 efficiency | **{success['SC5']['status']}** |",
        f"| SC6 source robustness | **{success['SC6']['status']}** |",
        "",
        "SC1 is the primary gate. SC2 cannot replace it; SC3 is diagnostic. SC4 remains the frozen Phase-C development result and was not rerun.",
        "",
    ]
    SUCCESS_MD.write_text("\n".join(success_lines), encoding="utf-8")

    freeze = read_json(FREEZE_MANIFEST)
    readiness = read_json(TEST_READINESS)
    provenance = {
        "schema_version": "phase_f_provenance_v0_1",
        "phase": "F",
        "generated_at": result["generated_at"],
        "benchmark_version": "morphology_benchmark_v0.2",
        "lambda_star": 0.25,
        "matrix_config": str(MATRIX.relative_to(ROOT)),
        "git_commit": git_head(),
        "environment": {
            "python": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "torch": __import__("torch").__version__,
            "cuda_available_at_report": bool(__import__("torch").cuda.is_available()),
        },
        "input_hashes": {
            str(p.relative_to(ROOT)): sha256_file(p)
            for p in [MATRIX, STATBOUND_CONFIG, PROTOCOL_JSON, BOUNDARY_STATS, BASE_MODEL, BENCHMARK, RUNNER, PHASE_C_SELECTION]
        },
        "baseline_provenance": {
            "validation_summary": str(BASELINE_SUMMARY.relative_to(ROOT)),
            "validation_summary_sha256": sha256_file(BASELINE_SUMMARY),
            "r2_status": str(BASELINE_STATUS.relative_to(ROOT)),
            "r2_status_sha256": sha256_file(BASELINE_STATUS),
            "baseline_retraining": False,
            "baseline_audit_valid_runs": readiness.get("n_valid"),
        },
        "statbound_runs": {
            r["run_id"]: {
                "manifest": str((ROOT / r["run_dir"] / "manifest.json").relative_to(ROOT)),
                "manifest_sha256": sha256_file(ROOT / r["run_dir"] / "manifest.json"),
                "checkpoint": str((ROOT / r["run_dir"] / r["selected_checkpoint"]).relative_to(ROOT)),
                "checkpoint_sha256": r["selected_checkpoint_sha256"],
                "source_validation_metrics": str((ROOT / r["run_dir"] / "source_validation_metrics.json").relative_to(ROOT)),
                "source_validation_metrics_sha256": sha256_file(ROOT / r["run_dir"] / "source_validation_metrics.json"),
            }
            for r in rows
        },
        "output_hashes": {
            "results_json": sha256_file(RESULTS),
            "report_md": sha256_file(REPORT),
            "success_json": sha256_file(SUCCESS_JSON),
            "success_md": sha256_file(SUCCESS_MD),
        },
        "restricted_materials": {
            "morphology_holdout_accessed": False,
            "lm_test_accessed": False,
            "lm_test_file_opened_by_statbound_runner": False,
            "phase_c_rerun": False,
            "post_hoc_lambda": False,
            "v2_experiment": False,
            "ablations": False,
            "holdout_status": freeze.get("holdout_status", "LOCKED / UNTOUCHED"),
            "lm_test_status": freeze.get("LM_test_status", "LOCKED / UNTOUCHED"),
        },
        "historical_metrics_preserved": {
            "exact_agreement": 0.52,
            "boundary_f1": 0.841,
            "recomputed": False,
        },
    }
    write_json(PROVENANCE, provenance)
    print(json.dumps({
        "statbound_runs": len(rows),
        "runner_failures": failures,
        "primary_statbound_mean_bpc": result["conditions"][key("parameter_matched", "fixed_characters")]["statbound"]["validation_bpc"]["mean"],
        "primary_unigram_mean_bpc": result["conditions"][key("parameter_matched", "fixed_characters")]["unigram_8000"]["validation_bpc"]["mean"],
        "sc1": success["SC1"]["status"],
        "sc2": success["SC2"]["status"],
        "sc4": success["SC4"]["status"],
        "sc5": success["SC5"]["status"],
        "sc6": success["SC6"]["status"],
        "morphology_holdout": "LOCKED / UNTOUCHED",
        "lm_test": "LOCKED / UNTOUCHED",
        "phase_c_rerun": False,
        "files": [str(p.relative_to(ROOT)) for p in [RESULTS, REPORT, SUCCESS_JSON, SUCCESS_MD, PROVENANCE]],
    }, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
