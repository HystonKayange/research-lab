# Mthandizi tokenizer research blueprint v0.1

**Status:** research design only — **implementation not executed**  
**Language case study:** Chichewa (not Bantu-general)  
**Primary LM baseline to beat (validation, provisional):** Unigram-8000  
**LM test split:** ready but **untouched**  
**Morphology holdout:** **locked**  

Config: `configs/research/mthandizi_tokenizer_research_v0_1.json`  
Decision log: `docs/research/MTHANDIZI_TOKENIZER_DECISION_LOG.md`  
Prior-art plan: `docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_PLAN.md`

---

## Core research question

Under fixed data, parameter, and compute budgets:

> Can a morphology-aware hybrid tokenization method improve Chichewa language modelling over SentencePiece Unigram and BPE while preserving efficient sequence lengths and generalization to unseen word forms?

**Do not** begin from the assumption that the proposed tokenizer is better.

---

## Evidence discipline

| Layer | Meaning | Allowed claims |
|-------|---------|----------------|
| **Orthographic** | Surface strings, Unicode, length, `ŵ` | “form contains X” |
| **Statistical** | Fertility, disagreement rates, correlations | “rate/mean/correlation is …” |
| **Linguistic interpretation** | Morphemes, noun class, tense, etc. | Only after human review |

Recurring character strings are **not** morphemes without human validation.

Banned without evidence: *novel*, *state of the art*, *linguistically correct*, *morphology preserving*, *Bantu-general*.

---

## Established baseline context (validation only)

LM Baselines v0.1 r2 — mean validation BPC (provisional; test not run):

| Group | character | BPE-8000 | Unigram-8000 |
|-------|-----------|----------|--------------|
| arch × fixed_characters | 1.4779 | 1.4389 | **1.4313** |
| arch × fixed_updates | 1.8868 | 1.4567 | **1.4434** |
| param × fixed_characters | 1.4779 | 1.4463 | **1.4371** |
| param × fixed_updates | 1.8868 | 1.4987 | **1.4793** |

---

# Phase A — Baseline tokenization failure audit

**Script:** `scripts/tokenizers/analyze_baseline_morphology_failures.py`  
**Reports:**

- `data/reports/tokenizer_morphology_failure_audit_v0_1.md`
- `data/reports/tokenizer_morphology_failure_summary_v0_1.json`
- `data/reports/tokenizer_disagreement_candidates_v0_1.jsonl`

### Automatic diagnostics (computed)

- token count per word  
- characters per token  
- whole-word token rate  
- single-character fragment rate  
- rare-fragment / singleton-piece rates  
- segmentation disagreement rate (BPE-8000 vs Unigram-8000)  
- validation unseen-form fragmentation  
- consistency of recurring **initial** strings (statistical)  
- consistency of recurring **final** strings (statistical)  
- consistency across automatically discovered **surface** word families  
- vocabulary utilization (sample proxy)  
- frequency sensitivity (bands)  
- source sensitivity (bible vs wikipedia)  
- correlation(word frequency, fertility)  
- correlation(word length, fertility)  

### Inputs

Frozen train + validation; existing tokenizer artifacts; morphology probe candidates; LM **validation** summaries only.

### Outputs map to mechanisms

See Phase C tables: each design family must cite at least one **measured** automatic failure class.

---

# Phase B — Candidate morphology benchmark

**Scripts:**

- `scripts/tokenizers/build_morphology_benchmark.py`
- `scripts/tokenizers/release_morphology_holdout.py` (blocked without method freeze)

### Layout

```
data/research/morphology_benchmark_v0.1/
├── development/
│   ├── annotation_candidates.jsonl
│   ├── annotation_template.csv
│   └── README.md
├── locked/
│   ├── holdout_manifest.json      # counts + strata dist; no surface forms
│   ├── holdout_checksums.json
│   ├── holdout_payload.sealed.json
│   ├── RELEASE_BLOCKED
│   └── README.md
└── metadata/
    └── benchmark_manifest.json
```

### Development annotation set

- Release **now** for human review  
- Source primarily from **training** split  
- Target **160–240** examples (config default 200)  
- Stratified across candidate categories (hypotheses, not gold):

  subject/agreement prefixes · tense/aspect · object marking · negation ·  
  noun-class contrast · singular/plural · derivational suffixes · locatives ·  
  long agglutinative-looking words · frequent families · rare words ·  
  unseen/low-frequency · `ŵ` · mixed-language · BPE/Unigram disagreements ·  
  whole-word memorization  

**Do not** assert every selected example contains the proposed phenomenon.

### Human schema (development)

```json
{
  "item_id": "morph_dev_0001",
  "surface_form": "...",
  "context": "...",
  "source": "...",
  "automatic_tags": [],
  "human_segments": null,
  "human_phenomenon_tags": null,
  "alternative_analysis": null,
  "uncertain": null,
  "confidence": null,
  "annotator_id": null,
  "reviewer_id": null,
  "adjudication_status": "unreviewed",
  "notes": null
}
```

Support disagreement via `alternative_analysis`. **No fake gold.**

### Locked morphology holdout

- Prefer validation-derived unseen / low-frequency forms  
- Full text **not** in development reports  
- Deterministic IDs, line refs, checksums in manifest  
- Ordinary access refused (`RELEASE_BLOCKED`)  
- Release requires:

```bash
.venv/bin/python scripts/tokenizers/release_morphology_holdout.py \
  --confirm-method-freeze \
  --i-understand-this-is-irreversible-for-design
```

**Not released during design tasks.**

---

# Phase C — Proposed-method design space

These are **design candidates**, not an approved architecture.  
**Important principle:** learn as much as possible from the training corpus; allow only **small, reviewable** linguistic constraints. Avoid a large manual Chichewa dictionary unless evidence shows it is necessary.

Separate:

1. **language-independent machinery**  
2. **Chichewa-specific configuration**  
3. **optional human-reviewed constraints**  

---

### C1. Morphology-aware pre-segmentation + Unigram fallback

| Field | Content |
|-------|---------|
| mechanism | Apply constrained pre-splits on high-confidence affix/stem matches; Unigram on residual |
| baseline failure addressed | family inconsistency; high fragmentation on long forms |
| training-data requirements | train text + optional small reviewed inventory |
| dependency on human rules | medium (inventory quality) |
| language-specific assumptions | inventory content is Chichewa-specific |
| computational cost | low–medium at train; low at encode |
| deterministic behaviour | yes if Unigram + fixed inventory |
| unseen words | fallback to Unigram |
| compatibility | encode API same as SP |
| expected sequence-length impact | mild decrease if productive merges work |
| risk over-segmentation | if inventory too aggressive |
| risk under-segmentation | if inventory forces whole stems wrongly |
| risk wrong linguistic assumptions | high if inventory unvalidated |
| novelty uncertainty | high until prior-art review |
| required ablations | no pre-seg; inventory-size; fallback-only |
| falsification | val BPC ≥ Unigram **or** fertility regresses beyond cap **or** boundary F1 no better than Unigram on holdout |

### C2. Boundary-biased Unigram training

| Field | Content |
|-------|---------|
| mechanism | Bias Unigram EM / loss with soft preferences at candidate boundaries |
| baseline failure addressed | inconsistent splits within surface families |
| training-data requirements | train + boundary candidates (stats and/or human) |
| dependency on human rules | low–medium |
| language-specific assumptions | candidate generator may be configured per language |
| computational cost | medium (custom trainer) |
| deterministic behaviour | if seeded / single-thread like SP baseline |
| unseen words | standard Unigram composition |
| compatibility | custom train; standard encode |
| sequence-length impact | similar to Unigram if mild bias |
| risk over-seg | high bias → char-like |
| risk under-seg | weak bias → status quo |
| risk wrong assumptions | if candidates are false boundaries |
| novelty uncertainty | high until prior-art |
| ablations | bias strength 0; stats-only vs human candidates |
| falsification | no family-consistency gain at equal fertility |

### C3. Morphology-constrained BPE merges

| Field | Content |
|-------|---------|
| mechanism | Block or penalize merges that cross candidate boundaries |
| baseline failure addressed | destructive merges; family inconsistency |
| training-data requirements | train + boundary candidates |
| dependency on human rules | medium |
| language-specific assumptions | boundary list |
| computational cost | medium |
| deterministic behaviour | yes with fixed rules |
| unseen words | BPE residual behaviour |
| compatibility | SP BPE-like or HF tokenizers |
| sequence-length impact | often higher fertility than unconstrained BPE |
| risk over-seg | yes |
| risk under-seg | if constraints too few |
| risk wrong assumptions | blocked merges may be wrong |
| novelty uncertainty | high until prior-art |
| ablations | no constraints; hard vs soft block |
| falsification | worse than Unigram on val BPC and boundaries |

### C4. Hybrid affix/stem vocabulary allocation

| Field | Content |
|-------|---------|
| mechanism | Reserve vocab slots for productive pieces; fill rest with Unigram/BPE |
| baseline failure addressed | whole-word memorization of rare forms; under-allocation to affixes |
| training-data requirements | train frequencies + optional inventory |
| dependency on human rules | low–medium |
| language-specific assumptions | allocation policy config |
| computational cost | low–medium |
| deterministic behaviour | yes |
| unseen words | composition via reserved pieces |
| compatibility | custom vocab build |
| sequence-length impact | should stay near Unigram |
| risk over-seg | if too many short reserved pieces |
| risk under-seg | if reserved whole stems |
| risk wrong assumptions | reserved pieces not real units |
| novelty uncertainty | high |
| ablations | no reserved slots; vary slot fraction |
| falsification | no OOV fertility improvement; val BPC not better |

### C5. Statistical affix discovery + character fallback

| Field | Content |
|-------|---------|
| mechanism | Unsupervised affix mining; char/byte fallback for unresolved |
| baseline failure addressed | unseen fragmentation; rare short pieces |
| training-data requirements | train only |
| dependency on human rules | low |
| language-specific assumptions | minimal (threshold config) |
| computational cost | medium |
| deterministic behaviour | if fixed seed/thresholds |
| unseen words | strong via char fallback |
| compatibility | hybrid encode path |
| sequence-length impact | char fallback can inflate length |
| risk over-seg | high on fallback path |
| risk under-seg | if discovery merges too much |
| risk wrong assumptions | lower linguistic risk; statistical only |
| novelty uncertainty | medium–high |
| ablations | no discovery; no char fallback |
| falsification | sequence length exceeds cap; BPC worse under fixed updates |

### C6. Vocabulary regularization vs whole-word memorization

| Field | Content |
|-------|---------|
| mechanism | Cap whole-word pieces by frequency; force composition below threshold |
| baseline failure addressed | `apparent_whole_word_memorization`; poor rare relatives |
| training-data requirements | train counts |
| dependency on human rules | none required |
| language-specific assumptions | none |
| computational cost | low |
| deterministic behaviour | yes |
| unseen words | improved composition expected |
| compatibility | post-process vocab or train constraint |
| sequence-length impact | slight fertility ↑ possible |
| risk over-seg | if cap too aggressive |
| risk under-seg | low |
| risk wrong assumptions | low |
| novelty uncertainty | medium |
| ablations | cap off; vary threshold |
| falsification | no gain on rare/unseen fertility or val BPC |

### C7. Word-family-consistency regularization

| Field | Content |
|-------|---------|
| mechanism | Encourage shared pieces for surface families discovered statistically |
| baseline failure addressed | automatic family inconsistency |
| training-data requirements | train |
| dependency on human rules | optional review of family keys |
| language-specific assumptions | family discovery config |
| computational cost | medium |
| deterministic behaviour | depends on optimizer |
| unseen words | partial (if family member seen) |
| compatibility | custom objective |
| sequence-length impact | unclear |
| risk over-seg / under-seg | medium |
| risk wrong assumptions | families ≠ paradigms |
| novelty uncertainty | high |
| ablations | regularization weight 0 |
| falsification | family metric ↑ but LM BPC ↓ or unchanged |

### C8. Stochastic segmentation during LM training

| Field | Content |
|-------|---------|
| mechanism | Sample segmentations (e.g. Unigram lattice) per batch |
| baseline failure addressed | brittleness to one segmentation; some disagreement harm |
| training-data requirements | train |
| dependency on human rules | none |
| language-specific assumptions | none |
| computational cost | higher train cost |
| deterministic behaviour | **no** (unless locked sample seed) |
| unseen words | may help |
| compatibility | training-time only; eval may use mode |
| sequence-length impact | variable |
| risk over/under-seg | both via sampling |
| risk wrong assumptions | low linguistic |
| novelty uncertainty | medium (exists in literature — verify) |
| ablations | deterministic encode train |
| falsification | no val BPC gain vs deterministic Unigram |

### C9. Character or byte fallback for unresolved forms

| Field | Content |
|-------|---------|
| mechanism | Fallback path for OOV / low-confidence |
| baseline failure addressed | unk / shatter failure modes |
| training-data requirements | train alphabet |
| dependency on human rules | none |
| language-specific assumptions | none |
| computational cost | low |
| deterministic behaviour | yes |
| unseen words | complete coverage |
| compatibility | like byte-fallback SP |
| sequence-length impact | can increase sharply |
| risk over-seg | high |
| risk under-seg | low |
| risk wrong assumptions | low |
| novelty uncertainty | low (known pattern — verify citations later) |
| ablations | fallback off |
| falsification | fixed-update LM BPC worse due to length |

### Design selection rule

Select a final method only if:

1. it maps to **measured** Phase A failures;  
2. prior-art review does not make it a pure reimplementation without Chichewa protocol value;  
3. ablations (Phase E) show component necessity;  
4. pre-registered criteria (Phase D) pass on validation;  
5. holdout morphology metrics improve after freeze release.

---

# Phase D — Pre-registered evaluation plan

**Define before implementation. Do not retune criteria after seeing proposed-method results.**

## D.1 Tokenization-level (after human labels)

Script scaffolding: `scripts/tokenizers/evaluate_morphology_boundaries.py`

- boundary precision / recall / F1  
- exact segmentation accuracy  
- over- / under-segmentation rates  
- root/stem consistency (where annotated)  
- affix consistency (where annotated)  
- word-family consistency  
- unseen-form fertility  
- sequence-length inflation (tokens/char, fertility)  
- vocabulary utilization  
- unknown handling  

**Development set:** analysis and model selection among pre-registered variants only with care.  
**Locked holdout:** final morphology metrics after method freeze.

## D.2 Language-model evaluation

Compare proposed tokenizer against **character**, **BPE-8000**, **Unigram-8000** using the same:

- frozen corpus and splits  
- architecture_matched and parameter_matched tracks  
- fixed_characters and fixed_updates budgets (r2 calibrated)  
- seeds `{42, 1337, 2026}`  
- BPC / BPB (not raw token perplexity)  
- test-isolation policy  

Primary baseline to beat: **Unigram-8000**.

## D.3 Success criteria (**proposed — requires human approval**)

Status in config: `proposed_pending_human_approval`.

Candidate requirements (not yet approved):

1. Lower mean **validation** BPC than Unigram-8000  
2. Improvement direction consistent across three seeds  
3. Improvement survives parameter matching  
4. No unacceptable sequence-length increase (candidate: fertility ≤ +10% vs Unigram-8000)  
5. Improved morphology-boundary metrics on **locked** human-reviewed holdout  
6. No substantial source-specific regression (candidate: ≤ 0.02 BPC on bible/wiki means)  
7. Final LM evidence on **untouched test** only after method freeze  

**Do not** quietly change thresholds after observing results. Log approvals in the decision log.

---

# Phase E — Ablation matrix

Rule: **one component change at a time.**

| ID | Full system role | Component removed | Expected failure if component matters | Tokenizer metric | LM metric | Compute | Min seeds | Decision criterion |
|----|------------------|-------------------|----------------------------------------|------------------|-----------|---------|-----------|--------------------|
| E1 | full | learned affix candidate discovery | worse family/boundary stats | boundary F1, family consistency | val BPC | med | 3 | ΔBPC vs full |
| E2 | full | human-reviewed affix constraints | drop on annotated affix consistency | affix consistency | val BPC | low | 3 | ΔF1 and ΔBPC |
| E3 | full | merge penalties across candidate boundaries | more destructive merges | over-merge rate | val BPC | med | 3 | |
| E4 | full | whole-word frequency cap | more rare whole-word pieces | whole-word rate on rare band | val BPC rare subset | low | 3 | |
| E5 | full | stem consistency objective | family consistency ↓ | family metric | val BPC | med | 3 | |
| E6 | full | vocabulary partitioning | affix under-allocation | util of short pieces | val BPC | low | 3 | |
| E7 | full | stochastic segmentation | possible generalization drop | — | val BPC | high | 3 | |
| E8 | full | character fallback | unk / crash on odd forms | unk rate, OOV fertility | val BPC | low | 3 | |
| E9 | full | source balancing (if used) | domain gap ↑ | source fertility gap | bible/wiki val BPC | low | 3 | |

Exact “full system” is chosen only after Phase C selection; rows apply to the chosen family.

---

# Phase F — Threats to validity

| Threat | Why it matters | Mitigation |
|--------|----------------|------------|
| Small corpus size | unstable pieces, high variance | multi-seed; report std; cautious claims |
| Bible-heavy data | domain skew | source-stratified metrics |
| Source-domain imbalance | Wikipedia vs Bible ranking shifts | paired source reports |
| Imperfect cleaning | spurious fragments | residual analysis link; do not “fix” with silent edits |
| Missing original document boundaries | packing artifacts | document in split design |
| Chichewa-specific assumptions | non-transfer | separate config vs machinery |
| Annotator subjectivity | noisy gold | multi-annotator + adjudication |
| Limited annotators | low IAA power | report IAA; small claim set |
| Morphology ambiguity | multiple valid analyses | alternative_analysis field |
| Vocab-size confounding | 8k vs other sizes | fix 8k for LM matrix; analyze 1k–8k only diagnostically |
| Parameter-count confounding | arch vs param tracks | keep both tracks |
| Compute-budget confounding | chars vs updates | keep both budgets |
| Method tuning on validation | optimistic val | locked morphology holdout + final LM test once |
| Overfit morphology development set | inflated boundary F1 | holdout; limit peeking |
| No second-language replication | no Bantu-general claim | explicit non-claim |
| Licensing limitations | redistribution | follow SOURCE_ATTRIBUTION |
| Prior-art uncertainty | novelty/positioning | complete prior-art plan before claims |

---

# Phase G — Prior art

See `docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_PLAN.md`.  
No fabricated references. Contribution language only after verified table is filled.

---

## Tooling map

| Tool | Role |
|------|------|
| `analyze_baseline_morphology_failures.py` | Phase A diagnostics |
| `build_morphology_benchmark.py` | Phase B scaffold |
| `release_morphology_holdout.py` | gated holdout release |
| `evaluate_morphology_boundaries.py` | boundary metrics when labels exist |
| `audit_tokenizer_failures.py` | earlier failure candidate bank (related) |

---

## Execution boundary (this research package)

**Allowed:** validation-only tokenizer analysis; train/val mining; benchmark scaffolding; unit tests; reports.  

**Forbidden:** LM test evaluation; new LM training; MthandiziTokenizer training/implementation as production method; morphology holdout release; changing frozen splits or baseline tokenizer artifacts.

---

## Recommended next human decisions

1. Approve or revise success criteria thresholds (D-0003).  
2. Fund/assign annotators for development set; fix phenomenon tag inventory.  
3. Complete prior-art table (Phase G).  
4. Choose **one** Phase C family to prototype only after (1–3).  
5. Keep LM test and morphology holdout locked until method freeze.
