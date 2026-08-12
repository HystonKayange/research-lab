# Tokenizer baselines v0.1 — Chichewa Corpus

_Generated at 2026-08-05T04:49:09.159461Z by evaluate_tokenizers 0.1.0_

## 1. Research objective

Train and evaluate character-level, SentencePiece BPE, and SentencePiece Unigram tokenizers on frozen Chichewa training text to measure sequence efficiency, vocabulary behavior, coverage, fragmentation, and morphology-related observations. This is **tokenizer analysis only** — not language-model quality.

## 2. Frozen corpus and split identity

- Corpus version: `chichewa_corpus_v0.1`
- Split version: `v0.1`
- Split root: `data/splits/chichewa_corpus_v0.1`
- Experiment: `baselines_v0.1`
- Freeze verified: `True`

## 3. Training-data restrictions

- Tokenizers trained **only** on `train/combined.txt` (and character vocab from that text).
- Validation and test text were **not** used for vocabulary induction or SP training.
- Forbidden path substrings checked before training/evaluation wiring.

## 4. Tokenizer configurations

- Character: specials ['<pad>', '<unk>', '<bos>', '<eos>']
- SentencePiece vocab sizes: [1000, 2000, 4000, 8000]
- model types: ['bpe', 'unigram']
- character_coverage: 1.0
- normalization_rule_name: identity
- byte_fallback: False
- seed: None (sentencepiece 0.2.0 TrainerSpec has no seed field; determinism via shuffle_input_sentence=false, num_threads=1, full corpus, fixed config.)
- num_threads: 1
- pad/unk/bos/eos ids: 0/1/2/3

## 5. Normalization policy

- Policy: **identity**
- Preserve case, punctuation, `ŵ`, and Unicode; no lowercasing; no accent stripping; no NFKC.
- Audit: identity; 0 changes on train samples at train time

## 6. Character baseline results (validation)

- fertility (overall): 7.1419
- unk rate: 0.0001
- tokens/line: 120.6750
- tokens/char: 1.0000
- chars/token: 1.0000
- vocab utilization: 0.2339
- p95 sequence length: 242.0000
- bible fertility: 7.2008
- wikipedia fertility: 6.9943
- Note: character fertility is tokens-per-word at character granularity; do not use it as a subword 'winner' metric.

## 7. BPE results by vocabulary size (validation)

### BPE 1000

- fertility (overall): 4.2783
- unk rate: 0.0001
- tokens/line: 72.2897
- tokens/char: 0.5990
- chars/token: 1.6693
- vocab utilization: 0.3290
- p95 sequence length: 142.0000
- bible fertility: 4.1489
- wikipedia fertility: 4.6027

### BPE 2000

- fertility (overall): 2.3136
- unk rate: 0.0002
- tokens/line: 39.0917
- tokens/char: 0.3239
- chars/token: 3.0870
- vocab utilization: 0.6625
- p95 sequence length: 77.0000
- bible fertility: 2.1577
- wikipedia fertility: 2.7041

### BPE 4000

- fertility (overall): 1.8641
- unk rate: 0.0002
- tokens/line: 31.4975
- tokens/char: 0.2610
- chars/token: 3.8313
- vocab utilization: 0.8115
- p95 sequence length: 62.0000
- bible fertility: 1.7350
- wikipedia fertility: 2.1876

### BPE 8000

- fertility (overall): 1.6318
- unk rate: 0.0002
- tokens/line: 27.5721
- tokens/char: 0.2285
- chars/token: 4.3767
- vocab utilization: 0.8325
- p95 sequence length: 54.0000
- bible fertility: 1.5367
- wikipedia fertility: 1.8700

## 8. Unigram results by vocabulary size (validation)

### Unigram 1000

- fertility (overall): 4.1891
- unk rate: 0.0001
- tokens/line: 70.7828
- tokens/char: 0.5866
- chars/token: 1.7049
- vocab utilization: 0.3280
- p95 sequence length: 139.1500
- bible fertility: 4.0474
- wikipedia fertility: 4.5442

### Unigram 2000

- fertility (overall): 2.2278
- unk rate: 0.0002
- tokens/line: 37.6421
- tokens/char: 0.3119
- chars/token: 3.2059
- vocab utilization: 0.6630
- p95 sequence length: 74.0000
- bible fertility: 2.0538
- wikipedia fertility: 2.6635

### Unigram 4000

- fertility (overall): 1.8371
- unk rate: 0.0002
- tokens/line: 31.0409
- tokens/char: 0.2572
- chars/token: 3.8876
- vocab utilization: 0.8125
- p95 sequence length: 61.0000
- bible fertility: 1.7020
- wikipedia fertility: 2.1755

### Unigram 8000

- fertility (overall): 1.6291
- unk rate: 0.0002
- tokens/line: 27.5262
- tokens/char: 0.2281
- chars/token: 4.3840
- vocab utilization: 0.7966
- p95 sequence length: 54.0000
- bible fertility: 1.5321
- wikipedia fertility: 1.8721

## 9. Validation comparison

| tokenizer | fertility | unk_rate | util | tokens/char | p95 seq | score |
|-----------|----------:|---------:|-----:|------------:|--------:|------:|
| bpe_1000 | 4.2783 | 0.0001 | 0.3290 | 0.5990 | 142.0000 | 6.9222 |
| bpe_2000 | 2.3136 | 0.0002 | 0.6625 | 0.3239 | 77.0000 | 11.6264 |
| bpe_4000 | 1.8641 | 0.0002 | 0.8115 | 0.2610 | 62.0000 | 12.7563 |
| bpe_8000 | 1.6318 | 0.0002 | 0.8325 | 0.2285 | 54.0000 | 13.1726 |
| character | 7.1419 | 0.0001 | 0.2339 | 1.0000 | 242.0000 | — |
| unigram_1000 | 4.1891 | 0.0001 | 0.3280 | 0.5866 | 139.1500 | 7.1128 |
| unigram_2000 | 2.2278 | 0.0002 | 0.6630 | 0.3119 | 74.0000 | 11.8119 |
| unigram_4000 | 1.8371 | 0.0002 | 0.8125 | 0.2572 | 61.0000 | 12.8160 |
| unigram_8000 | 1.6291 | 0.0002 | 0.7966 | 0.2281 | 54.0000 | 13.1241 |

## 10. Selected BPE candidate

- **Selected:** `bpe_8000`
- Rationale: Highest multi-criteria validation score (13.172570500960132). fertility=1.631799916707, unk_rate=0.00023452481134548264, util=0.8325, vocab_size=8000. Test data was not used for this choice.

## 11. Selected Unigram candidate

- **Selected:** `unigram_8000`
- Rationale: Highest multi-criteria validation score (13.124066147122358). fertility=1.629087266301228, unk_rate=0.00023491532684322166, util=0.796625, vocab_size=8000. Test data was not used for this choice.

## 12. Test results for selected candidates

Test metrics were computed **after** validation-only selection.

### bpe_8000 (test)

- fertility (overall): 1.6524
- unk rate: 0.0002
- tokens/line: 28.7390
- tokens/char: 0.2308
- chars/token: 4.3325
- vocab utilization: 0.8439
- p95 sequence length: 57.0000
- bible fertility: 1.5381
- wikipedia fertility: 1.8528

### character (test)

- fertility (overall): 7.1592
- unk rate: 0.0001
- tokens/line: 124.5126
- tokens/char: 1.0000
- chars/token: 1.0000
- vocab utilization: 0.2885
- p95 sequence length: 244.0000
- bible fertility: 7.1551
- wikipedia fertility: 7.1665

### unigram_8000 (test)

- fertility (overall): 1.6478
- unk rate: 0.0002
- tokens/line: 28.6584
- tokens/char: 0.2302
- chars/token: 4.3447
- vocab utilization: 0.8077
- p95 sequence length: 57.0000
- bible fertility: 1.5297
- wikipedia fertility: 1.8547

## 13. Fertility comparison

Fertility = encoded tokens / whitespace-delimited words.
Character fertility is reported separately and is not a fair subword competitor.

## 14. Vocabulary utilization

See validation table (util column) and per-model `vocabulary_usage` in JSON metrics.

## 15. Sequence-length comparison

See p50/p90/p95/p99 in JSON metrics; summary p95 in the comparison table.

## 16. Source-specific differences

Bible vs Wikipedia fertility and tokens/char are in each metric blob under `by_source`.
Religious formulaic text may yield different fragmentation than encyclopedic text.

## 17. Representative tokenizations

See `data/reports/tokenizer_examples_v0_1.jsonl` and `evaluation/examples.jsonl`.
Segmentations are **not** claimed to be morphologically correct.

## 18. Morphology-related observations

Probe candidates (unlabeled): `data/reports/chichewa_morphology_probe_v0_1.jsonl`.
The tokenizer produced surface pieces that may or may not align with morphemes; this requires human linguistic review. Do not treat pieces as gold morphology.

## 19. Limitations

- No language-model experiments yet; efficiency ≠ predictive quality.
- SentencePiece pieces can look English-like for loanwords; diagnostic only.
- Contiguous-block corpus splits mean adjacent verses stay together, but tokenizer training is line-agnostic over train text.
- byte_fallback=false may increase <unk> if rare scripts appear only in eval (expected to be low given character_coverage=1.0 on train).
- Selection rubric is multi-criteria and approximate.

## 20. Next experiment recommendation

Run a **controlled small language-model baseline** comparing:
1. character
2. selected BPE `bpe_8000`
3. selected Unigram `unigram_8000`

Train models only on the frozen train split; select on validation; report test bits/character (or bits/byte). Do not compare raw token-level perplexity across tokenizers.
Do not implement MthandiziTokenizer until baselines are measured.

### Integrity

- Config SHA-256: `23e3ebb67bb21b51eb02126cca2d3a3b92452313c463386a47dcb694c79306f8`
- SentencePiece version: `0.2.0`
- Git commit: `None`

This report documents representation efficiency and diagnostics. It does **not** declare a superior tokenizer for language modeling.
