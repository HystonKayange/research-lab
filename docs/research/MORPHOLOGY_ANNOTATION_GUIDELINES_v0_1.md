# Morphology annotation guidelines v0.1

**Benchmark:** Chichewa morphology development set (`morphology_benchmark_v0.1`)  
**Pilot:** 40-item stratified subset of the development set  
**Not included:** locked morphology holdout; LM test set  

These guidelines support careful human annotation, alternative analyses, and uncertainty flags.

**Current research phase (v0.1 development):** a **single native Chichewa annotator** (`annotator_a`).  
There is **no human–human IAA claim** in this phase. Dual annotation remains **future work**.  
Any human–AI co-pilot session is **exploratory only** and is **not** gold.

---

## 1. Purpose

Collect **human judgments** about possible morphological structure of Chichewa surface forms in context, so that:

1. automatic BPE/Unigram failure analysis can be calibrated;
2. boundary and phenomenon metrics can be computed later;
3. method design is constrained by evidence, not by automatic tags alone.

**Automatic candidate tags are not gold.** Treat them as optional hints that may be wrong.

---

## 2. What you are **not** required to do

- You are **not** required to force a morpheme segmentation for every item.
- You are **not** required to agree with BPE or Unigram.
- You are **not** required to invent fine-grained morphosyntactic glosses.
- You must **not** open or annotate the locked holdout.
- You must **not** invent confident labels when unsure.

---

## 3. Materials

| File | Role |
|------|------|
| `pilot_40.jsonl` | Pilot items (source records) |
| `pilot_40_annotator_a.csv` / `_b.csv` | Independent annotator worksheets |
| `annotation_candidates.jsonl` | Full 200-item development set (later) |
| Local annotator UI (optional) | `scripts/tokenizers/morphology_annotation_ui.py` |

Each source item is preserved. Your annotations are stored separately or in dedicated fields.

---

## 4. Annotation fields

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | string | Stable ID (do not change) |
| `surface_form` | string | Form as in corpus (do not edit unless noting OCR issue) |
| `context` | string | Short context line |
| `proposed_segmentation` | string | Preferred analysis, segments joined by `+` (e.g. `ndi+ma+konda`) |
| `alternative_segmentation` | string | Second plausible analysis, or empty |
| `boundary_positions` | string | Optional: character offsets after which a boundary falls, comma-separated (0-based after chars). If empty, derived from proposed_segmentation |
| `phenomenon_tags` | string | Pipe-separated tags from the allowed list below |
| `no_segmentation_required` | true/false/empty | True if form should stay unsegmented for LM tokenization purposes |
| `mixed_language` | true/false/empty | Non-Chichewa or clearly mixed form |
| `spelling_or_ocr_issue` | true/false/empty | Apparent spelling/OCR/encoding issue |
| `insufficient_context` | true/false/empty | Context too thin to decide |
| `uncertain` | true/false/empty | Annotator uncertain about preferred analysis |
| `confidence` | 1–5 or empty | Subjective confidence in preferred analysis |
| `annotator_id` | string | e.g. `annotator_a` |
| `notes` | string | Free text |

Boolean fields: use `true` / `false` (case-insensitive) or `1` / `0`. Leave empty if not applicable.

---

## 5. Allowed phenomenon tags

Use only these (pipe-separated). Multiple allowed.

| Tag | Meaning |
|-----|---------|
| `no_meaningful_segmentation` | No useful morphological split for our purposes |
| `uncertain_segmentation` | Segmentation attempted but doubtful |
| `multiple_plausible_analyses` | More than one defensible split |
| `insufficient_context` | Need more context (also set boolean) |
| `non_chichewa_or_mixed` | Foreign / mixed form |
| `spelling_or_ocr_issue` | Surface may be corrupt |
| `apparent_inflectional_boundary` | Inflection-like boundary (agreement, TA, etc.) — **apparent** |
| `apparent_derivational_boundary` | Derivational-like boundary — **apparent** |
| `apparent_stem_or_root` | A segment is judged to be a stem/root candidate |
| `unresolved_analysis` | Could not resolve; leave segmentation empty or partial |
| `apparent_prefix` | Prefix-like material (not gold gloss) |
| `apparent_suffix` | Suffix-like material |
| `locative_like` | Locative-like pattern (apparent) |
| `negation_like` | Negation-like pattern (apparent) |
| `noun_class_like` | Noun-class-like contrast (apparent) |
| `other` | Use notes |

Language in tags is deliberately cautious (**apparent**). Do not claim dictionary-grade morphology unless you are certain.

---

## 6. Segmentation conventions

1. **Join segments with `+` only** (no spaces inside a segment).  
   Example: `ndi+ma+konda` reconstructs to `ndimakukonda` only if those pieces concatenate exactly to the surface (case-sensitive as written).

2. **Surface reconstruction check:**  
   `"".join(segments)` must equal `surface_form` **unless** you mark `spelling_or_ocr_issue` or `uncertain` and explain in notes.

3. **Do not** insert orthographic hyphens that are not in the surface unless they appear in the form.

4. **Whole-word option:** set `no_segmentation_required=true` and leave `proposed_segmentation` empty **or** set segmentation to the full surface as a single piece.

5. **Alternative analysis:** if two splits are plausible, put the preferred in `proposed_segmentation` and the other in `alternative_segmentation`, and tag `multiple_plausible_analyses`.

6. **Boundary positions (optional):** for surface `abcde` with split `ab+cde`, boundaries = `2` (after index 2). Multiple: `2,4`.

7. **Granularity (self-review / adjudication):** Add a boundary only when there is a defensible grammatical, inflectional, derivational, or reusable lexical morphological function. Do not split merely because a substring is pronounceable, syllabic, or can be decomposed into smaller character chunks. When two analyses are linguistically plausible and there is no strong evidence for the finer analysis, prefer the coarser segmentation.

   This is a **human review principle**, not an automatic segmentation algorithm. It is **not** applied retroactively by software.

---

## 7. Decision flowchart (summary)

```
Is the form clearly non-Chichewa / mixed?
  → mixed_language=true, tag non_chichewa_or_mixed; optional minimal split

Is the form likely OCR/spelling damage?
  → spelling_or_ocr_issue=true; do not force morphology

Is context too thin?
  → insufficient_context=true; uncertain=true; unresolved_analysis

Can you propose at least one segmentation that reconstructs the surface?
  → fill proposed_segmentation; add phenomenon tags
  → if unsure: uncertain=true, confidence≤2

Would you rather leave it unsegmented for tokenizer evaluation?
  → no_segmentation_required=true

Still stuck?
  → unresolved_analysis; leave segmentation empty; notes
```

---

## 8. Independence and bias control

- **This phase:** one annotator (`annotator_a`). Do **not** treat AI suggestions as answers to paste.
- For the **remaining 160** and **self-review 25**, the interface **hides** BPE/Unigram and automatic tags.
- Do **not** open locked holdout or LM test data.
- If a future multi-annotator phase is run, annotators work independently until adjudication.

---

## 9. Pilot procedure (40 items)

1. Read this document fully.  
2. Open `pilot_40_annotator_*.csv` **or** the local UI with `--annotator-id`.  
3. Annotate all 40 pilot items.  
4. Save incrementally.  
5. Export JSONL.  
6. Run agreement measurement (lead / researcher).  
7. Adjudicate disagreements on a scheduled call; record adjudicated file.

Pilot goals:

- test guideline clarity;
- estimate agreement;
- revise tag inventory if needed **before** full 200-item annotation;
- **not** tune a tokenizer method on pilot labels alone without logging the decision.

---

## 10. Adjudication

After dual annotation:

1. Compute agreement (`measure_morphology_annotation_agreement.py`).  
2. Items with segmentation disagreement, one-sided uncertainty, or tag conflicts enter adjudication.  
3. Adjudicator fills a third record (`adjudicator` / `reviewer_id`) using `adjudicate_morphology_annotations.py`.  
4. Adjudicated segmentation becomes the development reference for metrics **on the development/pilot set only**.  
5. Locked holdout remains sealed until method freeze.

---

## 11. Ethics and data safety

- Training/validation text only in this benchmark.  
- No LM test items.  
- No holdout items in the pilot.  
- Do not upload annotations to external services without project approval.

---

## 12. Examples (illustrative only — not gold for the corpus)

| Surface | Acceptable annotation style |
|---------|-----------------------------|
| `ndimakukonda` | `ndi+ma+ku+konda` **or** `ndi+makukonda` + alternative; tags as appropriate; or uncertain |
| `Malaŵi` | may be `no_segmentation_required` or single piece; note orthography |
| `Berlin` | `mixed_language=true`; often no Chichewa morphology |

These examples teach **format**, not answers for real pilot items.

---

## 13. Versioning

- Guidelines version: **v0.1**  
- Changes require an entry in `MTHANDIZI_TOKENIZER_DECISION_LOG.md`  
- Do not silently change allowed tags mid-pilot; finish pilot, then revise if needed.
