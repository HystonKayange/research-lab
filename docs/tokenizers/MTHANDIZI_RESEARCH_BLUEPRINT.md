# Research blueprint: morphology-aware hybrid tokenization for Chichewa LM

**Status:** design only — **no MthandiziTokenizer implementation in this phase.**  
**Corpus case study:** Chichewa (Chichewa Corpus v0.1).  
**Do not** generalize conclusions to all Bantu languages from this work alone.  
**Do not** access the LM **test** split for method design, tokenizer training, or selection.

---

## 1. Core research question

Under fixed data, parameter, and compute budgets:

> Can a morphology-aware hybrid tokenization method improve Chichewa language modelling over SentencePiece Unigram and BPE while preserving efficient sequence lengths and generalization to unseen word forms?

This question is **empirical**. The proposed method starts with **no assumed advantage**. Baselines (character, BPE-8000, Unigram-8000) already provide controlled LM validation evidence; Unigram-8000 is the **provisional validation leader** only.

---

## 2. What is already established (validation only)

LM Baselines v0.1 r2 (36 scientific runs; `test_ready: true`; **test not evaluated**):

| Comparison group | character BPC | BPE-8000 BPC | Unigram-8000 BPC |
|------------------|---------------|--------------|------------------|
| architecture_matched × fixed_characters | 1.4779 | 1.4389 | **1.4313** |
| architecture_matched × fixed_updates | 1.8868 | 1.4567 | **1.4434** |
| parameter_matched × fixed_characters | 1.4779 | 1.4463 | **1.4371** |
| parameter_matched × fixed_updates | 1.8868 | 1.4987 | **1.4793** |

Tokenizer baseline metrics (validation fertility; not LM quality):

| Tokenizer | Val fertility (tokens/word) | Notes |
|-----------|----------------------------|--------|
| character | ~7.14 | Not a subword winner criterion |
| BPE-8000 | ~1.63 | Selected subword BPE |
| Unigram-8000 | slightly lower fertility than BPE at same size | Selected subword Unigram |

**Interpretation discipline**

- Lower validation BPC for Unigram-8000 under these budgets does **not** prove morphological superiority.
- Fertility alone does not prove morphological adequacy.
- Source-specific validation (Bible vs Wikipedia) shows domain gaps; domain must remain a controlled factor.

---

## 3. Failure hypotheses to test (not assert)

Phase A treats these as **hypotheses** for measurement:

| ID | Hypothesis | Falsifiable if… |
|----|------------|-----------------|
| H1 | BPE and Unigram often **disagree** on productive Chichewa word forms | Disagreement rate is low on families / long words / rare forms |
| H2 | High **fragmentation** concentrates on long / rare / unseen-validation forms | Fragmentation is uniform across frequency bands |
| H3 | Some frequent stems are **over-merged** (one opaque token) while rare relatives are shattered | Stem-relative fertility variance is small |
| H4 | Segmentation is **inconsistent within word families** (shared stem not reused as a piece) | Family-level shared-piece rate is high |
| H5 | Failures involving `ŵ` or mixed orthography are **representation** issues, not morphology | `ŵ` tokens behave like other rare characters |
| H6 | Segmentation failures that look morphological **do not always** track poorer LM behaviour | High-disagreement words do not co-occur with higher local loss / worse OOV handling |
| H7 | A hybrid morphology-aware method helps **only** on a measurable subset of failures | Gains vanish when that subset is excluded from analysis |

Phase A produces **automatic** diagnostics. Claims that a failure is “genuinely morphological” require **human** (or verified morph analyzer) labels on a stratified sample — fields reserved in the candidate schema.

---

## 4. Phase A — Baseline tokenization failure audit

### 4.1 Allowed inputs

- Frozen **train** and **validation** splits only  
- Existing tokenizer artifacts (character; BPE/Unigram 1k–8k)  
- Existing morphology probe candidates  
- Existing tokenizer and LM **validation** reports  

### 4.2 Forbidden

- LM **test** split  
- Retraining LM matrix  
- Implementing the hybrid tokenizer as production code in this phase  
- Filling `human_*` fields with invented morphology  

### 4.3 Mining goals

Find surface forms (and short contexts) where BPE and Unigram (especially 8000) produce **meaningfully different** segmentations, prioritized by:

- frequent word families  
- rare forms  
- validation forms **unseen** in train  
- long words  
- words containing `ŵ`  
- mixed Chichewa–English surface patterns (heuristic)  
- source-specific items (bible / wikipedia)  
- high fragment count  
- single whole-word tokens  
- inconsistent family segmentation  

### 4.4 Candidate record schema

See `data/reports/tokenizer_failure_audit_v0_1/failure_candidates.jsonl`. Each row includes automatic tags; human morphology fields remain `null` until annotated.

### 4.5 Automatic diagnostic tags (non-morphological claims)

Tags are **operational**, not linguistic verdicts:

- `bpe_unigram_disagree` — piece sequences differ (8000 or multi-vocab)  
- `high_fragmentation` — fertility ≥ threshold for a subword model  
- `whole_word_single_token` — word is one non-atomic piece after ▁ strip  
- `contains_w_hat` — surface contains `ŵ`/`Ŵ`  
- `unseen_in_train` — validation form absent from train word inventory  
- `rare_train` — train frequency ≤ threshold  
- `frequent_train` — train frequency ≥ threshold  
- `long_word` — character length ≥ threshold  
- `mixed_orthography_heuristic` — ASCII letter runs plus non-ASCII (diagnostic only)  
- `family_stem_hit` — matches configured stem list  
- `family_segmentation_inconsistent` — stem-sharing words do not share a stem piece  
- `fertility_asymmetric` — |BPE fertility − Unigram fertility| ≥ threshold  
- `vocab_size_sensitive` — segmentation changes materially across 1k→8k  
- `source_bible` / `source_wikipedia`  

### 4.6 Relating failures to LM behaviour (without test)

Use **only**:

- aggregate validation BPC/BPB by tokenizer (existing matrix)  
- validation fertility / sequence length (tokenizer eval)  
- optional future: validation **per-line** loss on locked checkpoints (still validation only)  

Do **not** select tokenizer design choices on the LM test set.

---

## 5. When is a failure “morphological”?

| Level | Evidence required | Phase |
|-------|-------------------|-------|
| Surface disagreement | Automatic BPE≠Unigram / fertility tags | A |
| Representational inefficiency | High fertility, long sequences, rare pieces | A |
| Putative morphological boundary error | Human segments disagree with both systems on morpheme-like units | B (annotation) |
| Causal LM impact | Controlled ablations; same data/param/compute; validation + final locked test | C–D |

Until human annotation, reports must use cautious language:

- “segmentation disagreement”  
- “high fragmentation under this vocabulary”  
- “consistent with a morphological analysis *if* annotators confirm…”  

Avoid: *linguistically correct*, *morphology preserving*, *Bantu-general*, *novel*, *state of the art* without evidence.

---

## 6. Proposed method (design sketch only)

**Name working title:** MthandiziTokenizer (implementation deferred).

**Idea (to be justified only if Phase A–B support it):** a **hybrid** tokenization stack that:

1. **Keeps** a data-driven subword backbone (Unigram or BPE inventory trained on train only).  
2. **Injects** a small, audited inventory of high-confidence **stem / affix** pieces derived from (a) annotated failure samples, (b) high-precision heuristics validated against annotation, not from the LM test set.  
3. **Constrains** decode/segment so that, when a surface matches inventory, boundaries preferred by the inventory win over pure likelihood **only** under pre-registered rules.  
4. **Falls back** to the backbone for unmatched forms (no forced wrong morphology).  
5. **Preserves** sequence efficiency: fertility and tokens/char must remain competitive with Unigram-8000 on validation; character-level explosion is a failure mode.

### 6.1 Mechanism ↔ measured failure map

| Measured failure class | Candidate mechanism | Must measure |
|------------------------|---------------------|--------------|
| Family-inconsistent splits | Shared stem piece forcing / merge rules | Family agreement rate ↑ without fertility blow-up |
| Rare form shattered; frequent relative merged | Productive composition over whole-word rare tokens | Unseen-validation fertility ↓; LM val BPC on rare subset |
| Prefix/suffix over-fragmentation | Affix seed pieces in SP user-defined symbols or post-hoc resegment | Affix-boundary F1 vs human sample |
| Opaque whole-word rare tokens | Discourage low-count whole-word pieces | Type coverage of productive paradigms |
| `ŵ` / unicode edge cases | Keep identity normalization; ensure inventory and SP retain codepoints | Zero regression on `ŵ` word fertility vs baseline |
| Domain (Bible vs Wikipedia) mismatch | Domain-stratified reporting; no single-domain tuning | Leaders stable across sources on val |

Mechanisms that do **not** map to a measured failure class should not be implemented.

---

## 7. Evaluation design without overfitting

### 7.1 Data roles (locked)

| Split | Tokenizer training | Hyperparameter / early design | Final LM report |
|-------|--------------------|-------------------------------|-----------------|
| train | yes | yes | train only |
| validation | **no** vocab induction | yes (metrics, selection among pre-registered variants) | report |
| test | **no** | **no** | single final unlock |

### 7.2 Pre-registration (before hybrid training)

1. Primary LM metric: **validation BPC** (bits per character), then locked **test BPC** once.  
2. Secondary: BPB, fertility, tokens/char, unseen-validation type fertility, family agreement (annotated subset).  
3. Comparison groups: same four LM matrix axes (arch/param × chars/updates).  
4. Seeds: same three seeds as baselines where feasible.  
5. Budget: same calibrated character/update budgets as r2 unless a change is justified and re-calibrated on validation only.  
6. **One** primary hybrid configuration for test unlock; exploratory variants stay validation-only.

### 7.3 Nested protocol

1. Phase A automatic audit (this phase).  
2. Phase B stratified human annotation on a fixed candidate sample (morph tags).  
3. Phase C ablations on **validation** only (inventory size, constraint strength).  
4. Phase D full scientific matrix vs BPE-8000 / Unigram-8000 / character.  
5. Phase E explicit test authorization (same discipline as LM baselines).

### 7.4 Overfitting controls

- No test peeking for piece inventory design.  
- Annotation set disjoint from any “dev2” if introduced.  
- Report **all** pre-registered ablations, including null results.  
- Require improvement on **both** architecture-matched and parameter-matched tracks **or** document track-specific limits.  
- Require no large fertility regression (threshold pre-registered, e.g. mean val fertility within +X% of Unigram-8000).

---

## 8. Deliverables by phase

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **A** | Failure candidates JSONL, aggregate diagnostics, mechanism map draft | Automatic only; no hybrid code |
| **B** | Annotated morphology sample + inter-annotator agreement | Human fields filled for sample |
| **C** | Prototype hybrid + val-only ablations | Beats or matches Unigram on pre-registered metrics **or** documents failure |
| **D** | Full LM matrix (no test) | Integrity audit like r2 |
| **E** | Test unlock | Explicit operator authorization |

---

## 9. Tooling

| Tool | Role |
|------|------|
| `scripts/tokenizers/audit_tokenizer_failures.py` | Phase A mining + aggregates |
| `scripts/tokenizers/inspect_tokenizations.py` | Existing examples + probes |
| `scripts/tokenizers/evaluate_tokenizers.py` | Fertility / coverage baselines |
| `scripts/models/audit_lm_validation_results.py` | LM validation integrity (no test) |

---

## 10. Phase A empirical snapshot (first run)

Tool: `scripts/tokenizers/audit_tokenizer_failures.py`  
Outputs: `data/reports/tokenizer_failure_audit_v0_1/`

| Quantity | Value (this run) | Reading |
|----------|------------------|---------|
| Word surfaces compared | ~12,055 | Prioritized pool (not full type inventory) |
| BPE-8000 ≠ Unigram-8000 in pool | ~6,436 | Disagreement is common on the prioritized pool |
| Candidate bank size | 2,500 | Ranked by automatic priority |
| High fragmentation in bank | majority of bank | Bank is skewed toward hard forms by design |
| Family-inconsistent (heuristic) | ~151 surfaces | Needs human confirmation |
| `ŵ` tagged in bank | tens of forms | Small but orthographically important set |
| Human morphology fields | all `null` | Annotation not done |
| Test split accessed | **false** | Required |

**Important:** High disagreement on a **prioritized hard pool** does not mean half of all corpus tokens disagree. Pool rates are not corpus prevalence.

### Implications for the research question

1. **Where standard methods diverge:** Long, rare, validation-unseen, and family-related surfaces—not only frequent closed-class words.  
2. **Morphological vs not:** Automatic tags **cannot** settle H2–H4; Phase B annotation is mandatory before claiming morphology.  
3. **LM correlation:** Unigram-8000’s better **validation** BPC coexists with frequent segmentation disagreements with BPE; disagreement alone does not explain the BPC gap. Future work should measure local validation loss on disagreeing types (still no test).  
4. **Mechanism filter:** Prefer mechanisms tied to `family_segmentation_inconsistent`, `unseen_in_train` fragmentation, and asymmetric fertility—not generic “add morphology.”  
5. **Evaluation:** Keep the four-group LM matrix and locked test protocol from LM baselines v0.1.

---

## 11. Immediate next step

1. Review `data/reports/tokenizer_failure_audit_v0_1/FAILURE_AUDIT_REPORT.md`.  
2. Design Phase B stratified annotation sample (size, tag inventory, IAA plan).  
3. **Do not** implement MthandiziTokenizer until Phase A is reviewed and Phase B scope is fixed.
