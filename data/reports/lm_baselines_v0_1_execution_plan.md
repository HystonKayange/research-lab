# LM baselines v0.1 execution plan — stage `canary`

_Generated at 2026-08-05T08:50:24.689149Z_

- Matrix ID: `lm_baselines_v0_1_final_matrix`
- Expected full runs: **36**
- This stage run count: **1**
- Canary accepted: **True**

## Enumerated runs

| # | run_id | tokenizer | seed | track | budget |
|--:|--------|-----------|-----:|-------|--------|
| 1 | `lm_baselines_v0_1_final_matrix__final__arch__bpe_8000__seed42__chars` | bpe_8000 | 42 | architecture_matched | fixed_characters |

## Notes

- Dry-run does not train.
- Full stage blocked until canary acceptance manifest exists.
- Pilot results are excluded from final aggregation.
