# Cleaning holdout validation report

**Generated:** 2026-08-05T00:09:55.228286Z
**Sample:** `data/reports/cleaning_holdout_stage1_sample.jsonl`
**Dataset role:** `blind_holdout` (blind holdout)
**Development set role:** `development_validation` (original 367 — not independent final validation)
**Annotation status:** `complete`

Records: 80; labeled 80; unlabeled 0.

## Metrics

| metric | value | 95% Wilson CI |
|--------|------:|---------------|
| removal_precision | 0.975 | [0.871183, 0.995573] n=40 |
| false_removal_rate | 0.025 | [0.004427, 0.128817] n=40 |
| useful_text_retention | 0.954545 | [0.782015, 0.991931] n=22 |
| noise_removal_recall | 0.672414 | [0.544238, 0.779169] n=58 |
| foreign_language_removal_recall | 0.733333 | — |
| boilerplate_removal_recall | 0.651163 | — |
| kept_noise_rate | 0.475 | — |
| foreign_language_leakage | 0.1 | — |
| boilerplate_leakage | 0.375 | — |

## Confusion matrix

|  | v2 remove | v2 keep |
|--|---------:|--------:|
| human useful | 1 | 21 |
| human noise | 39 | 19 |

## Rule-specific removal metrics

| rule | n | correct | false | precision | FRR |
|------|--:|--------:|------:|----------:|----:|
| `drop_category` | 3 | 3 | 0 | 1.0 | 0.0 |
| `drop_high_confidence_foreign` | 12 | 11 | 1 | 0.916667 | 0.083333 |
| `drop_long_table_dump` | 2 | 2 | 0 | 1.0 | 0.0 |
| `drop_short_conditional` | 10 | 10 | 0 | 1.0 | 0.0 |
| `drop_url_only` | 8 | 8 | 0 | 1.0 | 0.0 |
| `drop_wikimedia_chrome` | 5 | 5 | 0 | 1.0 | 0.0 |

## Targets (generalization)

- `removal_precision`: **met**
- `false_removal_rate`: **met**
- `useful_text_retention`: **met**

All preferred targets met on this **holdout**.

Development set (original 367) informed v2 design. Holdout estimates generalization; do not retune v2 on holdout before labeling is complete.

## Sequential stopping recommendation

**Decision:** `release_next_chunk`

Targets unclear or missed. Release the next 40 records from the locked extension pool (not the entire remainder). Do not modify Cleaning Policy v2. Re-evaluate after the new chunk is labeled.

| criterion | passed | detail |
|-----------|:------:|--------|
| removal_precision | yes | point=0.975 |
| false_removal_rate | yes | point=0.025 |
| useful_text_retention | no | point=0.954545 |

To release the next chunk (only after reviewing this recommendation):

```bash
python3 scripts/data/summarize_cleaning_holdout_stage.py \
  --config configs/data/cleaning_holdout_sequential.json \
  --sample data/reports/cleaning_holdout_stage1_sample.jsonl \
  --release-next
```

Cleaning Policy v2 SHA-256 (must remain unchanged): `c2f734aa5115be3b7a4a5f5bce813018b189d9b08a69133b2991514ab0ad29cb`

