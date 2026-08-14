# Chichewa Level-B Adjudication Policy v0.2

## Policy status

Policy name: **Level B — conservative medium granularity**

This policy is frozen before scientific tokenizer evaluation on the morphology benchmark. It governs benchmark adjudication only. It must not be changed in response to tokenizer outputs, tokenizer scores, efficiency results, language-model results, or holdout behavior.

This document materializes the source-grounded Level-B standard used by the subsequent policy application. The prior re-audit remains evidence and recommendation, not unquestionable gold.

## Governing principle

Split productive grammatical morphology and linguistically well-supported internal morphology; preserve the safest lexical/derived stem when finer decomposition is uncertain; never use syllable shape alone as evidence.

## Rule 1 — Verbal final vowels

Split a verbal final vowel when the grammatical construction **and** lexical/paradigmatic evidence independently support it.

Examples:

- `ndi+teng+a`
- `Nen+a`
- `U+gon+e`
- `mu+dza+zi+yes+e`

Do not split final `a`/`e` merely because the orthographic word ends in `a`/`e`. Final-vowel segmentation must correspond to an independently justified verbal slot.

## Rule 2 — Negative morphology

Distinguish contracted negative morphology from constructions in which a larger TAM element is itself grammatical.

Where the construction clearly contains negative allomorph `s-` plus an independently recoverable subject marker `a-`, analyses such as these are permitted:

- `s+a+na+kond+e`
- `s+a+na+loŵ+e`
- `s+a+na+yi+pez+e`

Do not mechanically decompose every occurrence of `sana`. Where `sana` is independently licensed as the anterior/before/not-yet pre-stem construction, retain `sana` as one element.

The native-speaker adjudication `ndisananene → ndi+sana+nen+e` is high confidence and is preserved by this policy. Any case where `s+a` versus `sa`/`sana` is not determined by the construction goes to `HUMAN_REVIEW` rather than being forced.

## Rule 3 — Verbal extensions

Split productive derivational extensions only with positive morphological evidence. Evidence can include a clear lexical family, an argument-structure or valency contrast, a grammatical function, or an established paradigm already documented in the source-grounded audit.

Supported examples may include:

- `nen+edw+a`
- `lemb+edw+er+a`
- `pang+ir+a`
- `yik+ir+a`
- `gaŵan+ik+e`

Shape alone is never sufficient. Strings such as `-ir-`, `-er-`, `-an-`, `-ik-`, `-ek-`, `-its-`, and `-ets-` must not automatically trigger boundaries.

When finer decomposition is uncertain, preserve the safest derived stem. Conservative examples include:

- `phunzir+a`
- `limban+a`
- `yitanir+a`
- `tchinjiriz+e`
- `phatikizir+a`

## Rule 4 — Post-final material

Split post-final material when its grammatical or discourse contribution is independently recoverable.

Examples:

- `khal+a+nso`
- `teng+a+po`
- `bwer+a+ko`
- `low+a+mo`
- `pitikits+a+be`
- `pez+a+di`

`-ni` may be split where the construction supports a plural/formal/addressee post-final marker, for example `Khululuk+ir+a+ni` and `Kwez+a+ni`. Do not assume every final `ni` has identical status. If the function of `-ni` is not supported by the full construction, send the item to `HUMAN_REVIEW`.

## Rule 5 — Noun classes and agreement

Split overt productive noun-class morphology when independently supported by the noun or agreement paradigm.

Examples:

- `ma+tchalitchi`
- `Ma+timu`
- `a+kapolo`
- `Chi+ŵerengero`
- `zi+ŵeto`
- `ya+mi+landu`
- `ya+chi+nkhoswe`
- `M+dima`
- `la+chi+ŵiri`

Agreement/concord material may also be segmented where independently recoverable, as in `ya+mi+landu` and `la+chi+ŵiri`. Do not split a word merely because its initial letters resemble a noun-class prefix. The remaining lexical material must form a plausible stem.

## Rule 6 — Locatives and contractions

Use a conservative standard. Bound or orthographically attached locative material may be segmented where its grammatical function is clear. Lexicalized or structurally ambiguous locative expressions must not be forced.

Potentially difficult examples include:

- `m’Chicheŵa`
- `M’nthaŵi`
- `m'gululi`
- `kumadzulo`
- `pakatipa`
- `m’nyumbazo`

If the policy plus existing context does not confidently determine whether locative material is an independent morphological boundary, classify the item `HUMAN_REVIEW`. Do not invent a global “always split `m'`/`ku`/`pa`” rule.

## Rule 7 — Loans, proper names, and mixed language

Foreign origin alone is not grounds for exclusion. A loan or proper-name stem may remain in the benchmark when productive Chichewa morphology is attached, as in `ma+tchalitchi`, `Ma+timu`, and `Davide+yo`.

Exclude an item when the target itself contains no meaningful Chichewa morphological boundary and is essentially non-Chichewa or source noise, as in the prior audit’s `Karl`, `Michel`, `Darussalam`, and `oral` recommendations. The operative question is:

> Does this item provide a defensible Chichewa morphological boundary for the benchmark?

It is not:

> Is every lexical segment historically Chichewa?

Proper-name, loan, and mixed-language cases remain subject to the frozen benchmark scope and the existing source-quality evidence; this rule does not create a blanket exclusion rule.

## Overriding constraints

### Exact surface reconstruction

Concatenating all proposed segments must reproduce the original `surface_form` exactly. Preserve capitalization, apostrophe form, `ŵ`/`w` as present in the frozen corpus, and all original orthography. Do not normalize spelling during morphology annotation.

### No syllabic segmentation

Syllable shape alone is never evidence of morphology. `pi+ta` is invalid where it merely divides syllables; `pit+a` is valid only when final-vowel evidence supports it. `Ne+na` is invalid; `Nen+a` is valid when the paradigm supports it. `vula+la` is invalid without morphological evidence; `vulal+a` is the conservative Level-B analysis.

### Uncertainty over false precision

When multiple linguistically defensible analyses remain and the frozen policy cannot distinguish them, use `HUMAN_REVIEW`. Do not choose the more detailed segmentation simply because it is available.

## Confidence standard

- **HIGH:** productive morphology and the relevant boundary are clearly supported by context or paradigm.
- **MEDIUM:** the main boundary is supported but some lexical/internal interpretation remains uncertain.
- **LOW:** multiple plausible analyses, insufficient context, unresolved locative/lexicalization issue, or policy ambiguity.

Low-confidence cases should normally enter `HUMAN_REVIEW`. Medium confidence does not automatically require review when the policy clearly determines the boundary.

## Deterministic application procedure

Process all 195 active development items in deterministic `item_id` order. Compare the surface form, context, original segmentation, existing re-audit recommendation, existing re-audit proposal, and evidence already recorded in the re-audit.

Assign exactly one policy result:

- `KEEP_CURRENT`: the current/original segmentation already satisfies Level B.
- `ACCEPT_REVISION`: the re-audit revision clearly follows Level B.
- `EXCLUDE`: the item is unsuitable for the Chichewa morphology-boundary benchmark under Rule 7 or the documented source-quality criteria.
- `HUMAN_REVIEW`: the frozen policy cannot determine the correct result with sufficient confidence.

For `HUMAN_REVIEW`, record the exact unresolved question. Examples include whether `m'` is a benchmark-level locative boundary, whether a construction licenses `s+a` or a larger negative/TAM unit, whether `-ir-` is productively applicative or part of the safest lexical stem, whether final `-ni` is a post-final grammatical marker, and whether a loan/proper-name token carries enough Chichewa morphology to remain.

## Provenance and non-effects

This policy application is a proposed adjudication only. It does not modify the active annotations, canonical annotations, previous reviewed annotations, self-review files, or benchmark gold. No v0.2 benchmark is created by this policy.

The historical self-review measurements remain unchanged:

- exact agreement = **0.52**
- boundary F1 = **0.841**

These are historical measurements of the original annotation protocol and are not recomputed or retroactively replaced.

The policy application must not access BPE, Unigram, StatBound, morphology-holdout, LM validation/test, tokenizer performance, or tokenizer-efficiency artifacts, and must not rerun Phase C or any tokenizer evaluation.


## v0.2 clarification — Native-speaker lexical integrity

**NATIVE-SPEAKER LEXICAL-INTEGRITY RULE:**

When source-grounded analyses permit multiple defensible granularities, prefer the segmentation that preserves the smallest lexical or grammatical unit recognized by the native annotator, unless a finer boundary is independently established by a productive grammatical paradigm.

Native-speaker lexical intuition does NOT imply that every morpheme must be a standalone word. Bound grammatical morphology remains valid when independently motivated.

This clarification applies only where the frozen Level-B policy left genuine ambiguity.

This clarification arose during adjudication of the 11 previously flagged HUMAN_REVIEW cases. It was introduced before Phase C, and no tokenizer outputs or evaluation results were consulted. It is therefore a benchmark-instrument clarification, not outcome-driven tuning.
