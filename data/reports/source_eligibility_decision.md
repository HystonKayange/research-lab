# Source eligibility decision record

**Status:** pending human review  
**Schema:** `data/metadata/source_eligibility.json`  
**Rule:** Do not invent licenses, provenance, or training/redistribution permissions.

These states are **separate**:

1. Technically cleaned  
2. Legally / provenance reviewed  
3. Approved for training  
4. Approved for redistribution  

Promotion to `data/processed/` requires explicit human decisions in the eligibility JSON.
Technical cleaning quality alone does **not** approve training use.

## Decision table

| Source | Exact origin | License verified | Training allowed | Redistribution allowed | Attribution required | Include in processed corpus | Decision evidence |
| ------ | ------------ | ---------------: | ---------------: | ---------------------: | -------------------: | --------------------------: | ----------------- |
| bible | eBible `nya` / Biblica TCCl; `nya_vpl.zip` (archive not retained) | verified CC BY-SA 4.0 | true | true (with notices) | true | **true** | eBible details page 2026-08-05; reviewer Hyston Kayange |
| wikipedia | Chichewa Wikipedia `nywiki` pages-articles; moving `/latest/` URL | verified CC BY-SA 4.0 | true | true (with notices) | true | **true** | Wikimedia ToU + dump URL; dump SHA not retained; reviewer Hyston Kayange |
| existing_corpus | local composite | n/a independent | **false** | **false** | n/a | **false** (redundant composite) | Residual analysis: 0 unique non-blank lines after Bible+Wikipedia subtraction |

## Known technical status (not legal approval)

| Source | Technical status | Notes |
| ------ | ---------------- | ----- |
| bible | light-touch clean under current rules | Interim output under Bible cleaning path; raw checksum verified against inventory when promoting |
| wikipedia | Cleaning Policy v2 selected technical candidate | Holdout Stage 1+2 provisional metrics strong; v2 must not be retuned on holdout |
| existing_corpus | `redundant_composite` | Must not be included as an independent processed source |

## Reviewer checklist (per source)

- [ ] Confirm exact translation or dump (edition / dump date / language code)
- [ ] Confirm original download location (URL, archive, or internal path)
- [ ] Confirm copyright holder
- [ ] Confirm license text (and keep a copy of the license document)
- [ ] Confirm whether model training is allowed
- [ ] Confirm whether derived weights may be distributed
- [ ] Confirm whether cleaned text may be redistributed
- [ ] Confirm required attribution (and exact attribution string if any)
- [ ] Record evidence location (path or URL to license / dump notice)
- [ ] Record reviewer name/handle and ISO date
- [ ] Update `data/metadata/source_eligibility.json` with explicit values only

## How to record decisions

Edit `data/metadata/source_eligibility.json` for each source:

| Field | Allowed values |
| ----- | -------------- |
| `provenance_status` | `pending` \| `verified` \| `rejected` |
| `license_status` | `pending` \| `verified` \| `rejected` |
| `allowed_for_training` | `true` \| `false` \| `null` |
| `allowed_for_redistribution` | `true` \| `false` \| `null` |
| `attribution_required` | `true` \| `false` \| `null` |
| `include_in_processed_corpus` | `true` \| `false` \| `null` |
| `source_url`, `license_name`, `license_url` | string or `null` |
| `reviewed_by`, `reviewed_at`, `evidence_notes` | string or `null` |

**Do not** set unresolved fields to `true`.

## Promotion gates (summary)

Promotion (`scripts/data/promote_processed_corpus.py`) refuses unless every
**included** source has:

* `provenance_status == verified`
* `license_status == verified`
* `allowed_for_training == true`
* `include_in_processed_corpus == true`
* technical cleaning output present with matching checksums
* raw inventory checksum match
* cleaning config checksum match
* not redundant / excluded / holdout-only

Redistribution is separate: `allowed_for_redistribution == true` enables an
exportable corpus layout; `false` or `null` restricts to a local non-redistribution
artifact directory (training use may still be allowed if training is explicitly true).

## Unresolved human information required to unblock promotion

For **bible** and **wikipedia** at minimum:

1. Exact origin / dump or translation identity  
2. License name + license text URL or local copy  
3. Explicit yes/no for model training  
4. Explicit yes/no for redistribution of cleaned text  
5. Attribution requirements  
6. Reviewer identity and review timestamp  
7. `include_in_processed_corpus: true` only after the above are verified  

Until then, dry-run and real promotion must report **blocked**.
