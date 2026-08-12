# Test readiness — LM baselines v0.1

**test_ready: `True`**

Conditions:

- `all_36_completed`: **True**
- `all_36_audited`: **True**
- `all_manifests_valid`: **True**
- `all_selection_locks_valid`: **True**
- `all_checkpoint_checksums_valid`: **True**
- `all_budget_exposures_valid`: **True**
- `no_nan_inf`: **True**
- `no_test_access_detected`: **True**
- `canary_excluded`: **True**
- `calibration_excluded`: **True**
- `pilots_excluded`: **True**
- `validation_aggregation_complete`: **True**
- `source_validation_complete`: **True**
- `figures_complete`: **True**
- `checkpoint_reload_ok_all`: **True**
- `test_ready`: **True**
- `n_expected`: **36**
- `n_valid`: **36**
- `n_failed_audit`: **0**

Failed run IDs: (none)

Later test authorization (do **not** run until operator decides):

```bash
.venv/bin/python scripts/models/evaluate_lm_baseline.py \
  --run-dir <SCIENTIFIC_RUN_DIR> \
  --splits test bible_test wikipedia_test \
  --allow-test
```
