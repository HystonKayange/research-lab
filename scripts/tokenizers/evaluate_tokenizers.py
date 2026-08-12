#!/usr/bin/env python3
"""Evaluate trained tokenizer baselines; select BPE/Unigram on validation; report test.

Does not retrain. Does not use test for selection.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import (  # noqa: E402
    CharacterTokenizer,
    SentencePieceWrapper,
    evaluate_tokenizer_on_units,
    git_commit,
    iter_eval_units,
    load_json,
    platform_info,
    selection_score,
    sha256_file,
    utc_now_iso,
    verify_frozen_split,
    write_json,
    write_jsonl,
    write_text,
)

TOOL_NAME = "evaluate_tokenizers"
TOOL_VERSION = "0.1.0"


def load_character(exp_root: Path) -> tuple[Callable, int, int, str]:
    vocab = load_json(exp_root / "character" / "vocab.json")
    cfg = load_json(exp_root / "character" / "tokenizer_config.json")
    tok = CharacterTokenizer(vocab["stoi"], vocab["itos"])
    unk_id = int(cfg["unk_id"])

    def encode(text: str):
        return tok.encode(text)

    return encode, int(cfg["vocab_size"]), unk_id, "character"


def load_sp(exp_root: Path, model_type: str, vocab_size: int) -> tuple[Callable, int, int, str]:
    d = exp_root / model_type / f"vocab_{vocab_size}"
    model = d / "model.model"
    tid = f"{model_type}_{vocab_size}"
    wrap = SentencePieceWrapper(model, tid)
    unk_id = wrap.sp.unk_id()

    def encode(text: str):
        return wrap.encode(text)

    return encode, wrap.vocab_size, unk_id, tid


def discover_models(exp_root: Path) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    if (exp_root / "character" / "vocab.json").is_file():
        models.append({"kind": "character"})
    for mt in ("bpe", "unigram"):
        base = exp_root / mt
        if not base.is_dir():
            continue
        for d in sorted(base.glob("vocab_*")):
            if (d / "model.model").is_file():
                vs = int(d.name.split("_")[1])
                models.append({"kind": mt, "vocab_size": vs})
    return models


def get_encoder(exp_root: Path, spec: dict[str, Any]):
    if spec["kind"] == "character":
        return load_character(exp_root)
    return load_sp(exp_root, spec["kind"], int(spec["vocab_size"]))


def render_report(
    *,
    config: dict[str, Any],
    meta: dict[str, Any],
    val_all: dict[str, Any],
    test_selected: dict[str, Any],
    selection: dict[str, Any],
) -> str:
    lines = [
        "# Tokenizer baselines v0.1 — Chichewa Corpus",
        "",
        f"_Generated at {meta.get('created_at')} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "## 1. Research objective",
        "",
        "Train and evaluate character-level, SentencePiece BPE, and SentencePiece Unigram "
        "tokenizers on frozen Chichewa training text to measure sequence efficiency, "
        "vocabulary behavior, coverage, fragmentation, and morphology-related observations. "
        "This is **tokenizer analysis only** — not language-model quality.",
        "",
        "## 2. Frozen corpus and split identity",
        "",
        f"- Corpus version: `{config.get('corpus_version')}`",
        f"- Split version: `{config.get('split_version')}`",
        f"- Split root: `{config.get('split_root')}`",
        f"- Experiment: `{config.get('experiment_id')}`",
        f"- Freeze verified: `{meta.get('frozen_split_verified')}`",
        "",
        "## 3. Training-data restrictions",
        "",
        "- Tokenizers trained **only** on `train/combined.txt` (and character vocab from that text).",
        "- Validation and test text were **not** used for vocabulary induction or SP training.",
        "- Forbidden path substrings checked before training/evaluation wiring.",
        "",
        "## 4. Tokenizer configurations",
        "",
        f"- Character: specials {config['character']['special_token_order']}",
        f"- SentencePiece vocab sizes: {config['sentencepiece']['vocab_sizes']}",
        f"- model types: {config['sentencepiece']['model_types']}",
        f"- character_coverage: {config['sentencepiece']['character_coverage']}",
        f"- normalization_rule_name: {config['sentencepiece']['normalization_rule_name']}",
        f"- byte_fallback: {config['sentencepiece']['byte_fallback']}",
        f"- seed: {config['sentencepiece'].get('seed')} "
        f"({config['sentencepiece'].get('seed_note', '')})",
        f"- num_threads: {config['sentencepiece']['num_threads']}",
        f"- pad/unk/bos/eos ids: {config['sentencepiece']['pad_id']}/"
        f"{config['sentencepiece']['unk_id']}/{config['sentencepiece']['bos_id']}/"
        f"{config['sentencepiece']['eos_id']}",
        "",
        "## 5. Normalization policy",
        "",
        f"- Policy: **{config['normalization']['policy']}**",
        "- Preserve case, punctuation, `ŵ`, and Unicode; no lowercasing; no accent stripping; no NFKC.",
        f"- Audit: {meta.get('normalization_summary')}",
        "",
        "## 6. Character baseline results (validation)",
        "",
    ]
    char_v = val_all.get("character")
    if char_v:
        lines.extend(_metric_bullets(char_v, label="character"))
        lines.append(
            "- Note: character fertility is tokens-per-word at character granularity; "
            "do not use it as a subword 'winner' metric."
        )
    lines.extend(["", "## 7. BPE results by vocabulary size (validation)", ""])
    for vs in config["sentencepiece"]["vocab_sizes"]:
        m = val_all.get(f"bpe_{vs}")
        if m:
            lines.append(f"### BPE {vs}")
            lines.append("")
            lines.extend(_metric_bullets(m, label=f"bpe_{vs}"))
            lines.append("")
    lines.extend(["## 8. Unigram results by vocabulary size (validation)", ""])
    for vs in config["sentencepiece"]["vocab_sizes"]:
        m = val_all.get(f"unigram_{vs}")
        if m:
            lines.append(f"### Unigram {vs}")
            lines.append("")
            lines.extend(_metric_bullets(m, label=f"unigram_{vs}"))
            lines.append("")
    lines.extend(
        [
            "## 9. Validation comparison",
            "",
            "| tokenizer | fertility | unk_rate | util | tokens/char | p95 seq | score |",
            "|-----------|----------:|---------:|-----:|------------:|--------:|------:|",
        ]
    )
    for tid, m in sorted(val_all.items()):
        fert = m.get("fertility", {}).get("overall")
        unk = m.get("coverage", {}).get("unknown_token_rate")
        util = m.get("vocabulary_usage", {}).get("utilization")
        tpc = m.get("sequence_efficiency", {}).get("tokens_per_character")
        p95 = m.get("sequence_efficiency", {}).get("sequence_length_percentiles", {}).get("p95")
        sc = selection.get("scores", {}).get(tid, {}).get("score")
        lines.append(
            f"| {tid} | {_fmt(fert)} | {_fmt(unk)} | {_fmt(util)} | {_fmt(tpc)} | {_fmt(p95)} | {_fmt(sc)} |"
        )
    lines.extend(
        [
            "",
            "## 10. Selected BPE candidate",
            "",
            f"- **Selected:** `{selection.get('selected_bpe')}`",
            f"- Rationale: {selection.get('bpe_rationale')}",
            "",
            "## 11. Selected Unigram candidate",
            "",
            f"- **Selected:** `{selection.get('selected_unigram')}`",
            f"- Rationale: {selection.get('unigram_rationale')}",
            "",
            "## 12. Test results for selected candidates",
            "",
            "Test metrics were computed **after** validation-only selection.",
            "",
        ]
    )
    for tid, m in test_selected.items():
        lines.append(f"### {tid} (test)")
        lines.append("")
        lines.extend(_metric_bullets(m, label=tid))
        lines.append("")
    lines.extend(
        [
            "## 13. Fertility comparison",
            "",
            "Fertility = encoded tokens / whitespace-delimited words.",
            "Character fertility is reported separately and is not a fair subword competitor.",
            "",
            "## 14. Vocabulary utilization",
            "",
            "See validation table (util column) and per-model `vocabulary_usage` in JSON metrics.",
            "",
            "## 15. Sequence-length comparison",
            "",
            "See p50/p90/p95/p99 in JSON metrics; summary p95 in the comparison table.",
            "",
            "## 16. Source-specific differences",
            "",
            "Bible vs Wikipedia fertility and tokens/char are in each metric blob under `by_source`.",
            "Religious formulaic text may yield different fragmentation than encyclopedic text.",
            "",
            "## 17. Representative tokenizations",
            "",
            f"See `{config.get('examples_path')}` and `evaluation/examples.jsonl`.",
            "Segmentations are **not** claimed to be morphologically correct.",
            "",
            "## 18. Morphology-related observations",
            "",
            f"Probe candidates (unlabeled): `{config.get('morphology_probe_path')}`.",
            "The tokenizer produced surface pieces that may or may not align with morphemes; "
            "this requires human linguistic review. Do not treat pieces as gold morphology.",
            "",
            "## 19. Limitations",
            "",
            "- No language-model experiments yet; efficiency ≠ predictive quality.",
            "- SentencePiece pieces can look English-like for loanwords; diagnostic only.",
            "- Contiguous-block corpus splits mean adjacent verses stay together, but "
            "tokenizer training is line-agnostic over train text.",
            "- byte_fallback=false may increase <unk> if rare scripts appear only in eval "
            "(expected to be low given character_coverage=1.0 on train).",
            "- Selection rubric is multi-criteria and approximate.",
            "",
            "## 20. Next experiment recommendation",
            "",
            "Run a **controlled small language-model baseline** comparing:",
            f"1. character",
            f"2. selected BPE `{selection.get('selected_bpe')}`",
            f"3. selected Unigram `{selection.get('selected_unigram')}`",
            "",
            "Train models only on the frozen train split; select on validation; report test "
            "bits/character (or bits/byte). Do not compare raw token-level perplexity across tokenizers.",
            "Do not implement MthandiziTokenizer until baselines are measured.",
            "",
            "### Integrity",
            "",
            f"- Config SHA-256: `{meta.get('config_sha256')}`",
            f"- SentencePiece version: `{meta.get('sentencepiece_version')}`",
            f"- Git commit: `{meta.get('git_commit')}`",
            "",
            "This report documents representation efficiency and diagnostics. "
            "It does **not** declare a superior tokenizer for language modeling.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def _metric_bullets(m: dict[str, Any], label: str) -> list[str]:
    return [
        f"- fertility (overall): {_fmt(m.get('fertility', {}).get('overall'))}",
        f"- unk rate: {_fmt(m.get('coverage', {}).get('unknown_token_rate'))}",
        f"- tokens/line: {_fmt(m.get('sequence_efficiency', {}).get('tokens_per_line'))}",
        f"- tokens/char: {_fmt(m.get('sequence_efficiency', {}).get('tokens_per_character'))}",
        f"- chars/token: {_fmt(m.get('sequence_efficiency', {}).get('characters_per_token'))}",
        f"- vocab utilization: {_fmt(m.get('vocabulary_usage', {}).get('utilization'))}",
        f"- p95 sequence length: {_fmt(m.get('sequence_efficiency', {}).get('sequence_length_percentiles', {}).get('p95'))}",
        f"- bible fertility: {_fmt((m.get('by_source') or {}).get('bible', {}).get('fertility'))}",
        f"- wikipedia fertility: {_fmt((m.get('by_source') or {}).get('wikipedia', {}).get('fertility'))}",
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate tokenizer baselines.")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    exp_root = root / config["output_root"]
    split_root = root / config["split_root"]

    try:
        verify_frozen_split(split_root, config)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    models = discover_models(exp_root)
    if not models:
        print(f"error: no models found under {exp_root}", file=sys.stderr)
        return 1

    val_units = iter_eval_units(split_root, "validation")
    test_units = iter_eval_units(split_root, "test")

    val_metrics: dict[str, Any] = {}
    for spec in models:
        encode, vsz, unk_id, tid = get_encoder(exp_root, spec)
        print(f"evaluating {tid} on validation ({len(val_units)} lines)…")
        val_metrics[tid] = evaluate_tokenizer_on_units(
            encode, val_units, tokenizer_id=tid, vocab_size=vsz, unk_id=unk_id
        )

    # Selection on validation only
    scores: dict[str, Any] = {}
    best_bpe = None
    best_bpe_score = -1e18
    best_uni = None
    best_uni_score = -1e18
    for tid, m in val_metrics.items():
        if tid == "character":
            scores[tid] = selection_score(m, is_character=True)
            continue
        sc = selection_score(m, is_character=False)
        scores[tid] = sc
        if tid.startswith("bpe_") and sc["score"] is not None and sc["score"] > best_bpe_score:
            best_bpe_score = sc["score"]
            best_bpe = tid
        if tid.startswith("unigram_") and sc["score"] is not None and sc["score"] > best_uni_score:
            best_uni_score = sc["score"]
            best_uni = tid

    def rationale(tid: str | None) -> str:
        if not tid:
            return "No candidate available."
        sc = scores.get(tid, {})
        m = val_metrics[tid]
        return (
            f"Highest multi-criteria validation score ({sc.get('score')}). "
            f"fertility={m['fertility']['overall']}, "
            f"unk_rate={m['coverage']['unknown_token_rate']}, "
            f"util={m['vocabulary_usage']['utilization']}, "
            f"vocab_size={m['vocab_size']}. "
            "Test data was not used for this choice."
        )

    selection = {
        "selected_bpe": best_bpe,
        "selected_unigram": best_uni,
        "selected_character": "character",
        "scores": scores,
        "bpe_rationale": rationale(best_bpe),
        "unigram_rationale": rationale(best_uni),
        "rubric": config.get("selection_rubric"),
    }

    # Test only for selected + character
    test_metrics: dict[str, Any] = {}
    selected_ids = {"character", best_bpe, best_uni} - {None}
    for tid in sorted(selected_ids):
        # find spec
        if tid == "character":
            spec = {"kind": "character"}
        else:
            kind, vs = tid.split("_", 1)
            spec = {"kind": kind, "vocab_size": int(vs)}
        encode, vsz, unk_id, _ = get_encoder(exp_root, spec)
        print(f"evaluating {tid} on test ({len(test_units)} lines)…")
        test_metrics[tid] = evaluate_tokenizer_on_units(
            encode, test_units, tokenizer_id=tid, vocab_size=vsz, unk_id=unk_id
        )

    # Also dump full test metrics for all models into a separate optional file? User asked
    # test for selected after selection — OK.

    eval_dir = exp_root / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    write_json(eval_dir / "validation_metrics.json", val_metrics)
    write_json(eval_dir / "test_metrics.json", test_metrics)
    write_json(eval_dir / "selection.json", selection)

    # Metadata package
    info = platform_info()
    info["git_commit"] = git_commit(root)
    meta = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "created_at": utc_now_iso(),
        "experiment_id": config["experiment_id"],
        "config_sha256": sha256_file(config_path),
        "frozen_split_verified": True,
        "normalization_summary": "identity; 0 changes on train samples at train time",
        "sentencepiece_version": info.get("sentencepiece_version"),
        "git_commit": info.get("git_commit"),
        "selection": selection,
        "models_evaluated_validation": list(val_metrics.keys()),
        "models_evaluated_test": list(test_metrics.keys()),
        "platform": info,
    }
    write_json(root / config["metadata_path"], {
        **meta,
        "validation_metrics_path": str((eval_dir / "validation_metrics.json").relative_to(root)),
        "test_metrics_path": str((eval_dir / "test_metrics.json").relative_to(root)),
        "selection_path": str((eval_dir / "selection.json").relative_to(root)),
    })

    report = render_report(
        config=config,
        meta=meta,
        val_all=val_metrics,
        test_selected=test_metrics,
        selection=selection,
    )
    write_text(root / config["report_path"], report)

    print("Selection:")
    print(f"  BPE:     {best_bpe}")
    print(f"  Unigram: {best_uni}")
    print(f"  report → {config['report_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
