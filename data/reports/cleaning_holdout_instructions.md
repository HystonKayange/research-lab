# Cleaning holdout — annotation instructions

## Experimental role of this set

This is a **blind holdout** sample for Cleaning Policy **v2**. It was drawn **after** v2 was designed using the original 367-record review.

| Dataset | Path | Role |
|---------|------|------|
| Development review (367) | `data/reports/cleaning_review_sample.jsonl` | **development validation only** — used to diagnose v1 and design v2 |
| Blind holdout (~250) | `data/reports/cleaning_holdout_sample.jsonl` | **independent generalization estimate** — do not tune v2 on these before labeling |
| Final test set | *(not yet created)* | Future locked evaluation |

Evaluating and tuning on the **same** examples overestimates performance. The development set already informed v2 rule choices; only the holdout estimates how v2 behaves on unseen lines.

## Goal

Label each record so we can compute removal precision, false-removal rate, useful-text retention, and leakage metrics for v2 on **unseen** data.

## Labels

- `valid_chichewa`
- `useful_mixed_chichewa`
- `boilerplate_or_noise`
- `foreign_language`
- `duplicate`
- `uncertain`

| Label | Meaning |
|-------|---------|
| `valid_chichewa` | Usable Chichewa |
| `useful_mixed_chichewa` | Mostly Chichewa; minor foreign OK |
| `boilerplate_or_noise` | Nav, category, tables, junk |
| `foreign_language` | Mostly non-Chichewa |
| `duplicate` | Non-informative duplicate |
| `uncertain` | Cannot decide |

### For `v2_decision=removed`

- **keep-worthy content** (valid/useful) → label `valid_chichewa` or `useful_mixed_chichewa` (**false removal**)
- **noise/foreign** → `boilerplate_or_noise` / `foreign_language` / `duplicate` (**correct removal**)

### For `v2_decision=kept`

- Good text → `valid_chichewa` / `useful_mixed_chichewa`
- Noise that leaked through → `boilerplate_or_noise` / `foreign_language`

## Sample composition

- Total: **250**
- v2 removed: **120**
- v2 kept: **130**

By v2 rule / kept:

- `kept`: 130
- `drop_category`: 36
- `drop_high_confidence_foreign`: 28
- `drop_short_conditional`: 20
- `drop_url_only`: 15
- `drop_digit_only`: 8
- `drop_wikimedia_chrome`: 8
- `drop_blank`: 3
- `drop_long_table_dump`: 2

## How to annotate

1. Open `data/reports/cleaning_holdout_sample.jsonl`.
2. Set only `review_label` (and optional `review_notes`).
3. Do not change immutable fields.
4. Optionally use a review UI if extended for this path.
5. After full labeling:

```bash
python3 scripts/data/summarize_cleaning_holdout.py \
  --config configs/data/cleaning_holdout.json \
  --sample data/reports/cleaning_holdout_sample.jsonl
```

## Do not

- Modify `configs/data/cleaning_v2.json` based on holdout impressions **before** labeling is complete
- Merge holdout into the development set
- Promote to `data/processed/` from this step alone
- Auto-label with an LLM as ground truth

