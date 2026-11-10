# StatBound-Unigram V1 — close-out and research reset

**Status:** StatBound V1 closed (negative)  
**Decision:** D-0015  
**Date:** 2026-08-18  

This note closes a method. It does not propose a replacement algorithm.

Morphology holdout remains **locked**.  
LM test remains **locked**.  
No new tokenizer experiment is authorized here.

---

## 1. What is closed

StatBound-Unigram V1 is a completed negative experiment.

| Gate | Outcome |
|------|---------|
| SC4 development morphology | Fail (F1 identical to Unigram: 0.5551) |
| SC1 primary LM | Fail (ΔBPC +0.000341; 1/3 seeds) |
| SC2 / SC5 / SC6 | Pass at negligible effect; not a morphological result |

V1 never left Unigram top-1 on the 162-item development set. Phase F therefore did not test a morphology-aware tokenizer. It compared two nearly identical segmentations.

**Forbidden now**

- Changing V1 λ after seeing results
- RelBound / temperature / z-score / rank reranking of the **same** `compat`
- Calling any such change V1, V1b, or an informal patch
- Unlocking holdout or LM test to rescue the story

The algorithm, λ*, and evaluation record stay as historical artifacts (D-0010–D-0014).

---

## 2. What we thought we were testing

The registered question was:

> Can corpus-derived morphological boundary information improve an already strong Unigram tokenizer without a large supervised analyzer?

The method we actually ran was narrower:

> Can Harris-style edge productivity, added to Unigram n-best log-probabilities with a small global λ, change MAP segmentations toward Level-B gold?

Those are not the same question. Closing V1 falsifies the second. It does not falsify the first.

---

## 3. The real finding is a construct mismatch

The n-best oracle (analysis only) is the result that should change how we think.

| Fact | Number | Use |
|------|--------|-----|
| Unigram development F1 | 0.5551 | P=0.84, R=0.45: systematic **undersegmentation** |
| Best-of-n-best=16 F1 | 0.7913 | Δ **+0.2362** vs Unigram |
| Exact gold in n-best | 22/162 (13.58%) | SC4 can move a lot without exact gold |
| Better-F1 neighbour exists | 115/162 | Generator room is common |
| Better-F1 has higher `compat` | 41/115 | Minority |
| Better-F1 has identical `compat` | 73/115 | All disputed cuts have V1 strength **0** |
| Compat-oracle F1 | 0.5169 | **Worse** than Unigram |

So:

1. Useful Level-B alternatives often already sit in Unigram’s n-best list (median oracle rank among changes: 4).
2. V1’s statistic usually **does not score the cuts that matter**.
3. When it does score something, it does **not** track Level-B F1.

That is not “λ was too small.” A perfect argmax of `compat` would have hurt the metric we care about.

**Why this was predictable in hindsight**

Level-B gold is a conservative linguistic rubric: namable prefixes, object markers, TAM, negation, supported extensions, enclitics; derived stems kept; syllable cuts forbidden.

V1 `compat` rewards *surface type productivity near word edges* under support/productivity gates. Level-B often wants cuts that are real but not frequent enough to pass those gates (final vowels, stacked prefixes, some extensions). It also rejects productive-looking cuts that are not those morphs.

We optimized a **proxy** and evaluated a **different construct**. Calibration cannot reconcile them.

---

## 4. Three questions were glued together

Before designing anything else, pick **one** primary claim.

### A. Language-modeling claim

Unigram can be beaten on **validation BPC** under the frozen matrix (SC1), with morphology as a hypothesized mechanism.

Then SC4 is diagnostic, not a co-equal success gate. Saleva & Lignos (2021) and Mager et al. (2022) already warn that morph-better tokenizers often do not win generation.

### B. Computational-morphology claim

A drop-in tokenizer can move **Level-B boundary F1** by at least +0.03 without a supervised analyzer, and must not wreck efficiency or BPC too badly.

Then SC1 is a harm constraint. The method must be designed from Level-B error structure (recall on 4–7-piece words, prefix stacks, final vowels), not from a generic segmentation prior.

### C. Instrument / negative-result claim

A locked Chichewa Level-B development benchmark, plus Unigram≫BPE, plus an n-best oracle, plus a failed unsupervised boundary reranker, is the contribution.

Then we stop method-hunting on these 162 items.

V1 tried to win A and B with one cheap proxy. That was the design mistake. “Think better” means refusing to do that again.

---

## 5. What is still scientifically live

- Unigram is the right backbone (strongest standard baseline on both LM validation and Level-B F1).
- The failure mode is **undersegmentation of longer words**, not random noise.
- The unused n-best list is large enough that SC4 is not fantasy.
- Low-supervision is still the right constraint. The 162 labels are an instrument, not a training set.
- The locks, frozen corpus, and native-speaker Level-B rubric are the scarce assets. They outrank any tokenizer name.

---

## 6. What we will not rush into

These remain **unauthorized** until a new decision entry exists:

| Temptation | Why not now |
|------------|-------------|
| RelBound / bigger λ | Same wrong `b` |
| Morfessor-as-V2 | Also a productivity/MDL proxy; may repeat the construct mismatch. At most an **analysis-only probe** later |
| Original S1 train-time Unigram bias | Never tested, but still uses the same statistic unless the signal changes |
| Supervised reranker on the 162 | Spends the only development instrument; holdout would have to be unlocked immediately to be honest |
| Unlocking holdout “just to see” | That is the end of confirmatory morphology evidence |
| Another method menu from ACL | Method-first is how we got V1 |

---

## 7. Thinking work before any new experiment

No code. No α grid. Sit with these until one claim is written in a single sentence.

1. **Which of A / B / C is the paper?** If we cannot choose, we are not ready to implement.
2. **Is Level-B the right *target* for a tokenizer?** It may be the right *audit* and still be too fine (final-vowel splits, stem-internal extensions) for what an LM should tokenize. That is a scientific choice, not a bug to paper over.
3. **What do the unused n-best winners actually do?** Before inventing a score, describe the 115 better candidates linguistically (prefix addition, FV split, extension, clitic, syllable-like junk). If we cannot name the pattern, we cannot design a signal.
4. **Does any existing unsupervised morph analyzer even correlate with Level-B inside the same n-best list?** That is another analysis-only oracle (Morfessor as `b`, not as a shipped tokenizer). If it also anti-correlates, Family 5 is the wrong next bet.
5. **What would count as giving up the method line, as opposed to the research line?** Already answered for StatBound. For the program: one later registered attempt with a *different* signal, or a decision to publish C and stop.

---

## 8. Cooling-off rule

Do not implement a successor until:

- D-0015 remains in force,
- the primary claim (A, B, or C) is written and accepted in a new decision entry,
- and, if the claim is A or B, an analysis-only characterization of oracle winners exists.

Until then, the correct activity is thinking and writing, not training.

---

## 9. Error anatomy of the unused n-best list (analysis only)

Post-close inspection of the frozen oracle (gold used only to label already generated candidates).

Unigram’s 292 missed gold boundaries:

| Zone | Unigram misses | Still missing after F1-oracle |
|------|---------------:|------------------------------:|
| Left edge (≤4 chars) | 129 | **2** |
| Right edge (last 2 chars) | 93 | **71** |
| Internal | 70 | 41 |

Among 125 oracle≠Unigram items:

- **124 only add pieces** (never merge). Mean +1.64 pieces.
- **66** are clean: only left-edge gold cuts, no new false-positive cuts.
- **31** raise item F1 while introducing false-positive cuts (metric-lucky junk, e.g. `ndi+tenga` → `ndi+te+ng+a`).
- **28** add some true gold cuts but also right-edge or internal cuts.

**Interpretation**

1. **Inflectional prefix / TAM / NEG stacks are already in Unigram n-best=16.** The generator problem for that class is essentially solved. The missing object is a *selector*.
2. **Verbal final vowels are mostly not in the n-best list.** Level-B Rule 1 cannot be met by reranking this generator. Many apparent FV recoveries are stem-internal junk that happens to hit `+a`/`+e`.
3. **The +0.236 oracle F1 is not a target to imitate.** It mixes 66 clean prefix harvests with 31 metric-lucky oversplits.
4. V1 `compat` failed because it does not fire on those left-edge grammatical cuts (strength 0 at the disputed positions).

This anatomy, not another ACL method, should constrain any later experiment.

## Publication addendum — 2026-11-10

This close-out is retained as the historical rationale for closing V1. The
publication review found that the 2/71/41 misses of the selected oracle cannot be
read as absence from every candidate. Stored-candidate union absence is 0/27/22
for the same left/right/internal bins. The v0.2 paper also qualifies conditional
macro averages and avoids inferring that every mixed weighting must fail from
the maximum-compatibility result. No V1 result, scoring rule, or closure decision
is changed; any successor remains a separate research decision.
