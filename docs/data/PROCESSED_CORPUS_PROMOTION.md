# Processed corpus promotion (license-gated)

## Purpose

Promote **technically cleaned** interim outputs into a **versioned processed corpus**
only after explicit human eligibility decisions. No source is auto-approved for training.

## Separate states

| State | Meaning |
|-------|---------|
| Technically cleaned | Interim cleaner ran; checksums match |
| Legally / provenance reviewed | Human verified origin and license |
| Approved for training | `allowed_for_training: true` |
| Approved for redistribution | `allowed_for_redistribution: true` |

These are independent. Cleaning quality ≠ legal permission.

## Eligibility file

Path: `data/metadata/source_eligibility.json`

Human review worksheet: `data/reports/source_eligibility_decision.md`

### Allowed values

| Field | Values |
|-------|--------|
| `provenance_status`, `license_status` | `pending` \| `verified` \| `rejected` |
| `allowed_for_training`, `allowed_for_redistribution`, `attribution_required`, `include_in_processed_corpus` | `true` \| `false` \| `null` |

**Do not** set unresolved fields to `true`.

### How to fill

1. Complete the checklist in `source_eligibility_decision.md`.
2. Set provenance and license statuses to `verified` only with evidence.
3. Set training / redistribution / attribution booleans explicitly.
4. Set `include_in_processed_corpus: true` only for sources that should enter the build.
5. Record `reviewed_by`, `reviewed_at`, and `evidence_notes`.

### Why `existing_corpus` is excluded

It is a **redundant composite** of Bible and Wikipedia content (measured duplication).
`include_in_processed_corpus` is `false` and `technical_status` is `redundant_composite`.
This exclusion is technical, not a licensing conclusion.

## Training vs redistribution

* **Training true, redistribution false/null**  
  Local restricted artifact under `corpus_restricted_local/` with a non-redistribution notice.  
  Local experimentation is not blocked solely by redistribution=false.

* **Training false or null**  
  Promotion is **blocked** for that source (and overall if no eligible sources remain).

* **Redistribution true** (all included sources)  
  Exportable layout under `corpus/`.

## Config

* Promotion: `configs/data/promotion_v0_1.json`
* Deduplication: `data/metadata/deduplication_policy_v0_1.json`

## Dry-run

```bash
python3 scripts/data/promote_processed_corpus.py \
  --config configs/data/promotion_v0_1.json \
  --eligibility data/metadata/source_eligibility.json \
  --dry-run
```

Dry-run reports:

* sources eligible / blocked and exact reasons  
* expected inputs and output paths  
* planned checksums  
* redistribution and local-training permission  
* **does not** copy or modify corpus content  

Exit code `2` when blocked.

## Real promotion

```bash
python3 scripts/data/promote_processed_corpus.py \
  --config configs/data/promotion_v0_1.json \
  --eligibility data/metadata/source_eligibility.json
```

Runs only when **all** gates pass for every included source.

### Minimum gates

* provenance verified  
* license verified  
* allowed_for_training true  
* include_in_processed_corpus true  
* technical cleaning output exists  
* technical output checksum matches interim summary  
* raw checksum matches inventory  
* cleaning config checksum matches expected validated version  
* not redundant / excluded / holdout-only  

## Output layout

```text
data/processed/chichewa_corpus_v0.1/
├── corpus/                         # or corpus_restricted_local/
│   ├── bible.txt
│   └── wikipedia.txt
├── metadata/
│   ├── documents.jsonl
│   ├── sources.json
│   ├── checksums.json
│   ├── build_manifest.json
│   ├── eligibility_snapshot.json
│   └── deduplication_log.jsonl
├── reports/
│   ├── CORPUS_CARD.md
│   ├── cleaning_summary.md
│   ├── known_limitations.md
│   └── deduplication_report.md
└── README.md
```

Source boundaries are preserved (no single anonymous merge file).

## Deduplication (v0.1)

* Exact **within-source** dedup: configurable (default on)  
* Exact **cross-source** dedup: configurable (default off)  
* Source priority default: `bible`, then `wikipedia`  
* Cross-source drops retain multi-source attribution in the dedup log  
* **No** MinHash, embeddings, or fuzzy near-dedup  

Do not run processed-level dedup on real data until eligibility gates pass.

## Blocking conditions (examples)

* Any included source with `pending` provenance or license  
* `allowed_for_training` null or false  
* `include_in_processed_corpus` null or false for intended sources  
* Checksum mismatches (raw, cleaned, cleaning config)  
* Missing interim outputs  
* Attempt to include redundant/excluded sources  
* Output directory already exists  

## Rollback / removal

Processed corpora are disposable packaging of interim outputs:

1. Delete the versioned directory, e.g. `data/processed/chichewa_corpus_v0.1/`.  
2. Do **not** delete `data/raw/` or interim cleaning outputs unless intentionally reprocessing.  
3. Eligibility decisions remain in `data/metadata/source_eligibility.json`.  
4. Re-run dry-run then promote after decisions change.  

Never “fix” a promotion by editing files inside a published version in place; cut a new version string instead.

## Safety constraints

* Do not modify `data/raw/`.  
* Do not modify Cleaning Policy v2 to pass promotion.  
* Do not invent licenses.  
* Do not create train/val/test splits in this pipeline.  
* Do not train tokenizers or models as part of promotion.  

## Implementation

| Component | Path |
|-----------|------|
| Promoter | `scripts/data/promote_processed_corpus.py` |
| Config | `configs/data/promotion_v0_1.json` |
| Eligibility | `data/metadata/source_eligibility.json` |
| Dedup policy | `data/metadata/deduplication_policy_v0_1.json` |
| Tests | `tests/test_promote_processed_corpus.py` |
