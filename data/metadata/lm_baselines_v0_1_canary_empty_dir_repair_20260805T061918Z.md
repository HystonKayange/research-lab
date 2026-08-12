# Canary empty-directory repair audit

**Timestamp (UTC):** 2026-08-05T06:19:18Z  
**Real training executed:** no  
**CUDA training executed:** no  
**Canary accepted:** no  

## Cause

Canary launch failed with exit code 1 before producing artifacts. The run directory existed but was empty (no files, no nested dirs). Root cause: matrix lock file was created *inside* the run directory; `train_lm_baseline` then treated the non-empty directory as an existing run and refused to proceed. After the launcher released the lock, only an empty directory remained.

## Actions

1. Verified target was empty (`find -mindepth 1` → 0 entries).
2. Moved empty directory to:

   `data/models/chichewa_corpus_v0.1/lm_baselines_v0.1/architecture_matched/bpe_8000/seed_42/final/fixed_characters_empty_backup_20260805T061918Z`

3. Backed up matrix status to:

   `data/metadata/lm_baselines_v0_1_matrix_status.pre_canary_repair_20260805T061918Z.json`

4. Reset canary run  
   `lm_baselines_v0_1_final_matrix__final__arch__bpe_8000__seed42__chars`  
   from `failed` → `pending`, preserving `previous_failure` and `failure_history`.

5. Code hardening (no training):

   * matrix lock moved **beside** the run dir (not inside)
   * `ensure_run_dir_free` allows empty dirs and ignores `.run.lock`

## Status after repair

* pending: 36  
* failed: 0  
* completed: 0  
* canary_accepted: false  
