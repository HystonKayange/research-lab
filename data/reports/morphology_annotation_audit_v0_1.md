# Morphology annotation quality audit v0.1

_Generated 2026-08-11T07:56:49.381806Z_

## Framing

- **Mode:** read-only structural/schema/consistency audit
- **Input:** `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200.jsonl`
- **Annotator:** `annotator_a` (single native-speaker pass)
- **Does not claim** any annotation is linguistically wrong
- **Does not** use BPE, Unigram, Claude, or other model outputs to judge correctness
- **Does not** access morphology holdout or LM test
- **Does not** modify, normalize, adjudicate, or auto-correct annotations

## Executive summary

| Metric | Value |
|---|---|
| Total audited | **200** |
| Unique item IDs | **200** |
| Duplicate item IDs | 0 |
| Reconstruction failures | **0** |
| Missing/empty field issues | 0 |
| WHOLE / no-segmentation | 40 |
| Uncertain | 3 |
| Alternative segmentation present | 33 |
| Mixed-language flag | 35 |
| Spelling/OCR flag | 1 |
| Repeated surface forms (exact) | 0 |
| Repeated-form inconsistencies | 0 |
| Suspicious boundary-pattern cases | 2 |
| Suspicious one-char segment flags | 0 |
| High segment-count flags (≥5) | 9 |
| Items recommended for human review | **20** |
| Files modified (annotations) | none |
| Morphology holdout released | false |
| LM test evaluations | 0 |

## 1. Unique item IDs

- Rows: 200
- Unique IDs: 200
- Missing IDs: 0
- Duplicate IDs: none
- Pass (exactly 200 unique): **True**

## 2. Surface reconstruction

Rule: `proposed_segmentation` with `+` removed must equal `surface_form`.

- Failures: **0**
- All 200 items reconstruct successfully.

## 3. Missing / empty required fields

- Issues: **0**
- No missing core fields detected.

- Soft `boundary_positions` notes on multi-segment items: 0 (informational).

## 4. Segment-count distribution

- Min / median / mean / max: 1 / 3.0 / 2.625 / 5

| n_segments | count |
|---:|---:|
| 1 | 40 |
| 2 | 50 |
| 3 | 64 |
| 4 | 37 |
| 5 | 9 |

## 5. WHOLE / no-segmentation

- Count: **40** (20.0%)
- `no_segmentation_required=true`: 40

## 6. Uncertain

- Count: **3**
- `morph_dev_0095` `tursk` · `tursk` — uncertain=true
- `morph_dev_0097` `Clairol` · `Clairol` — uncertain=true
- `morph_dev_0133` `trompe-l'œil` · `trompe-l'œil` — uncertain=true

## 7. Alternative analyses

- Items with non-empty `alternative_segmentation`: **33**

| item_id | surface | proposed | alternative |
|---|---|---|---|
| morph_dev_0002 | imafunsidwa | i+ma+funsidwa | i+ma+funs+idwa |
| morph_dev_0007 | Tikukudalitsani | Ti+ku+ku+dalitsani | Ti+ku+kudalitsani |
| morph_dev_0018 | matsiriziro | ma+tsirizi+ro | ma+tsiriziro |
| morph_dev_0020 | anakakamizika | a+na+ka+kamizika | a+na+kakamizika |
| morph_dev_0022 | masuleni | ma+suleni | masule+ni |
| morph_dev_0023 | Davideyo | Davide+yo | Davideyo |
| morph_dev_0025 | kuphwanyaphwanya | ku+phwanya+phwanya | kuphwanya+phwanya |
| morph_dev_0039 | mudzamumvera | mu+dza+mu+mvera | mudza+mu+mvera |
| morph_dev_0040 | ndinawalamulira | ndi+na+wa+lamulira | ndinawa+lamulira |
| morph_dev_0041 | adzamubweretsa | a+dza+mu+bweretsa | adzamu+bweretsa |
| morph_dev_0042 | wolonjezedwa | wo+lonje+zedwa | wo+lonjezedwa |
| morph_dev_0049 | munkachitira | mu+n+ka+chitira | mu+nka+chitira |
| morph_dev_0054 | adapita | ada+pita | a+da+pita |
| morph_dev_0057 | pita | pi+ta | pita |
| morph_dev_0058 | inkayenda | i+n+ka+yenda | i+nka+yenda |
| morph_dev_0060 | Nena | Ne+na | Nena |
| morph_dev_0061 | tinachita | ti+na+chita | tina+chita |
| morph_dev_0071 | M’nthaŵi | M’+nthaŵi | M+’+nthaŵi |
| morph_dev_0087 | Mudzateteza | Mu+dza+teteza | Mudza+teteza |
| morph_dev_0088 | ananeneza | a+na+neneza | ana+neneza |
| morph_dev_0098 | zalembedwera | za+lembe+dwera | za+lembedwera |
| morph_dev_0102 | amavulala | a+ma+vula+la | a+ma+vulala |
| morph_dev_0106 | m'gululi | m'+gulu+li | m'+gululi |
| morph_dev_0108 | amatsamwitsidwa | a+ma+tsamwitsidwa | a+ma+tsamwits+idwa |
| morph_dev_0131 | linatsimikiziranso | lina+tsimikizira+nso | li+na+tsimikizira+nso |
| morph_dev_0132 | kudzathira | ku+dza+thira | kudza+thira |
| morph_dev_0135 | zoonadi | zoona+di | zo+onadi |
| morph_dev_0138 | zikadzatha | zi+ka+dza+tha | zi+kadza+tha |
| morph_dev_0148 | ndidzadziwa | ndi+dza+dziwa | ndidza+dziwa |
| morph_dev_0150 | Anaphunzira | A+na+phunzira | Ana+phunzira |
| morph_dev_0157 | ndidzakhazika | ndi+dza+khazika | ndidza+khazika |
| morph_dev_0188 | kuwabalalitsira | ku+wa+balalitsira | kuwa+balalitsira |
| morph_dev_0192 | wasungunulidwa | wa+sungunulidwa | wa+sungunul+idwa |

## 8. Mixed-language / name-like / OCR-spelling

- `mixed_language=true`: **35**
- `spelling_or_ocr_issue=true`: **1**
- `insufficient_context=true`: **1**
- Non-Chichewa / name / mixed-tagged (descriptive union): **39**

### Top phenomenon tags

| tag | count |
|---|---:|
| `apparent_stem_or_root` | 162 |
| `apparent_prefix` | 157 |
| `apparent_inflectional_boundary` | 150 |
| `no_meaningful_segmentation` | 40 |
| `non_chichewa_or_mixed` | 35 |
| `apparent_suffix` | 9 |
| `noun_class_like` | 7 |
| `multiple_plausible_analyses` | 4 |
| `negation_like` | 4 |
| `locative_like` | 4 |
| `unresolved_analysis` | 3 |
| `apparent_derivational_boundary` | 2 |
| `spelling_or_ocr_issue` | 1 |
| `numeral_or_code` | 1 |
| `insufficient_context` | 1 |

### OCR / spelling flagged
- `morph_dev_0117` `lmmaculate` · `lmmaculate` — spelling_or_ocr_issue=true

## 9. Repeated surface forms

- Exact duplicate surfaces: **0**
- Case-insensitive duplicate surfaces: **0**
- Segmentation inconsistencies among repeats: **0**

## 10. Affix / boundary treatment consistency

Among multi-segment items sharing orthographic prefix length 2–4 with group size ≥5 and majority first-boundary rate ≥60%, flag minority first cuts. Weak frequent-token fused examples listed separately and excluded from primary review.

- Prefix-boundary minority flags (primary): **2**

| item_id | surface | segmentation | reason |
|---|---|---|---|
| morph_dev_0054 | adapita | ada+pita | orthographic prefix 'ad' (len=2, n=5) has majority first-boundary after 1 chars (4/5=80%); this item first segment 'ada' (len=3) |
| morph_dev_0033 | sizidzamvekanso | sizidza+mveka+nso | orthographic prefix 'si' (len=2, n=10) has majority first-boundary after 2 chars (9/10=90%); this item first segment 'sizidza' (len=7) |

- Weak frequent-segment fused examples (not in primary review): **30**
- `morph_dev_0001` `Analigawa` · `Anali+gawa` — weak heuristic: frequent segment token 'a' (n_as_segment≈30) not used as a segment here
- `morph_dev_0002` `imafunsidwa` · `i+ma+funsidwa` — weak heuristic: frequent segment token 'a' (n_as_segment≈30) not used as a segment here
- `morph_dev_0003` `nditenga` · `ndi+tenga` — weak heuristic: frequent segment token 'a' (n_as_segment≈30) not used as a segment here
- `morph_dev_0001` `Analigawa` · `Anali+gawa` — weak heuristic: frequent segment token 'na' (n_as_segment≈30) not used as a segment here
- `morph_dev_0009` `inasandukanso` · `ina+sanduka+nso` — weak heuristic: frequent segment token 'na' (n_as_segment≈30) not used as a segment here
- `morph_dev_0010` `chikulimbana` · `chi+ku+limbana` — weak heuristic: frequent segment token 'na' (n_as_segment≈30) not used as a segment here
- `morph_dev_0036` `silinakule` · `si+li+na+kule` — weak heuristic: frequent segment token 'ku' (n_as_segment≈26) not used as a segment here
- `morph_dev_0076` `yaikulu` · `ya+i+kulu` — weak heuristic: frequent segment token 'ku' (n_as_segment≈26) not used as a segment here
- `morph_dev_0168` `wokunthidwa` · `wo+kunthidwa` — weak heuristic: frequent segment token 'ku' (n_as_segment≈26) not used as a segment here
- `morph_dev_0033` `sizidzamvekanso` · `sizidza+mveka+nso` — weak heuristic: frequent segment token 'dza' (n_as_segment≈21) not used as a segment here
- `morph_dev_0050` `Kundipembedza` · `Ku+ndi+pembedza` — weak heuristic: frequent segment token 'dza' (n_as_segment≈21) not used as a segment here
- `morph_dev_0030` `sadzawathandizanso` · `sa+dza+wa+thandiza+nso` — weak heuristic: frequent segment token 'ndi' (n_as_segment≈17) not used as a segment here
- `morph_dev_0016` `akanamasulidwa` · `a+kana+masulidwa` — weak heuristic: frequent segment token 'ma' (n_as_segment≈15) not used as a segment here
- `morph_dev_0078` `kumadzulo` · `ku+madzulo` — weak heuristic: frequent segment token 'ma' (n_as_segment≈15) not used as a segment here
- `morph_dev_0081` `komanso` · `koma+nso` — weak heuristic: frequent segment token 'ma' (n_as_segment≈15) not used as a segment here

### Most frequent segment tokens (descriptive)

| segment | count |
|---|---:|
| `a` | 30 |
| `na` | 30 |
| `ku` | 29 |
| `dza` | 21 |
| `ndi` | 17 |
| `ma` | 15 |
| `mu` | 15 |
| `wa` | 12 |
| `nso` | 11 |
| `zi` | 11 |
| `ka` | 11 |
| `chi` | 10 |
| `sa` | 9 |
| `si` | 9 |
| `i` | 8 |
| `ti` | 8 |
| `u` | 6 |
| `li` | 6 |
| `ya` | 4 |
| `zo` | 4 |

## 11. One-character segments

- Occurrences: 46 across 45 items
- Character inventory: `{'i': 8, 'U': 1, 'a': 27, 'n': 2, 'u': 5, 'A': 3}`
- Allowlist (not flagged): `AEINOUaeinou`
- Suspicious (non-allowlist): **0**
- No non-allowlist one-character segments.

## 12. High segment counts

- Threshold: ≥ 5 segments
- Max observed: 5
- Flagged: **9**

| item_id | surface | segmentation | reason |
|---|---|---|---|
| morph_dev_0012 | mudzandipezadi | mu+dza+ndi+peza+di | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0024 | anakazichotsa | a+na+ka+zi+chotsa | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0030 | sadzawathandizanso | sa+dza+wa+thandiza+nso | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0038 | sikukupezekanso | si+ku+ku+pezeka+nso | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0065 | unalikuŵalira | u+na+li+ku+ŵalira | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0125 | sizinachitikepo | si+zi+na+chitike+po | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0140 | zidzakusokonezani | zi+dza+ku+sokoneza+ni | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0171 | ndikanakupatsa | ndi+ka+na+ku+patsa | unusually high segment count n=5 (threshold>=5) |
| morph_dev_0197 | Anawapitikitsabe | A+na+wa+pitikitsa+be | unusually high segment count n=5 (threshold>=5) |

## 13. Pilot 40 vs remaining 160 patterns

| Metric | pilot_40 | remaining_160 |
|---|---:|---:|
| n | 40 | 160 |
| WHOLE | 5 | 35 |
| uncertain | 0 | 3 |
| mixed_language | 5 | 30 |
| alternative_segmentation | 20 | 13 |
| mean n_segments | 2.625 | 2.625 |
| median n_segments | 3.0 | 3.0 |
| tokenizer provenance fields present | 40 | 0 |

### Notable differences (descriptive)

- alternative_segmentation rate pilot=50.00% vs remaining=8.12%
- confidence value types differ: pilot={'int': 40} remaining={'int': 100, 'str': 60} (schema storage inconsistency, not a linguistic judgment)
- tokenizer provenance fields present on 40/pilot vs 0/remaining (merge provenance only)

- Confidence storage types — pilot: `{'int': 40}`; remaining: `{'int': 100, 'str': 60}`
- Confidence values — pilot: `{'4': 28, '5': 10, '3': 2}`; remaining: `{'4': 79, '5': 15, '3': 4, '2': 2, 'high': 59, 'low': 1}`

## 14. Recommended human re-review

**20** items in the **primary** re-review list (union of schema, annotator uncertainty/OCR/unresolved, high segment count, tightened boundary-pattern minorities, and multiple_plausible_analyses tags). Weak fused-token heuristics are **excluded** from this list.

This is **not** an automatic rejection of the labels and does **not** assert linguistic error.

Priority: 1 = schema/reconstruction, 2 = annotator uncertainty/OCR/unresolved, 3 = boundary/high-seg/multiple-analysis patterns.

| priority | item_id | surface | segmentation | categories | reasons |
|---:|---|---|---|---|---|
| 2 | morph_dev_0095 | tursk | tursk | uncertain, unresolved_analysis | annotator marked uncertain=true; phenomenon_tags includes unresolved_analysis |
| 2 | morph_dev_0097 | Clairol | Clairol | uncertain, unresolved_analysis | annotator marked uncertain=true; phenomenon_tags includes unresolved_analysis |
| 2 | morph_dev_0117 | lmmaculate | lmmaculate | ocr_spelling | spelling_or_ocr_issue=true |
| 2 | morph_dev_0133 | trompe-l'œil | trompe-l'œil | uncertain, unresolved_analysis | annotator marked uncertain=true; phenomenon_tags includes unresolved_analysis |
| 2 | morph_dev_0176 | Achikaladi | A+chikaladi | insufficient_context | insufficient_context=true |
| 3 | morph_dev_0012 | mudzandipezadi | mu+dza+ndi+peza+di | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0018 | matsiriziro | ma+tsirizi+ro | multiple_analyses | phenomenon_tags includes multiple_plausible_analyses |
| 3 | morph_dev_0020 | anakakamizika | a+na+ka+kamizika | multiple_analyses | phenomenon_tags includes multiple_plausible_analyses |
| 3 | morph_dev_0024 | anakazichotsa | a+na+ka+zi+chotsa | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0030 | sadzawathandizanso | sa+dza+wa+thandiza+nso | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0033 | sizidzamvekanso | sizidza+mveka+nso | boundary_pattern_inconsistency | orthographic prefix 'si' (len=2, n=10) has majority first-boundary after 2 chars (9/10=90%); this item first segment 'sizidza' (len=7) |
| 3 | morph_dev_0038 | sikukupezekanso | si+ku+ku+pezeka+nso | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0054 | adapita | ada+pita | boundary_pattern_inconsistency | orthographic prefix 'ad' (len=2, n=5) has majority first-boundary after 1 chars (4/5=80%); this item first segment 'ada' (len=3) |
| 3 | morph_dev_0065 | unalikuŵalira | u+na+li+ku+ŵalira | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0088 | ananeneza | a+na+neneza | multiple_analyses | phenomenon_tags includes multiple_plausible_analyses |
| 3 | morph_dev_0108 | amatsamwitsidwa | a+ma+tsamwitsidwa | multiple_analyses | phenomenon_tags includes multiple_plausible_analyses |
| 3 | morph_dev_0125 | sizinachitikepo | si+zi+na+chitike+po | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0140 | zidzakusokonezani | zi+dza+ku+sokoneza+ni | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0171 | ndikanakupatsa | ndi+ka+na+ku+patsa | high_segment_count | unusually high segment count n=5 (threshold>=5) |
| 3 | morph_dev_0197 | Anawapitikitsabe | A+na+wa+pitikitsa+be | high_segment_count | unusually high segment count n=5 (threshold>=5) |

## Constraints checklist

| Constraint | Status |
|---|---|
| Annotations modified | **false** |
| Annotations normalized/adjudicated/auto-corrected | **false** |
| Morphology holdout released | **false** |
| LM test evaluations | **0** |
| MthandiziTokenizer trained/implemented | **false** |
| BPE/Unigram/Claude used as correctness judge | **false** |

## Concise end report

- **total audited:** 200
- **reconstruction failures:** 0
- **duplicates:** 0 item IDs; 0 repeated surfaces
- **repeated-form inconsistencies:** 0
- **suspicious boundary-pattern cases:** 2
- **items recommended for human review:** 20
- **files modified:** none
- **morphology holdout released:** false
- **LM test evaluations:** 0

## Outputs

- `data/reports/morphology_annotation_audit_v0_1.json`
- `data/reports/morphology_annotation_audit_v0_1.md`
