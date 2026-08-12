# Tokenizer morphology-oriented failure audit v0.1

_Generated 2026-08-06T00:06:36.591504Z by analyze_baseline_morphology_failures 0.1.0_

## Safety

- Splits: train + validation only
- LM test split: **not accessed**
- Human gold morphology: **not generated**
- Recurring strings are **not** called morphemes without human validation

## Evidence taxonomy

### Orthographic evidence

- Unicode surface forms as written in corpus
- Presence of ŵ / mixed scripts
- Word length in characters

### Statistical evidence

- Fertility, disagreement rates, correlations, consistency rates
- Frequency bands and source aggregates

### Linguistic interpretation (human review required)

- Whether a prefix/suffix string is a morpheme
- Whether disagreement is morphologically meaningful
- Noun-class, tense/aspect, object marking claims

## Aggregate diagnostics

- Words analyzed: **15000**
- BPE≠Unigram (8000) count: **9087** (rate=0.6058)
- Mean tokens/word BPE: 3.4699333333333335
- Mean tokens/word Unigram: 3.5561333333333334
- Mean chars/token BPE: 2.5862303664169235
- Mean chars/token Unigram: 2.5830144631249827
- Whole-word token rate BPE: 0.005933333333333333
- Whole-word token rate Unigram: 0.003933333333333333
- Single-char fragment rate BPE: 0.31447290053603333
- Single-char fragment rate Unigram: 0.3143301713471561
- Unseen-form mean fertility BPE: 3.5033152501506932
- Unseen-form mean fertility Unigram: 3.619047619047619
- Corr(log freq, fertility) BPE: -0.0848250901527604
- Corr(log freq, fertility) Unigram: -0.09416338835262936
- Corr(length, fertility) BPE: 0.649021336411969
- Corr(length, fertility) Unigram: 0.60414667026207

### Frequency sensitivity

```json
{
  "common_21_100": {
    "n": 3,
    "mean_bpe_fertility": 1.0,
    "mean_unigram_fertility": 1.0
  },
  "frequent_100p": {
    "n": 1,
    "mean_bpe_fertility": 1.0,
    "mean_unigram_fertility": 1.0
  },
  "mid_4_20": {
    "n": 94,
    "mean_bpe_fertility": 3.4893617021276597,
    "mean_unigram_fertility": 2.6808510638297873
  },
  "rare_1_3": {
    "n": 13243,
    "mean_bpe_fertility": 3.4663595861964813,
    "mean_unigram_fertility": 3.5552367288378766
  },
  "unseen": {
    "n": 1659,
    "mean_bpe_fertility": 3.5033152501506932,
    "mean_unigram_fertility": 3.619047619047619
  }
}
```

### Source sensitivity

```json
{
  "bible": {
    "n": 4964,
    "mean_bpe_fertility": 2.8736905721192585
  },
  "wikipedia": {
    "n": 10036,
    "mean_bpe_fertility": 3.7648465524113193
  }
}
```

### Surface family consistency (not morphemes)

- BPE mean stem-as-piece rate: 0.425
- Unigram mean stem-as-piece rate: 0.55

## Dominant automatic patterns

- `high_bpe_unigram_disagreement_on_prioritized_sample` (statistical)
- `fertility_increases_for_unseen_and_rare_bands` (statistical)
- `incomplete_stem_piece_sharing_in_surface_families` (statistical)

Disagreement export: `data/reports/tokenizer_disagreement_candidates_v0_1.jsonl` (n=3000)

## Sampling note

The analyzed word list is a **prioritized sample** (rare, long, unseen, `ŵ`-containing forms preferred), not a uniform draw over all train types. Absolute rates (e.g. disagreement ≈ 0.61) describe this sample, not full-corpus token prevalence. Frequency-band cell sizes for high-frequency words may be small under this sampling policy.

## What this report does not claim

- Morphological correctness of any tokenization
- That BPE or Unigram is linguistically superior
- That a hybrid method will improve LM test BPC
- That recurring character strings are morphemes
