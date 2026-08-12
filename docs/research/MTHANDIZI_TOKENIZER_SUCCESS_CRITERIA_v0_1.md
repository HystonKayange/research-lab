# Mthandizi tokenizer — success criteria v0.1

**Status: `frozen_pre_implementation`**  
**Frozen before:** MthandiziTokenizer design selection, implementation, training, and hyperparameter search  
**Decision log:** `D-0008` in `MTHANDIZI_TOKENIZER_DECISION_LOG.md`  
**Machine-readable twin:** `configs/tokenizers/mthandizi_success_criteria_v0_1.json`

These criteria are **frozen**. They must **not** be silently revised after observing proposed-method results.  
Any change requires a new dated decision-log entry with `changes_registered_eval_protocol: yes`.

---

## 0. Experimental framing

**Research question.** Under fixed data, parameter, and compute conditions, can a morphology-aware tokenizer for Chichewa improve language-model efficiency/performance and morphological boundary quality compared with standard tokenization baselines?

**Existing baselines (v0.1):**

| Tokenizer | Role |
|-----------|------|
| Character | Efficiency / fragmentation diagnostic; **not** a directly equivalent morphology segmentation baseline |
| SentencePiece **BPE-8000** | Standard subword baseline |
| SentencePiece **Unigram-8000** | **Strongest validation LM baseline** → **primary standard-subword comparator** |

**Constraints (non-negotiable during development):**

| Resource | Status during design / selection / ablations |
|----------|-----------------------------------------------|
| Morphology holdout (~80 items) | **LOCKED** — inaccessible |
| LM test set | **UNTOUCHED** — no evaluation for selection |
| MthandiziTokenizer | **Not yet implemented** at criteria freeze |
| Human morphology labels | Not altered to fit method results |

---

## 1. Comparison hierarchy

### 1.1 Primary LM condition (drives SC1)

| Factor | Frozen value |
|--------|----------------|
| Parameter track | **parameter_matched** |
| Budget policy | **fixed_characters** |
| Corpus | frozen Chichewa Corpus v0.1 |
| Split | frozen train / validation (same as baselines) |
| Effective-epoch / character budget | same as baselines r2 matrix (**30** effective epochs; train_characters = **138,713,970**) |
| Model family | same as baselines |
| Architecture | **parameter-matched** |
| Seeds | **42, 1337, 2026** (3 fixed seeds) |
| Primary metric | **validation bits per character (BPC)** |
| Primary baseline | **Unigram-8000** |
| Other baselines (report) | character, BPE-8000 |
| Test isolation | LM **test** not used for development or selection |

Do **not** use raw token perplexity as a primary cross-tokenizer metric.

### 1.2 Secondary / diagnostic conditions

| Condition | Role |
|-----------|------|
| architecture_matched × fixed_characters | **SC2** — robustness; does **not** replace SC1 |
| parameter_matched × fixed_updates | **SC3** — compute/tokenization diagnostic |
| architecture_matched × fixed_updates | **SC3** — compute/tokenization diagnostic |

Report mean ± standard deviation over the three seeds for all LM conditions that are run.

---

## 2. Frozen criteria SC1–SC9

### SC1 — Primary LM comparison

**Condition:** parameter_matched × fixed_characters (primary).  
**Compare:** MthandiziTokenizer vs Unigram-8000 (same corpus, split, character budget, model family, parameter-matched architecture, seeds 42/1337/2026).

**Primary metric:** validation BPC (mean over seeds).

**Pass requires both:**

1. Proposed tokenizer has **strictly lower mean validation BPC** than Unigram-8000.  
2. At least **2 of 3** seeds individually improve (lower BPC) over the corresponding Unigram-8000 seed runs.

**Forbidden:** using LM **test** results for development or selection.

---

### SC2 — Architecture-matched robustness

**Condition:** architecture_matched × fixed_characters.

**Role:** secondary evidence only; **must not replace SC1**.

**Report:** mean ± std validation BPC over 3 seeds for proposed and baselines.

**Pass (secondary):** mean validation BPC not worse than Unigram-8000 under this condition by more than a documented failure narrative if SC1 already passed — SC2 is **required to report**, not a substitute primary gate.  
For outcome labels (STRONG / PARTIAL / NEGATIVE), SC2 informs robustness narrative; **STRONG SUCCESS does not require SC2 to beat Unigram**, but SC2 results must be fully reported.

---

### SC3 — Fixed-update diagnostic

Evaluate and report both:

- parameter_matched × fixed_updates  
- architecture_matched × fixed_updates  

**Role:** compute / tokenization diagnostics only — **not** the primary success criterion.

---

### SC4 — Morphological boundary quality (DEVELOPMENT-set evidence)

**Gold set (active development only):**

`data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl`

| Property | Value |
|----------|--------|
| Active items | **195** |
| Excluded from scoring | 5 unsuitable items (never included) |
| Annotator | single native Chichewa speaker (`annotator_a`) |
| Holdout | **not used** for SC4 |

**Metrics:**

- boundary precision  
- boundary recall  
- boundary F1  
- exact segmentation match  
- boundary Jaccard  

**Comparators:** BPE-8000, Unigram-8000, MthandiziTokenizer.  
Character tokenization may be reported **descriptively** only (not a directly equivalent morphology segmentation baseline).

**Pass (development evidence):** MthandiziTokenizer **boundary F1** exceeds the **strongest standard subword baseline** (max of BPE-8000 and Unigram-8000 F1 on the same active set) by at least **+0.03 absolute**.

**Label explicitly:** **DEVELOPMENT-set evidence** — tokenizer design may use this benchmark; it is **not** confirmatory holdout evidence.

**Do not** inspect or unlock the morphology holdout for SC4.

---

### SC5 — Tokenization efficiency

**Measure (report all):**

- tokens per character  
- word fertility  
- sequence-length expansion  
- single-character fragment rate  
- whole-word rate where applicable  

**Pass:** MthandiziTokenizer must **not** increase **tokens-per-character** by more than **+10% relative** to Unigram-8000 (same evaluation split as primary LM condition), **unless** the primary LM criterion (SC1) improves enough that the trade-off is justified **and** documented as an explicit exception in the decision log **before** claiming success.

If the +10% threshold is exceeded **without** a pre-logged justified exception: mark **SC5 failed**.  
**Do not** change the 10% threshold after seeing proposed-tokenizer results.

---

### SC6 — Source robustness

Under the **primary** condition (parameter_matched × fixed_characters), report validation BPC separately for:

- Bible  
- Wikipedia  

**Pass:** **no source** may regress by more than **0.02 absolute BPC** relative to Unigram-8000 under that primary condition.

Report source results **even if** aggregate BPC improves.

---

### SC7 — Ablations

Any final MthandiziTokenizer design with multiple mechanisms **must** be ablated.

Examples of components (only if present in the selected design):

- statistical affix discovery  
- morphology / boundary bias  
- Unigram fallback  
- character fallback  

Evaluate meaningful component removals so improvements cannot be attributed to an unidentified component.

**Do not invent ablations until the actual method is selected.**  
Ablations use development resources only (no holdout, no LM test for selection).

---

### SC8 — Morphology holdout

The locked morphology holdout must remain **inaccessible** during:

- method design  
- hyperparameter selection  
- development benchmark analysis  
- ablations  

Only **after** the tokenizer algorithm and hyperparameters are frozen may the holdout be unlocked **once** for confirmatory morphology evaluation, via the existing release protocol, with a decision-log entry recording the unlock.

Holdout metrics are **confirmatory**, not for method selection.

---

### SC9 — LM test

The LM test set remains **untouched** during all model/tokenizer development.

After **all** of:

1. tokenizer design frozen  
2. hyperparameters frozen  
3. ablations complete  
4. development conclusions written  

perform **one** final test evaluation for all required baseline and proposed configurations.

**Do not** select or modify the method based on test performance.  
Test results are for final reporting only.

---

## 3. Interpretation rules (outcomes)

### STRONG SUCCESS

- **SC1** passes  
- **SC4** passes  
- Efficiency / source safeguards pass (**SC5** and **SC6**)

### PARTIAL RESULT

- Morphology improves substantially (**SC4** passes) but LM BPC does **not** beat Unigram (**SC1** fails), **or**  
- LM BPC improves (**SC1** passes) but morphology boundary quality does **not** meet SC4  

### NEGATIVE RESULT

- Proposed tokenizer does **not** improve the primary LM criterion (**SC1** fails) **and** provides no convincing morphology / efficiency advantage  

A **negative result must be preserved and reported**.  
It is **forbidden** to change success criteria after results are known to convert a negative into a success.

---

## 4. Methodology notes (frozen context)

Document and respect:

1. Morphology development annotations are from **one** native Chichewa annotator (`annotator_a`).  
2. Self-consistency evaluation is planned (delayed re-annotation of 25 items); this is **not** human–human IAA.  
3. Confidence metadata includes unresolved raw string values (`high` / `low`); confidence is **not** an evaluation metric for SC1–SC9.  
4. **Excluded** records (5) are **not** included in morphology scores; active development set size is **195**.  
5. The ~**80**-item morphology holdout remains **locked** until SC8 unlock.  
6. Canonical reviewed provenance remains 200 rows; benchmark scoring uses **active 195**.  
7. **MasakhaNER** is reserved for later external downstream evaluation and is **not** part of tokenizer development success criteria.  
8. Unigram-8000 is the primary standard-subword LM comparator; BPE-8000 remains a required morphology/LM reporter.

---

## 5. Required reporting (regardless of outcome)

- Mean ± std validation BPC over seeds for every LM condition run  
- Per-seed ΔBPC (proposed − Unigram) under SC1  
- SC2 architecture-matched means ± std  
- SC3 fixed-update diagnostics  
- Fertility / tokens-per-character / sequence expansion (SC5)  
- Source-specific BPC (SC6)  
- Morphology boundary metrics on **active 195** (SC4), labeled DEVELOPMENT  
- Ablation table once method is selected (SC7)  
- Explicit statement: holdout locked / unlocked status; LM test untouched / final-only  
- Outcome label: STRONG SUCCESS | PARTIAL RESULT | NEGATIVE RESULT  

---

## 6. Failure modes that block success claims

- Using LM **test** during design, selection, or threshold tuning  
- Releasing morphology holdout before method + hyperparameter freeze  
- Changing SC thresholds after seeing proposed-method numbers without decision-log entry  
- Including excluded items in morphology scores  
- Claiming morphological correctness from BPE/Unigram/automatic tags alone  
- Using character tokenizer as an equivalent morphology segmentation baseline for SC4 pass/fail  
- Comparing raw token perplexity as primary evidence  
- Implementing or training MthandiziTokenizer **before** this freeze (historical: freeze is now in place; implementation may proceed only after this document)  

---

## 7. Freeze checklist

- [x] SC1–SC9 defined with numerical thresholds where applicable  
- [x] Primary comparison hierarchy confirmed (parameter_matched × fixed_characters; Unigram-8000)  
- [x] Active morphology path and n=195 documented  
- [x] Holdout and LM test isolation documented  
- [x] Outcome labels STRONG / PARTIAL / NEGATIVE defined  
- [x] Decision log entry `D-0008` — criteria frozen pre-implementation  
- [x] Config `configs/tokenizers/mthandizi_success_criteria_v0_1.json` written with `approval_status: frozen_pre_implementation`

**Status: `frozen_pre_implementation`.**  
Method development may begin **after** this freeze; criteria must not be retuned to fit results.
