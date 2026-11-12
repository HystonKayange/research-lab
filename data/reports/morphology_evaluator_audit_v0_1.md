# Morphology evaluator v0.1 — archived-prediction audit

Post-hoc measurement audit, not a new tokenizer experiment or replacement V1 result. The evaluator specification and synthetic tests were committed before applying it to stored predictions (`b535f50`). The rules were informed by known scoring limitations, not independently preregistered.

## Validation-session access incident

On 2026-11-11 an overly broad unittest-discovery command ran older tests that read `locked/holdout_manifest.json` and `locked/RELEASE_BLOCKED`. This was an unauthorized metadata read; this session must **not** be described as having no holdout access. No sealed payload was decoded, no holdout evaluation or release occurred, and LM test was not accessed. An old tokenizer dry-run also failed on missing SentencePiece before encoding. Work stopped and the owner was notified. On 2026-11-12 the owner authorized transparent documentation and restricted validation. The new CI and commands below name only the two new synthetic-test files. See the [incident record](morphology_evaluator_validation_incident_v0_1.json). The restricted metadata was not reopened or hashed for this remediation.

## Measurements

Macro P/R/F1 now use the same 162 items. Empty prediction pieces are removed; only strictly internal character offsets count. Matching whole-word analyses score 1; one-sided-empty cases score 0. Micro scores pool TP/FP/FN. See the [specification](../../docs/research/MORPHOLOGY_EVALUATOR_SPEC_v0_1.md).

| Fixed stored path | Archived macro F1 | Cleanup only, old nulls | Strict macro P | Strict macro R | Strict macro F1 | Strict micro F1 | Exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unigram8k archived top-1 | 0.555081 | 0.557303 | 0.803395 | 0.450823 | 0.522194 | 0.527443 | 14/162 |
| Fixed legacy-F1-selected paths (not a new oracle) | 0.791282 | 0.793365 | 0.840770 | 0.806893 | 0.789743 | 0.786988 | 24/162 |
| Fixed legacy-compatibility-selected paths (not a new oracle) | 0.516916 | 0.517630 | 0.547222 | 0.588580 | 0.511240 | 0.509921 | 4/162 |
| StatBound lambda=0.25 stored selected paths | 0.555081 | 0.557303 | 0.803395 | 0.450823 | 0.522194 | 0.527443 | 14/162 |
| StatBound lambda=0.5 stored selected paths | 0.555081 | 0.557303 | 0.803395 | 0.450823 | 0.522194 | 0.527443 | 14/162 |
| StatBound lambda=1.0 stored selected paths | 0.555081 | 0.557303 | 0.803395 | 0.450823 | 0.522194 | 0.527443 | 14/162 |
| StatBound lambda=2.0 stored selected paths | 0.555081 | 0.557303 | 0.803395 | 0.450823 | 0.522194 | 0.527443 | 14/162 |

BPE: strict scores are **unavailable** because per-item predictions are not present in the approved artifacts. Its archived macro F1 remains 0.462178. Do not compare that historical value directly with new-version scores as though scoring were identical.

The two legacy-selected path sets above are held fixed. They are **not new-version oracle ceilings**; no n-best path was reselected. All four StatBound paths were independently rescored from stored diagnostic pieces and checked to equal Unigram on 162/162 items. This audit does not remedy or reinterpret V1's negative result.

## Denominators and artifact effects

| Path | Old P/R/F1 denominators | Strict P/R/F1 denominators | Empty-piece items | Exact changes | Gold-whole macro F1 | Gold-segmented macro F1 |
|---|---|---|---:|---:|---:|---:|
| unigram | 152/160/150 | 162/162/162 | 3 | 1 | 0.500000 | 0.522472 |
| f1_oracle | 162/160/160 | 162/162/162 | 2 | 2 | 0.500000 | 0.793365 |
| compat_oracle | 162/160/160 | 162/162/162 | 2 | 0 | 0.000000 | 0.517630 |

The two gold whole-word items are `aloe` and `fupi`. Whole-word and segmented strata remain separate diagnostics as well as contributing to the all-item macro. Cleanup-only keeps the historical missing-value rules after removing empty pieces. Its difference from archived scoring isolates cleanup effects; strict minus cleanup-only isolates the zero-boundary/denominator convention. These effects can have opposite signs.

## Item-level changes

The CSV contains every fixed path/item, input and canonical pieces, old/new metrics, offsets, counts, and change flags. Below are changes for the three distinct archived path sets; StatBound duplicates Unigram.

| Path | Item | Surface | Empty pieces removed | Old F1 | Strict F1 | Exact old → strict |
|---|---|---|---:|---:|---:|---|
| unigram | morph_dev_0022 | masuleni | 1 | 0.500000 | 0.666667 | False → False |
| unigram | morph_dev_0053 | anamutenga | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0057 | pita | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0063 | mumakhala | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0076 | yaikulu | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0078 | kumadzulo | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0081 | komanso | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0082 | akapolo | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0083 | anasankha | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0111 | Chiyambi | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0120 | msonkhano | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0136 | aloe | 0 | undefined | 0.000000 | False → False |
| unigram | morph_dev_0161 | fupi | 1 | undefined | 1.000000 | False → True |
| unigram | morph_dev_0173 | Kwezani | 1 | 0.500000 | 0.666667 | False → False |
| f1_oracle | morph_dev_0057 | pita | 1 | 0.666667 | 1.000000 | False → True |
| f1_oracle | morph_dev_0136 | aloe | 0 | undefined | 0.000000 | False → False |
| f1_oracle | morph_dev_0161 | fupi | 1 | undefined | 1.000000 | False → True |
| compat_oracle | morph_dev_0092 | umapewa | 1 | 0.285714 | 0.333333 | False → False |
| compat_oracle | morph_dev_0136 | aloe | 0 | undefined | 0.000000 | False → False |
| compat_oracle | morph_dev_0161 | fupi | 0 | undefined | 0.000000 | False → False |
| compat_oracle | morph_dev_0189 | itamaliza | 1 | 0.333333 | 0.400000 | False → False |

## Integrity and provenance

162 unique development IDs; all seven stored-path sets reconstruct exactly; zero reconstruction failures or invalid strict offsets. Archived P/R/F1 and exact values reconcile with the stored pieces. All input and implementation SHA-256 hashes are recorded before/after in the JSON and match. The benchmark SHA-256 remains `73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67`.

The fixed-input audit runner performs no tokenizer/model invocation, candidate generation/reselection, corpus evaluation, LM BPC, or restricted-file access. This runner-specific statement does not erase the broader validation incident above. Morphology holdout remains **LOCKED**, with metadata read during prior validation and payload not decoded. LM test remains **LOCKED / UNTOUCHED**. Original scoring code, source annotations, policies, Phase-C outputs, λ*=0.25, and success criteria are unchanged. Historical self-review exact agreement 0.52 and boundary F1 0.841 are preserved, not recomputed. Historical SC4 remains NOT MET. No Phase C/F rerun or successor tokenizer.

## Reproduce this audit

```bash
python3 -m unittest discover -s tests -p test_morphology_boundaries_v0_1.py
python3 -m unittest discover -s tests -p test_morphology_evaluator_audit_v0_1.py
python3 scripts/evaluation/audit_morphology_evaluator_v0_1.py --check
```

Omit `--check` to regenerate only these new audit artifacts. The runner uses an explicit input allowlist, not repository-wide data discovery. It neither loads models nor touches locked corpus files.
