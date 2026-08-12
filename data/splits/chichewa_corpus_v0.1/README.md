# Corpus splits — chichewa_corpus v0.1 / v0.1

**Frozen:** yes  
**Created:** 2026-08-05T04:09:01.057702Z

## Layout

- `train/`, `validation/`, `test/` — each with `bible.txt`, `wikipedia.txt`, `combined.txt`
- `metadata/split_assignments.jsonl` — group → split map
- `metadata/*_documents.jsonl` — line-level membership
- `metadata/FROZEN_SPLIT.json` — freeze marker

## Tokenizer / LM rules

1. Train tokenizers **only** on `train/`.
2. Do **not** use `validation/` or `test/` for tokenizer training or vocabulary selection.
3. Validation is for model selection; test is for final comparison only.
4. Prefer bits/character or bits/byte for cross-tokenizer LM comparison (raw perplexity is not comparable).
5. External benchmarks (e.g. FLORES) are separate from these splits.

## Grouping note

Document-level Bible book/chapter and Wikipedia article IDs are **not** available in the
processed corpus. Groups are **contiguous character blocks** (~5000 chars).
This is a documented fallback, not recovered structure.

Config: `configs/data/split_v0_1.json`  
Config SHA-256: `89ebdbb1ffb32f86f87b25b598cfe03780bfdc38f0b8d07a20000d90a4fac5e4`
