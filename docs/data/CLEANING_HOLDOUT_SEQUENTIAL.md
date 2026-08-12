# Sequential holdout evaluation (Cleaning Policy v2)

## Motivation

The original 367-record review set is a **development validation** set: it was used
to diagnose Cleaning Policy v1 and design v2. Metrics on that set overstate
independent generalization.

A **blind holdout** of 250 records was drawn with zero overlap. Labeling all 250
at once is expensive. This document defines **sequential, risk-stratified** labeling.

## Stages

Each released chunk is written to a **new immutable stage file**. Prior stages are
never overwritten.

| Stage | File | Size (current) | Action |
|-------|------|---------------:|--------|
| Stage 1 | `data/reports/cleaning_holdout_stage1_sample.jsonl` | 80 | Labeled (risk-heavy) |
| Stage 2 | `data/reports/cleaning_holdout_stage2_sample.jsonl` | 40 | Labeled |
| Stage N | `data/reports/cleaning_holdout_stageN_sample.jsonl` | chunk_size | Created only on release |
| Extension (locked) | `data/reports/cleaning_holdout_extension_pool.jsonl` | ~130 remaining | Do not label until released |
| Parent pool | `data/reports/cleaning_holdout_sample.jsonl` | 250 | Full pool; do not label wholesale |

Stage numbering is automatic:

```text
stage1_sample.jsonl
stage2_sample.jsonl
stage3_sample.jsonl
stage4_sample.jsonl
...
```

The release helper discovers existing `cleaning_holdout_stage*_sample.jsonl` files
and assigns the next free integer. It **refuses** to overwrite an existing stage
sample.

Stage 1 prioritizes high-risk removed rules (foreign, short-conditional, URL-only,
wikimedia chrome, long-table dumps) and ambiguous kept strata (mixed, insufficient,
institutions, near-threshold). Obvious blank/digit-only and bulk trivial Category
lines are deprioritized.

## Workflow

1. Label **only** the active stage sample.
2. Run `summarize_cleaning_holdout_stage.py` on that sample.
3. Read stop/release recommendation:
   - **Stop** if precision, FRR, and useful retention are clearly good (point + CI).
   - Else **release next chunk** from the extension pool into a **new** stage file.
4. Never default to labeling all remaining records in one shot.
5. **Do not modify** `configs/data/cleaning_v2.json` to fit stage results mid-stream.
6. **Do not** release the remaining locked pool based on this document alone without
   an explicit operator decision.

### Release command

```bash
python3 scripts/data/summarize_cleaning_holdout_stage.py \
  --config configs/data/cleaning_holdout_sequential.json \
  --sample data/reports/cleaning_holdout_stage2_sample.jsonl \
  --release-next
```

Expected behavior when stages 1 and 2 already exist:

* Creates `cleaning_holdout_stage3_sample.jsonl` (not stage2)
* Writes `cleaning_holdout_stage3_manifest.json`
* Backs up the extension pool under `data/reports/cleaning_holdout_backups/`
* Removes released records from the extension pool atomically
* Leaves stage1 and stage2 files byte-identical

### Overrides

| Flag | Effect |
|------|--------|
| `--allow-partial-prior-stage` | Allow release when a prior stage is not fully labeled (default: block) |
| `--force-release` | Release even if stopping logic does not recommend `release_next_chunk` |

## Release guarantees

* **Detect existing stages** via filename pattern `cleaning_holdout_stageN_sample.jsonl`
* **Next stage number** = `max(existing) + 1` (or 1 if none)
* **Never overwrite** an existing stage sample
* **Never modify labels** in prior stage files
* **Preserve** locked extension pool except for the released head chunk
* **Atomic** stage write + extension rewrite; timestamped backup before pool mutation
* **Manifest** per stage with `parent_holdout_ids`, `review_ids`, counts, backup path
* **Reject** when extension pool is empty
* **Reject** when any prior stage is not fully labeled (unless override)
* **Deterministic** selection: head of the extension pool in file order

## Stopping criteria (defaults)

Stop if all hold:

- removal precision ≥ 0.90 and Wilson CI lower bound ≥ 0.80  
- false-removal rate ≤ 0.10 and Wilson CI upper bound ≤ 0.20  
- useful-text retention ≥ 0.90 and Wilson CI lower bound ≥ 0.80  

Otherwise release `chunk_size` (40) more records from the locked pool.

**Soft caution:** useful-retention CI can remain wide when few useful examples are
represented; treat stop recommendations carefully even when point estimates look strong.

## Current independent evidence (do not retune v2 on this)

| Evaluation | Removal precision | False-removal rate | Useful-text retention |
|------------|------------------:|-------------------:|----------------------:|
| Stage 1 (risk-heavy) | 97.5% | 2.5% | 95.5% |
| Combined Stage 1 + 2 (120 labels) | 98.8% | 1.25% | 95.5% |

* Only one false removal was observed across the 120 reviewed records.
* Useful-retention CI remains wide because only ~22 useful examples were represented.
* Cleaning Policy v2 **must not** be modified based on the holdout.
* The remaining ~130 holdout records **must remain locked** until an explicit release.

## Relation to development set

| Set | Use for tuning v2/v3? | Use for final claim? |
|-----|----------------------:|---------------------:|
| Development 367 | Yes (design only) | No |
| Holdout stage 1 / extensions | No (eval only) | Provisional generalization |
| Future final test set | No | Yes (when created) |

## Integrity

- Parent holdout file is not rewritten by the stage builder (identity of the 250 preserved).
- Cleaning Policy v2 is not modified by this workflow.
- Extension pool remains locked until the summarizer issues a release recommendation
  and an operator runs `--release-next`.
- Prior stage samples and labels are immutable after creation (only human labeling of
  the active stage file is expected).

## Implementation

| Component | Path |
|-----------|------|
| Stage builder | `scripts/data/build_cleaning_holdout_stages.py` |
| Summarize + release | `scripts/data/summarize_cleaning_holdout_stage.py` |
| Config | `configs/data/cleaning_holdout_sequential.json` |
| Tests | `tests/test_cleaning_holdout_stages.py` |
