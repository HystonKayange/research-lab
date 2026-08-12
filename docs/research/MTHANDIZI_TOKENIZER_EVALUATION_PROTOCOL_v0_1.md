# StatBound-Unigram V1 — Scientific Evaluation & Hyperparameter Protocol v0.1

**Status:** `frozen_pre_results`  
**Decision log:** `D-0011`  
**Machine-readable twin:** `configs/tokenizers/statbound_unigram_v1_eval_protocol.json`  
**Parent criteria:** `docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md` (D-0008)  
**V1 algorithm:** `docs/research/MTHANDIZI_TOKENIZER_V1_SPEC.md` (D-0010)

This protocol is frozen **before** inspecting StatBound-Unigram development morphology or LM results.  
Do **not** revise selection rules after seeing outcomes. Any change requires a new decision-log entry.

**This document does not authorize running evaluation yet.** It only freezes *how* evaluation and \(\lambda\) selection will proceed.

---

## 0. Hard locks (until later phases)

| Resource | Status until named phase |
|----------|--------------------------|
| Morphology holdout | **LOCKED** until Phase I |
| LM test | **UNTOUCHED** until Phase J |
| MasakhaNER | **Outside** this development loop |
| Scientific metrics in *this* freeze task | **Not executed** |

---

## 1. Reproducibility snapshot (recorded at protocol freeze)

Artifacts hashed in place (not modified to “pretty” hashes).

| Artifact | Path | SHA-256 | Bytes |
|----------|------|---------|------:|
| LM train corpus | `data/splits/chichewa_corpus_v0.1/train/combined.txt` | `40ac7798b7dd1b98b1aa60f139a9794eefa75db751497166f1190c8da6ccc81d` | 4,703,801 |
| LM validation corpus | `data/splits/chichewa_corpus_v0.1/validation/combined.txt` | `d2de8aa56c5df64830502945544fac9335e91fbc100435f9c2491cd68d763665` | 646,024 |
| Unigram-8000 model | `data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model` | `230646c68ff9212ddbe35f01f688db43bba63cadb32d96f820b85cab572414be` | 132,073 |
| StatBound V1 config | `configs/tokenizers/statbound_unigram_v1.json` | `95df313888f929c3fa63371a843d7d8edac3ca3d03ee96a31e8e1e1bdcc00a46` | 3,152 |
| Boundary stats | `data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json` | `4744460d14bd30b8941c0e92d753cbdc54ead8471f43bb78dead922941bd721f` | 12,155,990 |
| V1 executable spec | `docs/research/MTHANDIZI_TOKENIZER_V1_SPEC.md` | `348c0bc4be60be6c5f61cbe4e0d6778087c4b926c84c0e62fc1ea816dc3c1ec6` | 12,057 |
| Success criteria config | `configs/tokenizers/mthandizi_success_criteria_v0_1.json` | `fc1a90c830dc74ea6f014636105c1b805be9ebb91627cbb8ff8ad65c8c6d83dd` | 9,169 |
| Success criteria doc | `docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md` | `4f88f4cbeae3029e7189fc3b828c7e5e7f8f2082aa8fc11453ef2a65ec3d447d` | 12,046 |
| Active morph dev (pre–self-review freeze) | `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl` | `665ee2fc464448696d78dc646455c4fa2bcadbcdbb4fac4de2c9f200ca1df0b1` | 224,007 |

**Environment at freeze**

| Item | Value |
|------|--------|
| Git commit | **unavailable** — workspace is **not** a git repository (no `.git`) |
| Dirty working tree | **n/a** (no git) |
| Python | 3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0] via `.venv` |
| SentencePiece | 0.2.0 |
| PyTorch | 2.11.0+cu128 |
| Platform | Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39 |

**Note:** Before Phase C, re-verify these hashes. If any core artifact drifts, **stop** and log a decision entry before continuing.

**LM seeds (frozen, same as baseline matrix):** `42`, `1337`, `2026`  
**LM matrix config reference:** `configs/models/lm_baselines_v0_1_final_matrix.json`

---

## 2. \(\lambda\) candidates (frozen)

\[
\lambda \in \{0.0,\ 0.25,\ 0.5,\ 1.0,\ 2.0\}
\]

| Rule | Detail |
|------|--------|
| \(\lambda=0.0\) | **Mandatory control** — must match ordinary Unigram segmentation |
| \(\lambda=0.0\) as “proposed method” | **Forbidden** |
| Grid expansion after results | **Forbidden** |

---

## 3. \(\lambda\) selection rule (no LM BPC)

### 3.1 Inputs for selection only

For every **nonzero** \(\lambda \in \{0.25, 0.5, 1.0, 2.0\}\):

**A. Morphology development metrics** on the **final frozen** morphology development set (Phase B output):

- boundary precision  
- boundary recall  
- boundary F1  
- exact segmentation match  
- boundary Jaccard  

**B. Tokenizer efficiency** on frozen **LM validation** text (`validation/combined.txt`):

- tokens per character  
- word fertility  
- sequence-length expansion  
- single-character fragment rate  
- whole-word rate (where applicable)

Also evaluate \(\lambda=0.0\), BPE-8000, and Unigram-8000 for comparison / control (see §6).  
\(\lambda=0.0\) is **not** eligible for selection as proposed StatBound.

### 3.2 Forbidden selection signals

Do **not** use any of the following to choose \(\lambda^*\):

- LM BPC / BPB  
- LM test  
- morphology holdout  
- MasakhaNER or other downstream tasks  

### 3.3 Selection algorithm (exact)

Let \(t(\lambda)\) = tokens-per-character of StatBound with that \(\lambda\) on LM validation.  
Let \(t_U\) = tokens-per-character of Unigram-8000 on the same validation text.  
Let \(F(\lambda)\) = boundary F1 of StatBound with that \(\lambda\) on the frozen morphology development set.

**Step A — efficiency eligibility**

\[
\mathcal{E} = \{\lambda \in \{0.25, 0.5, 1.0, 2.0\} : t(\lambda) \le 1.10 \cdot t_U \}
\]

**Step B — primary pick among eligible**

If \(\mathcal{E} \neq \emptyset\):

\[
\lambda^* = \arg\max_{\lambda \in \mathcal{E}} F(\lambda)
\]

**Step C — tie on F1**  
Among \(\lambda\) achieving \(\max F\): choose **lower** \(t(\lambda)\).

**Step D — remaining tie**  
Choose **smaller** \(\lambda\).

**Step E — if no eligible nonzero \(\lambda\)**

1. Record **SC5 failed** for all nonzero candidates (efficiency threshold not met).  
2. **Do not** change the 1.10 threshold.  
3. Still set \(\lambda^*\) by maximizing \(F(\lambda)\) over \(\{0.25,0.5,1.0,2.0\}\) (then C, then D) for **diagnostic completion** of the protocol.  
4. Mark the selected run as **efficiency-failed / diagnostic** in all reports.

### 3.4 Interpretation of development morphology F1

Because \(\lambda\) is selected using the morphology **development** benchmark:

| Use | Status |
|-----|--------|
| Development morph F1 | **Tuning / development evidence only** |
| SC4 development target check | Allowed as **development** SC4 (non-confirmatory) |
| Confirmatory morphology evidence | **Only** locked morphology holdout (Phase I) |

Document in every report:  
**“Morphology-development F1 used for \(\lambda\) selection is not confirmatory.”**

---

## 4. Self-consistency dependency (Phase A gate)

Scientific morphology evaluation and \(\lambda\) selection **must not begin** until:

1. Single-annotator delayed **25-item self-review** is completed.  
2. Any **purely human** annotation corrections are finalized.  
3. **No tokenizer outputs** (BPE / Unigram / StatBound) are shown during self-review.

After self-review:

- Create and freeze the **final active morphology development** file.  
- Record exact **row count** and **SHA-256**.  
- **Never** modify that file based on StatBound/BPE/Unigram outputs.

**Current pre-gate artifact (not yet “final post–self-review”):**  
`annotator_a_active_195_v0_1.jsonl` · n=195 · hash in §1.

Expected final path (to be confirmed at Phase B):  
e.g. `.../annotator_a_active_NNN_final_v0_1.jsonl` (exact name fixed when written).

---

## 5. Order of scientific operations (frozen)

| Phase | Action | Status at protocol freeze |
|-------|--------|---------------------------|
| **A** | Single-annotator delayed self-review (no tokenizer views) | Not started here |
| **B** | Freeze final morphology development benchmark (count + hash) | Blocked on A |
| **C** | Evaluate BPE / Unigram / StatBound \(\lambda\) on morph **dev** + val efficiency | Blocked on B |
| **D** | Select \(\lambda^*\) via §3 | Blocked on C |
| **E** | Freeze final StatBound tokenizer artifact (settings + hashes) | Blocked on D |
| **F** | Train LM matrix **only** for selected nonzero \(\lambda^*\) | Blocked on E |
| **G** | Analyze validation SC1–SC7 | Blocked on F |
| **H** | Freeze algorithm, HPs, conclusions, ablations | Blocked on G |
| **I** | Unlock morphology holdout **once** (confirmatory morph) | Blocked on H + decision log |
| **J** | Unlock LM test **once** (final LM) | Blocked on H + decision log |

MasakhaNER remains **outside** Phases A–J development loop.

---

## 6. Morphology comparison protocol (Phase C)

### 6.1 Systems to score on frozen morph development gold

| System | Role |
|--------|------|
| BPE-8000 | Standard subword baseline |
| Unigram-8000 | Primary standard subword baseline |
| StatBound \(\lambda=0.0\) | Control (= Unigram) |
| StatBound \(\lambda\in\{0.25,0.5,1.0,2.0\}\) | Tunable candidates |

**Character** tokenizer: report descriptively only; **not** an equivalent morpheme segmentation baseline for SC4 pass/fail.

### 6.2 Metrics

- boundary precision, recall, F1  
- exact segmentation match  
- boundary Jaccard  

### 6.3 Controls

- Confirm: StatBound \(\lambda=0\) segmentation **==** ordinary Unigram segmentation on the morph evaluation items (piece sequences / boundary sets as defined by the eval harness).  
- If this fails: **stop**; do not select \(\lambda^*\) until resolved and logged.

### 6.4 SC4 development target (non-confirmatory)

\[
\begin{align*}
F_{\mathrm{ref}} &= \max(F_{\mathrm{BPE\text{-}8000}},\ F_{\mathrm{Unigram\text{-}8000}}) \\
\text{SC4-dev passes} &\iff F(\lambda^*) \ge F_{\mathrm{ref}} + 0.03
\end{align*}
\]

Threshold **0.03 absolute** is frozen (D-0008). Do not change it after results.

---

## 7. LM evaluation protocol (Phase F–G) — only after \(\lambda^*\) freeze

### 7.1 Freeze package before any StatBound LM training

Record and freeze:

- \(\lambda^*\)  
- tokenizer code version / commit note (if git later available)  
- `boundary_stats.json` SHA-256  
- base Unigram model SHA-256  
- effective vocabulary (= 8000)  
- full `statbound_unigram_v1.json` + eval protocol hashes  

### 7.2 Train only selected nonzero \(\lambda^*\)

- **Do not** train LM variants for every \(\lambda\) and pick by BPC.  
- \(\lambda=0\) is already covered by the existing **Unigram-8000** baseline matrix (no need to retrain as “StatBound-0” unless reproducibility failure).

### 7.3 Matrix (same as frozen baselines)

Conditions (3 seeds each: 42, 1337, 2026):

1. parameter-matched × fixed characters — **primary (SC1)**  
2. architecture-matched × fixed characters — **SC2**  
3. parameter-matched × fixed updates — **SC3**  
4. architecture-matched × fixed updates — **SC3**

Use existing machinery: `configs/models/lm_baselines_v0_1_final_matrix.json` and associated scripts.

**Primary baseline:** existing Unigram-8000 validation BPC.  
**Do not retrain baselines** unless a documented reproducibility failure requires it.

### 7.4 SC application (summary)

| ID | When |
|----|------|
| SC1 | Phase G primary BPC vs Unigram |
| SC2–SC3 | Phase G secondary/diagnostic |
| SC4-dev | Phase C/D development only |
| SC4-holdout | Phase I only |
| SC5 | Efficiency at selection (Phase C/D) and report with selected tok |
| SC6 | Source BPC after Phase F/G |
| SC7 | Ablations after method freeze (Phase H; predeclared in method selection) |
| SC8–SC9 | Phases I–J only |

---

## 8. What this freeze task does **not** do

- Run morphology metrics  
- Inspect tokenizer outputs on the active morphology benchmark for scientific tables  
- Compute efficiency comparisons for selection  
- Train LMs  
- Access morphology holdout  
- Access LM test  
- Change tokenizer implementation  
- Change success criteria thresholds  
- Change human annotations  

---

## 9. Protocol freeze checklist

- [x] Reproducibility hashes recorded  
- [x] \(\lambda\) grid frozen  
- [x] \(\lambda\) selection rule frozen (efficiency → F1 → tpc → smaller \(\lambda\))  
- [x] Development vs confirmatory morph evidence distinguished  
- [x] Self-review gate before morph scientific eval  
- [x] Phase order A–J frozen  
- [x] LM training only after \(\lambda^*\) selection  
- [x] No scientific results produced in this step  

**Evaluation protocol frozen: true.**
