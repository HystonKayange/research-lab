# Morphology benchmark v0.1 — development annotation set

This set is **released for human review**.

## Important

- `human_*` fields are **null** until annotated.
- `candidate_strata` / `automatic_tags` are **hypotheses**, not gold morphology.
- Do **not** treat recurring strings as morphemes without annotator confirmation.
- Support **disagreement** and `alternative_analysis`.
- The locked holdout is **not** included here.

- Items: **200**
- Primary source split: **train**

## Files

- `annotation_candidates.jsonl` — full machine-readable records
- `annotation_template.csv` — spreadsheet-friendly template

## Annotation fields

| field | meaning |
|-------|---------|
| human_segments | space- or `+`-separated segments (annotator) |
| human_phenomenon_tags | verified phenomenon tags |
| alternative_analysis | competing segmentation if disagreement |
| uncertain | true if annotator unsure |
| confidence | 1–5 optional |
| adjudication_status | unreviewed / annotated / adjudicated |

## Category distribution (candidate strata counts; multi-label)

- `rare_word`: 159
- `unseen_or_low_frequency`: 148
- `apparent_singular_plural_contrast`: 120
- `bpe_unigram_disagreement`: 110
- `apparent_subject_or_agreement_prefix`: 96
- `apparent_noun_class_contrast`: 73
- `apparent_object_marking`: 65
- `long_agglutinative_looking`: 52
- `apparent_derivational_suffix`: 50
- `apparent_locative`: 20
- `apparent_negation`: 19
- `apparent_tense_aspect`: 16
- `mixed_language_form`: 16
- `apparent_whole_word_memorization`: 14
- `frequent_word_family`: 13
- `contains_w_hat`: 12

## Pilot (40 items)

For the dual-annotator pilot before full 200-item annotation:

- `pilot_40.jsonl`
- `pilot_40_annotator_a.csv` / `pilot_40_annotator_b.csv`
- `PILOT_README.md`
- Guidelines: `docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md`
- Offline UI: `scripts/tokenizers/morphology_annotation_ui.py`
- Agreement: `scripts/tokenizers/measure_morphology_annotation_agreement.py`
- Adjudication: `scripts/tokenizers/adjudicate_morphology_annotations.py`

## Safety

- LM test split not used
- Locked morphology holdout not included
- No fake gold morphology
