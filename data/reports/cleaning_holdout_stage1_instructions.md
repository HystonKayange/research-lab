# Holdout stage 1 — sequential evaluation (80 records)

## Why sequential

Labeling all 250 holdout records at once is costly. Stage 1 concentrates effort on **ambiguous / high-risk** cases. The remaining records stay in a **locked extension pool** and are only released in chunks of 40 if stage-1 results are inconclusive.

## Dataset roles

| Set | Path | Role |
|-----|------|------|
| Development (367) | `data/reports/cleaning_review_sample.jsonl` | v1 diagnosis / v2 design — **not** independent final proof |
| Parent holdout (250) | `data/reports/cleaning_holdout_sample.jsonl` | Full blind pool (do not label all at once) |
| **Stage 1 active (80)** | `data/reports/cleaning_holdout_stage1_sample.jsonl` | **Label these first** |
| Extension locked (~170) | `data/reports/cleaning_holdout_extension_pool.jsonl` | **Do not open/label** until released |
| Cleaning policy | `configs/data/cleaning_v2.json` | **Do not modify** during this evaluation |

## Stage 1 composition

- Total: **80** (target 40 removed + 40 kept)
- Removed: **40**
- Kept: **40**

By v2 rule:
- `kept`: 40
- `drop_high_confidence_foreign`: 12
- `drop_short_conditional`: 10
- `drop_url_only`: 8
- `drop_wikimedia_chrome`: 5
- `drop_category`: 3
- `drop_long_table_dump`: 2

Obvious `drop_blank` / `drop_digit_only` and bulk trivial Category lines are **deprioritized** (excluded or minimal coverage).

## Labels

- `valid_chichewa`
- `useful_mixed_chichewa`
- `boilerplate_or_noise`
- `foreign_language`
- `duplicate`
- `uncertain`

Only edit `review_label` and optional `review_notes`.

## After labeling stage 1

```bash
python3 scripts/data/summarize_cleaning_holdout_stage.py \
  --config configs/data/cleaning_holdout_sequential.json \
  --sample data/reports/cleaning_holdout_stage1_sample.jsonl
```

### Stopping logic

The summarizer applies documented stop/release rules:

- **Stop** if precision, false-removal rate, and useful retention are clearly on the good side of targets (point estimates + CI bounds).
- **Otherwise release the next 40** records from the locked extension pool (do not dump the remaining 170).
- **Never** expose the full 250 for simultaneous labeling as the default path.

Do **not** change Cleaning Policy v2 to chase stage-1 scores.

