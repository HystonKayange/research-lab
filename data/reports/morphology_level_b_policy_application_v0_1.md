# Chichewa Level-B policy application v0.1

This is a proposed adjudication produced by applying the frozen `Level B — conservative medium granularity` policy to the 195 active development items in deterministic `item_id` order. It does not create benchmark gold or modify any annotation file.

The application used the active source, the existing Level-B re-audit JSON, and the existing Level-B re-audit Markdown only. No linguistic analysis was rerun and no new segmentation rule was introduced.

## Summary

| Policy result | Count | Meaning |
|---|---:|---|
| KEEP_CURRENT | 18 | Original segmentation satisfies the frozen policy. |
| ACCEPT_REVISION | 133 | Existing re-audit proposal is accepted under the frozen policy. |
| EXCLUDE | 33 | Existing source-quality exclusion is accepted under Rule 7; no segmentation is invented. |
| HUMAN_REVIEW | 11 | Policy cannot determine a final result; provisional proposal is retained for human adjudication. |

## Confidence counts

| Confidence | Count |
|---|---:|
| HIGH | 148 |
| MEDIUM | 39 |
| LOW | 8 |

## Counts by policy rule

Counts are item counts and can overlap because one item can use multiple rules.

| Rule | Count |
|---|---:|
| OVERRIDING_1_EXACT_SURFACE_RECONSTRUCTION | 195 |
| OVERRIDING_2_NO_SYLLABIC_SEGMENTATION | 21 |
| OVERRIDING_3_UNCERTAINTY_OVER_FALSE_PRECISION | 11 |
| RULE_1_VERBAL_FINAL_VOWELS | 126 |
| RULE_2_NEGATIVE_MORPHOLOGY | 19 |
| RULE_3_VERBAL_EXTENSIONS | 67 |
| RULE_4_POST_FINAL_MATERIAL | 30 |
| RULE_5_NOUN_CLASSES_AGREEMENT | 78 |
| RULE_6_LOCATIVES_CONTRACTIONS | 15 |
| RULE_7_LOANS_PROPER_NAMES_MIXED_LANGUAGE | 38 |

## HUMAN_REVIEW items

### morph_dev_0043 — pakatipa

- Original: `pa+katipa`
- Provisional re-audit proposal: `pa+katipa`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The context does not establish whether pa- is a productive locative prefix or part of a lexicalized adverb. Do not split katipa by syllable shape.
- Human-review question: Is pa- a benchmark-level locative boundary here, or is pakatipa lexicalized as a single adverbial item?

### morph_dev_0064 — m’Chicheŵa

- Original: `m’+Chicheŵa`
- Provisional re-audit proposal: `m’+Chicheŵa`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The contraction is orthographically clear, but the degree to which m’ is morphologically independent in this phrase should be confirmed by a native speaker; do not split the language name.
- Human-review question: Is m’ a benchmark-level locative boundary before Chicheŵa, or should the contracted phrase be treated as one orthographic/phrase-level unit?

### morph_dev_0071 — M’nthaŵi

- Original: `M’+nthaŵi`
- Provisional re-audit proposal: `M’+nthaŵi`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The contraction M’ is orthographically visible, but whether it should receive a standalone benchmark boundary depends on the treatment of locative prepositions/clitics in the annotation manual.
- Human-review question: Is M’ an independent locative boundary before nthaŵi in this construction, or only an orthographic contraction?

### morph_dev_0078 — kumadzulo

- Original: `ku+madzulo`
- Provisional re-audit proposal: `ku+madzulo`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: Ku- is plausible in the directional construction, but ku-madzulo may be lexicalized as a fixed directional expression; retain the split provisionally pending native-speaker judgment.
- Human-review question: Is ku- an independent locative/directional boundary in kumadzulo here, or is the expression lexicalized?

### morph_dev_0106 — m'gululi

- Original: `m'+gulu+li`
- Provisional re-audit proposal: `m'+gulu+li`
- Confidence: **MEDIUM**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The construction is plausibly mu-gulu-li “in this group,” but the contracted locative and final demonstrative require a consistent native-speaker decision.
- Human-review question: In m'gululi, is m' + gulu + li the appropriate benchmark morphology, or should the contracted locative/demonstrative construction remain coarser?

### morph_dev_0136 — aloe

- Original: `aloe`
- Provisional re-audit proposal: `aloe`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The context is Chichewa but aloe is a loan or citation plant name with no secure productive Chichewa morphology in the item. A native speaker should decide whether to keep it as a whole loan or exclude it.
- Human-review question: Is aloe an accepted Chichewa-integrated loan/plant name that should remain whole, or is it outside the frozen benchmark scope?

### morph_dev_0155 — watiwona

- Original: `wa+ti+wona`
- Provisional re-audit proposal: `wa+ti+won+a`
- Confidence: **MEDIUM**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The morphology is plausible, but the context contains only the isolated token; the clause-level TAM/interpretation cannot be confirmed.
- Human-review question: What clause-level TAM and argument structure is intended for watiwona, and does wa-ti-won-a apply in the missing context?

### morph_dev_0181 — chitambasulire

- Original: `chi+tambasulire`
- Provisional re-audit proposal: `chi+tambasulire`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The source context is noisy and does not establish whether this is a class-7 nominal/qualificative form or a productive applied verbal form. Do not force ta+mba+su or tambasul+ir+e.
- Human-review question: Is chi- productive class/agreement morphology in chitambasulire, and is -ir- plus final -e recoverable, or should tambasulire remain the safest stem?

### morph_dev_0183 — m’nyumbazo

- Original: `m’+nyumba+zo`
- Provisional re-audit proposal: `m’+nyumba+zo`
- Confidence: **MEDIUM**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The noun and demonstrative are clear, but the contracted locative is subject to the locative morphologization dispute.
- Human-review question: Is m’ an independent locative boundary in m’nyumbazo, with nyumba+zo, or should the contracted locative remain unresolved?

### morph_dev_0185 — movutika

- Original: `mo+vutika`
- Provisional re-audit proposal: `mo+vutika`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: Mo- may be a locative/adverbial element, but the lexicalized status of mo-vutika and -ik- is not recoverable from this context alone.
- Human-review question: Is mo- an independent locative/adverbial element in movutika, and is -ik- productive or lexicalized?

### morph_dev_0196 — ndidzamwenso

- Original: `ndi+dza+mwe+nso`
- Provisional re-audit proposal: `ndi+dza+mwe+nso`
- Confidence: **LOW**
- Policy issue: The existing audit leaves this item unresolved. The frozen policy does not select a final segmentation; the re-audit proposal is retained only as a provisional review aid. Existing audit reason: The boundary before -nso is strong, but mwe versus mwa is a dialectal/orthographic issue and should not be promoted to a confident final-vowel analysis.
- Human-review question: Does the context support a final vowel before -nso in ndidzamwenso, and is the lexical stem mwe/mwa resolved by the intended orthography or dialect?

The provisional proposals above are not policy-resolved answers. Human fields remain blank in the exceptions CSV.

## Differences from the previous re-audit recommendation

There are no substantive category changes from the prior recommendations: KEEP maps to KEEP_CURRENT, REVISE maps to ACCEPT_REVISION, EXCLUDE remains EXCLUDE, and UNCERTAIN enters HUMAN_REVIEW. The policy diff JSON records segmentation changes, exclusions, and human-review entries separately.

## Reconstruction validation

| Check | Result |
|---|---|
| Items processed | 195/195 |
| Non-EXCLUDE proposals checked | 162 |
| Exact surface reconstruction failures | 0 |
| Empty segments | 0 |
| Accidental whitespace changes | 0 |
| Orthographic normalization failures | 0 |
| Duplicate item IDs | 0 |
| EXCLUDE items with invented segmentation | 0 |
| HUMAN_REVIEW items silently resolved | 0 |
| Active annotation file byte-for-byte unchanged during application | true |
| Overall validation | **true** |

## Restricted materials and historical provenance

- BPE outputs accessed: **false**
- Unigram outputs accessed: **false**
- StatBound outputs accessed: **false**
- Morphology holdout accessed: **false**
- LM test accessed: **false**
- Tokenizer metrics/efficiency accessed: **false**
- Phase C rerun: **false**
- Tokenizer evaluation run: **false**

Historical measurements are preserved unchanged: exact agreement = **0.52** and boundary F1 = **0.841**. They remain measurements of the original annotation protocol and are not recomputed or overwritten.

No canonical/current annotation file, historical annotation, self-review measurement, or benchmark gold was modified. No v0.2 benchmark was created.
