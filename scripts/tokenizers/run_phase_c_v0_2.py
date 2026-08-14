#!/usr/bin/env python3
"""Run the frozen Phase C morphology-development evaluation.

This runner evaluates only the frozen v0.2 morphology development file and
the frozen LM validation text.  It does not read holdout/test data, train a
model, or compute LM BPC.  The tokenizer implementations and scoring helpers
are imported unchanged from the repository.
"""

from __future__ import annotations

import ast
import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    EncodeResult,
    SentencePieceWrapper,
    count_words,
    evaluate_tokenizer_on_units,
    platform_info,
    sha256_file,
    write_json,
    write_text,
)
from src.tokenizers.statbound.metrics import (  # noqa: E402
    aggregate_boundary_metrics,
    boundary_metrics,
    normalize_pieces,
    parse_segments,
)
from src.tokenizers.statbound.phase_c_harness import build_lambda_selection_table  # noqa: E402
from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402


ACTIVE = ROOT / "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl"
VALIDATION = ROOT / "data/splits/chichewa_corpus_v0.1/validation/combined.txt"
BPE_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/bpe/vocab_8000/model.model"
UNIGRAM_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
STATBOUND_CONFIG = ROOT / "configs/tokenizers/statbound_unigram_v1.json"
STATBOUND_PROTOCOL = ROOT / "configs/tokenizers/statbound_unigram_v1_eval_protocol.json"
PHASE_C_PROTOCOL = ROOT / "docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md"
BOUNDARY_STATS = ROOT / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
POLICY_APPLICATION = ROOT / "data/reports/morphology_level_b_policy_application_v0_1.json"
REAUDIT = ROOT / "data/reports/morphology_level_b_reaudit_v0_1.json"

RESULTS = ROOT / "data/reports/phase_c_morphology_v0_2_results.json"
REPORT = ROOT / "data/reports/phase_c_morphology_v0_2_report.md"
LAMBDA_RECORD = ROOT / "data/reports/phase_c_lambda_selection_v0_2.json"
PROVENANCE = ROOT / "data/reports/phase_c_provenance_v0_2.json"

EXPECTED_ACTIVE_SHA256 = "73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67"
LAMBDA_VALUES = (0.0, 0.25, 0.5, 1.0, 2.0)
SYSTEM_IDS = (
    "bpe_8000",
    "unigram_8000",
    "statbound_lambda_0_0",
    "statbound_lambda_0_25",
    "statbound_lambda_0_5",
    "statbound_lambda_1_0",
    "statbound_lambda_2_0",
)
LAMBDA_SYSTEM = {
    0.0: "statbound_lambda_0_0",
    0.25: "statbound_lambda_0_25",
    0.5: "statbound_lambda_0_5",
    1.0: "statbound_lambda_1_0",
    2.0: "statbound_lambda_2_0",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


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


def input_hashes() -> dict[str, str]:
    paths = {
        "active_benchmark": ACTIVE,
        "validation_text": VALIDATION,
        "bpe_8000_model": BPE_MODEL,
        "unigram_8000_model": UNIGRAM_MODEL,
        "statbound_config": STATBOUND_CONFIG,
        "statbound_eval_protocol": STATBOUND_PROTOCOL,
        "phase_c_protocol": PHASE_C_PROTOCOL,
        "boundary_stats": BOUNDARY_STATS,
    }
    return {key: sha256_file(path) for key, path in paths.items()}


def assert_phase_c_inputs(rows: list[dict[str, Any]]) -> None:
    if sha256_file(ACTIVE) != EXPECTED_ACTIVE_SHA256:
        raise RuntimeError("frozen active benchmark hash mismatch")
    if len(rows) != 162 or len({r.get("item_id") for r in rows}) != 162:
        raise RuntimeError("frozen active benchmark is not exactly 162 unique items")
    for path in (ACTIVE, VALIDATION, BPE_MODEL, UNIGRAM_MODEL, STATBOUND_CONFIG, STATBOUND_PROTOCOL, PHASE_C_PROTOCOL, BOUNDARY_STATS):
        normalized = str(path).replace("\\", "/")
        if "/test/" in normalized or "/locked/" in normalized or "holdout" in normalized.lower():
            raise RuntimeError(f"forbidden Phase C input path: {path}")
        if not path.is_file():
            raise FileNotFoundError(path)
    for row in rows:
        gold = parse_segments(row.get("final_segmentation"))
        if not gold or any(not p for p in gold):
            raise RuntimeError(f"invalid gold segmentation: {row.get('item_id')}")
        if "".join(gold) != row.get("surface_form"):
            raise RuntimeError(f"gold reconstruction failure: {row.get('item_id')}")


def parse_rule_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if raw is None:
        return []
    text = str(raw)
    try:
        value = ast.literal_eval(text)
        if isinstance(value, list):
            return [str(x) for x in value]
    except (SyntaxError, ValueError):
        pass
    return [text] if text else []


def rule_labels(policy_row: dict[str, Any] | None) -> list[str]:
    if not policy_row:
        return ["UNSPECIFIED"]
    raw = " ".join(parse_rule_list(policy_row.get("policy_rules_used")))
    low = raw.lower()
    labels: list[str] = []
    if "final-vowel" in low or "/fv" in low or " fv" in low or "fv)" in low:
        labels.append("RULE_1_FINAL_VOWEL")
    if "negative" in low or "negation" in low:
        labels.append("RULE_2_NEGATIVE")
    if "extension" in low or "valency" in low or "argument-structure" in low or "applicative" in low or "passive" in low:
        labels.append("RULE_3_EXTENSIONS")
    if "post-final" in low or "postfinal" in low or "-ni" in low or "post-final" in low:
        labels.append("RULE_4_POST_FINAL")
    if "noun class" in low or "agreement" in low or "class/agreement" in low:
        labels.append("RULE_5_NOUN_CLASS_AGREEMENT")
    if "locative" in low or "contraction" in low:
        labels.append("RULE_6_LOCATIVE_CONTRACTION")
    if "loan" in low or "proper name" in low or "target-language" in low or "quality" in low:
        labels.append("RULE_7_LOANS_NAMES_QUALITY")
    return labels or ["UNSPECIFIED"]


def build_metadata(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    policy_obj = json.loads(POLICY_APPLICATION.read_text(encoding="utf-8"))
    reaudit_obj = json.loads(REAUDIT.read_text(encoding="utf-8"))
    policy = {r["item_id"]: r for r in policy_obj["items"]}
    reaudit = {r["item_id"]: r for r in reaudit_obj["items"]}
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row["item_id"]
        pr = policy.get(item_id, {})
        rr = reaudit.get(item_id, {})
        disagreement = str(rr.get("disagreement_type") or "UNSPECIFIED")
        metadata[item_id] = {
            "source": row.get("source") or "UNSPECIFIED",
            "confidence": row.get("confidence") or "UNSPECIFIED",
            "adjudication_source": row.get("adjudication_source") or "UNSPECIFIED",
            "policy_rules": rule_labels(pr),
            "disagreement_type": disagreement,
            "gold_segment_count": len(parse_segments(row["final_segmentation"]) or []),
        }
    return metadata


def normalize_token_pieces(raw: list[str]) -> tuple[list[str], bool, bool]:
    pieces = normalize_pieces(raw)
    empty = any(p == "" for p in pieces)
    return pieces, empty, False


def score_system(
    rows: list[dict[str, Any]],
    predict: Callable[[str], list[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[list[str]]]:
    item_metrics: list[dict[str, Any]] = []
    predictions: list[list[str]] = []
    recon_failures: list[str] = []
    empty_failures: list[str] = []
    for row in rows:
        item_id = row["item_id"]
        gold = parse_segments(row["final_segmentation"])
        assert gold is not None
        raw = list(predict(row["surface_form"]))
        pred = normalize_pieces(raw)
        predictions.append(pred)
        if any(p == "" for p in pred):
            empty_failures.append(item_id)
        if "".join(pred) != row["surface_form"]:
            recon_failures.append(item_id)
        item_metrics.append(boundary_metrics(gold, pred))
    aggregate = aggregate_boundary_metrics(item_metrics)
    integrity = {
        "n_items_input": len(rows),
        "n_items_scored": len(item_metrics),
        "gold_reconstruction_failures": 0,
        "prediction_reconstruction_failures": len(recon_failures),
        "prediction_reconstruction_failure_item_ids": recon_failures,
        "empty_piece_failures": len(empty_failures),
        "empty_piece_failure_item_ids": empty_failures,
        "scoring_item_count_matches_input": len(item_metrics) == len(rows),
        "all_predictions_reconstruct_exactly": not recon_failures,
        "all_scored_metrics_surface_valid": all(m["surface_reconstruct_ok"] for m in item_metrics),
    }
    return {"aggregate": aggregate, "integrity": integrity}, item_metrics, predictions


def category_breakdown(
    rows: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    item_metrics: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    row_by_id = {r["item_id"]: r for r in rows}
    groups: dict[str, dict[str, list[int]]] = {
        "source": {},
        "confidence": {},
        "adjudication_source": {},
        "policy_rule": {},
        "disagreement_type": {},
        "gold_segment_count": {},
    }
    ordered_ids = [r["item_id"] for r in rows]
    for idx, item_id in enumerate(ordered_ids):
        meta = metadata[item_id]
        vals = {
            "source": [meta["source"]],
            "confidence": [meta["confidence"]],
            "adjudication_source": [meta["adjudication_source"]],
            "policy_rule": meta["policy_rules"],
            "disagreement_type": [meta["disagreement_type"]],
            "gold_segment_count": [str(meta["gold_segment_count"])],
        }
        for group, labels in vals.items():
            for label in labels:
                groups[group].setdefault(label, []).append(idx)
    out: dict[str, dict[str, Any]] = {}
    for group, label_map in groups.items():
        out[group] = {}
        for label, indexes in sorted(label_map.items()):
            metrics = [item_metrics[i] for i in indexes]
            aggregate = aggregate_boundary_metrics(metrics)
            out[group][label] = {
                "n_items": len(indexes),
                "boundary_precision": aggregate["boundary_precision"],
                "boundary_recall": aggregate["boundary_recall"],
                "boundary_f1": aggregate["boundary_f1"],
                "exact_segmentation_accuracy": aggregate["exact_match_rate"],
                "boundary_jaccard": aggregate["boundary_jaccard"],
            }
    return out


def validation_units() -> list[dict[str, Any]]:
    lines = VALIDATION.read_text(encoding="utf-8").splitlines()
    return [
        {
            "split": "validation",
            "source_id": "combined",
            "line_index": i,
            "text": line,
            "n_chars": len(line),
            "n_bytes": len(line.encode("utf-8")),
            "n_words": count_words(line),
        }
        for i, line in enumerate(lines)
    ]


def efficiency_for_baseline(wrapper: SentencePieceWrapper, units: list[dict[str, Any]]) -> dict[str, Any]:
    return evaluate_tokenizer_on_units(
        lambda text: wrapper.encode(text),
        units,
        tokenizer_id=wrapper.tokenizer_id,
        vocab_size=wrapper.vocab_size,
        unk_id=wrapper.sp.unk_id(),
    )


def efficiency_for_statbound(tok: StatBoundUnigramTokenizer, units: list[dict[str, Any]]) -> dict[str, Any]:
    def encode(text: str) -> EncodeResult:
        pieces = tok.encode_text(text)
        ids = [tok.adapter.sp.piece_to_id(p) for p in pieces]
        return EncodeResult(tokens=pieces, ids=ids)

    return evaluate_tokenizer_on_units(
        encode,
        units,
        tokenizer_id=f"statbound_lambda_{tok.lambda_bias:g}",
        vocab_size=tok.adapter.vocab_size,
        unk_id=tok.adapter.sp.unk_id(),
    )


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def system_label(system_id: str) -> str:
    return {
        "bpe_8000": "BPE8k",
        "unigram_8000": "Unigram8k",
        "statbound_lambda_0_0": "StatBound λ=0.0 (control)",
        "statbound_lambda_0_25": "StatBound λ=0.25",
        "statbound_lambda_0_5": "StatBound λ=0.5",
        "statbound_lambda_1_0": "StatBound λ=1.0",
        "statbound_lambda_2_0": "StatBound λ=2.0",
    }[system_id]


def make_report(result: dict[str, Any], output_hash: str | None = None) -> str:
    systems = result["systems"]
    sel = result["lambda_selection"]
    lines = [
        "# Phase C — Chichewa Level-B morphology development evaluation",
        "",
        "This report evaluates the frozen 162-item development benchmark under the frozen Phase C protocol. "
        "It is a development/tuning report, not confirmatory evidence.",
        "",
        "## Scope and locks",
        "",
        f"- Active benchmark items: **{result['evaluated_item_count']}**",
        f"- Active benchmark SHA-256: `{result['input_hashes']['active_benchmark']}`",
        f"- Expected frozen SHA-256 verified: `{result['input_hashes']['active_benchmark'] == EXPECTED_ACTIVE_SHA256}`",
        "- Morphology holdout: **LOCKED / UNTOUCHED**",
        "- LM test: **LOCKED / UNTOUCHED**",
        "- LM BPC trained/evaluated: **false**",
        "- LM BPC used for λ selection: **false**",
        "- Morphology-development F1 used for λ selection is not confirmatory.",
        "",
        "## Results",
        "",
        "| system | boundary P | boundary R | boundary F1 | exact segmentation | TPC | fertility | items | reconstruction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sid in SYSTEM_IDS:
        r = systems[sid]
        m = r["morphology"]["aggregate"]
        e = r["efficiency"]
        integ = r["morphology"]["integrity"]
        lines.append(
            f"| {system_label(sid)} | {fmt(m['boundary_precision'])} | {fmt(m['boundary_recall'])} | "
            f"{fmt(m['boundary_f1'])} | {fmt(m['exact_match_rate'])} | "
            f"{fmt(e['sequence_efficiency']['tokens_per_character'])} | "
            f"{fmt(e['fertility']['overall'])} | {m['n_items']} | "
            f"{'PASS' if integ['all_predictions_reconstruct_exactly'] else 'FAIL'} |"
        )
    lines += [
        "",
        "`exact segmentation` is the macro item-level exact match rate; morphology precision/recall/F1/Jaccard are macro-averaged by the frozen harness.",
        "",
        "## λ selection",
        "",
        f"- Unigram8k validation TPC: **{fmt(sel['unigram_tpc'])}**",
        f"- Eligibility threshold (1.10 × Unigram8k TPC): **{fmt(sel['tpc_threshold'])}**",
        f"- Selected provisional λ*: **{sel['lambda_star']}**",
        f"- Selection pool: `{sel['pool']}`",
        f"- LM BPC used: **{sel['selection_used_lm_bpc']}**",
        "",
        "| λ | morphology F1 | validation TPC | eligible | reason |",
        "|---:|---:|---:|:---:|---|",
    ]
    for row in sel["candidate_records"]:
        lines.append(
            f"| {row['lambda']} | {fmt(row['boundary_f1'])} | {fmt(row['tokens_per_character'])} | "
            f"{'yes' if row['eligible'] else 'no'} | {row['eligibility_reason']} |"
        )
    lines += [
        "",
        "## SC4 development diagnostic",
        "",
        f"- Strongest standard tokenizer F1: **{fmt(result['sc4_development']['reference_f1'])}**",
        f"- Selected StatBound F1: **{fmt(result['sc4_development']['selected_f1'])}**",
        f"- Margin over strongest standard tokenizer: **{fmt(result['sc4_development']['margin'])}**",
        f"- Frozen +0.03 threshold: **{fmt(result['sc4_development']['threshold'])}**",
        f"- SC4 development threshold met provisionally: **{result['sc4_development']['passes_provisionally']}**",
        "",
        "## λ=0 control",
        "",
        f"- StatBound λ=0.0 vs ordinary Unigram8k sequence equality: **{result['lambda_zero_control']['sequence_equal_items']}/{result['evaluated_item_count']}**",
        f"- Boundary-set equality: **{result['lambda_zero_control']['boundary_equal_items']}/{result['evaluated_item_count']}**",
        f"- Control passes: **{result['lambda_zero_control']['passes']}**",
        "",
        "## Diagnostic morphology-category breakdowns",
        "",
        "Breakdowns use available audit metadata (source, confidence, adjudication provenance, policy-rule labels, disagreement type, and gold segment count). They are descriptive only and were not used to select λ.",
        "",
    ]
    for category, values in result["diagnostics"].items():
        lines += [f"### {category}", "", "| group | n | B-P | B-R | B-F1 | exact | Jaccard |", "|---|---:|---:|---:|---:|---:|---:|"]
        for label, m in values.items():
            lines.append(
                f"| {label} | {m['n_items']} | {fmt(m['boundary_precision'])} | {fmt(m['boundary_recall'])} | "
                f"{fmt(m['boundary_f1'])} | {fmt(m['exact_segmentation_accuracy'])} | {fmt(m['boundary_jaccard'])} |"
            )
        lines.append("")
    lines += [
        "## Integrity and provenance",
        "",
        f"- Reconstruction failures in frozen gold: **{result['integrity']['gold_reconstruction_failures']}**",
        f"- Per-system prediction reconstruction failures: **{result['integrity']['prediction_reconstruction_failures_total']}**",
        f"- Duplicate active IDs: **{result['integrity']['duplicate_active_ids']}**",
        f"- Exact item count: **{result['integrity']['exact_item_count']}**",
        f"- Pre-Phase-C git commit: `{result['provenance']['git_commit']}`",
        f"- Pre-Phase-C tag: `{result['provenance']['pre_phase_c_tag']}`",
        f"- Results file SHA-256: `{output_hash or 'computed after write'}`",
        "",
        "Authorized Phase C tokenizer artifacts were evaluated. No morphology holdout, LM test, LM BPC, ablation, or Phase F operation was accessed.",
        "",
        "Historical exact agreement `0.52` and boundary F1 `0.841` are preserved as measurements of the original annotation protocol; they were not recomputed here.",
        "",
        "**STOP CONDITION:** provisional λ* selection is complete; Phase F and all later phases were not started.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows = sorted(load_jsonl(ACTIVE), key=lambda r: r["item_id"])
    assert_phase_c_inputs(rows)
    metadata = build_metadata(rows)
    hashes = input_hashes()

    bpe = SentencePieceWrapper(BPE_MODEL, "bpe_8000")
    unigram = SentencePieceWrapper(UNIGRAM_MODEL, "unigram_8000")
    base_statbound = StatBoundUnigramTokenizer.from_config(
        STATBOUND_CONFIG,
        stats_path=BOUNDARY_STATS,
        lambda_bias=0.0,
        repo_root=ROOT,
    )

    systems: dict[str, dict[str, Any]] = {}
    item_metrics_by_system: dict[str, list[dict[str, Any]]] = {}
    predictions_by_system: dict[str, list[list[str]]] = {}

    baseline_predictors = {
        "bpe_8000": lambda word: list(bpe.sp.encode(word, out_type=str)),
        "unigram_8000": lambda word: list(unigram.sp.encode(word, out_type=str)),
    }
    for sid, predictor in baseline_predictors.items():
        morphology, item_metrics, predictions = score_system(rows, predictor)
        systems[sid] = {"morphology": morphology}
        item_metrics_by_system[sid] = item_metrics
        predictions_by_system[sid] = predictions

    statbound_tokens: dict[float, StatBoundUnigramTokenizer] = {}
    for lam in LAMBDA_VALUES:
        statbound_tokens[lam] = replace(base_statbound, lambda_bias=lam)
        sid = LAMBDA_SYSTEM[lam]
        morphology, item_metrics, predictions = score_system(
            rows, lambda word, tok=statbound_tokens[lam]: tok.encode_word(word)
        )
        systems[sid] = {"morphology": morphology}
        item_metrics_by_system[sid] = item_metrics
        predictions_by_system[sid] = predictions

    # The protocol requires λ=0 to reproduce ordinary Unigram segmentation.
    uni_predictions = predictions_by_system["unigram_8000"]
    zero_predictions = predictions_by_system["statbound_lambda_0_0"]
    sequence_equal = sum(a == b for a, b in zip(uni_predictions, zero_predictions))
    boundary_equal = 0
    for a, b in zip(uni_predictions, zero_predictions):
        if {sum(map(len, a[:i])) for i in range(1, len(a))} == {sum(map(len, b[:i])) for i in range(1, len(b))}:
            boundary_equal += 1
    control = {
        "sequence_equal_items": sequence_equal,
        "boundary_equal_items": boundary_equal,
        "passes": sequence_equal == len(rows) and boundary_equal == len(rows),
        "required_item_count": len(rows),
    }
    if not control["passes"]:
        raise RuntimeError("λ=0 control failed; protocol requires stopping before selection")

    units = validation_units()
    systems["bpe_8000"]["efficiency"] = efficiency_for_baseline(bpe, units)
    systems["unigram_8000"]["efficiency"] = efficiency_for_baseline(unigram, units)
    for lam, tok in statbound_tokens.items():
        systems[LAMBDA_SYSTEM[lam]]["efficiency"] = efficiency_for_statbound(tok, units)

    selection_input = {
        sid: {
            "morphology": {"aggregate": systems[sid]["morphology"]["aggregate"]},
            "efficiency": {"tokens_per_character": systems[sid]["efficiency"]["sequence_efficiency"]["tokens_per_character"]},
        }
        for sid in SYSTEM_IDS
    }
    raw_selection = build_lambda_selection_table(selection_input, max_relative_tpc=1.10)
    threshold = raw_selection["tpc_threshold"]
    candidate_records: list[dict[str, Any]] = []
    for lam in LAMBDA_VALUES[1:]:
        sid = LAMBDA_SYSTEM[lam]
        tpc = selection_input[sid]["efficiency"]["tokens_per_character"]
        eligible = float(tpc) <= float(threshold)
        candidate_records.append({
            "lambda": lam,
            "system_id": sid,
            "boundary_f1": selection_input[sid]["morphology"]["aggregate"]["boundary_f1"],
            "tokens_per_character": tpc,
            "eligible": eligible,
            "eligibility_reason": f"TPC <= 1.10 × Unigram8k TPC ({threshold:.10f})" if eligible else f"TPC > 1.10 × Unigram8k TPC ({threshold:.10f})",
        })
    selection = {
        **raw_selection,
        "candidate_records": candidate_records,
        "selection_used_lm_bpc": False,
        "lm_bpc_accessed": False,
        "eligible_lambdas": [r["lambda"] for r in candidate_records if r["eligible"]],
        "winner_rule": "maximum morphology-development boundary F1 among eligible nonzero lambdas; tie lower TPC; tie smaller lambda",
    }

    selected_sid = LAMBDA_SYSTEM[float(selection["lambda_star"])]
    selected_f1 = systems[selected_sid]["morphology"]["aggregate"]["boundary_f1"]
    reference_f1 = max(
        systems["bpe_8000"]["morphology"]["aggregate"]["boundary_f1"],
        systems["unigram_8000"]["morphology"]["aggregate"]["boundary_f1"],
    )
    sc4 = {
        "reference_system": "max(bpe_8000, unigram_8000)",
        "reference_f1": reference_f1,
        "selected_system": selected_sid,
        "selected_f1": selected_f1,
        "margin": selected_f1 - reference_f1,
        "threshold": 0.03,
        "passes_provisionally": selected_f1 >= reference_f1 + 0.03,
        "confirmatory": False,
    }

    diagnostics: dict[str, dict[str, Any]] = {}
    for category in ("source", "confidence", "adjudication_source", "policy_rule", "disagreement_type", "gold_segment_count"):
        # Use the selected system for compact category diagnostics; full per-system
        # aggregates remain in the machine-readable result.
        diagnostics[category] = category_breakdown(rows, metadata, item_metrics_by_system[selected_sid])[category]

    pred_fail_total = sum(
        systems[sid]["morphology"]["integrity"]["prediction_reconstruction_failures"]
        for sid in SYSTEM_IDS
    )
    integrity = {
        "exact_item_count": len(rows) == 162,
        "duplicate_active_ids": len(rows) - len({r["item_id"] for r in rows}),
        "gold_reconstruction_failures": 0,
        "prediction_reconstruction_failures_total": pred_fail_total,
        "no_empty_segments_in_gold": all(parse_segments(r["final_segmentation"]) for r in rows),
        "no_whitespace_normalization": True,
        "lambda_zero_control_passes": control["passes"],
        "all_systems_scored_162": all(systems[sid]["morphology"]["aggregate"]["n_items"] == 162 for sid in SYSTEM_IDS),
    }
    provenance = {
        "phase": "C",
        "generated_at": now_iso(),
        "git_commit": git_head(),
        "pre_phase_c_tag": "morphology-benchmark-v0.2-pre-phase-c",
        "environment": {
            **platform_info(),
            "python_executable": sys.executable,
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
        },
        "input_hashes": hashes,
        "benchmark_expected_sha256": EXPECTED_ACTIVE_SHA256,
        "restricted_materials": {
            "morphology_holdout_accessed": False,
            "lm_test_accessed": False,
            "lm_bpc_accessed": False,
            "lm_models_trained": 0,
            "phase_f_lm_training_started": False,
            "phase_c_tokenizer_evaluation_authorized": True,
        },
        "historical_metrics_preserved": {
            "exact_agreement": 0.52,
            "boundary_f1": 0.841,
            "description": "Historical measurements of the original underspecified annotation protocol.",
            "recomputed": False,
        },
    }
    result = {
        "schema_version": "phase_c_morphology_v0_2",
        "protocol": "docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md",
        "evaluated_at": provenance["generated_at"],
        "evaluated_item_count": len(rows),
        "systems": systems,
        "lambda_selection": selection,
        "lambda_zero_control": control,
        "sc4_development": sc4,
        "diagnostics_selected_system": selected_sid,
        "diagnostics": diagnostics,
        "integrity": integrity,
        "input_hashes": hashes,
        "provenance": provenance,
        "stop_after_phase_c": True,
        "phase_f_started": False,
        "phase_i_holdout_unlocked": False,
        "phase_j_lm_test_accessed": False,
    }
    write_json(RESULTS, result)
    selection_record = {
        "schema_version": "phase_c_lambda_selection_v0_2",
        "protocol": "configs/tokenizers/statbound_unigram_v1_eval_protocol.json",
        "selection": selection,
        "selected_lambda": selection["lambda_star"],
        "selected_system": selected_sid,
        "morphology_development_f1_not_confirmatory": True,
        "sc4_development": sc4,
        "input_hashes": hashes,
        "lm_bpc_used": False,
        "holdout_accessed": False,
        "lm_test_accessed": False,
    }
    write_json(LAMBDA_RECORD, selection_record)
    report_text = make_report(result)
    write_text(REPORT, report_text)
    output_hashes = {
        "results_json": sha256_file(RESULTS),
        "report_md": sha256_file(REPORT),
        "lambda_selection_json": sha256_file(LAMBDA_RECORD),
    }
    provenance["output_hashes"] = output_hashes
    provenance["runner_sha256"] = sha256_file(Path(__file__))
    write_json(PROVENANCE, provenance)
    # Regenerate the report with its known results hash, then refresh provenance.
    write_text(REPORT, make_report(result, output_hash=output_hashes["results_json"]))
    output_hashes["report_md"] = sha256_file(REPORT)
    provenance["output_hashes"] = output_hashes
    write_json(PROVENANCE, provenance)

    print(f"BPE8k F1/TPC: {fmt(systems['bpe_8000']['morphology']['aggregate']['boundary_f1'])} / {fmt(systems['bpe_8000']['efficiency']['sequence_efficiency']['tokens_per_character'])}")
    print(f"Unigram8k F1/TPC: {fmt(systems['unigram_8000']['morphology']['aggregate']['boundary_f1'])} / {fmt(systems['unigram_8000']['efficiency']['sequence_efficiency']['tokens_per_character'])}")
    for lam in LAMBDA_VALUES:
        sid = LAMBDA_SYSTEM[lam]
        elig = next((r["eligible"] for r in candidate_records if r["lambda"] == lam), None)
        print(f"StatBound lambda={lam:g} F1/TPC/eligible: {fmt(systems[sid]['morphology']['aggregate']['boundary_f1'])} / {fmt(systems[sid]['efficiency']['sequence_efficiency']['tokens_per_character'])} / {elig if elig is not None else 'CONTROL'}")
    print(f"selected lambda*: {selection['lambda_star']}")
    print(f"margin over strongest standard tokenizer: {fmt(sc4['margin'])}")
    print(f"SC4 development threshold (+0.03) met provisionally: {sc4['passes_provisionally']}")
    print("morphology holdout status: LOCKED / UNTOUCHED")
    print("LM test status: LOCKED / UNTOUCHED")
    print("Phase F status: NOT_STARTED")
    print("restricted-material access status: holdout/test/LM-BPC not accessed; authorized Phase C tokenizer artifacts only")
    print(f"results: {RESULTS.relative_to(ROOT)}")
    print(f"report: {REPORT.relative_to(ROOT)}")
    print(f"lambda selection: {LAMBDA_RECORD.relative_to(ROOT)}")
    print(f"provenance: {PROVENANCE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
