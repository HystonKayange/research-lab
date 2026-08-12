# LM budget decision v0.1 (post-calibration)

## Fixed-character budget (primary)

| Quantity | Value |
|----------|------:|
| Frozen train content characters | **4,623,799** |
| Effective epoch target | **30** |
| Character target | **138,713,970** = 30 × 4,623,799 |
| Configured overshoot | canary-style stop after step that reaches target |

**Reason:** Selected from the BPE-8000 seed-42 architecture-matched calibration run. Validation BPC improved through approximately 30 effective epochs and degraded by 40 epochs.

Best calibration checkpoint (evidence, not the config target):

* ~30.0057 epochs, 138,740,486 characters, step 3964  
* val BPC 1.4426772869, val BPB 1.4287043822  

Configured target uses **exact** 30 × corpus characters (not the slight checkpoint overshoot).

## Fixed-update budget (secondary)

Measured packing (context 256, micro 16, accum 2):

| Tokenizer | chars / update | epochs @ 2000 | epochs @ 4000 | updates for ~30 ep |
|-----------|---------------:|--------------:|--------------:|-------------------:|
| character | ~8,094 | ~3.5 | ~7.0 | ~17,137 |
| bpe_8000 | ~35,000 | ~15.1 | ~30.3 | ~3,963 |
| unigram_8000 | ~35,276 | ~15.3 | ~30.5 | ~3,932 |

**Decision:** revise **2,000 → 4,000** optimizer updates.

* At 2,000 updates, subword models stay ~15 epochs — undertrained vs calibrated 30-epoch region.  
* At 4,000 updates, subword models ≈ 30 epochs of text under **equal updates**.  
* Character remains shorter in character exposure under equal updates (~7 epochs) — expected and documented.  
* Do **not** set per-tokenizer updates to 30 epochs (that would abandon fixed-update fairness).

## Artifacts excluded from final multi-seed stats

* Systems canary (4M characters, path `.../final/fixed_characters`)  
* Calibration run (`.../calibration/fixed_characters`)  
* Pilot runs  

## Final scientific matrix identity

`lm_baselines_v0_1_final_matrix_r2` — 36 runs with path slugs:

* `fixed_characters_e30`  
* `fixed_updates_u4000`  
