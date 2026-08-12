# Corpus splits (Chichewa Corpus v0.1)

## Purpose

Frozen **train / validation / test** splits for fair comparison of:

* character-level tokenization  
* standard SentencePiece / BPE  
* future morphology-aware tokenization  
* future hybrid MthandiziTokenizer variants  

**Tokenizers must be trained only on the training split.** Validation and test remain unseen by tokenizer training and by final model training (test is final evaluation only).

## Document-boundary findings (v0.1 processed corpus)

Inspected:

* `data/processed/chichewa_corpus_v0.1/metadata/documents.jsonl`  
* `sources.json`, `build_manifest.json`, `checksums.json`  
* `corpus/bible.txt`, `corpus/wikipedia.txt`  

| Question | Finding |
|----------|---------|
| Bible book/chapter/verse IDs? | **Not preserved** (VPL markers absent in processed text) |
| Wikipedia article boundaries? | **Not preserved** (no article IDs; no blank-line separators) |
| Line → source mapping? | **Yes** via `doc_id = source_id:line_index` |
| Safe line-level random split? | **No** — adjacent verses/lines would leak across splits |

**Grouping used:** deterministic **contiguous character blocks** (~5000 Unicode characters per group, configurable). This is a documented fallback, **not** invented book/article metadata.

## Principles

1. Deterministic (SHA-256 group hash; not Python `hash()`)  
2. Source-aware (per-source files + attribution in metadata)  
3. Group-aware (contiguous blocks never split across train/val/test)  
4. No exact or normalized exact line crossing splits  
5. No tokenizer training on val/test  
6. Frozen after creation  
7. Checksum-manifested  
8. Reproducible from the processed corpus  
9. Source proportions reported  
10. No modification of processed corpus text  

## Layout

```text
data/splits/chichewa_corpus_v0.1/
├── train/{bible,wikipedia,combined}.txt
├── validation/{bible,wikipedia,combined}.txt
├── test/{bible,wikipedia,combined}.txt
├── metadata/
│   ├── train_documents.jsonl
│   ├── validation_documents.jsonl
│   ├── test_documents.jsonl
│   ├── checksums.json
│   ├── split_assignments.jsonl
│   ├── split_manifest.json
│   └── FROZEN_SPLIT.json
└── README.md
```

## How to build

```bash
python3 scripts/data/build_corpus_splits.py \
  --config configs/data/split_v0_1.json
```

```bash
python3 scripts/data/validate_corpus_splits.py \
  --config configs/data/split_v0_1.json
```

### Frozen policy

* Split version **v0.1** is frozen after successful generation.  
* Re-running the builder **refuses** to overwrite.  
* Prefer a **new version path** (e.g. `split_v0_2`) rather than `--force-new-version`.  

## Assignment method

For each group_id:

```text
digest = SHA256("{salt}|{group_id}")
bucket = uint64(digest[:8]) % 10000
```

* train: `[0, 8000)`  
* validation: `[8000, 9000)`  
* test: `[9000, 10000)`  

If exact or normalized line collisions would cross splits, non-train groups involved are **reassigned to train** (whole group moves).

## Evaluation integrity

| Stage | Allowed use |
|-------|-------------|
| `train/` | Tokenizer training, vocabulary, model training |
| `validation/` | Model selection / early stopping only |
| `test/` | Final comparison only |
| Morphology rules | Train + separate dev resources — **not test** |

* Raw perplexity is **not** directly comparable across tokenizers.  
* Primary cross-tokenizer metric: **bits per character** or **bits per byte**.  
* FLORES / other external benchmarks stay **outside** these splits.  

## Reports and manifests

* `data/reports/split_v0_1_report.md`  
* `data/metadata/split_v0_1_manifest.json`  
* Config: `configs/data/split_v0_1.json`  

## Safety

* Do not modify `data/processed/chichewa_corpus_v0.1/`.  
* Do not unlock cleaning holdouts for split design.  
* Do not train tokenizers/models as part of split construction.  
