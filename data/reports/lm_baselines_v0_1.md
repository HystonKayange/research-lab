# LM baselines v0.1 — pilot (architecture_matched)

_Generated at 2026-08-05T05:04:33.249974Z by compare_lm_baselines 0.1.0_

## 1. Research question

Under the same data and controlled training budget, which tokenizer (character, BPE-8000, Unigram-8000) achieves better validation/test BPC, sample efficiency, stability, generation quality, and compute efficiency?

## 2. Hypotheses (locked before training)

- **H1 character:** The character model may generalize well to unseen word forms but will require longer sequences and more computation.
- **H2 BPE-8000:** BPE may achieve stronger compression and faster optimization but may over-rely on frequent whole words and non-morphological merges.
- **H3 Unigram-8000:** Unigram may provide similar efficiency to BPE while allowing more flexible subword segmentation.

## 3. Corpus and split identity

- Corpus: `chichewa_corpus_v0.1`
- Split: `v0.1` at `data/splits/chichewa_corpus_v0.1`

## 4. Tokenizers

- character, bpe_8000, unigram_8000 from `baselines_v0.1`

## 5. Architecture

```json
{
  "n_layer": 4,
  "n_embd": 256,
  "n_head": 4,
  "n_inner": 1024,
  "dropout": 0.1,
  "context_length": 256,
  "pre_ln": true,
  "tie_embeddings": true,
  "positional_encoding": "learned"
}
```

## 6. Parameter fairness

Track: **architecture_matched**. Embedding parameter differences are reported per run.

## 7. Compute-budget policy

Primary: fixed characters. Phase `pilot` budget: `{"train_characters": 200000, "max_optimizer_steps": 400, "seeds": [42]}`

## 8. Training configuration

```json
{
  "optimizer": "adamw",
  "learning_rate": 0.0003,
  "beta1": 0.9,
  "beta2": 0.95,
  "weight_decay": 0.1,
  "grad_clip": 1.0,
  "warmup_steps": 50,
  "schedule": "cosine",
  "micro_batch_size": 16,
  "grad_accum_steps": 2,
  "dtype": "bfloat16",
  "amp": true,
  "log_every": 20,
  "eval_every": 100,
  "save_every": 200,
  "packing": {
    "method": "line_pack_with_eos",
    "concatenate_lines": true,
    "eos_between_lines": true,
    "document_note": "Lines from combined.txt are packed in order with EOS between lines. Source boundaries within combined are not re-split; combined is bible then wikipedia concatenation from split builder."
  }
}
```

## 9. Pilot results

**Pilot results are not final multi-seed evidence.**

| tokenizer | seed | params | emb | non-emb | steps | chars | val BPC | val BPB | time_s | peak_GB |
|-----------|-----:|-------:|----:|--------:|------:|------:|--------:|--------:|-------:|--------:|
| bpe_8000 | 42 | 5273088 | 2113536 | 3159552 | 6 | 210816 | 2.9847 | 2.9558 | 0.8 | 0.74 |
| character | 42 | 3459328 | 299776 | 3159552 | 25 | 203150 | 7.2584 | 7.1881 | 1.5 | 0.38 |
| unigram_8000 | 42 | 5273088 | 2113536 | 3159552 | 6 | 212484 | 2.9800 | 2.9511 | 0.8 | 0.74 |

### Multi-seed summary (validation BPC)

- **bpe_8000:** mean=2.9847 ± 0.0000 (n=1, min=2.9847, max=2.9847)
- **character:** mean=7.2584 ± 0.0000 (n=1, min=7.2584, max=7.2584)
- **unigram_8000:** mean=2.9800 ± 0.0000 (n=1, min=2.9800, max=2.9800)

## 10–12. Validation / test BPC-BPB

Validation BPC is primary for checkpoint selection. Test metrics appear only if `eval_metrics.json` contains test splits (after `--allow-test`).

### bpe_8000 seed 42
- validation: BPC=2.984742456661339 BPB=2.95583403599689

### character seed 42
- validation: BPC=7.256637967662944 BPB=7.186354535834301

### unigram_8000 seed 42
- validation: BPC=2.97992632937961 BPB=2.951064554828002

## 13. Source-specific results

See per-run `eval_metrics.json` for bible_* and wikipedia_* splits when evaluated.

## 14. Learning curves

See each run's `validation_history.json` and `train_log.jsonl`.

## 15. Throughput and memory

See table peak_GB and runtime characters_per_second in manifests.

## 16. Generation samples

Human-review scaffold: `data/reports/lm_generation_review_v0_1.jsonl` (labels null).

## 17. Human-review status

Not filled automatically.

## 18. Memorization diagnostics

See per-run `memorization.json` when generated.

## 19. Limitations

- Small model / limited pilot character budget.
- Architecture-matched track gives subword models more embedding parameters.
- Token perplexity is not cross-comparable.
- Generation quality is qualitative only.

## 20. Conclusion

Pilot pipeline verification only — not final evidence.

## 21. Exact evidence motivating MthandiziTokenizer

MthandiziTokenizer is **not** motivated by this pilot alone. Motivation requires final multi-seed BPC gaps, morphology probe review, and generation/memorization patterns. Do not implement morphology-aware tokenizers until final baselines complete.
