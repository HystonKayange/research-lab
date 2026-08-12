# Split report — chichewa_corpus v0.1 / split v0.1

_Generated at 2026-08-05T04:09:01.057702Z by build_corpus_splits 0.1.0_

## 1. Methodology

- Volume metric: Unicode character counts (not tokenizer-dependent).
- Target proportions: train=0.8, validation=0.1, test=0.1.
- Assignment: `sha256_group_hash` with salt `chichewa_corpus_v0.1_split_v0.1` and modulus 10000.
- Assignment does **not** use Python's built-in `hash()`.
- Source files written separately; `combined.txt` concatenates sources in fixed order: ['bible', 'wikipedia'].

## 2. Grouping strategy by source

- Global strategy: `contiguous_char_blocks`
- Target group size: ~5000 Unicode characters

### bible

- Preferred: `book_or_chapter`
- Used: `contiguous_char_blocks`
- Limitation: VPL book/chapter/verse markers were stripped before or during raw placement; processed bible.txt is sequential verse-like lines without recoverable identifiers.

### wikipedia

- Preferred: `article_document`
- Used: `contiguous_char_blocks`
- Limitation: Article boundaries were not retained through extraction/cleaning; documents.jsonl has no article IDs; no blank-line document separators remain.

## 3. Limitations

- No Bible book/chapter/verse identifiers in processed text.
- No Wikipedia article/document boundaries in processed text or documents.jsonl.
- documents.jsonl entries are line-level (source_id:line_index) only.
- Contiguous character blocks used as safest reproducible grouping without inventing metadata.
- Contiguous blocks reduce adjacent-verse / adjacent-line leakage risk but are **not** recovered Bible chapters or Wikipedia articles.
- Formulaic religious phrasing may share n-gram shingles across splits without exact-line leakage.

## 4. Split sizes by source

### train

- Totals: groups=911, lines=37248, words=642903, characters=4623799, bytes=4666553
- `bible`: groups=644, lines=24433, words=453692, characters=3267529, bytes=3304081
- `wikipedia`: groups=267, lines=12815, words=189211, characters=1356270, bytes=1362472

### validation

- Totals: groups=125, lines=5258, words=88843, characters=634509, bytes=640766
- `bible`: groups=90, lines=3430, words=63497, characters=457231, bytes=462232
- `wikipedia`: groups=35, lines=1828, words=25346, characters=177278, bytes=178534

### test

- Totals: groups=124, lines=5068, words=88142, characters=631030, bytes=637246
- `bible`: groups=79, lines=3013, words=56119, characters=401536, bytes=406269
- `wikipedia`: groups=45, lines=2055, words=32023, characters=229494, bytes=230977

## 5. Character and word distributions

- **train:** characters=4623799 (0.7851), words=642903
- **validation:** characters=634509 (0.1077), words=88843
- **test:** characters=631030 (0.1071), words=88142

## 6. Group/document counts

- Total groups: 1160
- Grouping unit: contiguous character blocks (source_document_id == group_id)

## 7. Exact overlap checks

- Exact cross-split non-empty lines: **0**
- Reassignments for exact conflicts: 0

## 8. Normalized overlap checks

- Normalization: `unicode_nfc_whitespace_collapse_strip`
- Normalized cross-split non-empty lines after resolution: **0**
- Reassignments for normalized conflicts: 0

## 9. Optional shingle diagnostics

- Enabled: True
- Shingle size: 5
- Note: Diagnostic only. High overlap may reflect formulaic religious language rather than exact-line leakage. No fuzzy matches are removed.

- train vs test: jaccard=0.004033, intersection=2866, |A|=626773, |B|=86673
- train vs validation: jaccard=0.003109, intersection=2215, |A|=626773, |B|=87971
- validation vs test: jaccard=0.001479, intersection=258, |A|=87971, |B|=86673

### Formulaic repetition (separate from leakage)

Prefix-frequency diagnostic for formulaic phrasing. Exact full-line duplicates were removed at corpus promotion within sources.

## 10. Corpus reconciliation

- Input lines: 47574
- Output lines (all splits): 47574
- Match: True
- Input characters: 5889338
- Output characters: 5889338

## 11. Checksums

- Config SHA-256: `89ebdbb1ffb32f86f87b25b598cfe03780bfdc38f0b8d07a20000d90a4fac5e4`
- Processed corpus build_manifest SHA-256: `99045afafc9217378b8fed4036010b928084a6f02e7a1a8f14671d581a245c2b`
- Split output root: `data/splits/chichewa_corpus_v0.1`
- See `metadata/checksums.json` inside the split directory.

## 12. Frozen-split declaration

- **Frozen:** `True`
- Split version: `v0.1`
- Corpus version: `v0.1`
- Created at: `2026-08-05T04:09:01.057702Z`
- Git commit: `None`
- Do not overwrite in place. Use a new version path + `--force-new-version` only when intentionally replacing policy.

## 13. Rules for future tokenizer experiments

- Train tokenizers **only** on `train/`.
- Vocabulary selection **only** from `train/`.
- Morphological-rule development may use train + separate development resources; **never test text**.
- Validation may guide model selection / early stopping.
- Test is for **final comparison only**.
- Raw perplexity is **not** directly comparable across tokenizers.
- Primary cross-tokenizer LM metric: **bits per character** or **bits per byte**.
- External benchmarks (e.g. FLORES) remain **separate** from these corpus splits.
