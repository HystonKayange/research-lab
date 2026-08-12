# Tokenizer baselines (v0.1)

## Objective

Compare **character**, **SentencePiece BPE**, and **SentencePiece Unigram** tokenizers on frozen Chichewa train data for representation efficiency and diagnostics. This is **not** language-model training.

## Frozen split requirement

All training uses:

* `data/splits/chichewa_corpus_v0.1/train/` only

Scripts call `verify_frozen_split()` and refuse validation/test paths as training inputs.

## Install dependency

```bash
cd ~/projects/research/transformer-lab
python3 -m venv .venv
.venv/bin/pip install -r requirements-tokenizers.txt
```

Pinned: `sentencepiece==0.2.0`

## Train

```bash
.venv/bin/python scripts/tokenizers/train_character_tokenizer.py \
  --config configs/tokenizers/baselines_v0_1.json

.venv/bin/python scripts/tokenizers/train_sentencepiece_baselines.py \
  --config configs/tokenizers/baselines_v0_1.json
```

## Evaluate + select + examples

```bash
.venv/bin/python scripts/tokenizers/evaluate_tokenizers.py \
  --config configs/tokenizers/baselines_v0_1.json

.venv/bin/python scripts/tokenizers/inspect_tokenizations.py \
  --config configs/tokenizers/baselines_v0_1.json
```

Selection of one BPE and one Unigram size uses **validation only**. Test metrics are computed afterward for selected models (+ character).

## Normalization

**Identity** by default: preserve case, punctuation, `ŵ`, Unicode; no lowercasing; no NFKC.

## Fertility

`tokens / whitespace_delimited_words`

Character fertility is reported but **not** used as a subword winner criterion.

## Rules

* Do not train tokenizers on val/test.
* Do not tune vocab sizes on test.
* Do not claim morphological correctness from pieces.
* Do not compare raw token perplexity across tokenizers in later LM work — use bits/char or bits/byte.
* Do not overwrite `baselines_v0.1`; cut a new experiment version instead.

## Outputs

See `data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/` and:

* `data/reports/tokenizer_baselines_v0_1.md`
* `data/reports/tokenizer_examples_v0_1.jsonl`
* `data/reports/chichewa_morphology_probe_v0_1.jsonl`
* `data/metadata/tokenizer_baselines_v0_1.json`

## Morphology-aware follow-on (design + Phase A only)

Research blueprint (no hybrid implementation yet):

* `docs/tokenizers/MTHANDIZI_RESEARCH_BLUEPRINT.md`

Phase A failure audit (train+validation only; does **not** open LM test):

```bash
.venv/bin/python scripts/tokenizers/audit_tokenizer_failures.py \
  --config configs/tokenizers/baselines_v0_1.json
```

Outputs:

* `data/reports/tokenizer_failure_audit_v0_1/failure_candidates.jsonl`
* `data/reports/tokenizer_failure_audit_v0_1/FAILURE_AUDIT_REPORT.md`
* `data/metadata/tokenizer_failure_audit_v0_1.json`
