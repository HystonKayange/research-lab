# Canary report

Accepted: **true**

```json
{
  "run_dir": "/home/cyai/projects/research/transformer-lab/data/models/chichewa_corpus_v0.1/lm_baselines_v0.1/architecture_matched/bpe_8000/seed_42/final/fixed_characters",
  "exists": true,
  "canary_acceptance_criteria_passed": true,
  "run_id": "lm_baselines_v0_1_final_matrix__final__arch__bpe_8000__seed42__chars",
  "status": "completed",
  "tokenizer_id": "bpe_8000",
  "seed": 42,
  "track": "architecture_matched",
  "budget_policy": "fixed_characters",
  "validation_bpc": 2.413509798534404,
  "validation_bpb": 2.3901339939057373,
  "characters_processed": 4009606.818601813,
  "character_target": 4000000,
  "character_overshoot": 9606.818601813167,
  "optimizer_steps": 112,
  "tokens_processed": 913920,
  "runtime_s": 4.465069457000936,
  "peak_vram_gb": 0.7370014190673828,
  "tokens_per_second": 204682.14633638752,
  "characters_per_second": 897994.2769568819,
  "best_checkpoint": "best.pt",
  "checkpoint_sha256": "360d4cf95721e19376f6eeb4ad74ad04d081e5b88c89a598afeb342b52f07d49",
  "checkpoint_reload_ok": true,
  "reloaded_validation_bpc": 2.4135339476365782,
  "nan_or_inf_detected": false,
  "validation_improved_from_initial": true,
  "initial_validation_bpc": 3.046009948885168,
  "test_evaluated_during_training": false,
  "split_checksums_ok": true,
  "parameter_counts": {
    "total": 5273088,
    "embedding": 2113536,
    "non_embedding": 3159552,
    "tied_embeddings": true
  },
  "selection_lock_present": true,
  "character_exposure_within_tolerance": true,
  "criteria": {
    "training_completed": true,
    "no_nan_inf": true,
    "character_exposure_ok": true,
    "validation_improved": true,
    "checkpoint_reload_ok": true,
    "checksums_ok": true,
    "manifest_complete": true,
    "selection_lock_present": true,
    "test_not_used": true
  }
}
```
