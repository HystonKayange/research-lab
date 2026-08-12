# Mthandizi tokenizer — method selection v0.1

**Status:** Prototype V1 selected (design only; **not implemented**)  
**Prior art:** `docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_v0_1.md`  
**Matrix:** `data/reports/mthandizi_tokenizer_prior_art_matrix_v0_1.json`  
**Success criteria:** frozen `SC1–SC9` (D-0008)  
**Date framing:** post morphology prep (active **195**); pre any Mthandizi code/training

---

## 1. Selection principles (applied)

Prefer a method that:

| Principle | Applied decision |
|-----------|------------------|
| No full Chichewa morphological analyzer | Reject Latin/MoVoC-style resource-heavy pipelines as V1 |
| Learn mostly from train corpus | Prefer unsupervised/statistical boundary cues |
| 195 labels primarily for evaluation | Forbid default supervised training on the 195 |
| Fixed ~8k vocabulary comparison | Drop-in tokenizer, not joint SSLM architecture |
| Exact reconstruction | Character residual + reversible encode/decode |
| Determinism where appropriate | Prefer deterministic MAP Unigram encode for LM runs; optional stochastic as ablation only |
| Clear fallback | Character units always available |
| Ablatable | Bias, affix inventory, residual each switchable |
| Distinct from MorphBPE / Morfessor-preseg / plain Unigram | Unigram base + weak statistical bias + explicit char residual; **not** MorphBPE clone |

---

## 2. Candidate family triage (from prior art)

| # | Family | Novelty risk | Selectable as V1? |
|---|--------|--------------|-------------------|
| 1 | Pre-seg + Unigram fallback | HIGH | Control/ablation only |
| 2 | Boundary-biased Unigram | MEDIUM | **Yes (core)** |
| 3 | Morphology-constrained BPE | HIGH | **No** (MorphBPE) |
| 4 | Hybrid affix/stem vocab | HIGH | Optional later |
| 5 | Statistical affix + char fallback | MEDIUM | **Yes (core)** |
| 6 | Whole-word memorization | MEDIUM | Optional efficiency knob only |
| 7 | Word-family consistency | MEDIUM | Metric/aux loss later, not V1 core |
| 8 | Stochastic segmentation | HIGH | Ablation only (Kudo 2018) |
| 9 | Char/byte fallback alone | HIGH | Component only |

**Previously suggested direction**  
`statistical affix/boundary discovery + boundary-biased Unigram + character fallback`  
→ Remains **defensible** as composition under Unigram backbone + weak supervision + fixed LM protocol.  
→ **Not** selected merely because previously suggested; selected because MorphBPE closes BPE-constraint space while Unigram remains our strongest Chichewa LM baseline and Bantu-relevant literature (Richburg 2020; Bostrom & Durrett 2020).

---

## 3. Shortlist (at most three)

### S1 — **Prototype V1 (recommended)**  
**Name:** *StatBound-Unigram* (statistical boundary-biased Unigram with character residual)  
**Combines families:** 2 + 5 + 9  

### S2 — **Strong literature control**  
**Name:** *Unsupervised-preseg → Unigram residual*  
**Family:** 1 (Morfessor-like / unsupervised morph pre-seg + Unigram on residual)  
**Role:** Not novelty claim; required scientific control against classic morph pipelines.

### S3 — **Minimal bias ablation sibling**  
**Name:** *Plain Unigram-8000 + optional char-only OOV emphasis*  
**Families:** baseline + 9  
**Role:** Isolates whether any bias term helps beyond our existing primary baseline.

---

## 4. Detailed shortlist cards

### S1 — StatBound-Unigram (Prototype V1)

**Algorithm sketch (design level only)**

1. **Train corpus only:** estimate lightweight statistical boundary/affix cues from surface co-occurrence (e.g., high-frequency prefix/suffix candidates, optional unsupervised morph tool **without** using the 195 gold labels as training targets).  
2. **Boundary bias in Unigram training:** penalize or down-weight candidate subwords / EM steps that systematically cross high-confidence statistical boundaries (soft bias preferred over hard MorphBPE-style bans when boundaries are noisy).  
3. **Vocabulary:** Unigram LM vocabulary at **8000** total units (matched to baselines), retaining full character inventory for reconstruction.  
4. **Inference:** deterministic Unigram segmentation (SentencePiece-style MAP); exact detokenization / reconstructibility required.  
5. **Fallback:** characters for residual mass / rare forms (always on).  
6. **Eval:** SC1–SC3 LM matrix; SC4 on active 195; SC5–SC6 safeguards; SC7 ablations below.

**Expected novelty:** **Provisional composition** — not a new primitive. Distinct from MorphBPE by Unigram base + weak statistical (not full-corpus gold) boundaries + explicit residual policy under frozen Chichewa LM protocol.

**Strongest prior-art overlap:** Kudo 2018 (Unigram); MorphBPE (constraint *idea*, different base/supervision); unsupervised morph (Mager 2022); Bostrom & Durrett 2020; Richburg 2020 (Swahili Unigram).

**Why it could work for Chichewa**

- Unigram already leads our validation LM baselines.  
- Chichewa agglutination has frequent prefix/suffix patterns visible in surface statistics.  
- Avoids nonexistent large analyzer.  
- SC4 development set can measure boundary F1 without training on it.

**Expected weaknesses**

- Statistical boundaries may be wrong (over-split stems; miss orthographic variants like `ŵ`).  
- Soft bias may be too weak for SC4 +0.03.  
- Risk of fertility increase (SC5).  
- Literature shows morph-aware methods can fail SC1 while helping morph metrics (PARTIAL).

**Implementation complexity:** Medium (custom Unigram training objective / data weighting; not full new architecture).

**Required hyperparameters (to freeze later, pre-results)**

- Vocabulary size = 8000 (matched)  
- Boundary-bias strength λ  
- Affix/boundary candidate frequency thresholds  
- Minimum affix length / stop-list of spurious fragments  
- Character residual always enabled  
- Seeds for any stochastic training steps (prefer 0 stochasticity in primary runs)

**Necessary ablations (SC7)**

| Ablation | Removes |
|----------|---------|
| A0 | Full StatBound-Unigram |
| A1 | No boundary bias (≈ plain Unigram-8000) |
| A2 | No statistical affix inventory (bias off or uniform) |
| A3 | Hard vs soft boundary constraint (if both implemented) |
| A4 | Stochastic subword regularization on/off (Candidate 8) |

**Leakage risk:** **Low–medium** if 195 never used for training targets/vocab seeds; **high** if gold segments are injected into inventory. V1 rule: **no gold 195 in train.**

---

### S2 — Unsupervised pre-seg + Unigram residual (control)

**Algorithm sketch:** Run unsupervised morphological segmentation on train words → treat morph-like pieces as pre-tokens → train Unigram on residual/pre-token stream → encode with same pipeline.

**Expected novelty:** **Unsupported** as main claim (classic family).

**Strongest overlap:** Mager 2022; MoVoC-related hybrids; Saleva & Lignos 2021.

**Why useful:** Establishes whether simple pre-seg already beats Unigram; prevents false novelty for S1.

**Weaknesses:** Pipeline brittleness; double segmentation errors; may hurt SC1 (Saleva).

**Complexity:** Medium–low with off-the-shelf unsupervised morph tools.  
**Ablations:** morph tool on/off; Unigram vs BPE residual.  
**Leakage risk:** Low if unsupervised only.

---

### S3 — Plain Unigram-8000 (+ residual emphasis)

**Algorithm sketch:** Existing baseline; optional stronger character coverage diagnostics.

**Expected novelty:** None (baseline).

**Role:** SC1 reference; A1 ablation target for S1.

---

## 5. Recommended Prototype V1

### Decision

**Select S1 — StatBound-Unigram** as **Prototype V1** for future implementation.

**Do not implement yet** in this phase (criteria freeze + prior art + selection only).

### Why literature supports a defensible distinction

| Claim | Supported? |
|-------|------------|
| Pure MorphBPE-on-Chichewa is novel | **No** |
| Pure Unigram is novel | **No** |
| Pure stochastic segmentation is novel | **No** |
| Unigram + **weak statistical boundary bias** + char residual under **fixed 8k Chichewa LM BPC + active morph F1** protocol is a coherent, ablatable experiment with incomplete prior packing | **Yes (provisional)** |

Distinction axes vs MorphBPE:

1. **Base model:** Unigram (primary Chichewa LM baseline) vs BPE.  
2. **Supervision:** corpus-statistical / unsupervised cues vs full-corpus morpheme boundaries.  
3. **Fallback:** explicit character residual policy stressed for low-resource OOV.  
4. **Evaluation:** frozen SC1–SC9 including active 195 morph F1 and matched compute matrix.

### Novelty claim status

**`provisional`**

Not `strong`. If ablations show all gains come from plain Unigram or from S2 pre-seg, claim must be reduced to negative/partial and reported honestly.

### If V1 fails

Revised directions (not implemented now):

1. Report **negative/partial** under frozen criteria (allowed and required).  
2. Consider architecture-level segmental LM (Meyer & Buys) only as a **separate** research track (breaks current drop-in tokenizer protocol).  
3. Consider limited weak supervision **explicitly logged** (e.g., tiny seed affix list hand-built without using 195 gold segmentations).  
4. Do **not** silently retune SC thresholds.

---

## 6. What we explicitly reject for V1

| Rejected | Reason |
|----------|--------|
| Morphology-constrained BPE as flagship | MorphBPE (Asgari et al. 2026) |
| Supervised morph vocab from 195 gold | Leakage + MoVoC-style requires larger annotation |
| Latin-style lexical resource pipeline | Resource mismatch (Hudspeth 2026) |
| Stochastic segmentation as main idea | Kudo 2018 |
| Character-only method | Already baseline |
| Joint SSLM as drop-in V1 | Violates fixed tokenizer→LM matrix without protocol change |

---

## 7. Implementation gate (future)

Only after this selection document is accepted:

1. Implement StatBound-Unigram **without** reading holdout or LM test.  
2. Freeze hyperparameters **before** large LM sweeps where possible.  
3. Run ablations A0–A4.  
4. Score SC1–SC6; label SC4 as DEVELOPMENT.  
5. Write development conclusions **before** any holdout unlock (SC8) or LM test (SC9).

---

## 8. Concise end state

| Item | Status |
|------|--------|
| Papers reviewed (verified primary) | **11** (8 must-include + 3 additional) |
| Bantu/African-relevant papers | Richburg 2020 (Swahili); Meyer & Buys 2022 (Nguni); MoVoC 2025; Lundin 2026 |
| High novelty-risk families | **1, 3, 4, 8, 9** |
| Shortlist | S1 StatBound-Unigram; S2 unsupervised pre-seg control; S3 plain Unigram |
| Recommended Prototype V1 | **StatBound-Unigram (S1)** |
| Novelty claim status | **provisional** |
| Morphology holdout accessed | **false** |
| LM test evaluations | **0** |
| Tokenizer implementation | **false** |
