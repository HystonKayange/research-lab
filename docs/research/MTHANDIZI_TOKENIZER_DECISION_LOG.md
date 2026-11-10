# Mthandizi tokenizer — decision log

Every material research decision is recorded here.  
**Do not silently change decisions.** If a decision is revised, add a new dated entry that references the old one and state whether the registered evaluation protocol changes.

| Field | Meaning |
|-------|---------|
| date | UTC date |
| evidence considered | What was looked at |
| decision | What was chosen |
| rejected alternatives | What was not chosen |
| unresolved questions | Open issues |
| approval status | draft / proposed / approved / superseded |
| changes_registered_eval_protocol | yes / no |

---

## D-0001 — Open research design without implementation

- **date:** 2026-08-06
- **evidence considered:**
  - LM baselines v0.1 r2 validation: Unigram-8000 provisional leader in all four groups; test not evaluated
  - Tokenizer baselines v0.1 fertility/coverage on validation
  - Automatic disagreement audit on train+validation word samples
- **decision:**
  - Treat Unigram-8000 as primary LM baseline to beat
  - Defer MthandiziTokenizer implementation until Phase A–B review and pre-registration approval
  - Keep LM test and morphology holdout locked
- **rejected alternatives:**
  - Implement hybrid tokenizer immediately from linguistic intuition
  - Use LM test metrics for design
  - Claim morphological superiority of Unigram from BPC alone
- **unresolved questions:**
  - What fraction of BPE/Unigram disagreements are genuinely morphological?
  - Which design family (Phase C) is justified after annotation?
- **approval status:** proposed
- **changes_registered_eval_protocol:** no (protocol defined in parallel; not yet frozen)

---

## D-0002 — Morphology benchmark structure

- **date:** 2026-08-06
- **evidence considered:** need for human labels without overfitting method design
- **decision:**
  - Development annotation set ~160–240 items, train-primary, multi-label candidate strata
  - Locked holdout ~80 items, validation-derived unseen/low-frequency preference, sealed payload
  - Release only via `release_morphology_holdout.py` with dual method-freeze flags
- **rejected alternatives:**
  - Single pooled annotation set used for both design and final morphology metrics
  - Auto-generated gold morpheme labels
- **unresolved questions:**
  - Annotator recruitment and IAA targets
  - Exact phenomenon tag inventory for human_phenomenon_tags
- **approval status:** proposed
- **changes_registered_eval_protocol:** yes (introduces locked morphology holdout metrics)

---

## D-0003 — Success criteria remain unapproved until human sign-off

- **date:** 2026-08-06
- **evidence considered:** risk of post-hoc threshold fishing
- **decision:**
  - Document candidate success thresholds in config and blueprint as `proposed_pending_human_approval`
  - Forbidden: choosing thresholds after observing proposed-method results
- **rejected alternatives:**
  - Silent adoption of arbitrary BPC deltas without review
- **unresolved questions:**
  - Exact fertility regression cap (candidate 10%)
  - Exact source-specific BPC regression cap (candidate 0.02)
- **approval status:** draft (requires human approval)
- **changes_registered_eval_protocol:** yes (when approved)

---

## D-0004 — Language scope

- **date:** 2026-08-06
- **evidence considered:** single-language corpus; no second Bantu corpus prepared
- **decision:**
  - Chichewa is the only case study for v0.1 claims
  - Design machinery should separate language-independent code from Chichewa config for later replication
  - Do not claim Bantu-general results
- **rejected alternatives:**
  - Marketing the method as Bantu-general without multi-language evidence
- **unresolved questions:**
  - Which second language for a later replication study?
- **approval status:** proposed
- **changes_registered_eval_protocol:** no

---

## D-0005 — Freeze proposed success criteria (pending human approval)

- **date:** 2026-08-06
- **evidence considered:**
  - LM baselines v0.1 r2 validation hierarchy
  - Need to prevent post-hoc threshold fishing
  - Annotation workflow readiness (pilot 40 + dual annotators)
- **decision:**
  - Register primary comparison as parameter_matched × fixed_characters (30 epochs), seeds 42/1337/2026, metric validation BPC, baseline Unigram-8000
  - Record SC1–SC9 numerical candidates as `proposed_pending_human_approval` in `docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md` and matching JSON config
  - Do not auto-approve thresholds
- **rejected alternatives:**
  - Approving thresholds automatically in software
  - Making architecture_matched the sole primary comparison without human sign-off
- **unresolved questions:**
  - Exact absolute values for SC3/SC4/SC5 after stakeholder review
- **approval status:** proposed (criteria text frozen as proposal; numeric approval still pending)
- **changes_registered_eval_protocol:** yes

---

## D-0006 — Annotation pilot and dual-annotator workflow

- **date:** 2026-08-06
- **evidence considered:** 200-item development set; need IAA before full annotation
- **decision:**
  - Create deterministic 40-item pilot stratified across disagreement, length, rarity, prefixes/suffixes, noun/verb-like patterns, ŵ, mixed language, uncertain automatic candidates
  - Require independent annotator_a and annotator_b worksheets
  - Measure exact segmentation agreement, boundary F1, tag Jaccard, uncertainty agreement, adjudication rate; do not default to Cohen’s kappa without justification
- **rejected alternatives:**
  - Single-annotator gold
  - Auto-filling human labels from BPE/Unigram
  - Using locked holdout in the pilot
- **unresolved questions:**
  - Annotator recruitment; target IAA levels for proceeding to full 200
- **approval status:** proposed
- **changes_registered_eval_protocol:** no

---

## D-0007 — Single native annotator for development benchmark (this phase)

- **date:** 2026-08-06
- **evidence considered:**
  - Completed 40-item pilot with annotator_a (native Chichewa)
  - No second human annotator available this phase
  - AI/Claude co-pilot labels must not become gold
- **decision:**
  - Development benchmark uses **one** native annotator: `annotator_id=annotator_a`
  - Do **not** require dual human annotation or human–human IAA this phase
  - Preserve Claude/AI pilot material as **exploratory only**; exclude from final development gold
  - Prepare remaining **160** items for Annotator A; merge to full **200** when complete
  - Quality control via **delayed self-review** of 25 blinded items (self-consistency), not second annotator
  - Morphology holdout remains locked; multi-annotator validation is future work
- **rejected alternatives:**
  - Treating Claude annotations as gold
  - Requiring Annotator B for this phase
  - Releasing morphology holdout for development labeling
- **unresolved questions:**
  - Self-consistency thresholds for accepting full 200 after re-review
  - Timeline for multi-annotator upgrade
- **approval status:** proposed
- **changes_registered_eval_protocol:** yes (annotator design for morphology metrics)

---

## D-0008 — Freeze success criteria before MthandiziTokenizer implementation

- **date:** 2026-08-11
- **evidence considered:**
  - LM baselines v0.1: Unigram-8000 strongest validation LM baseline under the registered matrix
  - Morphology development preparation complete: canonical 200; active **195**; excluded **5**; reconstruction failures 0 on active set
  - Single native annotator (`annotator_a`); self-consistency planned (not human–human IAA)
  - Prior draft criteria (`D-0003`, `D-0005`) were `proposed_pending_human_approval` with risk of post-hoc threshold fishing
  - Active gold path: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_active_195_v0_1.jsonl`
- **decision:**
  - **Freeze** success criteria SC1–SC9 as `frozen_pre_implementation` **before** method selection, MthandiziTokenizer implementation, training, or hyperparameter search
  - Authoritative documents:
    - `docs/research/MTHANDIZI_TOKENIZER_SUCCESS_CRITERIA_v0_1.md`
    - `configs/tokenizers/mthandizi_success_criteria_v0_1.json`
  - **SC1 (primary):** parameter_matched × fixed_characters; metric validation BPC; baseline Unigram-8000; 3 seeds (42, 1337, 2026); pass = lower mean BPC **and** ≥2/3 seeds improve; no LM test for selection
  - **SC2:** architecture_matched × fixed_characters — secondary robustness only (does not replace SC1)
  - **SC3:** fixed-updates tracks — diagnostic only
  - **SC4:** morphology on **active 195**; boundary F1 ≥ strongest of {BPE-8000, Unigram-8000} **+ 0.03** absolute; labeled DEVELOPMENT-set evidence; holdout not used
  - **SC5:** tokens-per-character ≤ **+10%** relative vs Unigram-8000 (or pre-logged justified exception if SC1 improves enough); do not retune the 10% after results
  - **SC6:** no Bible/Wikipedia source regression > **0.02** BPC vs Unigram under primary condition
  - **SC7:** multi-mechanism designs require ablations after method selection (do not invent ablations early)
  - **SC8:** morphology holdout remains locked until algorithm + hyperparameters frozen; one confirmatory unlock with decision-log entry
  - **SC9:** LM test untouched until design, HPs, ablations, and development conclusions are complete; one final test pass; no method selection on test
  - Outcome labels frozen: **STRONG SUCCESS** / **PARTIAL RESULT** / **NEGATIVE RESULT**; negative results must be reported without criteria revision
  - Supersedes the “pending human approval” status of draft thresholds in **D-0003** and **D-0005** for protocol freezes (those entries remain historical)
- **rejected alternatives:**
  - Implementing or training MthandiziTokenizer before criteria freeze
  - Using morphology holdout or LM test during development/selection
  - Making architecture_matched or fixed-updates the primary success gate
  - Treating character tokenization as an equivalent morphology baseline for SC4 pass/fail
  - Silent post-hoc threshold changes after seeing proposed-method results
  - Including the 5 excluded items in morphology scores
- **unresolved questions:**
  - Which design family (Phase C) will be selected under these frozen criteria
  - Exact ablation list (depends on selected method; SC7 forbids inventing it early)
  - Self-consistency pass-2 timing relative to method work (does not alter SC1–SC9)
- **approval status:** **approved / frozen_pre_implementation**
- **changes_registered_eval_protocol:** **yes** (evaluation success protocol frozen pre-implementation)

---

## D-0009 — Prior-art review and Prototype V1 method selection (pre-implementation)

- **date:** 2026-08-11
- **evidence considered:**
  - Verified ACL primary sources (must-include 8 + additional 3): MorphBPE (Asgari et al. 2026), Latin morph-guided tokenization (Hudspeth et al. 2026), MoVoC (Teklehaymanot et al. 2025), Saleva & Lignos 2021, Richburg et al. 2020 (Swahili), Kudo 2018, Mager et al. 2022, Lundin et al. 2026 (token tax), Bostrom & Durrett 2020, Meyer & Buys 2022 (Nguni SSLM), García et al. 2025
  - Frozen success criteria SC1–SC9 (D-0008)
  - Active morph development set n=195; no large Chichewa analyzer
- **decision:**
  - Record prior-art review in `docs/research/MTHANDIZI_TOKENIZER_PRIOR_ART_v0_1.md` and matrix `data/reports/mthandizi_tokenizer_prior_art_matrix_v0_1.json`
  - Reject morphology-constrained BPE as flagship (**MorphBPE overlap**; Candidate 3 HIGH novelty risk)
  - Reject pure stochastic segmentation, pure char fallback, and supervised 195-gold vocab injection for V1
  - Shortlist: (S1) StatBound-Unigram; (S2) unsupervised pre-seg + Unigram control; (S3) plain Unigram baseline
  - **Select Prototype V1 = StatBound-Unigram** (statistical boundary/affix discovery + boundary-biased Unigram + character residual) — design only
  - Novelty claim status: **provisional** (composition under Unigram + weak stats + fixed Chichewa protocol; not a new primitive)
  - Do **not** implement or train until a later implementation phase
- **rejected alternatives:**
  - MorphBPE-style constrained BPE as primary method claim
  - MoVoC-style supervised morph vocabulary requiring large labeled morph data
  - Joint segmental LM (Meyer & Buys) as drop-in V1 under current fixed-tokenizer protocol
  - Claiming novelty solely from “first for Chichewa”
- **unresolved questions:**
  - Exact statistical boundary estimator and soft-bias formulation at implementation time
  - Whether S1 can clear SC1 and SC4 jointly (PARTIAL outcome remains likely a priori)
- **approval status:** proposed (method selected for V1; implementation not started)
- **changes_registered_eval_protocol:** no (criteria unchanged; method choice recorded)

---

## D-0010 — Freeze StatBound-Unigram V1 executable algorithm (pre-scientific evaluation)

- **date:** 2026-08-11
- **evidence considered:**
  - Method selection D-0009 (StatBound-Unigram Prototype V1)
  - Existing Unigram-8000 baseline artifacts and SentencePiece 0.2.0 API (n-best + piece scores)
  - Leakage rules: train-only boundary learning; no morph gold; holdout/test locked
- **decision:**
  - Freeze executable V1 in `docs/research/MTHANDIZI_TOKENIZER_V1_SPEC.md` and `configs/tokenizers/statbound_unigram_v1.json`
  - Foundation: frozen SentencePiece Unigram-8000 model (no MorphBPE; no vocab expansion)
  - Boundary discovery: train-only statistical prefix/suffix productivity + branching scores; length-1 affix downweight; gates \(S_{\min}=5\), \(P_{\min}=3\), \(L_{\max}=6\)
  - Re-ranking: \(\mathrm{score}=\mathrm{unigram\_score}+\lambda\cdot\mathrm{compat}\) over n-best (\(N=16\)); deterministic tie-break
  - Hyperparameter search space frozen: \(\lambda \in \{0.0, 0.25, 0.5, 1.0, 2.0\}\) with mandatory \(\lambda=0\) Unigram equivalence control
  - Implement tokenizer + unit/sanity tests only; **no** SC1–SC4 scientific eval in this step
- **rejected alternatives:**
  - Hard pre-segmentation before Unigram
  - Morphology-constrained BPE
  - Learning boundaries from morphology development labels or validation text
  - Expanding \(\lambda\) grid after seeing Mthandizi results
  - Enlarging vocabulary beyond base 8000
- **unresolved questions:**
  - Which \(\lambda\) will pass SC1/SC4 after scientific evaluation (not answered here)
- **approval status:** frozen_pre_evaluation
- **changes_registered_eval_protocol:** no (SC1–SC9 unchanged; V1 algorithm frozen)

---

## D-0011 — Freeze StatBound-Unigram V1 scientific evaluation & λ-selection protocol (pre-results)

- **date:** 2026-08-11
- **evidence considered:**
  - Frozen success criteria SC1–SC9 (D-0008)
  - Frozen StatBound-Unigram V1 algorithm + implementation (D-0010); λ=0 equivalence tests pass
  - Existing LM baseline matrix seeds/config (`configs/models/lm_baselines_v0_1_final_matrix.json`)
  - Active morphology development file exists (n=195) but self-review gate not yet completed
  - Reproducibility snapshot hashes of train/val corpora, Unigram-8000 model, V1 config, boundary_stats, specs
- **decision:**
  - Freeze evaluation protocol in `docs/research/MTHANDIZI_TOKENIZER_EVALUATION_PROTOCOL_v0_1.md` and `configs/tokenizers/statbound_unigram_v1_eval_protocol.json`
  - λ candidates remain `{0.0, 0.25, 0.5, 1.0, 2.0}`; λ=0 is mandatory control and **cannot** be selected as the proposed method
  - Select nonzero λ* **without LM BPC**: efficiency gate `tpc ≤ 1.10 × Unigram` → max development boundary F1 → lower tpc → smaller λ
  - If no nonzero λ passes efficiency: record SC5 failed; still pick max development F1 for diagnostics; **do not** retune 1.10
  - Development morph F1 is **tuning evidence only**; confirmatory morph = holdout (Phase I)
  - Scientific morph eval / λ selection blocked until delayed self-review 25 completes and final morph dev file is frozen
  - LM matrix trains **only** selected nonzero λ* after λ* freeze (no multi-λ BPC shopping)
  - Phase order A→J frozen (self-review → morph freeze → morph/efficiency → λ* → tok freeze → LM → analysis → conclusions → holdout once → LM test once)
  - **No scientific results computed in this decision**
- **rejected alternatives:**
  - Choosing λ by validation BPC
  - Training all λ LMs then picking the best BPC
  - Using morphology holdout or LM test for λ selection
  - Expanding λ grid after seeing StatBound results
  - Treating development morph F1 as confirmatory SC4
  - Starting Phase C before self-review
- **unresolved questions:**
  - Final post–self-review morphology development path, n, and hash (set in Phase B)
  - Which λ* will be selected (unknown until Phase D)
- **approval status:** frozen_pre_results
- **changes_registered_eval_protocol:** **yes** (selection and phase order for V1 scientific evaluation frozen pre-results)

---

## D-0012 — Freeze Chichewa Level-B morphology development benchmark v0.2 after native-speaker adjudication

- **date:** 2026-08-14
- **evidence considered:**
  - Frozen Level-B policy v0.1 and policy application v0.1
  - Native-speaker adjudication of all 11 previously unresolved HUMAN_REVIEW cases
  - Source-grounded Level-B re-audit of the active 195-item development set
- **decision:**
  - Version the policy clarification as `docs/research/CHICHEWA_LEVEL_B_ADJUDICATION_POLICY_v0_2.md`
  - Freeze the native-speaker adjudicated Chichewa morphology development benchmark v0.2 with 162 active items and 33 excluded items
  - Record the completed human exceptions and hashes in the v0.2 freeze manifest
  - Preserve exact agreement 0.52 and boundary F1 0.841 as historical measurements of the original underspecified annotation protocol
  - Keep the morphology holdout locked/untouched, keep the LM test locked/untouched, and leave Phase C not started
- **rejected alternatives:**
  - Reinterpreting historical self-review measurements after adjudication
  - Using tokenizer outputs, tokenizer metrics, LM results, or holdout behavior to resolve morphology
  - Creating benchmark gold changes beyond this adjudicated development benchmark
- **unresolved questions:**
  - None among the 11 HUMAN_REVIEW cases; future scientific evaluation remains outside this decision
- **approval status:** frozen_pre_evaluation
- **changes_registered_eval_protocol:** no (the morphology instrument was frozen before Phase C; no tokenizer evaluation was accessed)

---

## D-0013 — Freeze Phase-C negative morphology result and StatBound V1 λ*=0.25 before Phase F

- **date:** 2026-08-14
- **evidence considered:**
  - Frozen Phase-C results in `data/reports/phase_c_morphology_v0_2_results.json`
  - Frozen λ-selection record in `data/reports/phase_c_lambda_selection_v0_2.json`
  - Post-Phase-C failure diagnostic in `data/reports/phase_c_statbound_failure_diagnostic_v0_1.json`
  - Frozen Level-B development benchmark v0.2 and its SHA-256 provenance
- **decision:**
  - Preserve the Phase-C result, λ-selection, provenance, and failure-diagnostic artifacts as the scientific record
  - Record Unigram8k as the strongest standard morphology comparator (development boundary F1 `0.5551`)
  - Record all StatBound candidates at development boundary F1 `0.5551`; SC4 development criterion **NOT MET**
  - Freeze StatBound V1 `lambda_star = 0.25`, selected by the pre-registered nonzero-candidate tie-break rule
  - Enter LM evaluation despite failing SC4 because the pre-registered protocol evaluates the selected λ* on the remaining independent criteria; Phase-C morphology failure was not used to modify the method
  - Proceed to Phase F using only λ*=0.25 under the four frozen LM regimes; keep the morphology holdout and LM test locked/untouched
- **rejected alternatives:**
  - Changing λ after the morphology result
  - Rescaling the StatBound score, changing n-best, changing boundary statistics, or modifying the tokenizer algorithm
  - Altering the benchmark or success criteria
  - Running V2 fixes, post-hoc λ values, holdout evaluation, LM-test evaluation, or LM-BPC-based method changes
- **unresolved questions:**
  - Whether StatBound λ*=0.25 improves validation BPC under the pre-registered primary and secondary LM regimes
- **approval status:** frozen_pre_lm_evaluation
- **changes_registered_eval_protocol:** no (Phase-C result and λ* are recorded under the frozen protocol; no criteria or method changes)

---

---

## D-0014 — Complete Phase-F validation of StatBound V1 λ*=0.25

- **date:** 2026-08-14
- **evidence considered:**
  - Frozen Phase-C λ-selection and morphology result
  - Existing audited Unigram8k baseline matrix `lm_baselines_v0_1_final_matrix_r2`
  - Twelve validation-only StatBound V1 λ*=0.25 runs across the four preregistered LM regimes
  - Phase-F result, success-criteria, provenance, and integrity artifacts
- **decision:**
  - Preserve StatBound V1 λ*=0.25 as the evaluated frozen V1 method; no λ, algorithm, benchmark, n-best, score scaling, or success criterion was changed
  - Record SC1 primary parameter-matched × fixed-character as **FAIL**: StatBound mean validation BPC `1.4374023267` versus Unigram8k `1.4370611408` (Δ `+0.0003411859`), with `1/3` seeds beating Unigram
  - Record SC2 architecture-matched × fixed-character as **PASS** secondary evidence (mean Δ `-0.0005362697`), without replacing SC1
  - Record fixed-update regimes as diagnostic only; no additional criterion or method decision was made from them
  - Record SC4 as the frozen Phase-C morphology-development **FAIL**; it was not rerun or reinterpreted
  - Record SC5 efficiency as **PASS** and SC6 source-specific validation as **PASS** under the frozen thresholds
  - Stop after Phase-F validation; do not proceed automatically to later experiments
  - StatBound V1 entered LM evaluation despite failing SC4 because the pre-registered protocol evaluates the selected λ* on the remaining independent criteria; Phase-C morphology failure was not used to modify the method
- **rejected alternatives:**
  - Changing λ, rescaling the StatBound score, changing n-best or boundary statistics, modifying the algorithm, changing the benchmark, or altering success criteria
  - Using SC2 or fixed-update diagnostics to replace the failed primary SC1 gate
  - Accessing the morphology holdout or LM test, running post-hoc λ values, V2 fixes, or ablations
  - Recomputing or overwriting historical exact agreement `0.52` and boundary F1 `0.841`
- **unresolved questions:**
  - None within the completed preregistered Phase-F validation; any method improvement is outside this frozen V1 record and requires a separately authorized experiment
- **approval status:** frozen_phase_f_validation_complete
- **changes_registered_eval_protocol:** no (evaluation followed the frozen protocol; no outcome-driven method or criterion changes)

---

## D-0015 — Close StatBound-Unigram V1 as a completed negative method

- **date:** 2026-08-18
- **evidence considered:**
  - Frozen Phase-C negative morphology result and λ*=0.25 (D-0013)
  - Frozen Phase-F validation: SC1 fail, SC4 fail (D-0014)
  - Analysis-only Unigram n-best oracle and compat-alignment on the frozen 162-item development set (`data/reports/unigram_nbest_oracle_v0_1.md`)
  - Independent review that V1 must not be silently retuned
- **decision:**
  - Close **StatBound-Unigram V1** as a completed **negative** experiment. The method is finished. Do not revise λ, n-best, the compatibility formula, or the V1 score after seeing results
  - Record the oracle as analysis-only, not as a tokenizer and not as V2: Unigram n-best=16 has large unused Level-B room (macro F1 0.5551 → 0.7913, Δ **+0.2362**), but V1 `compat` does not select it
  - Record that a compat-oracle is **worse** than Unigram (macro F1 0.5169). Recalibrating `u + λb` or any RelBound-style use of the **same** `b` is therefore not an authorized next method
  - Pre-declared family decision from the oracle stands: `do_not_calibrate_wrong_signal`
  - Do **not** start RelBound, MorphCand, TrainBias, Morfessor, or any other successor in this decision
  - Do **not** unlock morphology holdout or LM test
  - Any later method must be a **separately named, separately pre-registered** experiment, and only after the research question is restated (see `docs/research/STATBOUND_V1_CLOSEOUT_AND_RETHINK_v0_1.md`)
- **rejected alternatives:**
  - Increasing λ or introducing α and calling that V1 or V1b
  - Implementing RelBound-Unigram V2 with V1 compatibility
  - Treating SC2/SC5/SC6 as a morphological or LM success
  - Using oracle choices or ΔF1 to set hyperparameters
  - Unlocking holdout or LM test to look for a positive story
  - Immediately starting a new tokenizer implementation
- **unresolved questions:**
  - What single claim the research program should make next (LM BPC vs Level-B morphology vs benchmark/resource)
  - Whether Level-B granularity is the right target construct for a tokenizer, as opposed to an evaluation instrument
  - What unsupervised or lightly linguistic signal, if any, actually prefers the unused n-best alternatives
- **approval status:** approved
- **changes_registered_eval_protocol:** no (closes a finished method; does not change SC1–SC9, locks, or V1)

---

## D-0016 — Pivot from method-hunting to empirical consolidation

- **date:** 2026-08-18
- **evidence considered:**
  - Closed StatBound-Unigram V1 negative result (D-0015)
  - Frozen Phase C/F numbers and Unigram n-best oracle / error anatomy
  - Decision to produce a small empirical paper / technical report rather than a successor tokenizer
- **decision:**
  - The active project goal is now **consolidation of existing evidence** into a reproducible Git research record and an eventual 6–8 page empirical paper / technical report
  - **No new tokenizer or V2** is authorized in this phase
  - Prefix-stack recovery is **future work only**, not required for the current project to be finished
  - Morphology holdout and LM test remain **locked** while the repository and paper draft are developed
  - The central story is Unigram vs BPE on Level-B morphology, undersegmentation anatomy, n-best availability vs selection, and the StatBound V1 negative result — not “does a proposed method win?”
  - Charter: `docs/research/EMPIRICAL_PAPER_CHARTER_v0_1.md`
- **rejected alternatives:**
  - Implementing RelBound, Morfessor-as-V2, or any other successor before consolidation
  - Treating prefix recovery as necessary for the current paper
  - Unlocking holdout or LM test during drafting
  - Reframing V1 as a partial success
- **unresolved questions:**
  - Venue (technical report vs AfricaNLP / Findings-style short paper) after the draft exists
  - Whether a later, separately registered prefix-recovery probe is ever run
- **approval status:** approved
- **changes_registered_eval_protocol:** no

## D-0017 — Restrict public research artifacts and preserve provenance through the approved history rewrite

- **date:** 2026-11-10
- **evidence considered:**
  - Owner approval to purge eight protected research artifacts and replace historical author/committer email fields
  - Remote ref inventory: only `main` was published; the morphology freeze tag existed locally only
  - Private original-history and uncommitted-work backups; complete old-to-new commit mapping
  - Rewrite validation: 10 commits, 4,940 unchanged retained file versions, unchanged development benchmark SHA-256, and zero credential findings in 446 scanned historical text versions
- **decision:**
  - Remove the exact eight LM-test/morphology-holdout/test-metrics paths listed in `data/reports/public_history_rewrite_2026_11_10.json` from the published history
  - Preserve every local private file and all pre-existing uncommitted work; do not open either locked set for analysis or evaluation
  - Replace historical author/committer email fields with the owner's GitHub noreply address; preserve names, dates, messages, and all retained file bytes
  - Publish rewritten `main` using an explicit force-with-lease; remap the local freeze tag without publishing a new tag
  - Keep original Git IDs inside scientific reports as historical evidence and provide the commit mapping separately
  - Preserve exact agreement `0.52` and boundary F1 `0.841` as historical measurements of the original annotation protocol; do not recompute or reinterpret them
  - Keep development benchmark gold, algorithms, configurations, policies, evaluation results, and morphology/LM-test research locks unchanged
  - Maintain credential ignore rules, the local publication hook, CI publication checks, GitHub secret scanning, and push protection
- **rejected alternatives:**
  - Rewriting scientific report bodies or changing data/content hashes to conceal the publication cleanup
  - Opening or evaluating a locked set, rerunning experiments, or starting a successor tokenizer
  - Claiming that previously downloaded/cloned data or cached GitHub views can be recalled by rewriting branch history
- **unresolved questions:**
  - Copies retained in older clones, forks, downloads, or server-side caches require separate handling outside the published branch refs
- **approval status:** approved_by_repository_owner
- **changes_registered_eval_protocol:** no (publication/privacy maintenance only; scientific rules and historical measurements are unchanged)

## D-0018 — Prepare publication v0.2 with corrected interpretation and preserved experiment records

- **date:** 2026-11-10
- **evidence considered:**
  - Frozen Phase-C, Phase-F, failure-diagnostic, adjudication, and stored oracle reports
  - Existing local policy/review/self-consistency records; their original bytes and historical measurements
  - The owner-authorized publication-readiness review and primary publisher/ACL bibliographic records
- **decision:**
  - Preserve V1, λ*=0.25, gold, scoring rules, selection criteria, scientific results, and all historical measurements
  - Correct current presentation to distinguish selected-oracle misses 2/71/41 from candidate-union absence 0/27/22; union coverage is not proof of joint path recoverability
  - Report metric-specific undefined-value handling, recorded empty normalized-piece warnings, and the difference between 125 changed paths and 115 strict defined-F1 improvements
  - State the actual label provenance: original native-speaker annotations, 133 accepted policy revisions, and explicit native-speaker decisions on 11 exceptions
  - Produce a seven-page v0.2 working draft from one Markdown source, checked tables, corrected figures, verified reference links, and a public artifact-build guide
  - Archive 26 pre-existing policy/review/self-review files without editing their contents or rerunning their analyses; do not interpret recommendations as a new gold file
  - Preserve the original v0.1 draft and append dated qualifications to the historical charter/close-out instead of silently rewriting their earlier rationale
  - Document prior public test-artifact exposure and separate presentation reproducibility from full training/source-acquisition reproducibility
  - Keep code licensing, annotation redistribution permission, and author approval explicit as pending formal-release decisions
- **rejected alternatives:**
  - Silently fixing the scorer, altering annotations, rerunning scientific evaluations, or treating the document revision as a successor tokenizer experiment
  - Using oracle paths as training labels or treating positional bins as independently adjudicated morpheme categories
  - Imposing a code/dataset license without the owner's choice or describing a previously public set as restored to historical secrecy
- **unresolved questions:**
  - Owner licensing and annotation-permission decisions; author acceptance of the revised claims before submission
  - Whether a future separately versioned methodology should change undefined-value or empty-piece handling (outside this revision)
- **approval status:** editorial_improvements_authorized_by_owner; formal_submission_pending_author_review
- **changes_registered_eval_protocol:** no (new summaries use stored outputs only; original scoring and outcomes are unchanged)

## Template for new entries

```markdown
## D-XXXX — title

- **date:** YYYY-MM-DD
- **evidence considered:** …
- **decision:** …
- **rejected alternatives:** …
- **unresolved questions:** …
- **approval status:** draft | proposed | approved | superseded
- **changes_registered_eval_protocol:** yes | no
```
