# Research Lab

A small-scale machine-learning research lab for understanding models from first principles and testing ideas under controlled experimental conditions.

The philosophy is:

```text
reproduce → measure → change one thing → measure again
```

The goal is **not** to claim novelty before evidence exists. Experiments use fixed data, fixed compute budgets, multiple seeds, explicit baselines, frozen success criteria, and locked evaluation sets wherever possible.

> **One run lies.** Prefer controlled comparisons and multi-seed results before drawing conclusions.

---

## Current research: MthandiziTokenizer

The active track studies **tokenization for low-resource, morphologically rich languages**, with **Chichewa** as the primary case study.

### Research question

Can **corpus-derived morphological boundary information** improve an already strong **Unigram** tokenizer under **fixed data, parameter, and compute** conditions—**without** requiring a large supervised morphological analyzer?

### Proposed method (pre-results)

**StatBound-Unigram V1** — a *provisional composition*, not a claim of a new tokenization primitive or of measured improvement.

```text
training corpus
     ↓
statistical boundary evidence
     ↓
Unigram candidate lattice
     ↓
soft boundary-aware reranking
     ↓
final segmentation
```

- Retains the existing **Unigram-8000** vocabulary (no separate morphology vocabulary).
- Boundary statistics are learned from the **frozen LM train corpus only**.
- **Human morphology annotations are not used** to learn those statistics.
- Frozen reranking score:

```text
score(S | w) = unigram_score(S | w) + λ · boundary_compatibility(S, w)
```

Boundary evidence uses corpus-only signals (e.g. recurring prefix/suffix structure, type productivity, branching).  
Frozen λ candidates: **`{0.0, 0.25, 0.5, 1.0, 2.0}`**.  
**λ = 0** is a control and must reproduce ordinary Unigram decoding.  
The nonzero λ is chosen with the frozen **efficiency + morphology-development F1** rule; **LM BPC is not used** to select λ.

Specification: [`docs/research/MTHANDIZI_TOKENIZER_V1_SPEC.md`](docs/research/MTHANDIZI_TOKENIZER_V1_SPEC.md)  
Config: [`configs/tokenizers/statbound_unigram_v1.json`](configs/tokenizers/statbound_unigram_v1.json)

### Baselines

| Tokenizer | Role |
|-----------|------|
| Character | Efficiency / fragmentation diagnostic |
| SentencePiece **BPE-8000** | Standard subword baseline |
| SentencePiece **Unigram-8000** | **Primary** standard-subword comparator (strongest current validation LM baseline) |

Numerical LM/morphology claims for StatBound are **not** listed here until evaluation is complete and approved for reporting.

---

## Experimental discipline

Predeclared criteria and protocol:

| Document | Purpose |
|----------|---------|
| [`docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md`](docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md) | SC1–SC9 (frozen pre-implementation) |
| [`docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md`](docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md) | Phase order, λ selection, locks |
| [`docs/research/MTHANDIZI_TOKENIZER_DECISION_LOG.md`](docs/research/MTHANDIZI_TOKENIZER_DECISION_LOG.md) | Dated decisions (D-0001…) |
| [`configs/tokenizers/mthandizi_success_criteria_v0_1.json`](configs/tokenizers/mthandizi_success_criteria_v0_1.json) | Machine-readable criteria |
| [`configs/tokenizers/statbound_unigram_v1_eval_protocol.json`](configs/tokenizers/statbound_unigram_v1_eval_protocol.json) | Eval protocol + artifact SHA-256s |

Safeguards in force:

- Frozen train / validation / test splits  
- Architecture-matched **and** parameter-matched comparisons  
- Fixed-character **and** fixed-update compute conditions  
- **3 seeds** (42, 1337, 2026) for LM matrix runs  
- Primary LM metric: **validation bits-per-character (BPC)**  
- Morphology boundary metrics + tokenizer efficiency metrics  
- Source-specific Bible / Wikipedia evaluation  
- Predeclared λ-selection rule (**no BPC**)  
- **Morphology holdout locked** until method freeze  
- **LM test locked** until final one-shot evaluation  
- Negative results preserved rather than rewriting success criteria  

---

## Morphology benchmark

A **small Chichewa morphology development set** supports tokenizer analysis (development evidence, not multi-annotator gold).

| Fact | Status |
|------|--------|
| Annotated development records | 200 |
| Annotators | **Single** native Chichewa speaker (`annotator_a`) |
| Excluded after human review | 5 |
| Active development records | **195** |
| Human annotation audit | Complete |
| Human re-review of audit flags | Complete |
| Schema normalization | Complete |
| Delayed blinded self-consistency (25) | **Pending** (time-gated) |
| Morphology holdout | **Locked** |

This is a **single-annotator development resource**. It is **not** multi-annotator gold and does **not** claim human–human IAA. Self-consistency (when run) is delayed re-annotation by the same annotator, not IAA.

---

## Current status

| Stage | Status |
|-------|--------|
| Corpus preparation | Complete |
| Character / BPE / Unigram baselines | Complete |
| Baseline LM validation experiments | Complete |
| Morphology development annotations | Complete |
| Human annotation audit | Complete |
| Human re-review | Complete |
| Schema normalization | Complete |
| Success criteria freeze | Complete |
| Prior-art review + method selection | Complete |
| StatBound-Unigram V1 specification | **Frozen** |
| StatBound-Unigram V1 implementation | Complete |
| Evaluation protocol | **Frozen** |
| Phase C harness + boundary_stats SHA verify | Complete |
| Pre-results Git snapshot | Complete |
| Remote (`origin/main`) | https://github.com/HystonKayange/research-lab |
| Delayed annotation self-review | **Pending** |
| Scientific StatBound morphology evaluation | **Not run** |
| StatBound LM experiments | **Not run** |
| Morphology holdout evaluation | **Locked** |
| LM test evaluation | **Locked** |

**Pre-results implementation anchor (no scientific StatBound results):**

```text
1498d79dc282b5bd5ea3df2454683fbd91ad8dc3
```

Later infrastructure commits may sit on top of this anchor; they do **not** imply that scientific evaluation has been completed.

---

## Repository structure

| Path | Contents |
|------|----------|
| [`configs/`](configs/) | Data, LM matrix, tokenizer, and research JSON configs |
| [`data/`](data/) | Splits, metadata, reports, research morphology artifacts, baseline tokenizers (large LM checkpoints under `data/models/` are **gitignored**) |
| [`docs/`](docs/) | Project docs; research design under [`docs/research/`](docs/research/) |
| [`scripts/tokenizers/`](scripts/tokenizers/) | Tokenizer training, morphology tooling, StatBound CLI, Phase C harness, SHA verify |
| [`scripts/models/`](scripts/models/) | Baseline LM train / matrix / plot utilities |
| [`scripts/data/`](scripts/data/) | Corpus cleaning, splits, validation |
| [`src/tokenizers/`](src/tokenizers/) | StatBound-Unigram implementation |
| [`tests/`](tests/) | Unit tests (including λ=0 Unigram equivalence and Phase C infra) |
| [`requirements-tokenizers.txt`](requirements-tokenizers.txt) | Tokenizer Python deps |

---

## Reproducibility

- Frozen JSON configs and executable specs  
- **SHA-256** hashes of key artifacts in the eval protocol  
- Decision log for protocol changes  
- Deterministic tokenizer tests; **λ=0 ≡ Unigram**; exact per-word reconstruction  
- Boundary-stats regeneration must match the frozen hash:

```bash
.venv/bin/python scripts/tokenizers/verify_boundary_stats_repro.py
```

- Git commits as experimental anchors (private remote: `research-lab`)

**Verified environment (development machine):**

- Python **3.12.3**  
- SentencePiece **0.2.0**  
- PyTorch **2.11.0+cu128**  
- NVIDIA RTX 5070 (~12 GB VRAM), WSL2  

Hardware notes describe the lab setup only; they are **not** performance guarantees.

---

## Earlier transformer-from-scratch work

This repository began with an educational goal: implement transformer components from first principles—

```text
attention → multi-head attention → transformer blocks → GPT → training loop
```

That remains part of the broader lab mission (**build it → measure it → change one thing → measure again**). The **active experimental track** today is low-resource **tokenization** under the Mthandizi program, not architecture speedrunning.

---

## Research roadmap (controlled sequence)

```text
delayed self-review (25)
        ↓
freeze final morphology development benchmark
        ↓
morphology + tokenizer-efficiency evaluation (Phase C)
        ↓
select λ*
        ↓
freeze final tokenizer
        ↓
LM validation matrix (selected λ* only)
        ↓
ablations / conclusions freeze
        ↓
morphology holdout (one-shot)
        ↓
LM test (one-shot)
        ↓
optional external downstream evaluation
```

**MasakhaNER** is reserved as a possible **later external** NER benchmark; it is **not** part of current tokenizer development or λ selection.

---

## Data and redistribution

This repository is currently **private**.  

Datasets and source corpora may carry **their own licenses and redistribution requirements**. Publication of this code repository does **not** automatically relicense third-party data. Consult provenance notes under `data/` and corpus documentation before redistribution.

No project-wide open-source license is declared in this README.

---

## What this README does **not** claim

Until controlled experiments establish otherwise, this project does **not** claim:

- a “novel” or “state-of-the-art” tokenizer  
- that StatBound improves language models  
- “first Chichewa tokenizer” as methodological novelty  
- multi-annotator gold morphology  
- scientific StatBound results (they have **not** been run)

Claims require evidence under the frozen criteria.
