# AI Annotator B — blinded pilot instructions

## Role

You are **Annotator B** for the Chichewa morphology **pilot** (40 items).

You work **independently**. You must **not** see or request:

- Annotator A answers
- BPE / Unigram tokenizations
- automatic tags or failure diagnostics
- suggested segmentations
- adjudicated references
- locked morphology holdout
- LM test data

## Materials in this bundle

| File | Use |
|------|-----|
| `MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md` | Full annotation rules |
| `pilot_40_blinded.jsonl` | 40 items (blinded fields only) |
| `bundle_manifest.json` | Provenance / integrity |

## Output

Create **one** file (do not overwrite the blinded input):

`annotator_b_annotations.jsonl`

Each line is one JSON object with at least:

```json
{
  "item_id": "morph_dev_....",
  "surface_form": "...",
  "context": "...",
  "source": "...",
  "proposed_segmentation": "piece1+piece2",
  "alternative_segmentation": null,
  "boundary_positions": null,
  "phenomenon_tags": [],
  "no_segmentation_required": false,
  "mixed_language": false,
  "spelling_or_ocr_issue": false,
  "insufficient_context": false,
  "uncertain": false,
  "confidence": null,
  "annotator_id": "annotator_b",
  "notes": null
}
```

Rules:

- `proposed_segmentation` uses `+` between pieces; pieces must concatenate to `surface_form` (unless OCR/uncertain noted).
- You may leave segmentation empty and set `no_segmentation_required` / `uncertain` / `unresolved_analysis` tag.
- Names and non-Chichewa forms: whole surface + `non_chichewa_or_mixed`.
- Do **not** invent gold for every item if unsure.

## Allowed phenomenon tags

See guidelines §5. Prefer listed tags only.

## Independence

- Do not search for Annotator A outputs in the repository.
- Do not open `annotator_a_annotations.*` or `pilot_chat_state.json`.
- Do not open `data/research/morphology_benchmark_v0.1/locked/`.
- Do not open LM test splits.

## Completion

Annotate all 40 `item_id`s exactly once, then stop.  
Agreement measurement and adjudication are **out of scope** for Annotator B.
