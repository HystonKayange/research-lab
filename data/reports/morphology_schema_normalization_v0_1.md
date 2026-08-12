# Morphology schema normalization v0.1

_Generated 2026-08-11T08:30:30.163729Z_

## Purpose

Schema-only normalization of the **reviewed** Annotator A development set.
**No human segmentation decisions were changed.**

## Inputs (untouched)

- Reviewed: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200_reviewed_v0_1.jsonl` (sha256 `7f6d0190e30ddd3d…`)
- Immutable original: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200.jsonl` (sha256 `d0d672e18819f4fa…`)

## Outputs

1. Canonical 200: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200_canonical_v0_1.jsonl`
2. Active 195: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl`
3. Report JSON: `data/reports/morphology_schema_normalization_v0_1.json`
4. Report MD: `data/reports/morphology_schema_normalization_v0_1.md`

## Counts

| Set | n |
|---|---:|
| Canonical (all reviewed) | 200 |
| Active (`excluded=false`) | 195 |
| Excluded (`excluded=true`) | 5 |

### Excluded item IDs

- `morph_dev_0095` · `tursk`
- `morph_dev_0097` · `Clairol`
- `morph_dev_0117` · `lmmaculate`
- `morph_dev_0133` · `trompe-l'œil`
- `morph_dev_0176` · `Achikaladi`

## Confidence normalization

### Pre-normalization inventory

| value | count |
|---|---:|
| `int:4` | 107 |
| `str:'high'` | 59 |
| `int:5` | 25 |
| `int:3` | 6 |
| `int:2` | 2 |
| `str:'low'` | 1 |

### Policy

Guidelines (MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md) define confidence as Likert 1–5. Integer values 1–5 are accepted as confidence_canonical. Chat-workflow strings 'high'/'low' are NOT defined in guidelines and do not map unambiguously onto 1–5 (high could be 4 or 5; low could be 1 or 2). No silent mapping: confidence_raw preserved; confidence_canonical=null for those rows.

Canonical representation:

- `confidence_raw` — original stored value (int or string)
- `confidence_canonical` — integer 1–5 if unambiguous Likert; else `null`
- legacy dual-type field `confidence` **removed** from canonical/active schema

### Status counts

| status | count |
|---|---:|
| `likert_int` | 140 |
| `unresolved_string_high_low_ambiguous` | 60 |

- `confidence_canonical` set: **140**
- `confidence_canonical` null: **60**
- unresolved (no silent map): **60**

### Unresolved confidence cases (first 15)

| item_id | confidence_raw | status |
|---|---|---|
| morph_dev_0125 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0126 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0127 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0128 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0129 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0130 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0133 | 'low' | unresolved_string_high_low_ambiguous |
| morph_dev_0134 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0136 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0137 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0139 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0140 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0141 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0142 | 'high' | unresolved_string_high_low_ambiguous |
| morph_dev_0143 | 'high' | unresolved_string_high_low_ambiguous |
| … | (45 more; see JSON) | |

Full unresolved ID list (60): see `confidence.unresolved_all_item_ids` in the JSON report.

## Tokenizer provenance fields

Removed from canonical and active rows (still present in reviewed/original sources):

- `bpe_tokens` (present on 40 reviewed rows before strip)
- `unigram_tokens` (present on 40 reviewed rows before strip)
- `automatic_tags` (present on 40 reviewed rows before strip)
- `candidate_strata` (present on 40 reviewed rows before strip)
- `tokenizer_hints_shown` (present on 160 reviewed rows before strip)

**No BPE/Unigram fields remain in the active morphology benchmark.**

## Preserved linguistic / review fields

- `item_id`, `surface_form`, `context`, `source`
- `proposed_segmentation`, `alternative_segmentation`, `boundary_positions`
- `uncertain`, `mixed_language`, `spelling_or_ocr_issue`, `insufficient_context`
- `no_segmentation_required`, `phenomenon_tags`, `notes`
- `excluded` (explicit boolean), `human_review` metadata
- `annotator_id`, partition/provenance non-tokenizer fields

## WHOLE statistics rule

- Active-195 WHOLE count: **36** (use this for benchmark stats)
- Canonical-200 WHOLE including excluded surfaces: 41
- Excluded items with WHOLE surface: 5
- Excluded items **must not** enter morphology evaluation or self-consistency sampling.

## Self-review 25

- Previous set overlapped excluded IDs: **['morph_dev_0117']**
- Action: **regenerated_from_active_195**
- Archive: `data/research/morphology_benchmark_v0.1/development/archive/self_review_25_blinded_pre_exclude_filter_v0_1.jsonl`
- Seed: `self_review_v0_1_annotator_a`
- Method: `stable_pick` — sort active IDs by `sha256(f"{seed}:{id}")`, take first 25
- Blinded fields only: `item_id`, `surface_form`, `context`, `source`
- Original annotations **not** revealed in the blinded file
- Final self-review contains excluded IDs: **false**

## Reconstruction

- Failures (active): **0**
- Failures (canonical all): **0**

## Validation checklist

| Check | Status |
|---|---|
| canonical_rows_200 | **True** |
| active_rows_195 | **True** |
| excluded_rows_5 | **True** |
| unique_ids_ok | **True** |
| recon_active_ok | **True** |
| no_tokenizer_fields_active | **True** |
| no_excluded_in_self_review | **True** |
| sources_untouched | **True** |
| morphology holdout accessed | **false** |
| LM test evaluations | **0** |
| MthandiziTokenizer implemented | **false** |
| human labels altered | **false** |

## Concise completion

- canonical rows: **200**
- active rows: **195**
- excluded rows: **5**
- reconstruction failures (active): **0**
- confidence unresolved (no silent map): **60**
- self-review action: **regenerated_from_active_195**
- sources untouched: **true**
