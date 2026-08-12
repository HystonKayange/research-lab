# Cleaning validation report

**Generated:** 2026-08-04T08:13:10.334488Z
**Tool:** summarize_cleaning_review v1.0.0
**Sample:** `data/reports/cleaning_review_sample.jsonl`
**Annotation status:** `complete`

Records: 367 total; 367 labeled; 0 unlabeled; 0 remaining.

## Definitions

- False removal labels: `['useful_mixed_chichewa', 'valid_chichewa']`
- Correct removal labels: `['boilerplate_or_noise', 'duplicate', 'foreign_language']`
- Useful kept labels: `['useful_mixed_chichewa', 'valid_chichewa']`
- Noise kept labels: `['boilerplate_or_noise', 'duplicate']`
- Uncertain handling: `excluded_from_precision`

## Removed samples

| metric | value |
|--------|------:|
| n_records | 287 |
| n_labeled | 287 |
| n_unlabeled | 0 |
| n_uncertain | 0 |
| n_correct_removal | 163 |
| n_false_removal | 124 |
| removal_precision | 0.567944 |
| false_removal_rate | 0.432056 |

### Rule-specific removal metrics

| rule_id | n | labeled | correct | false | precision | false-removal rate |
|---------|--:|--------:|--------:|------:|----------:|-------------------:|
| `dedupe_exact` | 25 | 25 | 6 | 19 | 0.24 | 0.76 |
| `drop_blank` | 10 | 10 | 10 | 0 | 1.0 | 0.0 |
| `drop_category` | 25 | 25 | 25 | 0 | 1.0 | 0.0 |
| `drop_digit_only` | 20 | 20 | 20 | 0 | 1.0 | 0.0 |
| `drop_english_signal` | 40 | 40 | 35 | 5 | 0.875 | 0.125 |
| `drop_german_signal` | 2 | 2 | 2 | 0 | 1.0 | 0.0 |
| `drop_in_german_meta` | 3 | 3 | 3 | 0 | 1.0 | 0.0 |
| `drop_max_length` | 30 | 30 | 17 | 13 | 0.566667 | 0.433333 |
| `drop_min_length` | 40 | 40 | 20 | 20 | 0.5 | 0.5 |
| `drop_mixed_signal` | 40 | 40 | 1 | 39 | 0.025 | 0.975 |
| `drop_mu_nkhani` | 6 | 6 | 1 | 5 | 0.166667 | 0.833333 |
| `drop_url` | 25 | 25 | 13 | 12 | 0.52 | 0.48 |
| `drop_wikimedia` | 20 | 20 | 9 | 11 | 0.45 | 0.55 |
| `drop_wikipedia_muzinenero` | 1 | 1 | 1 | 0 | 1.0 | 0.0 |

## Kept samples

| metric | value |
|--------|------:|
| n_records | 80 |
| n_labeled | 80 |
| n_unlabeled | 0 |
| n_uncertain | 0 |
| n_useful | 69 |
| n_noise | 7 |
| n_foreign | 4 |
| n_boilerplate | 7 |
| useful_text_rate | 0.8625 |
| kept_noise_rate | 0.0875 |
| foreign_language_leakage | 0.05 |
| boilerplate_leakage | 0.0875 |

## Label distribution (labeled only)

| label | count |
|-------|------:|
| `boilerplate_or_noise` | 127 |
| `duplicate` | 2 |
| `foreign_language` | 45 |
| `useful_mixed_chichewa` | 68 |
| `valid_chichewa` | 125 |

## Next steps

1. Review precision / leakage metrics with a second annotator if possible.
2. Decide whether to adjust rules (manual config change) or promote interim → processed.

This report does **not** modify cleaning rules, promote data, create splits, or train models.

