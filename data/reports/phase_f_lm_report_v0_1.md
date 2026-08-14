# Phase-F StatBound V1 LM evaluation

**Frozen method:** StatBound-Unigram V1, λ*=0.25
**Matrix:** `lm_baselines_v0_1_final_matrix_r2`
**Evaluation scope:** validation only; no morphology holdout or LM test access

## Outcome summary

| Criterion | Status | Evidence |
|---|---|---|
| SC1 primary parameter-matched × fixed-char | **FAIL** | StatBound mean BPC 1.437402 vs Unigram 1.437061; 1/3 seeds better |
| SC2 architecture-matched × fixed-char | **PASS** | Mean ΔBPC -0.000536; secondary only |
| SC3 fixed updates | **DIAGNOSTIC ONLY** | Both frozen fixed-update regimes reported below |
| SC4 morphology development | **FAIL** | Frozen Phase-C F1 0.5551; not rerun |
| SC5 tokenization efficiency | **PASS** | TPC relative Δ -0.001382% |
| SC6 Bible/Wikipedia source robustness | **PASS** | Maximum primary source regression ≤ 0.02 BPC |

StatBound V1 entered LM evaluation despite failing SC4 because the pre-registered protocol evaluates the selected λ* on the remaining independent criteria; Phase-C morphology failure was not used to modify the method.

## Primary: parameter-matched × fixed characters (SC1)

| Seed | Unigram BPC | StatBound BPC | Δ (SB−U) | StatBound BPB | Updates | Characters | Tokens | Runtime s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 1.437722 | 1.437744 | +0.000022 | 1.423819 | 3932 | 138743958 | 32085120 | 107.4 |
| 1337 | 1.436837 | 1.438762 | +0.001926 | 1.424827 | 3932 | 138746935 | 32085120 | 109.9 |
| 2026 | 1.436625 | 1.435700 | -0.000924 | 1.421795 | 3932 | 138743453 | 32085120 | 107.2 |

Aggregate: StatBound **1.437402 ± 0.001559** BPC; Unigram **1.437061 ± 0.000582**; Δ **+0.000341**. SC1 requires a negative Δ and at least 2/3 individual improvements.

## Secondary: architecture-matched × fixed characters (SC2)

StatBound mean BPC **1.430776 ± 0.001354**; Unigram **1.431313 ± 0.000617**; Δ **-0.000536**. This is secondary evidence and does not replace SC1.

## Fixed-update diagnostics (SC3)

| Regime | Unigram mean BPC | StatBound mean BPC | Δ (SB−U) | StatBound seeds better |
|---|---:|---:|---:|---:|
| parameter_matched_x_fixed_updates | 1.479306 | 1.479904 | +0.000598 | 1/3 |
| architecture_matched_x_fixed_updates | 1.443355 | 1.443348 | -0.000007 | 1/3 |

These regimes are diagnostic only and were not used as the primary success gate.

## Complete per-seed StatBound records

The following compact table reports every StatBound run, including the secondary and diagnostic regimes.

| Regime | Seed | Unigram BPC | StatBound BPC | Δ | BPB | Updates | Characters | Tokens | Runtime s | Params | Checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| parameter_matched_x_fixed_characters | 42 | 1.437722 | 1.437744 | +0.000022 | 1.423819 | 3932 | 138743958 | 32085120 | 107.4 | 3364992 | `best.pt` |
| parameter_matched_x_fixed_characters | 1337 | 1.436837 | 1.438762 | +0.001926 | 1.424827 | 3932 | 138746935 | 32085120 | 109.9 | 3364992 | `best.pt` |
| parameter_matched_x_fixed_characters | 2026 | 1.436625 | 1.435700 | -0.000924 | 1.421795 | 3932 | 138743453 | 32085120 | 107.2 | 3364992 | `best.pt` |
| architecture_matched_x_fixed_characters | 42 | 1.430964 | 1.429220 | -0.001744 | 1.415377 | 3932 | 138743958 | 32085120 | 115.7 | 5273088 | `best.pt` |
| architecture_matched_x_fixed_characters | 1337 | 1.432025 | 1.431677 | -0.000348 | 1.417811 | 3932 | 138746935 | 32085120 | 115.6 | 5273088 | `best.pt` |
| architecture_matched_x_fixed_characters | 2026 | 1.430949 | 1.431433 | +0.000483 | 1.417569 | 3932 | 138743453 | 32085120 | 118.1 | 5273088 | `best.pt` |
| parameter_matched_x_fixed_updates | 42 | 1.480010 | 1.479564 | -0.000445 | 1.465234 | 4000 | 141144802 | 32640000 | 112.3 | 3364992 | `best.pt` |
| parameter_matched_x_fixed_updates | 1337 | 1.480884 | 1.482510 | +0.001626 | 1.468151 | 4000 | 141144743 | 32640000 | 112.9 | 3364992 | `best.pt` |
| parameter_matched_x_fixed_updates | 2026 | 1.477023 | 1.477637 | +0.000614 | 1.463326 | 4000 | 141145421 | 32640000 | 114.8 | 3364992 | `best.pt` |
| architecture_matched_x_fixed_updates | 42 | 1.442300 | 1.441303 | -0.000997 | 1.427344 | 4000 | 141144802 | 32640000 | 118.3 | 5273088 | `best.pt` |
| architecture_matched_x_fixed_updates | 1337 | 1.444892 | 1.445159 | +0.000267 | 1.431162 | 4000 | 141144743 | 32640000 | 119.4 | 5273088 | `best.pt` |
| architecture_matched_x_fixed_updates | 2026 | 1.442872 | 1.443582 | +0.000710 | 1.429600 | 4000 | 141145421 | 32640000 | 116.4 | 5273088 | `best.pt` |

## Source-specific primary validation (SC6)

| Source | Unigram mean BPC | StatBound mean BPC | Δ (SB−U) | Threshold | Status |
|---|---:|---:|---:|---:|---|
| Bible | 1.245507 | 1.246818 | +0.001311 | +0.020000 | PASS |
| Wikipedia | 1.927629 | 1.925454 | -0.002176 | +0.020000 | PASS |

## Efficiency (SC5)

Frozen Phase-C validation-text TPC: StatBound **0.2280992074**, Unigram **0.2281023595**, relative Δ **-0.001382%**. The +10% threshold is unchanged and passes.

## Per-run integrity and provenance

- Required StatBound runs: **12**; finalized: **12**; runner failures: **0**.
- Every selected checkpoint was `best.pt`; checkpoint reload verification passed; no NaN/Inf was recorded.
- Training and source evaluation opened train/validation inputs only. No LM-test file was opened.
- Baseline comparisons use the existing audited r2 Unigram checkpoints; baselines were not retrained.
- Model fertility was not available in the frozen LM manifests; no new fertility computation was used for a criterion.

## Locks and historical provenance

- Morphology holdout: **LOCKED / UNTOUCHED**.
- LM test: **LOCKED / UNTOUCHED**.
- Phase C was not rerun; λ was not changed; no V2, post-hoc λ, or ablation was run.
- Historical exact agreement **0.52** and boundary F1 **0.841** remain unchanged and are not recomputed here.
- The Phase-C morphology failure is recorded as a frozen development result, not retroactively altered by LM outcomes.

## Stop condition

Phase F validation evaluation is complete. No LM test, morphology holdout, Phase H ablation, or automatic Phase-F-to-later-phase transition was performed.
