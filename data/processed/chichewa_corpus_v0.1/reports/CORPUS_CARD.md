# Corpus card: chichewa_corpus v0.1

_Generated at 2026-08-05T01:33:32.161297Z by promote_processed_corpus 0.1.0_

**Legal note:** This card documents licensing and provenance for research reproducibility. It is **not legal advice**. Downstream users remain responsible for compliance with CC BY-SA 4.0 and source-specific conditions.

## 1. Corpus name and version

- **Name:** chichewa_corpus (display: **Chichewa Corpus v0.1**)
- **Version:** v0.1
- This brand is distinct from Biblica® trademarks and from Wikipedia branding.

## 2. Purpose

Research-grade Chichewa text corpus assembled from approved interim cleaning outputs after explicit human eligibility decisions. Supports reproducible packaging with attribution; not a substitute for legal review of any specific downstream use.

## 3. Languages and orthographic observations

- Primary language: Chichewa (Nyanja); codes `ny` / `nya` appear in source records.
- Orthography is not normalized across sources.
- Bible text may retain characters such as `ŵ` that are less frequent or absent in other sources; this is an observed orthographic difference, not a cleaning error.

## 4. Included sources

- `bible` — CC-BY-SA-4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
- `wikipedia` — CC-BY-SA-4.0 (https://creativecommons.org/licenses/by-sa/4.0/)

## 5. Excluded sources

- `existing_corpus`
- `existing_corpus` is excluded as a **redundant composite** of Bible and Wikipedia (complete line-level containment; no unique residual). This is a technical exclusion, not a claim that underlying Bible or Wikipedia content is unlicensed.

## 6. Provenance

Structured records: `data/metadata/source_provenance/` (copied into this build under `metadata/source_provenance/`).

- **bible:** provenance_status=`verified`, source_url=`https://ebible.org/details.php?id=nya`, original_artifact=`nya_vpl.zip`, snapshot/date fields=`source_snapshot_date=2025-05-20` `stated_local_download_date=None`
  - Product page date / stated source date: `2025-05-20`. Download: `https://ebible.org/Scriptures/nya_vpl.zip`. Original zip not retained in-repo.
- **wikipedia:** provenance_status=`verified`, source_url=`https://ny.wikipedia.org/`, original_artifact=`nywiki-latest-pages-articles.xml.bz2`, snapshot/date fields=`source_snapshot_date=None` `stated_local_download_date=2026-04-03`
  - Dump URL class: moving `/latest/` (`https://dumps.wikimedia.org/nywiki/latest/nywiki-latest-pages-articles.xml.bz2`). Immutable dated dump URL: `None` (null if not proven). Original `.bz2` not retained in-repo.
- **existing_corpus:** provenance_status=`verified`, source_url=`None`, original_artifact=`None`, snapshot/date fields=`source_snapshot_date=None` `stated_local_download_date=None`

## 7. Licenses and permissions

### Summary

- **Both included textual sources are CC BY-SA 4.0.**
- **Attribution is required** for each source (see `reports/SOURCE_ATTRIBUTION.md` — source-specific, not one generic string).
- **Redistributed processed text** must retain applicable license obligations: attribution, license notice, modification notice, and share-alike for adapted text.
- **Modifications were made** during extraction and cleaning; treat processed outputs as derived/adapted text for notice purposes.
- **Bible-specific Biblica® trademark conditions apply:** unmodified redistribution may retain the trademark; modified/adapted text must remove Biblica® unless written permission exists. This corpus is treated as modified; do not brand the corpus as Biblica®.
- **Chichewa Wikipedia contributors retain their respective copyrights.** Do not claim the Wikimedia Foundation owns all article copyrights.
- **No endorsement** by Biblica, Inc., Wikimedia Foundation, or Wikipedia is implied.
- **Model training use** and **text redistribution** are different actions. Training permission in eligibility gates does not erase text-redistribution obligations.
- **Model weights:** Whether trained weights are adapted material under CC BY-SA is an **unresolved legal interpretation**. This project has not received qualified legal advice on that point. **No claim is made** that resulting model weights are or are not share-alike-encumbered.
- Downstream users remain responsible for compliance. This is documentation, not legal advice.

### Per-source fields

- **bible:** license_status=`verified`, license_name=`Creative Commons Attribution-ShareAlike 4.0 International`, license_id=`CC-BY-SA-4.0`, license_url=`https://creativecommons.org/licenses/by-sa/4.0/`, copyright_holder=`Biblica, Inc.`, training=`True`, redistribution=`True`, attribution_required=`True`, share_alike_required=`True`, modification_notice_required=`True`
- **wikipedia:** license_status=`verified`, license_name=`Creative Commons Attribution-ShareAlike 4.0 International`, license_id=`CC-BY-SA-4.0`, license_url=`https://creativecommons.org/licenses/by-sa/4.0/`, copyright_holder=`Chichewa Wikipedia contributors (individual authors); Wikimedia Foundation hosts content and does not own all article copyrights`, training=`True`, redistribution=`True`, attribution_required=`True`, share_alike_required=`True`, modification_notice_required=`True`
- **existing_corpus:** license_status=`not_applicable_as_independent_source`, license_name=`None`, license_id=`None`, license_url=`None`, copyright_holder=`None`, training=`False`, redistribution=`False`, attribution_required=`None`, share_alike_required=`None`, modification_notice_required=`None`

## 8. Cleaning methodology

- Bible: light-touch cleaning; local interim cleaned checksum currently matches raw extracted text under Cleaning Policy v2 path packaging.
- Wikipedia: Cleaning Policy v2 (`configs/data/cleaning_v2.json`) is the selected technical candidate.
- existing_corpus: not cleaned for independent promotion (redundant composite).
- Cleaning Policy v2 must not be modified based on blind holdout labels.

## 9. Human-review methodology

- Development set (~367 labels) used to design Cleaning Policy v2 only.
- Blind holdout with sequential stages; remainder of the 250-pool stays locked until explicitly released.
- Labels are frozen evaluation evidence; not a substitute for licensing.
- Eligibility reviewed by the human named in `source_eligibility.json`.

## 10. Development and blind-holdout metrics

Provisional independent holdout evidence (**do not retune v2 on holdout**):

**Context required when reading combined metrics:**

- **Stage 1** was **risk-stratified** (oversampled ambiguous foreign/short/URL/mixed cases; deprioritized trivial blank/digit/Category chrome).
- **Stage 2** consisted largely of **straightforward removal categories** (high removal precision; no kept-useful subsample in that chunk).
- Combined Stage 1+2 metrics therefore mix a hard risk slice with easier removal cases and must not be quoted as a single undifferentiated benchmark.

- Stage 1 removal precision: 0.975
- Stage 1 false-removal rate: 0.025
- Stage 1 useful-text retention: 0.955
- Combined Stage 1+2 (n=120), with the context above: precision=0.988, FRR=0.0125, useful retention=0.955
- Notes: Provisional independent evidence only. Do not retune Cleaning Policy v2 on holdout. Stage 1 was risk-stratified; Stage 2 was largely straightforward removal categories—do not present combined metrics without that context. Useful-retention CI wide due to few useful examples (~22). Remaining holdout extension pool stays locked.

## 11. Known biases

- Domain mix is not representative of all Chichewa text.
- Religious text and Wikipedia encyclopedic style dominate when both are included.
- Cleaning heuristics may under- or over-remove borderline mixed-language lines.

## 12. Religious-domain concentration

If Bible is included, a large fraction of tokens may be religious narrative and verse-like structure. Downstream models may overfit religious register.

## 13. Wikipedia-domain concentration

If Wikipedia is included, encyclopedic and list-like structures may dominate non-religious content. Foreign-language and chrome noise are reduced by v2 but residual risk remains.

## 14. Orthographic difference, including Bible ŵ observation

Bible text may use `ŵ` and related orthographic conventions that differ from Wikipedia or modern informal text. Promotion does not rewrite orthography.

## 15. Deduplication policy

- Within-source exact: True
- Cross-source exact: False
- Source priority: ['bible', 'wikipedia']
- No MinHash, embedding, or fuzzy near-dedup in v0.1.
- Attribution metadata is preserved even when exact cross-source duplicates collapse text instances.

## 16. Intended uses

- Research experimentation when `allowed_for_training` is explicitly true and the user accepts CC BY-SA text obligations for any redistribution of text.
- Reproducible packaging of cleaned text with provenance and attribution.

## 17. Prohibited or unsupported uses

- Redistributing processed text without attribution, license notice, modification notice, or share-alike compliance.
- Branding the corpus with Biblica® or implying Wikimedia/Biblica endorsement.
- Silent inclusion of `existing_corpus` as an independent source.
- Claiming that model weights are free of (or subject to) CC BY-SA without qualified legal advice.
- Claiming language ID or perfect noise removal.

## 18. Redistribution status

- Mode for this build: `exportable`
- Redistribution permitted (all included sources): `True`
- When exportable: text may be shared under CC BY-SA 4.0 with the notices in `reports/SOURCE_ATTRIBUTION.md`.

## 19. Reproducibility instructions

1. Acquire sources **manually** using `configs/data/source_acquisition_manifest.json` (no auto-download in this pipeline).
2. Prefer dated Wikimedia dump URLs over `/latest/`; record dump SHA-256 at acquisition.
3. Freeze raw inventory checksums (`data/metadata/inventory.json`).
4. Run validated cleaning (Bible path + Cleaning Policy v2 for Wikipedia).
5. Confirm eligibility in `data/metadata/source_eligibility.json`.
6. Dry-run then promote with `scripts/data/promote_processed_corpus.py`.
- Git commit recorded at build time: `None`

## 20. Limitations

- Original Wikipedia dump `.bz2` and Bible `nya_vpl.zip` are not retained in-repo; exact dump SHA-256 values are therefore unknown.
- Wikimedia dump date is not independently proven from a retained archive (stated download date is human-reported).
- Holdout useful-retention confidence intervals can be wide with few useful examples.
- No train/validation/test splits are created by this pipeline.
- Orthography and domain imbalance are not corrected.
- Model-weight licensing under CC BY-SA remains unresolved without legal advice.
