# Promotion dry-run report

**Status:** `ok`
**Promotion allowed:** True
**Primary reason:** None
**Redistribution mode (planned):** `exportable`
**Local training permitted (any eligible):** True
**Redistribution permitted (all eligible):** True

## Eligible sources

- `bible` → input `data/interim/cleaning_v2/bible/cleaned.txt` output `bible.txt`
- `wikipedia` → input `data/interim/cleaning_v2/wikipedia/cleaned.txt` output `wikipedia.txt`

## Blocked sources

### `existing_corpus`
- source marked redundant
- source marked excluded
- technical_status is redundant_composite
- include_in_processed_corpus is false

## Blocking reasons (aggregate)


## Unresolved fields


## Expected output paths

- corpus root: `data/processed/chichewa_corpus_v0.1`
- text subdir: `corpus`
- source text: `corpus/bible.txt` (bible)
- source text: `corpus/wikipedia.txt` (wikipedia)
- readme: `README.md`
- corpus_card: `reports/CORPUS_CARD.md`
- cleaning_summary: `reports/cleaning_summary.md`
- known_limitations: `reports/known_limitations.md`
- documents: `metadata/documents.jsonl`
- sources: `metadata/sources.json`
- checksums: `metadata/checksums.json`
- build_manifest: `metadata/build_manifest.json`
- deduplication_log: `metadata/deduplication_log.jsonl`
- deduplication_report: `reports/deduplication_report.md`
- eligibility_snapshot: `metadata/eligibility_snapshot.json`

## Planned input checksums

- `input:bible`: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- `input:wikipedia`: `69aac9abb9bc79e713b3d5d769f149aaaddda9fea9225b6ef554cb2ed7a99e0b`
