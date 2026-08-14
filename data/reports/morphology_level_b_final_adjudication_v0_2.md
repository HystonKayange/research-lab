# Chichewa Level-B final adjudication v0.2

This report records the native-speaker adjudication and freezes the Chichewa Level-B development benchmark before Phase C. It does not run tokenizer evaluation and does not modify v0.1 historical files.

## Final counts

| Measure | Count |
|---|---:|
| Source items | 195 |
| Final active benchmark | 162 |
| Excluded | 33 |
| Unresolved human review | 0 |
| Original KEEP items retained | 18 |
| Policy revisions accepted | 133 |
| Native-speaker adjudications | 11 |
| Reconstruction failures | 0 |

## Native-speaker adjudications

### morph_dev_0043 — pakatipa

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `pa+katipa`
- Human decision: **CHANGE**
- Final segmentation: `pakati+pa`
- Human note: Native-speaker judgment: pakati means “middle”; final pa contributes the relational/pointing sense in pakatipa, roughly “in the middle of”. Rejects the provisional pa+katipa. The item remains in the benchmark.

### morph_dev_0064 — m’Chicheŵa

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `m’+Chicheŵa`
- Human decision: **ACCEPT**
- Final segmentation: `m’+Chicheŵa`
- Human note: m’ is the contracted form corresponding to mu in this construction; the phrase means “in Chichewa”. Full “mu Chicheŵa” is not the natural surface form here. Exact apostrophe and orthography are preserved.

### morph_dev_0071 — M’nthaŵi

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `M’+nthaŵi`
- Human decision: **ACCEPT**
- Final segmentation: `M’+nthaŵi`
- Human note: M’ is contracted mu in the expression meaning approximately “in/at the time”. Capitalization and ŵ are preserved exactly.

### morph_dev_0078 — kumadzulo

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `ku+madzulo`
- Human decision: **ACCEPT**
- Final segmentation: `ku+madzulo`
- Human note: madzulo independently means “evening”; ku contributes locative/temporal/directional meaning such as “at/in/toward”, with contextual interpretation including west/westward.

### morph_dev_0106 — m'gululi

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `m'+gulu+li`
- Human decision: **ACCEPT**
- Final segmentation: `m'+gulu+li`
- Human note: m’ is contracted mu meaning “in”; gulu means “group”; li contributes the proximal/“this” interpretation, yielding approximately “in this group”. The exact apostrophe character found in surface_form is preserved.

### morph_dev_0136 — aloe

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `aloe`
- Human decision: **KEEP_WHOLE**
- Final segmentation: `aloe`
- Human note: Native speaker recognizes aloe as the plant name. There is no defensible internal Chichewa morphological boundary for this benchmark. This is not an EXCLUDE item.

### morph_dev_0155 — watiwona

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `wa+ti+won+a`
- Human decision: **CHANGE**
- Final segmentation: `wa+ti+wona`
- Human note: Native-speaker lexical judgment identifies wona as the meaningful Chichewa verb “see”. The finer won+a decomposition is not preferred for this conservative Level-B benchmark in this ambiguous case. This is a lexical-integrity resolution and does not remove independently supported final-vowel boundaries elsewhere.

### morph_dev_0181 — chitambasulire

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `chi+tambasulire`
- Human decision: **ACCEPT**
- Final segmentation: `chi+tambasulire`
- Human note: chi- is the clear grammatical/class element. The lexical family is associated with tambasula, with meanings related to unfolding/explaining/translation-like usage. No finer internal split of tambasulire is forced without stronger independent evidence.

### morph_dev_0183 — m’nyumbazo

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `m’+nyumba+zo`
- Human decision: **ACCEPT**
- Final segmentation: `m’+nyumba+zo`
- Human note: m’ is contracted mu meaning “in”; nyumba is “house”; zo supplies the relevant noun-class/deictic meaning, roughly “in those houses”. Exact orthography is preserved.

### morph_dev_0185 — movutika

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `mo+vutika`
- Human decision: **ACCEPT**
- Final segmentation: `mo+vutika`
- Human note: vutika is the verb “to struggle / have difficulty”. mo- contributes a descriptive/manner-like interpretation in context, e.g. akuyenda movutika “walking with difficulty”. The finer vut+ik+a analysis is not forced; vutika is retained as the lexical unit.

### morph_dev_0196 — ndidzamwenso

- Provisional policy result: **HUMAN_REVIEW**
- Provisional segmentation: `ndi+dza+mwe+nso`
- Human decision: **CHANGE**
- Final segmentation: `ndi+dzamwe+nso`
- Human note: Native-speaker judgment identifies ndi as the 1SG participant, dzamwe as the meaningful construction “come and drink / come to drink”, and nso as “again”. The lexical verb is kumwa “to drink”. Do not describe mwa as meaning “drink”, and do not treat dza as simply future TAM in this context. The conservative native-speaker unit is dzamwe.

Explicit overrides include `pakatipa`: `pa+katipa` → `pakati+pa`; `watiwona`: `wa+ti+won+a` → `wa+ti+wona`; and `ndidzamwenso`: `ndi+dza+mwe+nso` → `ndi+dzamwe+nso`. `aloe` is retained whole rather than excluded.

## Policy v0.1 → v0.2

Policy v0.2 preserves every v0.1 rule and adds the **NATIVE-SPEAKER LEXICAL-INTEGRITY RULE**:

> When source-grounded analyses permit multiple defensible granularities, prefer the segmentation that preserves the smallest lexical or grammatical unit recognized by the native annotator, unless a finer boundary is independently established by a productive grammatical paradigm.
>
> Native-speaker lexical intuition does NOT imply that every morpheme must be a standalone word. Bound grammatical morphology remains valid when independently motivated.
>
> This clarification applies only where the frozen Level-B policy left genuine ambiguity.

The clarification arose during adjudication of the 11 previously flagged HUMAN_REVIEW cases, before Phase C, without tokenizer outputs or evaluation results. It is a benchmark-instrument clarification, not outcome-driven tuning.

## Validation

- 162 unique active IDs and 33 unique excluded IDs
- active + excluded = 195 source IDs with no overlap
- exact surface reconstruction failures: **0**
- empty segments: **0**
- whitespace corruption: **0**
- capitalization/orthography failures: **0**
- apostrophe failures: **0**
- ŵ/w orthography failures: **0**
- unresolved HUMAN_REVIEW items: **0**
- v0.1 annotation files byte-for-byte unchanged: **true**

Human-case reconstruction checks:

- `morph_dev_0043`: `pakati+pa` → `pakatipa`; pass = **true**
- `morph_dev_0064`: `m’+Chicheŵa` → `m’Chicheŵa`; pass = **true**
- `morph_dev_0071`: `M’+nthaŵi` → `M’nthaŵi`; pass = **true**
- `morph_dev_0078`: `ku+madzulo` → `kumadzulo`; pass = **true**
- `morph_dev_0106`: `m'+gulu+li` → `m'gululi`; pass = **true**
- `morph_dev_0136`: `aloe` → `aloe`; pass = **true**
- `morph_dev_0155`: `wa+ti+wona` → `watiwona`; pass = **true**
- `morph_dev_0181`: `chi+tambasulire` → `chitambasulire`; pass = **true**
- `morph_dev_0183`: `m’+nyumba+zo` → `m’nyumbazo`; pass = **true**
- `morph_dev_0185`: `mo+vutika` → `movutika`; pass = **true**
- `morph_dev_0196`: `ndi+dzamwe+nso` → `ndidzamwenso`; pass = **true**

Overall validation: **true**.

## Restricted materials and historical provenance

- BPE outputs/metrics accessed: **false**
- Unigram outputs/metrics accessed: **false**
- StatBound outputs/metrics accessed: **false**
- Morphology holdout: **LOCKED / UNTOUCHED**
- LM test: **LOCKED / UNTOUCHED**
- Phase C: **NOT_STARTED**
- Tokenizer performance used for decisions: **false**

Historical measurements are preserved exactly: exact agreement = **0.52** and boundary F1 = **0.841**. They are historical measurements of the original underspecified annotation protocol. They were not recomputed or reinterpreted.

The v0.2 benchmark is native-speaker adjudicated under a frozen source-grounded Level-B conservative morphology framework, with computational linguistic assistance used for research and proposal generation. No human-human IAA is claimed.
