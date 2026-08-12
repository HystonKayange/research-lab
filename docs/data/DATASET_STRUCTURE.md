# Dataset structure

This document describes the layout used for **reproducible Chichewa language-model and tokenizer experiments** in `transformer-lab`.

Canonical data root: **`data/`** (lowercase). Do not reintroduce a top-level `Data/` directory.

## Directory purposes

| Directory | Purpose |
|-----------|---------|
| `data/raw/` | **Immutable** source files only. Byte-for-byte originals. Never edit, clean, or overwrite. See `data/raw/README.md`. |
| `data/interim/` | Intermediate artifacts from exploratory cleaning or inspection (partially processed, not final). Safe to regenerate. |
| `data/processed/` | Fully cleaned / normalized corpora ready for training pipelines. Derived from `raw` via documented scripts. |
| `data/splits/` | Train / validation / test (and any other) partitions. Created only after processed data is finalized. |
| `data/benchmarks/` | Evaluation-only sets (held-out tasks, probes). **Must not** be mixed into training data. |
| `data/metadata/` | Machine-readable catalogs: source registry (`sources.jsonl`), file inventory (`inventory.json`). |
| `data/reports/` | Human-readable audit reports (inventories, cleaning logs, split statistics). |

Supporting code and configuration:

| Directory | Purpose |
|-----------|---------|
| `scripts/data/` | Data tooling (inventory, future cleaners, splitters). |
| `configs/data/` | Configs for data pipelines (paths, thresholds, split ratios). |
| `docs/data/` | Data documentation (this file and related notes). |

## Raw sources (current)

| Source ID | Path | Notes |
|-----------|------|--------|
| `bible` | `data/raw/bible/bible_clean.txt` | Chichewa Bible text; provenance TBD |
| `wikipedia` | `data/raw/wikipedia/wiki_clean.txt` | Chichewa Wikipedia extract; provenance TBD |
| `existing_corpus` | `data/raw/existing_corpus/chichewa_corpus.txt` | Pre-existing mixed corpus; provenance TBD |

Registry: `data/metadata/sources.jsonl`  
Inventory: `data/metadata/inventory.json` (regenerate with the script below)

## Data lifecycle

```text
raw
  → interim
    → processed
      → splits
        → tokenizer / model experiments
```

1. **raw** — collect and freeze sources; record checksums and metadata.
2. **interim** — exploratory transforms, partial filters; disposable.
3. **processed** — deterministic, documented cleaning; versioned by script + config.
4. **splits** — fixed partitions with documented seed and ratios.
5. **experiments** — tokenizer training, LM training, eval; consume splits only.

**Never** write pipeline outputs into `data/raw/`.

## Benchmark and test isolation

- Data under `data/benchmarks/` and any test split under `data/splits/` are **evaluation-only**.
- Do not concatenate benchmark or test material into training corpora.
- Prefer recording `holdout_only: true` in `sources.jsonl` for any source reserved for evaluation.
- Before training, verify training paths do not include benchmark files (checksum / path checks).

## Regenerating the inventory

```bash
python scripts/data/build_inventory.py \
  --raw-dir data/raw \
  --output data/metadata/inventory.json
```

The script is read-only with respect to raw files. It uses the Python standard library only.

## Interim cleaning (Bible + Wikipedia)

### Policy versions

| Policy | Config | Interim output |
|--------|--------|----------------|
| v1 (aggressive) | `configs/data/cleaning.json` | `data/interim/cleaning/` |
| v2 (precision-first) | `configs/data/cleaning_v2.json` | `data/interim/cleaning_v2/` |

```bash
python3 scripts/data/clean_sources.py --config configs/data/cleaning_v2.json
```

Per source: `cleaned.txt`, `removal_log.jsonl`, `transform_log.jsonl`, `summary.json`, `before_after_report.md`.

- Raw files are never modified (SHA-256 verified pre/post).
- Interim outputs are **not** final `data/processed/` corpora and do **not** imply training eligibility.
- `existing_corpus` is intentionally excluded (redundant composite of Bible ∪ Wikipedia).

### Cleaning evaluation sets (do not conflate)

| Set | Path | Size | Role |
|-----|------|-----:|------|
| **Development validation** | `data/reports/cleaning_review_sample.jsonl` | 367 | Diagnosed v1 failures; guided **design of v2**. **Not** independent final proof of generalization. |
| **Blind holdout (parent pool)** | `data/reports/cleaning_holdout_sample.jsonl` | 250 | Drawn **after** v2 existed; **zero overlap** with development set. Do **not** label all 250 at once. |
| **Holdout stage 1 (active)** | `data/reports/cleaning_holdout_stage1_sample.jsonl` | 80 | Risk-stratified first annotation tranche (40 removed + 40 kept). |
| **Holdout extension (locked)** | `data/reports/cleaning_holdout_extension_pool.jsonl` | 170 | Released only in chunks of 40 if stage-1 results are inconclusive. |
| **Final test** | *(not yet created)* | — | Future locked set; do not use for tuning. |

Sequential workflow: `docs/data/CLEANING_HOLDOUT_SEQUENTIAL.md`.

**Why this matters:** Tuning and evaluating on the **same** examples overestimates quality (selection bias / double-dipping). Development metrics for v2 are useful for iteration; **holdout** (and a future test set) are required for honest generalization claims.

```bash
# build unlabeled holdout (does not change v2)
python3 scripts/data/build_cleaning_holdout_sample.py \
  --config configs/data/cleaning_holdout.json

# after human labeling
python3 scripts/data/summarize_cleaning_holdout.py \
  --config configs/data/cleaning_holdout.json \
  --sample data/reports/cleaning_holdout_sample.jsonl
```

Do **not** modify Cleaning Policy v2 to chase holdout scores until labeling is complete and a v3 design (if needed) is trained only on the development set.


## Provenance policy

Do not invent licenses, URLs, or collection dates. Unknown fields stay `null` or `"unknown"` in `sources.jsonl` until verified. Training on a source requires an explicit decision on `allowed_for_training` after license review.
