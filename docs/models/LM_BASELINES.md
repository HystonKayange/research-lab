# Language-model baselines v0.1

## Objective

Compare **character**, **BPE-8000**, and **Unigram-8000** under a controlled decoder-only Transformer. The tokenizer is the main experimental variable.

## Primary metric

**Bits per character (BPC)** from total NLL:

```text
BPC = sum(-log2 p(token_i | context)) / N_characters_original_text
```

Also **bits per byte (BPB)**. Token perplexity is reported but **not** cross-comparable.

## Phases

```bash
# Phase 1 — pilot (seed 42 only, small character budget)
.venv/bin/python scripts/models/train_lm_baseline.py \
  --config configs/models/lm_baselines_v0_1.json \
  --phase pilot --tokenizer character --seed 42 --track architecture_matched

.venv/bin/python scripts/models/train_lm_baseline.py \
  --phase pilot --tokenizer bpe_8000 --seed 42 --track architecture_matched

.venv/bin/python scripts/models/train_lm_baseline.py \
  --phase pilot --tokenizer unigram_8000 --seed 42 --track architecture_matched
```

Final multi-seed (`--phase final`, seeds 42/1337/2026) requires **explicit authorization**.

## Evaluation

```bash
.venv/bin/python scripts/models/evaluate_lm_baseline.py \
  --run-dir data/models/.../seed_42/pilot --splits validation

# Test only after selection lock:
.venv/bin/python scripts/models/evaluate_lm_baseline.py \
  --run-dir ... --splits test --allow-test
```

## Generation + memorization

```bash
.venv/bin/python scripts/models/generate_lm_samples.py --run-dir ...
.venv/bin/python scripts/models/check_memorization.py --run-dir ...
.venv/bin/python scripts/models/compare_lm_baselines.py --phase pilot
```

## Integrity

* Frozen split + tokenizer checksums verified before train.
* Test not used during training or checkpoint selection.
* Artifacts refuse overwrite without `--force`.

## Dependencies

```bash
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install -r requirements-tokenizers.txt
```
