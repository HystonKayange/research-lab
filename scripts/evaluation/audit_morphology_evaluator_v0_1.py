#!/usr/bin/env python3
"""Offline metric audit of fixed archived development paths; no tokenizer calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evaluation.morphology_boundaries_v0_1 import (  # noqa: E402
    EVALUATOR_ID, METRICS, SegmentationError, aggregate_items, evaluate_item,
)

EXPECTED_GOLD_SHA = "73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67"
SPECIFICATION_COMMIT = "b535f50"
INPUTS = {
    "gold": "data/research/morphology_benchmark_v0.2/development/annotations/annotator_a_level_b_adjudicated_v0_2.jsonl",
    "oracle": "data/reports/unigram_nbest_oracle_v0_1.json",
    "phase_c": "data/reports/phase_c_morphology_v0_2_results.json",
    "diagnostic": "data/reports/phase_c_statbound_failure_diagnostic_v0_1.json",
    "selection": "data/reports/phase_c_lambda_selection_v0_2.json",
    "validation_incident": "data/reports/morphology_evaluator_validation_incident_v0_1.json",
}
PROVENANCE = {
    "specification": "docs/research/MORPHOLOGY_EVALUATOR_SPEC_v0_1.md",
    "implementation": "src/evaluation/morphology_boundaries_v0_1.py",
    "synthetic_tests": "tests/test_morphology_boundaries_v0_1.py",
    "audit_tests": "tests/test_morphology_evaluator_audit_v0_1.py",
    "audit_ci": ".github/workflows/morphology-evaluator.yml",
    "audit_runner": "scripts/evaluation/audit_morphology_evaluator_v0_1.py",
    "original_scorer_unchanged": "src/tokenizers/statbound/metrics.py",
    "historical_active_annotations": "data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl",
    "policy_v0_1": "docs/research/CHICHEWA_LEVEL_B_ADJUDICATION_POLICY_v0_1.md",
    "policy_v0_2": "docs/research/CHICHEWA_LEVEL_B_ADJUDICATION_POLICY_v0_2.md",
}
OUTPUT_BASE = "data/reports/morphology_evaluator_audit_v0_1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SegmentationError(message)


def same_score(left: float | None, right: float | None) -> bool:
    return left is right if left is None or right is None else math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def difference(left: float | None, right: float | None) -> float | None:
    return None if left is None or right is None else left - right


def research_boundaries(incident: dict) -> dict:
    """Never describe the entire validation session as untouched after this incident."""
    require(incident["morphology_holdout_metadata_accessed"] is True,
            "The documented validation-session metadata incident must not be suppressed")
    for key in ("holdout_payload_decoded", "holdout_evaluation_run", "holdout_released",
                "lm_test_accessed", "lm_bpc_accessed"):
        require(incident[key] is False,
                "Unexpected restricted access beyond the documented incident; stop for review")
    return {
        "scope": "Entire audit/validation session, including the disclosed prior test-discovery incident",
        "morphology_holdout_accessed": True,
        "morphology_holdout_metadata_accessed": True,
        "holdout_payload_decoded": False, "holdout_evaluation_run": False, "holdout_released": False,
        "lm_test_accessed": False, "lm_bpc_accessed": False,
        "morphology_holdout_status": "LOCKED / METADATA READ DURING PRIOR VALIDATION; PAYLOAD NOT DECODED",
        "lm_test_status": "LOCKED / UNTOUCHED",
        "validation_incident_record": INPUTS["validation_incident"],
        "audit_runner_scope": {
            "tokenizer_or_model_invoked": False, "candidate_generation_or_reselection": False,
            "morphology_holdout_metadata_or_payload_accessed": False, "lm_test_accessed": False,
            "lm_bpc_accessed": False,
            "basis": "Fixed explicit input/provenance allowlist; the incident record is read, not the restricted files it names",
        },
        "original_scorer_gold_policies_results_modified": False,
        "lambda_selection_modified": False, "success_criteria_modified": False,
        "historical_self_review_metrics_recomputed": False,
        "historical_self_review": "exact agreement = 0.52; boundary F1 = 0.841; historical original-protocol measurements unchanged",
        "v1_sc4_status": "NOT MET (historical; not re-evaluated)",
        "new_scores_replace_v1_results": False,
    }


def hashes() -> dict:
    return {key: {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
            for key, path in {**INPUTS, **PROVENANCE}.items()}


def indexed(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        key = row["item_id"]
        require(isinstance(key, str) and key not in result, f"Duplicate/invalid {label} ID: {key}")
        result[key] = row
    return result


def legacy_missing_value_scores(tp: int, fp: int, fn: int) -> dict:
    """Diagnostic only: old null rules, but counts from internal boundaries."""
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = None if p is None or r is None else 2 * p * r / (p + r) if p + r else 0.0
    j = tp / (tp + fp + fn) if tp + fp + fn else None
    return dict(zip(METRICS, (p, r, f, j)))


def legacy_summary(rows: list[dict]) -> dict:
    return {
        "n_items": len(rows),
        "metric_item_denominators": {k: sum(r[k] is not None for r in rows) for k in METRICS},
        "macro": {k: math.fsum(r[k] for r in rows if r[k] is not None) / n if
                  (n := sum(r[k] is not None for r in rows)) else None for k in METRICS},
        "exact_match": {"count": sum(r["exact"] for r in rows), "denominator": len(rows),
                        "rate": sum(r["exact"] for r in rows) / len(rows) if rows else None},
    }


def raw_boundaries(pieces: list[str]) -> set[int]:
    total, offsets = 0, set()
    for piece in pieces[:-1]:
        total += len(piece)
        offsets.add(total)
    return offsets


def audit_path(gold: dict, predictions: dict, archived: dict, label: str) -> dict:
    require(set(gold) == set(predictions), f"{label}: prediction/gold ID mismatch")
    items, before_rows, normalized_rows = [], [], []
    for item_id in sorted(gold):
        g, prediction = gold[item_id], predictions[item_id]
        gold_pieces = g["final_segmentation"]
        gold_pieces = gold_pieces.split("+") if isinstance(gold_pieces, str) else gold_pieces
        row = evaluate_item(g["surface_form"], gold_pieces, prediction["pieces"])
        raw = raw_boundaries(prediction["pieces"])
        gb = set(row["gold_boundaries"])
        raw_tp, raw_fp, raw_fn = len(gb & raw), len(raw - gb), len(gb - raw)
        derived_legacy = legacy_missing_value_scores(raw_tp, raw_fp, raw_fn)
        stored = {k: prediction[k] for k in METRICS[:3]}
        for k, value in stored.items():
            actual = derived_legacy[k]
            require((value is None and actual is None) or
                    (value is not None and actual is not None and math.isclose(value, actual, abs_tol=1e-12)),
                    f"{label}/{item_id}: archived {k} cannot be reconciled")
        require(prediction["exact"] == row["raw_piece_list_exact_match"], f"{label}/{item_id}: exact mismatch")
        before = {**stored, "boundary_jaccard": derived_legacy["boundary_jaccard"], "exact": prediction["exact"]}
        normalized = {**legacy_missing_value_scores(row["tp"], row["fp"], row["fn"]),
                      "exact": row["exact_segmentation_match"]}
        flags = []
        if row["n_empty_prediction_pieces_removed"]:
            flags.append("empty_prediction_piece_removed")
        if row["zero_boundary_case"] != "neither":
            flags.append("explicit_zero_boundary_convention")
        if before["exact"] != normalized["exact"]:
            flags.append("canonical_exact_match_changed")
        if any(not same_score(before[k], row[k]) for k in METRICS):
            flags.append("item_metric_changed")
        items.append({"item_id": item_id, "source": g["source"], **row,
                      "archived_candidate_rank": prediction.get("unigram_rank"),
                      "legacy_as_recorded": before,
                      "normalization_only_legacy_nulls": normalized,
                      "legacy_raw_boundary_offsets": sorted(raw),
                      "noninternal_legacy_offsets_removed": sorted(x for x in raw if not 0 < x < len(g["surface_form"])),
                      "change_flags": flags})
        before_rows.append(before)
        normalized_rows.append(normalized)
    before = legacy_summary(before_rows)
    for key in METRICS:
        actual, expected = before["macro"][key], archived["macro"][key]
        require((actual is None and expected is None) or
                (actual is not None and expected is not None and math.isclose(actual, expected, abs_tol=1e-12)),
                f"{label}: archived aggregate {key} mismatch")
    require(before["exact_match"]["rate"] == archived["macro"]["exact_match_rate"], f"{label}: exact aggregate mismatch")
    normalized = legacy_summary(normalized_rows)
    strict = aggregate_items(items)
    return {
        "path_label": label, "available": True, "independently_rescored_from_stored_pieces": True,
        "selection_changed": False,
        "legacy_as_recorded": {**before, "archived_aggregate": archived},
        "normalization_only_legacy_nulls": normalized,
        "strict": strict,
        "effect_decomposition_macro": {
            k: {"normalization_only_minus_legacy": difference(normalized["macro"][k], before["macro"][k]),
                "strict_minus_normalization_only": difference(strict["macro"][k], normalized["macro"][k])}
            for k in METRICS
        },
        "items": items,
    }


def build_audit() -> dict:
    initial = hashes()
    require(initial["gold"]["sha256"] == EXPECTED_GOLD_SHA, "Frozen gold hash mismatch")
    data = {k: json.loads((ROOT / p).read_text(encoding="utf-8")) for k, p in INPUTS.items() if k != "gold"}
    boundaries = research_boundaries(data["validation_incident"])
    gold = indexed([json.loads(line) for line in (ROOT / INPUTS["gold"]).read_text(encoding="utf-8").splitlines()], "gold")
    oracle = data["oracle"]
    stored = indexed(oracle["items"], "oracle")
    require(len(gold) == 162 and set(gold) == set(stored), "Expected identical 162-item gold and archived IDs")
    require(oracle["active_sha256"] == EXPECTED_GOLD_SHA, "Oracle refers to different gold")
    require(data["selection"]["selected_lambda"] == 0.25, "Unexpected frozen lambda")
    for key in gold:
        require(gold[key]["surface_form"] == stored[key]["surface_form"], f"Surface mismatch: {key}")
        pieces = gold[key]["final_segmentation"]
        text = pieces if isinstance(pieces, str) else "+".join(pieces)
        require(text == stored[key]["gold_segmentation"], f"Archived gold mismatch: {key}")
    paths = {}
    for key, label in [("unigram", "Unigram8k archived top-1"),
                       ("f1_oracle", "Fixed legacy-F1-selected paths (not a new oracle)"),
                       ("compat_oracle", "Fixed legacy-compatibility-selected paths (not a new oracle)")]:
        paths[key] = audit_path(gold, {i: r[key] for i, r in stored.items()}, oracle[key], label)
    equality = {}
    for lam in ("0.25", "0.5", "1.0", "2.0"):
        diag = data["diagnostic"]["per_lambda"][lam]
        records = diag["selected_records_by_item"]
        require(set(records) == set(gold), f"StatBound {lam}: IDs mismatch")
        predictions = {i: {"pieces": r["pieces"], "boundary_precision": r["metrics"]["precision"],
                          "boundary_recall": r["metrics"]["recall"], "boundary_f1": r["metrics"]["f1"],
                          "exact": r["metrics"]["exact"], "unigram_rank": r["selected_candidate_nbest_rank"]}
                       for i, r in records.items()}
        equal_count = sum(records[i]["pieces"] == stored[i]["unigram"]["pieces"] for i in gold)
        require(equal_count == 162 and diag["changed_item_count"] == 0, f"StatBound {lam}: path equality failed")
        system = "statbound_lambda_" + lam.replace(".", "_")
        archived = {"macro": data["phase_c"]["systems"][system]["morphology"]["aggregate"]}
        paths[system] = audit_path(gold, predictions, archived, f"StatBound lambda={lam} stored selected paths")
        require(paths[system]["strict"] == paths["unigram"]["strict"], f"StatBound {lam}: strict aggregates diverged")
        equality[lam] = {"raw_piece_list_equal_items": equal_count, "n_items": 162,
                         "strict_scores_independently_verified_equal": True,
                         "basis": "Persisted diagnostic selected_records_by_item, not new inference"}
    bpe = data["phase_c"]["systems"]["bpe_8000"]["morphology"]
    final = hashes()
    require(initial == final, "An input changed during the audit")
    return {
        "schema_version": "0.1", "initial_audit_date": "2026-11-11", "audit_date": "2026-11-12", "evaluator_id": EVALUATOR_ID,
        "analysis_type": "Post-hoc metric audit of fixed archived development predictions",
        "specification_commit_before_audit": SPECIFICATION_COMMIT,
        "n_items": 162, "paths": paths,
        "bpe_8000": {"available": False, "strict": None, "legacy_as_recorded": bpe,
                     "reason": "Approved Phase-C artifacts contain only BPE aggregates, not per-item pieces; no re-encoding performed."},
        "statbound_path_equality": equality,
        "provenance": {"inputs_before": initial, "inputs_after": final, "all_inputs_unchanged": True,
                       "runtime_contract": "Python >=3.10; standard library only; Unicode code-point offsets"},
        "integrity": {"gold_hash_matches_freeze": True, "unique_gold_ids": 162, "all_path_id_sets_match_gold": True,
                      "reconstruction_failures": 0, "invalid_internal_offsets": 0,
                      "archived_metrics_reconciled": True, "all_strict_metric_denominators": 162},
        "research_boundaries": boundaries,
    }


def render_markdown(audit: dict) -> str:
    lines = ["# Morphology evaluator v0.1 — archived-prediction audit", "",
             "Post-hoc measurement audit, not a new tokenizer experiment or replacement V1 result. "
             "The evaluator specification and synthetic tests were committed before applying it to stored predictions "
             f"(`{SPECIFICATION_COMMIT}`). The rules were informed by known scoring limitations, not independently preregistered.", "",
             "## Validation-session access incident", "",
             "On 2026-11-11 an overly broad unittest-discovery command ran older tests that read "
             "`locked/holdout_manifest.json` and `locked/RELEASE_BLOCKED`. This was an unauthorized "
             "metadata read; this session must **not** be described as having no holdout access. "
             "No sealed payload was decoded, no holdout evaluation or release occurred, and LM test was not accessed. "
             "An old tokenizer dry-run also failed on missing SentencePiece before encoding. Work stopped and the owner "
             "was notified. On 2026-11-12 the owner authorized transparent documentation and restricted validation. "
             "The new CI and commands below name only the two new synthetic-test files. "
             "See the [incident record](morphology_evaluator_validation_incident_v0_1.json). "
             "The restricted metadata was not reopened or hashed for this remediation.", "",
             "## Measurements", "",
             "Macro P/R/F1 now use the same 162 items. Empty prediction pieces are removed; only strictly internal "
             "character offsets count. Matching whole-word analyses score 1; one-sided-empty cases score 0. "
             "Micro scores pool TP/FP/FN. See the [specification](../../docs/research/MORPHOLOGY_EVALUATOR_SPEC_v0_1.md).", "",
             "| Fixed stored path | Archived macro F1 | Cleanup only, old nulls | Strict macro P | Strict macro R | Strict macro F1 | Strict micro F1 | Exact |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for path in audit["paths"].values():
        strict = path["strict"]
        cells = [path["path_label"], f'{path["legacy_as_recorded"]["macro"]["boundary_f1"]:.6f}',
                 f'{path["normalization_only_legacy_nulls"]["macro"]["boundary_f1"]:.6f}']
        cells += [f'{strict["macro"][k]:.6f}' for k in METRICS[:3]]
        cells += [f'{strict["micro"]["boundary_f1"]:.6f}', f'{strict["exact_match"]["count"]}/162']
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "BPE: strict scores are **unavailable** because per-item predictions are not present in the approved "
              "artifacts. Its archived macro F1 remains "
              f'{audit["bpe_8000"]["legacy_as_recorded"]["aggregate"]["boundary_f1"]:.6f}. '
              "Do not compare that historical value directly with new-version scores as though scoring were identical.", "",
              "The two legacy-selected path sets above are held fixed. They are **not new-version oracle ceilings**; "
              "no n-best path was reselected. All four StatBound paths were independently rescored from stored diagnostic "
              "pieces and checked to equal Unigram on 162/162 items. This audit does not remedy or reinterpret V1's negative result.", "",
              "## Denominators and artifact effects", "",
              "| Path | Old P/R/F1 denominators | Strict P/R/F1 denominators | Empty-piece items | Exact changes | Gold-whole macro F1 | Gold-segmented macro F1 |",
              "|---|---|---|---:|---:|---:|---:|"]
    for key in ("unigram", "f1_oracle", "compat_oracle"):
        p = audit["paths"][key]; s = p["strict"]
        d = "/".join(str(p["legacy_as_recorded"]["metric_item_denominators"][k]) for k in METRICS[:3])
        lines.append(f'| {key} | {d} | 162/162/162 | {s["normalization"]["items_with_empty_prediction_pieces"]} | '
                     f'{s["normalization"]["canonical_exact_differs_from_input_exact"]} | '
                     f'{s["strata"]["gold_whole_word"]["macro"]["boundary_f1"]:.6f} | '
                     f'{s["strata"]["gold_segmented"]["macro"]["boundary_f1"]:.6f} |')
    lines += ["", "The two gold whole-word items are `aloe` and `fupi`. Whole-word and segmented strata remain separate "
              "diagnostics as well as contributing to the all-item macro. Cleanup-only keeps the historical missing-value "
              "rules after removing empty pieces. Its difference from archived scoring isolates cleanup effects; strict minus "
              "cleanup-only isolates the zero-boundary/denominator convention. These effects can have opposite signs.", "",
              "## Item-level changes", "",
              "The CSV contains every fixed path/item, input and canonical pieces, old/new metrics, offsets, counts, and "
              "change flags. Below are changes for the three distinct archived path sets; StatBound duplicates Unigram.", "",
              "| Path | Item | Surface | Empty pieces removed | Old F1 | Strict F1 | Exact old → strict |",
              "|---|---|---|---:|---:|---:|---|"]
    for key in ("unigram", "f1_oracle", "compat_oracle"):
        for r in audit["paths"][key]["items"]:
            if not r["change_flags"]:
                continue
            old = r["legacy_as_recorded"]; f = "undefined" if old["boundary_f1"] is None else f'{old["boundary_f1"]:.6f}'
            lines.append(f'| {key} | {r["item_id"]} | {r["surface_form"]} | {r["n_empty_prediction_pieces_removed"]} | '
                         f'{f} | {r["boundary_f1"]:.6f} | {old["exact"]} → {r["exact_segmentation_match"]} |')
    lines += ["", "## Integrity and provenance", "",
              "162 unique development IDs; all seven stored-path sets reconstruct exactly; zero reconstruction failures "
              "or invalid strict offsets. Archived P/R/F1 and exact values reconcile with the stored pieces. "
              "All input and implementation SHA-256 hashes are recorded before/after in the JSON and match. "
              "The benchmark SHA-256 remains `" + EXPECTED_GOLD_SHA + "`.", "",
              "The fixed-input audit runner performs no tokenizer/model invocation, candidate generation/reselection, "
              "corpus evaluation, LM BPC, or restricted-file access. This runner-specific statement does not erase "
              "the broader validation incident above. Morphology holdout remains **LOCKED**, with metadata read "
              "during prior validation and payload not decoded. LM test remains **LOCKED / UNTOUCHED**. "
              "Original scoring code, source annotations, policies, Phase-C outputs, λ*=0.25, and success criteria are unchanged. "
              "Historical self-review exact agreement 0.52 and boundary F1 0.841 are preserved, not recomputed. "
              "Historical SC4 remains NOT MET. No Phase C/F rerun or successor tokenizer.", "",
              "## Reproduce this audit", "", "```bash",
              "python3 -m unittest discover -s tests -p test_morphology_boundaries_v0_1.py",
              "python3 -m unittest discover -s tests -p test_morphology_evaluator_audit_v0_1.py",
              "python3 scripts/evaluation/audit_morphology_evaluator_v0_1.py --check", "```", "",
              "Omit `--check` to regenerate only these new audit artifacts. The runner uses an explicit input allowlist, "
              "not repository-wide data discovery. It neither loads models nor touches locked corpus files.", ""]
    return "\n".join(lines)


def render_csv(audit: dict) -> str:
    stream = io.StringIO(newline="")
    fields = ["path", "item_id", "surface_form", "gold_pieces", "input_prediction_pieces", "prediction_pieces",
              "gold_boundaries", "prediction_boundaries", "legacy_raw_boundary_offsets", "noninternal_legacy_offsets_removed",
              "tp", "fp", "fn", "n_empty_prediction_pieces_removed", "raw_piece_list_exact_match", "exact_segmentation_match",
              *["legacy_" + k for k in METRICS], *METRICS, "change_flags"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for path, result in audit["paths"].items():
        for row in result["items"]:
            output = {k: row[k] for k in fields if k in row}
            output.update({"path": path, **{"legacy_" + k: row["legacy_as_recorded"][k] for k in METRICS}})
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, bool)) else v for k, v in output.items()})
    return stream.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed audit artifacts without writing")
    args = parser.parse_args()
    audit = build_audit()
    outputs = {OUTPUT_BASE + ".json": json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
               OUTPUT_BASE + ".md": render_markdown(audit), OUTPUT_BASE + "_items.csv": render_csv(audit)}
    for name, content in outputs.items():
        path = ROOT / name
        if args.check:
            require(path.read_bytes() == content.encode("utf-8"), f"Audit artifact differs: {name}")
        else:
            path.write_bytes(content.encode("utf-8"))
    require(hashes() == audit["provenance"]["inputs_before"], "Inputs changed while publishing audit artifacts")
    print(f"{'Verified' if args.check else 'Wrote'} {len(outputs)} audit artifacts; 162 items, seven stored paths; "
          "zero reconstruction failures. Runner: no model/candidate generation or restricted-file access. "
          "Session: prior holdout metadata read documented; payload not decoded; LM test untouched.")


if __name__ == "__main__":
    main()
