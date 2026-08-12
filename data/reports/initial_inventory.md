# Initial inventory report

**Generated:** 2026-08-04 (organization pass)  
**Repository:** `transformer-lab`  
**Scope:** Structure, source organization, metadata, checksums only  
**Status:** **No cleaning, normalization, deduplication, merging, splitting, tokenization, or training was performed.**

---

## 1. Existing sources

Three local text files were found under the legacy directory `Data/` and migrated byte-for-byte into `data/raw/`:

| source_id | source_name | relative path | domain |
|-----------|-------------|---------------|--------|
| `bible` | Chichewa Bible | `data/raw/bible/bible_clean.txt` | religion |
| `wikipedia` | Chichewa Wikipedia | `data/raw/wikipedia/wiki_clean.txt` | general_knowledge |
| `existing_corpus` | Existing Chichewa Corpus | `data/raw/existing_corpus/chichewa_corpus.txt` | mixed |

Machine-readable registry: `data/metadata/sources.jsonl`.

---

## 2. File sizes

| file | size (bytes) | size (approx.) |
|------|-------------:|----------------|
| `bible_clean.txt` | 4,218,603 | 4.02 MiB |
| `chichewa_corpus.txt` | 6,103,844 | 5.82 MiB |
| `wiki_clean.txt` | 1,938,045 | 1.85 MiB |
| **Total** | **12,260,492** | **~11.69 MiB** |

---

## 3. Line counts

Line count is defined as the number of `\n` bytes (equivalent to `wc -l`).

| file | lines |
|------|------:|
| `bible_clean.txt` | 31,099 |
| `chichewa_corpus.txt` | 50,752 |
| `wiki_clean.txt` | 20,579 |
| **Total** | **102,430** |

All three files end with a trailing newline. Line endings are Unix LF only (no CRLF observed).

---

## 4. Character counts

Character count is the length of the UTF-8-decoded Unicode string (`len(text)`).

| file | characters | bytes | multi-byte overhead |
|------|----------:|------:|--------------------:|
| `bible_clean.txt` | 4,172,215 | 4,218,603 | 46,388 |
| `chichewa_corpus.txt` | 6,047,673 | 6,103,844 | 56,171 |
| `wiki_clean.txt` | 1,928,043 | 1,938,045 | 10,002 |
| **Total** | **12,147,931** | **12,260,492** | **112,561** |

Multi-byte overhead is expected for Chichewa orthography (e.g. characters such as ŵ).

---

## 5. Checksums (SHA-256)

| file | sha256 |
|------|--------|
| `bible_clean.txt` | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` |
| `chichewa_corpus.txt` | `32e65edccb4c341d45e55de3d35edc1dd8768cd6e47cfafeb22d21216c2c8932` |
| `wiki_clean.txt` | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` |

These values were recorded **before** migration from `Data/` and verified **after** copy into `data/raw/` (byte-identical `cmp` and matching SHA-256).

---

## 6. Encoding findings

| file | `file -bi` | detected encoding |
|------|------------|-------------------|
| `bible_clean.txt` | `text/plain; charset=utf-8` | utf-8 |
| `chichewa_corpus.txt` | `text/plain; charset=utf-8` | utf-8 |
| `wiki_clean.txt` | `text/plain; charset=utf-8` | utf-8 |

- No UTF-8 BOM detected.
- No null bytes (`\x00`) detected.
- Wikipedia and existing corpus files contain very long lines (on the order of ~500+ characters), flagged by the `file` utility; not an error.

---

## 7. Total corpus size

| metric | value |
|--------|------:|
| Files | 3 |
| Bytes | 12,260,492 |
| Lines | 102,430 |
| Characters | 12,147,931 |

Canonical machine-readable totals: `data/metadata/inventory.json` → `totals`.

---

## 8. Missing provenance or licensing information

For **all three** sources, the following fields are unresolved in `sources.jsonl`:

| field | current value |
|-------|---------------|
| `license` | `"unknown"` |
| `source_url` | `null` |
| `collection_date` | `null` |
| `allowed_for_training` | `null` |

No licenses, upstream URLs, dump dates, or training-eligibility decisions were invented. These require human verification before any production training run.

---

## 9. Suspicious issues observed during inspection

None that indicate corruption. Observations only:

1. **Filenames suggest prior cleaning** (`bible_clean.txt`, `wiki_clean.txt`) — the “raw” tier still freezes whatever was on disk; original uncleaned dumps are not present in the repository.
2. **`chichewa_corpus.txt` composition is opaque** — mixed domain; may overlap with Bible or Wikipedia text (overlap not measured; no deduplication run).
3. **Legacy path `Data/`** (capital D) conflicted with the canonical lowercase `data/` layout; content was copied then the legacy directory was removed after checksum verification.
4. **Repository had no prior data conventions**, scripts, configs, or tests for corpora — these were added in this pass.
5. **Long lines** in Wikipedia and existing corpus may affect naive line-based sampling later; noted only, not changed.

---

## 10. Transformation statement

> **No cleaning or transformation was performed.**  
> Files under `data/raw/` are byte-identical to the originals that lived under `Data/`.  
> This pass created directory structure, metadata, inventory, documentation, and a reproducibility script only.

Regenerate inventory:

```bash
python scripts/data/build_inventory.py \
  --raw-dir data/raw \
  --output data/metadata/inventory.json
```
