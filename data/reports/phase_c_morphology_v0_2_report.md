# Phase C — Chichewa Level-B morphology development evaluation

This report evaluates the frozen 162-item development benchmark under the frozen Phase C protocol. It is a development/tuning report, not confirmatory evidence.

## Scope and locks

- Active benchmark items: **162**
- Active benchmark SHA-256: `73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67`
- Expected frozen SHA-256 verified: `True`
- Morphology holdout: **LOCKED / UNTOUCHED**
- LM test: **LOCKED / UNTOUCHED**
- LM BPC trained/evaluated: **false**
- LM BPC used for λ selection: **false**
- Morphology-development F1 used for λ selection is not confirmatory.

## Results

| system | boundary P | boundary R | boundary F1 | exact segmentation | TPC | fertility | items | reconstruction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BPE8k | 0.7015 | 0.3764 | 0.4622 | 0.0556 | 0.2285 | 1.6318 | 162 | PASS |
| Unigram8k | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2281 | 1.6291 | 162 | PASS |
| StatBound λ=0.0 (control) | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2281 | 1.6291 | 162 | PASS |
| StatBound λ=0.25 | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2281 | 1.6291 | 162 | PASS |
| StatBound λ=0.5 | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2281 | 1.6291 | 162 | PASS |
| StatBound λ=1.0 | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2282 | 1.6294 | 162 | PASS |
| StatBound λ=2.0 | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.2283 | 1.6303 | 162 | PASS |

`exact segmentation` is the macro item-level exact match rate; morphology precision/recall/F1/Jaccard are macro-averaged by the frozen harness.

## λ selection

- Unigram8k validation TPC: **0.2281**
- Eligibility threshold (1.10 × Unigram8k TPC): **0.2509**
- Selected provisional λ*: **0.25**
- Selection pool: `eligible`
- LM BPC used: **False**

| λ | morphology F1 | validation TPC | eligible | reason |
|---:|---:|---:|:---:|---|
| 0.25 | 0.5551 | 0.2281 | yes | TPC <= 1.10 × Unigram8k TPC (0.2509125954) |
| 0.5 | 0.5551 | 0.2281 | yes | TPC <= 1.10 × Unigram8k TPC (0.2509125954) |
| 1.0 | 0.5551 | 0.2282 | yes | TPC <= 1.10 × Unigram8k TPC (0.2509125954) |
| 2.0 | 0.5551 | 0.2283 | yes | TPC <= 1.10 × Unigram8k TPC (0.2509125954) |

## SC4 development diagnostic

- Strongest standard tokenizer F1: **0.5551**
- Selected StatBound F1: **0.5551**
- Margin over strongest standard tokenizer: **0.0000**
- Frozen +0.03 threshold: **0.0300**
- SC4 development threshold met provisionally: **False**

## λ=0 control

- StatBound λ=0.0 vs ordinary Unigram8k sequence equality: **162/162**
- Boundary-set equality: **162/162**
- Control passes: **True**

## Diagnostic morphology-category breakdowns

Breakdowns use available audit metadata (source, confidence, adjudication provenance, policy-rule labels, disagreement type, and gold segment count). They are descriptive only and were not used to select λ.

### source

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| bible | 120 | 0.8824 | 0.4059 | 0.5437 | 0.0583 | 0.3678 |
| wikipedia | 42 | 0.7366 | 0.5789 | 0.5863 | 0.1429 | 0.4374 |

### confidence

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| HIGH | 115 | 0.8742 | 0.4284 | 0.5561 | 0.0783 | 0.3819 |
| LOW | 8 | 0.5286 | 0.7857 | 0.6944 | 0.2500 | 0.4417 |
| MEDIUM | 39 | 0.8150 | 0.4538 | 0.5309 | 0.0513 | 0.3860 |

### adjudication_source

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| native_speaker_adjudication | 11 | 0.6033 | 0.8500 | 0.7519 | 0.2727 | 0.5333 |
| original_keep | 18 | 0.6722 | 0.6863 | 0.7405 | 0.4444 | 0.5417 |
| policy_accepted_revision | 133 | 0.8822 | 0.3900 | 0.5207 | 0.0150 | 0.3525 |

### policy_rule

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| RULE_2_NEGATIVE | 19 | 0.9386 | 0.3877 | 0.5288 | 0.0000 | 0.3711 |
| RULE_3_EXTENSIONS | 67 | 0.8711 | 0.3781 | 0.4974 | 0.0299 | 0.3508 |
| RULE_5_NOUN_CLASS_AGREEMENT | 78 | 0.8059 | 0.4763 | 0.5579 | 0.0897 | 0.3948 |
| RULE_6_LOCATIVE_CONTRACTION | 15 | 0.8238 | 0.6122 | 0.6246 | 0.2000 | 0.4735 |
| RULE_7_LOANS_NAMES_QUALITY | 5 | 0.5000 | 0.7500 | 0.6667 | 0.4000 | 0.5000 |
| UNSPECIFIED | 34 | 0.8889 | 0.4242 | 0.5984 | 0.0882 | 0.3922 |

### disagreement_type

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| ['final-vowel issue', 'TAM issue'] | 5 | 1.0000 | 0.3500 | 0.5133 | 0.0000 | 0.3500 |
| ['final-vowel issue', 'lexicalization/root uncertainty'] | 18 | 0.8722 | 0.4019 | 0.5164 | 0.0000 | 0.3590 |
| ['final-vowel issue', 'missing productive morphology'] | 1 | 1.0000 | 0.4000 | 0.5714 | 0.0000 | 0.4000 |
| ['final-vowel issue', 'noun-class issue'] | 4 | 0.8750 | 0.4583 | 0.5595 | 0.0000 | 0.3917 |
| ['final-vowel issue', 'post-final/clitic issue', 'incorrect grammatical parse'] | 1 | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 0.5000 |
| ['final-vowel issue', 'post-final/clitic issue', 'lexicalization/root uncertainty'] | 4 | 0.7500 | 0.5250 | 0.5947 | 0.0000 | 0.4271 |
| ['final-vowel issue', 'post-final/clitic issue'] | 12 | 0.9583 | 0.4472 | 0.5846 | 0.0000 | 0.4333 |
| ['final-vowel issue'] | 33 | 0.9667 | 0.3869 | 0.5728 | 0.0303 | 0.3803 |
| ['granularity', 'final-vowel issue', 'missing productive morphology'] | 1 | 1.0000 | 0.2500 | 0.4000 | 0.0000 | 0.2500 |
| ['incorrect grammatical parse', 'TAM issue', 'syllabic oversegmentation', 'final-vowel issue'] | 1 | 0.6667 | 0.6667 | 0.6667 | 0.0000 | 0.5000 |
| ['incorrect grammatical parse', 'final-vowel issue', 'TAM issue'] | 5 | 0.9333 | 0.3867 | 0.5286 | 0.0000 | 0.3667 |
| ['incorrect grammatical parse', 'final-vowel issue', 'post-final/clitic issue'] | 2 | 1.0000 | 0.2667 | 0.4167 | 0.0000 | 0.2667 |
| ['incorrect grammatical parse', 'final-vowel issue'] | 1 | 1.0000 | 0.2500 | 0.4000 | 0.0000 | 0.2500 |
| ['incorrect grammatical parse', 'missing productive morphology', 'final-vowel issue', 'lexicalization/root uncertainty'] | 1 | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 0.5000 |
| ['incorrect grammatical parse', 'missing productive morphology', 'final-vowel issue'] | 1 | 1.0000 | 0.2500 | 0.4000 | 0.0000 | 0.2500 |
| ['insufficient context', 'final-vowel issue'] | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| ['language/quality issue', 'lexicalization/root uncertainty'] | 1 | 0.0000 | — | — | 0.0000 | 0.0000 |
| ['lexicalization/root uncertainty', 'final-vowel issue', 'noun-class issue', 'language/quality issue'] | 1 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 0.5000 |
| ['locative issue', 'language/quality issue'] | 2 | 0.3500 | 1.0000 | 0.5000 | 0.0000 | 0.3500 |
| ['locative issue', 'lexicalization/root uncertainty', 'language/quality issue'] | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| ['locative issue', 'lexicalization/root uncertainty'] | 2 | 1.0000 | 0.5000 | 1.0000 | 0.5000 | 0.5000 |
| ['locative issue'] | 2 | 0.6667 | 1.0000 | 0.8000 | 0.0000 | 0.6667 |
| ['missing productive morphology', 'final-vowel issue', 'TAM issue'] | 1 | 0.3333 | 0.2500 | 0.2857 | 0.0000 | 0.1667 |
| ['missing productive morphology', 'final-vowel issue', 'lexicalization/root uncertainty'] | 3 | 0.3611 | 0.2778 | 0.3016 | 0.0000 | 0.1778 |
| ['missing productive morphology', 'final-vowel issue', 'post-final/clitic issue', 'lexicalization/root uncertainty'] | 1 | 1.0000 | 0.5000 | 0.6667 | 0.0000 | 0.5000 |
| ['missing productive morphology', 'final-vowel issue', 'post-final/clitic issue', 'syllabic oversegmentation'] | 1 | 0.2500 | 0.3333 | 0.2857 | 0.0000 | 0.1667 |
| ['missing productive morphology', 'final-vowel issue', 'post-final/clitic issue'] | 3 | 1.0000 | 0.2333 | 0.3730 | 0.0000 | 0.2333 |
| ['missing productive morphology', 'final-vowel issue', 'syllabic oversegmentation'] | 1 | 1.0000 | 0.3333 | 0.5000 | 0.0000 | 0.3333 |
| ['missing productive morphology', 'final-vowel issue'] | 18 | 0.8704 | 0.2639 | 0.3894 | 0.0000 | 0.2444 |
| ['none'] | 18 | 0.6722 | 0.6863 | 0.7405 | 0.4444 | 0.5417 |
| ['noun-class issue', 'final-vowel issue', 'post-final/clitic issue', 'incorrect grammatical parse'] | 1 | 0.5000 | 0.5000 | 0.5000 | 0.0000 | 0.3333 |
| ['noun-class issue', 'granularity'] | 2 | 0.7500 | 0.5833 | 0.6500 | 0.0000 | 0.5000 |
| ['noun-class issue'] | 7 | 0.7778 | 0.7143 | 0.7444 | 0.1429 | 0.5238 |
| ['syllabic oversegmentation', 'final-vowel issue', 'lexicalization/root uncertainty'] | 1 | 1.0000 | 0.3333 | 0.5000 | 0.0000 | 0.3333 |
| ['syllabic oversegmentation', 'final-vowel issue'] | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| ['syllabic oversegmentation', 'lexicalization/root uncertainty'] | 2 | 0.5000 | 0.5000 | 0.6667 | 0.0000 | 0.2500 |
| ['syllabic oversegmentation', 'missing productive morphology', 'final-vowel issue'] | 1 | 1.0000 | 0.3333 | 0.5000 | 0.0000 | 0.3333 |

### gold_segment_count

| group | n | B-P | B-R | B-F1 | exact | Jaccard |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0.0000 | — | — | 0.0000 | 0.0000 |
| 2 | 25 | 0.5713 | 0.6000 | 0.6426 | 0.2800 | 0.4113 |
| 3 | 26 | 0.8333 | 0.6923 | 0.7192 | 0.1923 | 0.5897 |
| 4 | 50 | 0.8965 | 0.3867 | 0.5297 | 0.0200 | 0.3605 |
| 5 | 38 | 0.8964 | 0.3158 | 0.4620 | 0.0000 | 0.3026 |
| 6 | 16 | 0.9375 | 0.3875 | 0.5147 | 0.0000 | 0.3663 |
| 7 | 5 | 1.0000 | 0.3000 | 0.4476 | 0.0000 | 0.3000 |

## Integrity and provenance

- Reconstruction failures in frozen gold: **0**
- Per-system prediction reconstruction failures: **0**
- Duplicate active IDs: **0**
- Exact item count: **True**
- Pre-Phase-C git commit: `a5078c26327b1ec7b687c2852a27939db9a7650a`
- Pre-Phase-C tag: `morphology-benchmark-v0.2-pre-phase-c`
- Results file SHA-256: `d0d22cfa29ae92c73a08133794d8a6d7d507529522641de7c823b9fa81ac14eb`

Authorized Phase C tokenizer artifacts were evaluated. No morphology holdout, LM test, LM BPC, ablation, or Phase F operation was accessed.

Historical exact agreement `0.52` and boundary F1 `0.841` are preserved as measurements of the original annotation protocol; they were not recomputed here.

**STOP CONDITION:** provisional λ* selection is complete; Phase F and all later phases were not started.
