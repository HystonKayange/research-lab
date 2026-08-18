# Empirical paper / technical-report charter v0.1

**Status:** approved direction (D-0016)  
**Date:** 2026-08-18  
**Mode:** consolidate existing evidence; no new tokenizer  

Morphology holdout: **LOCKED**  
LM test: **LOCKED**  
StatBound V1: **CLOSED** (negative)  
Successor method: **not authorized**

This charter turns finished experiments into a research record. It does not authorize V2.

---

## 1. Research claim

### Conservative

On a frozen conservative Level-B Chichewa development benchmark, Unigram-8000 aligns better with morphological boundaries than BPE-8000 but systematically undersegments; a pre-registered unsupervised boundary-productivity reranker neither selected unused n-best alternatives nor improved matched language-model BPC.

### Slightly stronger

Unigram-8000 outperforms BPE-8000 on conservative Chichewa morphological boundary F1, and its n-best=16 list already contains most missing inflectional prefix cuts while many final-vowel and internal cuts are absent; a simple train-only productivity reranker does not exploit that structure and does not help primary LM BPC.

### Recommended (use this)

Unigram substantially outperforms BPE on a conservative native-speaker Chichewa morphology benchmark but undersegments; its n-best list already contains most missing prefix/TAM/NEG structure, while many final-vowel and internal boundaries are absent, and a pre-registered unsupervised boundary-productivity reranker fails both to select the unused alternatives and to improve matched LM BPC.

Do not add “first,” “novel tokenizer,” or “morphology-aware LM win.”

---

## 2. Research questions (what we actually measured)

**RQ1.** Under a frozen 8k vocabulary and the same corpus, how do BPE and Unigram compare on conservative Level-B morphological boundary quality for Chichewa?

**RQ2.** When Unigram misses gold boundaries, where are those misses (left-edge inflection vs final vowel vs internal), and how much of each class is already present in Unigram n-best=16?

**RQ3.** Can a pre-registered, train-only statistical-boundary reranker of Unigram n-best improve development morphology F1 or primary matched LM BPC relative to ordinary Unigram?

**RQ4.** Do morphological boundary F1 and language-model BPC move together under this protocol?

RQ3 is a **negative-result** question, not a method-sales question.  
RQ4 is answered only weakly: the reranker was a no-op on the benchmark, so Phase F is not a test of “more morphological ⇒ better BPC.” The honest RQ4 finding is that we must not treat the two objectives as identical, and that a failed morphology intervention produced no meaningful BPC change.

---

## 3. GitHub README story (target outline)

Rewrite the top-level README around findings, not around a proposed method.

```text
# Mthandizi — controlled Chichewa tokenization experiments

1.  What this repository is
2.  Motivation (low-resource Bantu tokenization; Unigram vs BPE; do not assume morph = LM)
3.  One-sentence finding
4.  Data
    - frozen Chichewa corpus v0.1 (Bible + Wikipedia)
    - splits and locks
5.  Morphology benchmark
    - Level-B conservative rubric
    - 162 active / 33 excluded
    - single native-speaker adjudicator
    - holdout locked
6.  Frozen evaluation protocol
    - SC1–SC9 (as registered)
    - what may be tuned on development
    - what must stay locked
7.  Tokenizer baselines
    - Character / BPE8k / Unigram8k
    - Unigram is the strongest standard baseline
8.  StatBound-Unigram V1
    - what it was
    - what it was not allowed to use
    - closed negative result (link Phase C/F)
9.  N-best oracle and error anatomy
    - availability vs selection
    - prefix vs final-vowel vs internal
    - why the oracle is not a target
10. Current conclusions
11. Limitations
12. Reproducibility
    - how to rerun Phase C, diagnostic, oracle, Phase F
    - hashes, seeds, configs
    - decision log
13. Future work (prefix-stack recovery only; not started)
14. Citation / status (unpublished draft)
```

The README must not still ask “can we invent a better tokenizer?” as if that were the live implementation goal.

---

## 4. Smallest set of tables and figures

Prefer **six** artifacts. Existing LM gallery plots are too many and mostly baseline-calibration detail.

| ID | Title | Contents | Why |
|----|--------|----------|-----|
| **T1** | Standard tokenizers on Level-B development | BPE vs Unigram (and character descriptive): P, R, F1, exact, TPC | RQ1; Unigram ≫ BPE, P≫R |
| **T2** | StatBound V1 vs Unigram | Morphology F1 (all λ identical), 0/162 changes, SC1 BPC mean±sd and seed wins, SC4/SC1 fail | The negative result, compact |
| **T3** | N-best oracle | Unigram top-1 vs best-of-16: P/R/F1/exact; ΔF1; gold-in-nbest 22/162; rank histogram summary | Availability vs selection |
| **F1** | Missed gold boundaries by location | Grouped bars: Unigram misses vs still-missing-after-oracle, for left / right / internal | The paper’s distinctive figure |
| **F2** | Oracle change types | 66 clean prefix / 28 mixed gold / 31 F1-with-junk; plus “124/125 only add splits” | Stops readers treating 0.79 F1 as a target |
| **F3** | Primary LM comparison | Unigram vs StatBound, parameter-matched × fixed-char, 3 seeds + mean | Shows SC1 fail and that V1 ≈ Unigram |

Optional appendix only: Phase F full 12-run table; λ grid; compat-alignment numbers (41/73/1 and compat-oracle 0.5169). Those support the text; they should not crowd the main story.

**New plots worth generating from existing numbers (no new training):**

1. F1 — missed-boundary location bars (from the oracle anatomy counts).
2. F2 — stacked/count bars of oracle change classes (66/28/31).
3. A small rank histogram of F1-oracle choices (already in the oracle JSON).
4. F3 — seed-level BPC dots (from Phase F JSON).

Do **not** generate more learning-curve panels for the paper.

---

## 5. Small paper roadmap (~6–8 pages)

**Working paper title:**  
*Unigram Undersegments Chichewa: A Conservative Morphology Benchmark and a Negative Boundary-Reranking Result*

**Venue realism:** AfricaNLP / workshop / Findings-style empirical short paper, or an arXiv technical report. Not a “new algorithm” ACL oral.

| Section | Main message |
|---------|----------------|
| **1. Introduction** | Tokenization for agglutinative low-resource Bantu is often discussed as if finer morphology would automatically help models. We measure that assumption on Chichewa with a frozen protocol. Unigram beats BPE on conservative morphology but undersegments; a simple unsupervised reranker does not fix it and does not help BPC. |
| **2. Related work** | Unigram vs BPE (Kudo; Bostrom & Durrett; Richburg/Swahili); morph-aware tokenization (MorphBPE, MoVoC, Banerjee & Bhattacharyya); morph ≠ generation (Saleva & Lignos; Mager et al.); Bantu LM+segmentation (Meyer & Buys — different architecture). Position as controlled measurement + negative result, not a new primitive. |
| **3. Data and benchmark** | Frozen corpus; Level-B rubric (split namable inflection, keep uncertain derived stems, forbid syllable cuts); 162/33; single annotator; holdout locked and unused. State this is development evidence. |
| **4. Experimental setup** | 8k BPE/Unigram/character; StatBound V1 as a pre-registered intervention; λ grid frozen; SC1 primary matched BPC; n-best=16 oracle as analysis only; gold never trains the tokenizer. |
| **5. Results** | T1–T2: Unigram ≫ BPE on F1; StatBound = Unigram on morphology; SC1 fail; tiny SC2/SC5/SC6 are not a win. |
| **6. N-best and error anatomy** | T3, F1, F2: prefixes are in the list; final vowels mostly are not; 66 clean vs 31 junk; do not imitate the oracle; V1 `compat` anti-aligned (max-compat hurts). |
| **7. Discussion** | Selection vs generation; morphological fidelity ≠ LM objective; why productivity was the wrong proxy for Level-B; what a later prefix-only probe could ask. |
| **8. Limitations and conclusion** | Single annotator; N=162; Bible-heavy; development-only morphology; V1 was a no-op so LM–morph coupling is untested; holdout/test unused. Close with the one-sentence claim. |

Target length: 6–8 pages + appendix tables.

---

## 6. Honest contributions

We can claim:

1. **A frozen, conservative, native-speaker Level-B Chichewa development benchmark** with an explicit granularity policy and locked holdout (resource / instrument).
2. **A controlled 8k BPE vs Unigram comparison** on that instrument plus a matched small decoder LM protocol (empirical measurement).
3. **An n-best anatomy** separating selection (prefixes mostly present) from generation (many FVs/internal cuts absent), including that some F1-better paths are linguistically poor.
4. **A pre-registered negative result:** train-only boundary-productivity reranking of Unigram n-best does not move Level-B F1 or primary BPC, and the auxiliary score does not point at the better-F1 candidates.

**Not methodological novelty:** Unigram, n-best reranking, Harris/productivity statistics, log-linear combination of scores, or “first Chichewa tokenizer.”

---

## 7. Novelty risk

**Potentially publishable**

- The Level-B instrument and the location-split n-best anatomy on Chichewa.
- A clean negative result with frozen protocol (rare, citable if honest).
- The explicit 66 vs 31 split (metric-lucky oversegmentation).

**Mostly replication / application**

- Unigram ≥ BPE on morph-rich language (Bostrom & Durrett 2020; Richburg et al. 2020).
- Morph scores ≠ generation quality (Saleva & Lignos 2021; Mager et al. 2022; MoVoC).
- Unsupervised morph cues can fail (expected).

**Avoid claiming**

- First morphology-aware tokenizer for Chichewa / Bantu.
- That Unigram “contains Chichewa morphology” (it contains many *prefix* alternatives).
- That 0.79 oracle F1 is achievable by a fair method.
- That Phase F tested a morphological LM tokenizer.
- That SC2/SC5/SC6 validate the approach.
- That Level-B is inter-annotator gold.

**Cite carefully**

- Kudo 2018; Bostrom & Durrett 2020; Richburg et al. 2020; Saleva & Lignos 2021; Mager et al. 2022; Meyer & Buys 2022; Banerjee & Bhattacharyya 2018; MorphBPE; MoVoC; Harris / Morfessor lineage; Lundin et al. 2026 only as motivation.

---

## 8. Holdout / test strategy

**Keep both locked while the repo and draft are written.**

| Set | Unlock only if |
|-----|----------------|
| Morphology holdout | The paper’s *development* claims and method list are frozen, and you need one confirmatory Unigram-vs-BPE (and optionally StatBound=Unigram) morphology number for submission. One unlock. No method change after seeing it. |
| LM test | You decide the paper’s primary LM claim needs a confirmatory test number **and** validation SC1 for the systems in the paper is already reported. For this anatomy + validation-negative paper, LM test may **remain locked permanently**; state validation-only as a limitation. |

Do not unlock either to explore, retune, or decide whether the story is interesting.

---

## 9. Optional prefix-recovery follow-up

Supported question (future only):

> Can Unigram be made to emit inflectional prefix stacks that already exist in n-best=16 without promoting linguistically bad extra cuts?

| Option | Meaning |
|--------|---------|
| **A. Entirely future work** | Mention in the paper; do not run for this project |
| **B. Optional pre-registered probe before submission** | Analysis-only or a tiny named experiment after the draft exists |
| **C. Necessary for this project** | Rejected |

**Recommendation: A.**  
This project is finished without that probe. B is allowed later as a *separate* decision if a reviewer or the author wants it; it is not on the critical path. C would restart method-hunting.

Do not design the method in this phase.

---

## 10. Stopping criteria (“done”)

The current Git project is scientifically finished when **all** of the following hold:

1. StatBound V1 remains closed; no successor experiment has been started to “complete” the paper.
2. Phase C, Phase F, failure diagnostic, and n-best oracle reports remain the scientific record, with hashes and the decision log consistent.
3. README tells the empirical story (outline in §3), not a live method pitch.
4. The six featured artifacts (T1–T3, F1–F3) exist and are generated from existing result files.
5. A 6–8 page draft exists that uses the recommended claim and does not invent unreported numbers.
6. Holdout and LM test are still locked, unless a later one-shot unlock was pre-declared for submission.
7. Limitations (single annotator, N=162, development-only morphology, V1 no-op) are stated in README and draft.

At that point: **experiments are complete, findings are documented, the repo is reproducible, and the small paper can be drafted.** V2/V3 are not required.

---

## Final card (D-0016)

| | |
|--|--|
| **A. Claim** | Unigram substantially outperforms BPE on a conservative native-speaker Chichewa morphology benchmark but undersegments; its n-best list already contains most missing prefix/TAM/NEG structure, while many final-vowel and internal boundaries are absent, and a pre-registered unsupervised boundary-productivity reranker fails both to select the unused alternatives and to improve matched LM BPC. |
| **B. Project title** | Mthandizi: Controlled Tokenization Experiments for Chichewa |
| **C. Paper title** | Unigram Undersegments Chichewa: A Conservative Morphology Benchmark and a Negative Boundary-Reranking Result |
| **D. Contributions** | Level-B instrument; controlled BPE vs Unigram; n-best selection-vs-generation anatomy; pre-registered StatBound negative result |
| **E. README** | Finding-first outline in §3 |
| **F. Paper** | Intro → related → data/benchmark → setup → results → n-best anatomy → discussion → limitations |
| **G. More experiments now** | **NO** |
| **H. Next Git work** | Rewrite README to this story; add T1–T3/F1–F3 from existing JSON; keep the charter and D-0016 as the living plan; then draft the paper |
| **I. Remain locked** | Morphology holdout; LM test |
| **J. Finished** | §10 checklist |
