#!/usr/bin/env python3
"""Phase C tokenizer eval harness CLI (infrastructure only by default).

Scientific runs against active morphology / LM validation are GATED and must
pass explicit flags after Phase B. This script by itself does not compute
scientific results on production paths.

Examples:
  # show schema only
  .venv/bin/python scripts/tokenizers/phase_c_eval_harness.py schema

  # run synthetic demo selection (no real corpora)
  .venv/bin/python scripts/tokenizers/phase_c_eval_harness.py synthetic-demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.tokenizers.statbound.phase_c_harness import (  # noqa: E402
    LAMBDA_BY_SYSTEM,
    SYSTEM_IDS,
    PhaseCGateError,
    assert_path_allowed_for_phase_c,
    build_lambda_selection_table,
    empty_phase_c_result_schema,
    evaluate_efficiency_words,
    evaluate_morphology_pairs,
)


def cmd_schema(_: argparse.Namespace) -> int:
    print(json.dumps(empty_phase_c_result_schema(), indent=2))
    return 0


def cmd_synthetic_demo(_: argparse.Namespace) -> int:
    """Tiny in-memory demo proving selection rule wiring (not scientific)."""
    # Fake system results
    systems = {
        "bpe_8000": {
            "morphology": {"aggregate": {"boundary_f1": 0.40}},
            "efficiency": {"tokens_per_character": 0.55},
        },
        "unigram_8000": {
            "morphology": {"aggregate": {"boundary_f1": 0.50}},
            "efficiency": {"tokens_per_character": 0.50},
        },
        "statbound_lambda_0_0": {
            "morphology": {"aggregate": {"boundary_f1": 0.50}},
            "efficiency": {"tokens_per_character": 0.50},
        },
        "statbound_lambda_0_25": {
            "morphology": {"aggregate": {"boundary_f1": 0.56}},
            "efficiency": {"tokens_per_character": 0.52},
        },
        "statbound_lambda_0_5": {
            "morphology": {"aggregate": {"boundary_f1": 0.58}},
            "efficiency": {"tokens_per_character": 0.54},
        },
        "statbound_lambda_1_0": {
            "morphology": {"aggregate": {"boundary_f1": 0.60}},
            "efficiency": {"tokens_per_character": 0.56},  # within 1.10*0.50=0.55? 0.56 > 0.55 fail
        },
        "statbound_lambda_2_0": {
            "morphology": {"aggregate": {"boundary_f1": 0.62}},
            "efficiency": {"tokens_per_character": 0.70},  # fails efficiency
        },
    }
    # Fix 0.5 to be eligible: 0.54 <= 0.55
    sel = build_lambda_selection_table(systems, max_relative_tpc=1.10)
    morph = evaluate_morphology_pairs(
        [
            (["a", "bc"], ["a", "bc"]),
            (["ab", "c"], ["a", "b", "c"]),
        ]
    )
    eff = evaluate_efficiency_words(
        ["abc", "de"],
        encode_fn=lambda w: list(w),  # char pieces
    )
    out = {
        "scientific": False,
        "demo_lambda_selection": sel,
        "demo_morphology": morph["aggregate"],
        "demo_efficiency": eff,
        "system_ids": list(SYSTEM_IDS),
        "lambda_map": LAMBDA_BY_SYSTEM,
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_check_gates(args: argparse.Namespace) -> int:
    """Verify blocked paths raise as expected."""
    root = Path(args.repo_root)
    cases = [
        (root / "data/research/morphology_benchmark_v0.1/locked/x.jsonl", False, False),
        (root / "data/splits/chichewa_corpus_v0.1/test/combined.txt", False, False),
        (
            root
            / "data/research/morphology_benchmark_v0.1/development/annotations/"
            "annotator_a_active_195_v0_1.jsonl",
            False,
            False,
        ),
        (root / "data/splits/chichewa_corpus_v0.1/validation/combined.txt", False, False),
    ]
    failures = 0
    for path, allow_m, allow_v in cases:
        try:
            assert_path_allowed_for_phase_c(
                path, allow_morphology_dev=allow_m, allow_lm_validation=allow_v
            )
            print(f"UNEXPECTED_ALLOW {path}")
            failures += 1
        except PhaseCGateError as e:
            print(f"blocked_ok: {e}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase C eval harness (gated)")
    p.add_argument("--repo-root", type=Path, default=_REPO)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema").set_defaults(func=cmd_schema)
    sub.add_parser("synthetic-demo").set_defaults(func=cmd_synthetic_demo)
    sub.add_parser("check-gates").set_defaults(func=cmd_check_gates)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
