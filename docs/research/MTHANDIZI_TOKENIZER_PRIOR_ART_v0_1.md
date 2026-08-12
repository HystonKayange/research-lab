# Mthandizi tokenizer — prior art review v0.1

**Status:** completed for method selection (pre-implementation)  
**Machine-readable matrix:** `data/reports/mthandizi_tokenizer_prior_art_matrix_v0_1.json`  
**Companion selection doc:** `docs/research/MTHANDIZI_TOKENIZER_METHOD_SELECTION_v0_1.md`  
**Frozen criteria:** `docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md` (D-0008)

**Rules observed**

- Primary sources only (ACL Anthology / official paper pages).  
- Unknown implementation details marked **UNKNOWN**.  
- “First for Chichewa” is **not** treated as methodological novelty.  
- Morphology holdout **not** accessed.  
- LM test **not** evaluated.  
- No tokenizer implementation.

---

## 1. Research question (restated)

Under fixed data, parameter, and compute conditions, can we develop a morphology-aware tokenizer for low-resource **Chichewa** that improves:

1. LM validation BPC (vs Unigram-8000 primary),  
2. morphological boundary quality (active development set, SC4),  
3. tokenization / sample efficiency,

**without** requiring a large supervised morphological analyzer or a large manually segmented training resource?

---

## 2. Search and inclusion

Executed against ACL Anthology for:

- morphology-aware tokenization / subword construction  
- Bantu / African tokenization  
- morphology-biased Unigram  
- Morfessor / unsupervised morphology + subwords  
- boundary-constrained BPE  
- affix discovery for tokenization  
- low-resource tokenizer learning  

**Must-include set (all verified on ACL Anthology):** 8 papers  
**Additional verified primary sources used in this review:** 3 papers  
**Total verified primary sources in matrix:** 11  

Papers that could not be bibliographically verified were **not** cited.

---

## 3. Must-include papers (verified)

### 3.1 Asgari et al., 2026 — MorphBPE  
**Anthology:** [2026.findings-acl.2068](https://aclanthology.org/2026.findings-acl.2068/)

| Field | Content |
|-------|---------|
| Languages | English, Russian, Hungarian, Arabic |
| Supervision | Morpheme boundaries during **tokenizer training** |
| Base | BPE |
| Vocab learning | Yes — merges that cross morpheme boundaries are disallowed |
| Inference | Standard BPE (no morphology runtime) |
| LM eval | 300M / 1B decoder LMs from scratch; lower cross-entropy |
| Morph eval | Morph Consistency F1, Morph Edit Distance |
| Downstream | Belebele gains (esp. Russian, Arabic) |
| Main result | Morphology-constrained BPE improves morph coherence + LM loss without much shorter tokens |
| Chichewa fit | Idea transferable; **requires corpus-scale boundaries we do not have** |
| Overlap | **Candidate 3 HIGH** |

**Critical detail (from PDF method):** MorphBPE only changes BPE **training** merge selection; resulting model is ordinary BPE at inference.

### 3.2 Hudspeth, Burns & O’Connor, 2026 — Latin morphologically-guided tokenization  
**Anthology:** [2026.eacl-long.270](https://aclanthology.org/2026.eacl-long.270/)

| Field | Content |
|-------|---------|
| Languages | Latin |
| Setting | Medium pretraining data + **high curated lexical resources** |
| Result | Morph-guided tokenization helps four downstream tasks; gains strongest OOD |
| Chichewa fit | Conceptual: resources can substitute data — but Chichewa lacks Latin-scale lexical resources |
| Overlap | Resource-heavy morph guidance; Candidates 1/4 |

### 3.3 Teklehaymanot et al., 2025 — MoVoC (Ge’ez script)  
**Anthology:** [2025.findings-emnlp.706](https://aclanthology.org/2025.findings-emnlp.706/)

| Field | Content |
|-------|---------|
| Languages | Ge’ez-script African languages |
| Supervision | **Supervised** morph analysis into vocab; manual morph data for 4 languages |
| Base | Hybrid morpheme units + BPE |
| Result | Intrinsic MorphoScore / Boundary Precision ↑; MT quality not significantly ↑ |
| Chichewa fit | African low-resource motivation; **not** a no-analyzer recipe |
| Overlap | Candidates 1, 4 (HIGH) |

### 3.4 Saleva & Lignos, 2021 — Morphology-aware segmentation in LR NMT  
**Anthology:** [2021.eacl-srw.22](https://aclanthology.org/2021.eacl-srw.22/)

| Field | Content |
|-------|---------|
| Languages | Nepali, Sinhala, Kazakh ↔ English |
| Methods | BPE vs LMVR vs MORSEL |
| Result | **No consistent** morphology-aware win over BPE; often statistically indistinguishable |
| Implication | Morphology-aware segmentation is **not** automatically better for sequence models |

### 3.5 Richburg et al., 2020 — Subword strategies for MRLs (incl. Swahili)  
**Anthology:** [2020.winlp-1.40](https://aclanthology.org/2020.winlp-1.40/)

| Field | Content |
|-------|---------|
| Languages | **Swahili** (Bantu), Turkish → English |
| Methods | BPE vs Unigram LM |
| Result | Unigram ≈ BLEU; **better rare-word recall** than BPE |
| Implication | Supports **Unigram as backbone** for Bantu-like morphology |

### 3.6 Kudo, 2018 — Subword regularization + Unigram LM  
**Anthology:** [P18-1007](https://aclanthology.org/P18-1007/)

| Field | Content |
|-------|---------|
| Contribution | Unigram LM segmentation + probabilistic multi-segmentation training |
| Result | Improves NMT especially low-resource / OOD |
| Overlap | Foundation of our Unigram-8000 baseline; **Candidate 8 HIGH** |

### 3.7 Mager et al., 2022 — BPE vs morphological segmentation (polysynthetic)  
**Anthology:** [2022.findings-acl.78](https://aclanthology.org/2022.findings-acl.78/)

| Field | Content |
|-------|---------|
| Languages | Nahuatl, Raramuri, Shipibo-Konibo, Wixarika |
| Result | Unsupervised morph often beats BPE in MT; **supervised morph better at morph scores but worse at MT** |
| Implication | Do **not** equate morph gold alignment with neural model success; unsupervised morph signals can help |

### 3.8 Lundin et al., 2026 — The Token Tax (AfricaNLP)  
**Anthology:** [2026.africanlp-main.10](https://aclanthology.org/2026.africanlp-main.10/)

| Field | Content |
|-------|---------|
| Scope | 10 LLMs × AfriMMLU (16 African languages) |
| Result | Higher fertility → lower accuracy; “token tax” economics |
| Role | **Motivation** for morph-aware / efficient African tokenization — not a competing algorithm |

---

## 4. Additional verified primary sources

| Paper | Anthology | Why included |
|-------|-----------|--------------|
| Bostrom & Durrett, 2020 | [2020.findings-emnlp.414](https://aclanthology.org/2020.findings-emnlp.414/) | Unigram aligns better with morphology than BPE; LM pretraining evidence |
| Meyer & Buys, 2022 | [2022.findings-emnlp.494](https://aclanthology.org/2022.findings-emnlp.494/) | **Nguni Bantu** joint subword segmental LM; strongest Bantu LM+segmentation hit |
| García et al., 2025 | [2025.emnlp-main.1552](https://aclanthology.org/2025.emnlp-main.1552/) | Spanish morph-aware tokenizer training helps MLM/downstream |

### Bantu / African-specific findings

1. **Richburg et al. 2020** — Swahili subword NMT (Unigram vs BPE).  
2. **Meyer & Buys 2022** — Nguni Bantu SSLM + unsupervised morph segmentation.  
3. **MoVoC 2025** — African Ge’ez-script morph-aware vocab (supervised).  
4. **Lundin et al. 2026** — African multilingual fertility / accuracy “token tax”.  

**No verified ACL primary paper was found that trains a drop-in 8k Unigram/BPE tokenizer specifically for Chichewa under a matched decoder LM BPC protocol.** That gap is experimental, not automatic novelty of algorithm families.

---

## 5. Synthesis themes

| Theme | Evidence | Consequence for Mthandizi |
|-------|----------|---------------------------|
| Unigram often ≥ BPE for morph-rich / rare words | Richburg 2020; Bostrom & Durrett 2020; our Unigram-8000 baseline | Prefer **Unigram backbone**, not MorphBPE-style BPE-first |
| Constrained BPE is now published | MorphBPE 2026 | Candidate 3 is **high novelty risk** |
| Supervised morph improves intrinsic morph metrics ≠ always helps generation/MT | MoVoC; Mager 2022; Saleva & Lignos 2021 | SC4 may rise without SC1; PARTIAL outcome is plausible |
| Pre-seg + subword is crowded | MoVoC; MorphBPE related work; Saleva/Mager | Candidate 1 high overlap |
| Joint segmentation+LM helps Bantu but changes architecture | Meyer & Buys 2022 | Outside frozen “fixed tokenizer then fixed LM matrix” unless redefined |
| African fertility tax is real | Lundin 2026 | Strengthens SC5/SC4 motivation |
| Latin-style lexical resources are not free | Hudspeth 2026 | Reject methods needing large curated morph lexica |

---

## 6. Candidate family novelty risks

| # | Family | Novelty risk | Strongest prior overlap |
|---|--------|--------------|-------------------------|
| 1 | Pre-segmentation + Unigram fallback | **HIGH** | MoVoC; Mager; Saleva & Lignos; MorphBPE pre-tok literature |
| 2 | Boundary-biased Unigram | **MEDIUM** | Kudo Unigram base; MorphBPE **constraint idea** on different algorithm |
| 3 | Morphology-constrained BPE | **HIGH** | **MorphBPE (direct)** |
| 4 | Hybrid affix/stem vocabulary | **HIGH** | MoVoC; resource-guided Latin work |
| 5 | Statistical affix + character fallback | **MEDIUM** | Unsupervised morph (Mager); Morfessor lineage; char residual of Unigram |
| 6 | Whole-word memorization regularization | **MEDIUM** | Engineering vocab allocation; weak morph story |
| 7 | Word-family consistency regularization | **MEDIUM** | MorphBPE consistency motivation / related metrics |
| 8 | Stochastic segmentation | **HIGH** | Kudo 2018 subword regularization |
| 9 | Character/byte fallback alone | **HIGH** | Already a baseline / Unigram primitive |

**High-novelty-risk families:** 1, 3, 4, 8, 9.

---

## 7. MorphBPE vs Candidate 3 (explicit)

| Dimension | MorphBPE | Our Candidate 3 |
|-----------|----------|-----------------|
| Algorithm class | BPE merge constraints | Same class |
| Needs full-corpus morph boundaries | Yes (training) | Yes if done honestly |
| Inference | Standard BPE | Standard BPE |
| Chichewa morph boundaries at train scale | Not available | Not available (only 195 eval items) |
| Novelty if reimplemented on Chichewa | **Unsupported** (“first Chichewa MorphBPE”) | **HIGH risk / not recommended as V1** |

Using the 195 gold labels as MorphBPE-style train boundaries would also violate the leakage rule (no supervised morph segmenter / vocab memorization of the 195 unless explicitly logged as a separate condition).

---

## 8. What space remains?

A **defensible residual space** (not pure novelty theater) is a method that:

1. Uses **Unigram** (already best Chichewa LM baseline; Bantu evidence from Swahili),  
2. Injects **weak, corpus-statistical** boundary/affix bias **without** a full analyzer and **without** treating the 195 labels as training gold,  
3. Keeps **exact reconstructibility** and a **character residual**,  
4. Remains a **drop-in tokenizer** under the frozen 8k matched LM protocol (unlike SSLM),  
5. Is **ablatable** (bias on/off; affix inventory on/off; char residual always on),  
6. Distinguishes itself from MorphBPE by **base algorithm (Unigram vs BPE)** and **supervision regime (statistical/weak vs full-corpus morph boundaries)**.

This residual is **provisional composition novelty**, not a new primitive. Components exist; the **composition + protocol + Chichewa evaluation** is the research contribution.

---

## 9. Leakage and evaluation discipline (reaffirmed)

| Resource | Allowed now | Forbidden |
|----------|-------------|-----------|
| Active 195 | Failure analysis; SC4 eval of prototypes | Memorize segmentations into vocab; train supervised morph segmenter by default |
| Morphology holdout | — | All access |
| LM test | — | All evaluation |
| Train corpus | Unsupervised/statistical learning | — |

---

## 10. Matrix pointer

Full structured rows (all fields requested) live in:

`data/reports/mthandizi_tokenizer_prior_art_matrix_v0_1.json`

---

## 11. Bottom line for method selection

- **Do not** select morphology-constrained BPE (Candidate 3) as the innovative claim.  
- **Do not** select pure stochastic segmentation or pure char fallback as novelty.  
- **Do** prefer Unigram-centric, low-supervision designs.  
- Expect literature-justified **PARTIAL** outcomes (morph ↑, LM flat) based on Saleva/MoVoC/Mager.  
- Proceed to method selection document for shortlist and Prototype V1 recommendation.
