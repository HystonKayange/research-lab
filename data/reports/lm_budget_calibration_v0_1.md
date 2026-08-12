# LM budget calibration v0.1

**Status:** configuration and tooling ready — **not auto-executed**  
**Real training by implementation agent:** 0  

## Motivation

The accepted canary processed ~4.01M original characters against a frozen train corpus of **4,623,799** content characters (~**0.87 effective epochs**). Validation BPC was still improving at the final canary checkpoint; that run validates the **system**, not budget sufficiency.

## Effective-epoch formula

Primary accounting unit remains **original character exposure**.

```text
effective_epochs =
    cumulative_original_characters_processed
    / frozen_training_corpus_character_count
```

Where:

* `cumulative_original_characters_processed` uses the same line-content definition as packing credits (`sum(len(line))`, newlines not counted).
* `frozen_training_corpus_character_count` = **4,623,799** for  
  `data/splits/chichewa_corpus_v0.1/train/combined.txt`.

Epoch is a **derived reporting metric only**.

## Calibration run (manual)

| Field | Value |
|-------|--------|
| tokenizer | `bpe_8000` |
| seed | 42 |
| track | `architecture_matched` |
| budget policy | `fixed_characters` |
| max characters | **185,000,000** (~40 corpus passes) |
| config | `configs/models/lm_budget_calibration_v0_1.json` |
| output | `data/models/.../bpe_8000/seed_42/calibration/fixed_characters/` |

### Validation checkpoints (effective epochs)

```text
1, 2, 5, 10, 15, 20, 30, 40
```

Derived character thresholds ≈ epoch × 4,623,799.

### Early stopping

| Setting | Value |
|---------|--------|
| metric | validation BPC (minimize) |
| min_delta | 0.01 |
| patience | 3 scheduled evaluations |
| min epochs before stop | 5 |
| restore best checkpoint | true |

Test set is **not** accessed.

## Exact manual command

```bash
cd ~/projects/research/transformer-lab

.venv/bin/python scripts/models/train_lm_baseline.py \
  --config configs/models/lm_baselines_v0_1.json \
  --calibration-config configs/models/lm_budget_calibration_v0_1.json \
  --yes
```

Dry-run plan only:

```bash
.venv/bin/python scripts/models/train_lm_baseline.py \
  --config configs/models/lm_baselines_v0_1.json \
  --calibration-config configs/models/lm_budget_calibration_v0_1.json \
  --dry-run-plan
```

## Plotting after calibration completes

```bash
.venv/bin/python scripts/models/plot_lm_learning_curves.py \
  --run-dir data/models/chichewa_corpus_v0.1/lm_baselines_v0.1/architecture_matched/bpe_8000/seed_42/calibration/fixed_characters \
  --out-dir data/reports/figures/lm_baselines_v0.1/calibration \
  --frozen-chars 4623799
```

Matrix comparisons (later, when multiple runs exist):

```bash
.venv/bin/python scripts/models/plot_lm_comparisons.py \
  --runs-root data/models/chichewa_corpus_v0.1/lm_baselines_v0.1 \
  --out-dir data/reports/figures/lm_baselines_v0.1/comparisons
```

## After calibration

1. Inspect validation BPC vs effective epochs.  
2. Choose a final character budget (and/or update schedule) where learning has largely flattened.  
3. Update the final matrix budget only via a **new documented config version** if the 4M-char budget is insufficient.  
4. Then re-authorize canary/full matrix under the chosen budget.  

**Do not** start the 35 pending final matrix runs until calibration informs the budget.

## Figures directory

```text
data/reports/figures/lm_baselines_v0.1/
```
