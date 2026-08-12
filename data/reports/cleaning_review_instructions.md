# Cleaning review — annotation instructions

**Source:** `wikipedia`  
**Sample file:** `data/reports/cleaning_review_sample.jsonl`  
**Total review records:** 367  
**Random seed:** 42  

## Goal

Measure **false removals** and **remaining noise** in the Wikipedia interim cleaning output before any promotion to `data/processed/`.

## What you will label

Each record in the JSONL sample has:

- `review_id` — stable id (do not change)
- `decision` — `removed` or `kept`
- `rule_id` — cleaning rule for removals (`null` for kept)
- `original_line_number` — line number in raw Wikipedia file
- `excerpt` — truncated text for review
- `text_sha256` — hash of the **full original line** from raw
- `review_label` — **you fill this**
- `review_notes` — optional free text

## Allowed labels

- `valid_chichewa`
- `useful_mixed_chichewa`
- `boilerplate_or_noise`
- `foreign_language`
- `duplicate`
- `uncertain`

### Label guide

| Label | Use when |
|-------|----------|
| `valid_chichewa` | Fluent / usable Chichewa content worth training on |
| `useful_mixed_chichewa` | Mostly Chichewa with minor foreign/noise but still useful |
| `boilerplate_or_noise` | Nav, chrome, categories, stubs, garbage |
| `foreign_language` | Predominantly non-Chichewa (EN/DE/other) |
| `duplicate` | Clear duplicate / non-informative repeat |
| `uncertain` | Cannot decide confidently |

## How labels map to metrics

### Removed samples

- **False removal:** `valid_chichewa` or `useful_mixed_chichewa`
- **Correct removal:** `boilerplate_or_noise`, `foreign_language`, or `duplicate`
- **`uncertain`:** counted separately; excluded from precision by default

### Kept samples

- **Useful text:** `valid_chichewa` or `useful_mixed_chichewa`
- **Noise:** `boilerplate_or_noise` or `duplicate`
- **Foreign leakage:** `foreign_language`
- **Boilerplate leakage:** `boilerplate_or_noise`

## Annotation procedure

1. Open `data/reports/cleaning_review_sample.jsonl`.
2. For each record, set `review_label` to exactly one allowed label.
3. Optionally set `review_notes` (short).
4. Do **not** change `review_id`, hashes, line numbers, or rule ids.
5. Save the file (or a copy) and run:

```bash
python scripts/data/summarize_cleaning_review.py \
  --config configs/data/cleaning_review.json \
  --sample data/reports/cleaning_review_sample.jsonl
```

## Sample composition (this build)

### Removed — by rule

| rule_id | population | requested | sampled |
|---------|----------:|----------:|--------:|
| `dedupe_exact` | 292 | 25 | 25 |
| `drop_blank` | 208 | 10 | 10 |
| `drop_category` | 1547 | 25 | 25 |
| `drop_digit_only` | 111 | 20 | 20 |
| `drop_english_signal` | 413 | 40 | 40 |
| `drop_german_signal` | 2 | 2 | 2 |
| `drop_html_tags` | 0 | 10 | 0 |
| `drop_image_meta` | 0 | 5 | 0 |
| `drop_in_german_meta` | 3 | 3 | 3 |
| `drop_max_length` | 56 | 30 | 30 |
| `drop_min_length` | 3167 | 40 | 40 |
| `drop_mixed_signal` | 267 | 40 | 40 |
| `drop_mu_nkhani` | 6 | 6 | 6 |
| `drop_url` | 74 | 25 | 25 |
| `drop_wiki_brackets` | 0 | 10 | 0 |
| `drop_wikimedia` | 34 | 20 | 20 |
| `drop_wikipedia_muzinenero` | 1 | 1 | 1 |

**Removed total sampled:** 287  
**Kept total sampled:** 80 (population non-blank kept ≈ 14398)

## Priority rules (higher scrutiny)

- `drop_min_length` — target n=40
- `drop_english_signal` — target n=40
- `drop_mixed_signal` — target n=40
- `drop_max_length` — target n=30

## Do not

- Modify `data/raw/` or interim cleaned corpora while annotating
- Change `configs/data/cleaning.json` based on partial impressions alone
- Promote to `data/processed/` until validation metrics are reviewed
- Train tokenizers/models on interim data under review

