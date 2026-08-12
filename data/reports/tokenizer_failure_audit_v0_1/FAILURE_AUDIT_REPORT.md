# Tokenizer failure audit v0.1 (Phase A)

_Generated 2026-08-05T23:57:57.578073Z by audit_tokenizer_failures 0.1.0_

## Scope

- Splits used: **train**, **validation** only
- LM **test** split: **not accessed**
- Hybrid tokenizer implementation: **not in this phase**
- Human morphology labels: **not invented** (`human_*` fields null)

## Inputs

- Config: `configs/tokenizers/baselines_v0_1.json`
- Experiment root: `data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1`
- Frozen split verified: `True`
- Models loaded: ['bpe_1000', 'bpe_2000', 'bpe_4000', 'bpe_8000', 'character', 'unigram_1000', 'unigram_2000', 'unigram_4000', 'unigram_8000']
- Morphology probes incorporated: 80

## Aggregate diagnostics (candidate bank)

- Words compared (pool): **12055**
- Candidates emitted: **2500**
- BPE≠Unigram (8000) in bank: **2500**
- Mean BPE-8000 fertility (bank): 4.3712
- Mean Unigram-8000 fertility (bank): 4.4592
- Split counts: `{'train': 657, 'validation': 1843}`
- Source counts: `{'wikipedia': 1183, 'bible': 1317}`

### Tag counts

- `bpe_unigram_disagree`: 2500
- `vocab_size_sensitive`: 2500
- `high_fragmentation`: 2455
- `split_validation`: 1843
- `unseen_in_train`: 1774
- `source_bible`: 1317
- `long_word`: 1311
- `source_wikipedia`: 1183
- `rare_train`: 680
- `split_train`: 657
- `fertility_asymmetric`: 549
- `mixed_orthography_heuristic`: 422
- `family_stem_hit`: 73
- `contains_w_hat`: 69
- `family_segmentation_inconsistent`: 39
- `whole_word_single_token`: 10

**Caution:** Automatic tags are not morphological gold labels. human_phenomenon_tags remain null until annotation.

## Link to LM validation (existing r2; test not run)

Provisional validation leaders (from prior audit):

- architecture_matched × fixed_characters: **unigram_8000** (mean BPC=1.4313127134139931)
- architecture_matched × fixed_updates: **unigram_8000** (mean BPC=1.4433547294988347)
- parameter_matched × fixed_characters: **unigram_8000** (mean BPC=1.4370611407962612)
- parameter_matched × fixed_updates: **unigram_8000** (mean BPC=1.4793057103427036)

These LM results motivate studying why Unigram performed better on validation under these budgets; they do **not** by themselves prove morphological adequacy of Unigram pieces.

## Failure class → proposed mechanism map (design only)

| failure_class | count | proposed_mechanism |
|---------------|------:|--------------------|
| bpe_unigram_disagree | 2500 | Hybrid constraints: prefer inventory-backed boundaries when annotation supports … |
| family_segmentation_inconsistent | 39 | Shared stem piece inventory with optional forced merges. |
| high_fragmentation | 2455 | Productive affix/stem pieces instead of character-like shatter. |
| whole_word_single_token | 10 | Discourage low-count whole-word pieces; favour composition. |
| unseen_in_train | 1774 | Composition-first segmentation for OOV types. |
| contains_w_hat | 69 | Preserve identity normalization; retain ŵ in inventory. |
| mixed_orthography_heuristic | 422 | Fallback to backbone; optional bilingual piece seeds if justified. |

Full mechanism notes are in `mechanism_map.json` and `docs/tokenizers/MTHANDIZI_RESEARCH_BLUEPRINT.md`.

## Example disagreements (sample)

- `Mönchengladbach` (train/wikipedia, freq_train=12): BPE=['▁M', 'ö', 'n', 'ch', 'eng', 'la', 'd', 'ba', 'ch'] Unigram=['▁Mönchengladbach'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'whole_word_single_token', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `imapeŵetsanso` (validation/wikipedia, freq_train=0): BPE=['▁ima', 'pe', 'ŵ', 'e', 'tsanso'] Unigram=['▁ima', 'pe', 'ŵ', 'e', 'tsa', 'nso'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'family_stem_hit', 'stem:ima', 'vocab_size_sensitive', 'source_wikipedia', 'split_validation']
- `Dzuŵa` (validation/wikipedia, freq_train=0): BPE=['▁Dzu', 'ŵa'] Unigram=['▁D', 'zu', 'ŵ', 'a'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'unseen_in_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_validation']
- `umphaŵi` (validation/wikipedia, freq_train=0): BPE=['▁um', 'pha', 'ŵi'] Unigram=['▁', 'um', 'pha', 'ŵ', 'i'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'unseen_in_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_validation']
- `woseŵakambe--bb` (train/wikipedia, freq_train=1): BPE=['▁wo', 'se', 'ŵa', 'kamb', 'e', '--', 'b', 'b'] Unigram=['▁wo', 'se', 'ŵ', 'a', 'ka', 'mbe', '-', '-', 'b', 'b'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `mʼBetelehemu` (validation/bible, freq_train=0): BPE=['▁m', 'ʼ', 'B', 'ete', 'lehemu'] Unigram=['▁m', 'ʼ', 'B', 'e', 'te', 'le', 'he', 'mu'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_bible', 'split_validation']
- `kupitamo` (train/bible, freq_train=1): BPE=['▁ku', 'pi', 't', 'amo'] Unigram=['▁kupita', 'mo'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'rare_train', 'family_stem_hit', 'stem:pita', 'family_segmentation_inconsistent', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_bible', 'split_train']
- `m'maseŵera` (train/wikipedia, freq_train=3): BPE=['▁m', "'", 'ma', 'se', 'ŵ', 'era'] Unigram=['▁m', "'", 'maseŵera'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `mʼMalamulomo` (validation/bible, freq_train=0): BPE=['▁m', 'ʼ', 'M', 'alam', 'ul', 'omo'] Unigram=['▁m', 'ʼ', 'Malamulo', 'mo'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_bible', 'split_validation']
- `mʼmaonekedwe` (validation/bible, freq_train=0): BPE=['▁m', 'ʼ', 'ma', 'onekedwe'] Unigram=['▁m', 'ʼ', 'ma', 'one', 'ke', 'dwe'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_bible', 'split_validation']
- `mʼtizidutswa` (validation/bible, freq_train=0): BPE=['▁m', 'ʼ', 'ti', 'zi', 'du', 'ts', 'wa'] Unigram=['▁m', 'ʼ', 'ti', 'zi', 'dutswa'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_bible', 'split_validation']
- `m’maonekedwe` (validation/wikipedia, freq_train=0): BPE=['▁m', '’', 'ma', 'onekedwe'] Unigram=['▁m', '’', 'ma', 'one', 'ke', 'dwe'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_validation']
- `№MonarchPortraitReignRoyal` (validation/wikipedia, freq_train=0): BPE=['▁', '№', 'M', 'ona', 'r', 'ch', 'P', 'or', 'tra', 'it', 'R', 'e', 'i', 'gn', 'Ro', 'yal'] Unigram=['▁', '№', 'M', 'ona', 'r', 'ch', 'Po', 'rt', 'ra', 'it', 'Re', 'i', 'g', 'n', 'R', 'o', 'ya', 'l'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'unseen_in_train', 'long_word', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_validation']
- `Chizoloŵezi` (train/wikipedia, freq_train=2): BPE=['▁Chi', 'zolo', 'ŵ', 'ezi'] Unigram=['▁Chi', 'zo', 'lo', 'ŵ', 'e', 'zi'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `Dzuŵa-Dzuwa` (train/wikipedia, freq_train=1): BPE=['▁Dzu', 'ŵa', '-', 'D', 'zu', 'wa'] Unigram=['▁D', 'zu', 'ŵ', 'a', '-', 'D', 'zu', 'wa'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `Khweŵa` (train/wikipedia, freq_train=1): BPE=['▁Kh', 'we', 'ŵa'] Unigram=['▁K', 'h', 'we', 'ŵ', 'a'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `M’nthaŵi` (train/wikipedia, freq_train=2): BPE=['▁M', '’', 'n', 'tha', 'ŵi'] Unigram=['▁M', '’', 'nthaŵi'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `chizoloŵezi` (train/wikipedia, freq_train=2): BPE=['▁chi', 'zolo', 'ŵ', 'ezi'] Unigram=['▁chi', 'zo', 'lo', 'ŵ', 'e', 'zi'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `dzuŵa` (train/wikipedia, freq_train=2): BPE=['▁dzu', 'ŵa'] Unigram=['▁', 'dzu', 'ŵ', 'a'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `kuloŵa` (train/wikipedia, freq_train=1): BPE=['▁kulo', 'ŵa'] Unigram=['▁ku', 'lo', 'ŵ', 'a'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `kuloŵerera` (train/wikipedia, freq_train=1): BPE=['▁kulo', 'ŵ', 'erera'] Unigram=['▁ku', 'lo', 'ŵ', 'ere', 'ra'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `kumaseŵera` (train/wikipedia, freq_train=1): BPE=['▁kuma', 'se', 'ŵ', 'era'] Unigram=['▁ku', 'maseŵera'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `m'nthaŵi` (train/wikipedia, freq_train=1): BPE=['▁m', "'", 'n', 'tha', 'ŵi'] Unigram=['▁m', "'", 'nthaŵi'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `m’nthaŵi` (train/wikipedia, freq_train=1): BPE=['▁m', '’', 'n', 'tha', 'ŵi'] Unigram=['▁m', '’', 'nthaŵi'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']
- `pamaseŵera` (train/wikipedia, freq_train=1): BPE=['▁pama', 'se', 'ŵ', 'era'] Unigram=['▁pa', 'maseŵera'] tags=['bpe_unigram_disagree', 'high_fragmentation', 'contains_w_hat', 'rare_train', 'mixed_orthography_heuristic', 'fertility_asymmetric', 'vocab_size_sensitive', 'source_wikipedia', 'split_train']

## What this audit does **not** claim

- That automatic tags equal morphological truth
- That Unigram or BPE is morphologically correct
- That a hybrid tokenizer will improve LM test BPC
- That results transfer to all Bantu languages

## Next phases

1. Stratified human annotation of a fixed sample (`human_*` fields)
2. Estimate how often disagreements are genuinely morphological
3. Only then implement hybrid mechanisms that map to measured classes
4. Validate under the same four LM comparison groups; keep test locked
