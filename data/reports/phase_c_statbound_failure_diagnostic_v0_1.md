# Phase-C StatBound morphology failure diagnostic

This is a diagnostics-only analysis of the already-produced Phase C result. It does not alter the benchmark, algorithm, hyperparameters, λ selection, or success criteria.

## Scope and restrictions

- Frozen benchmark items: **162**
- Phase C result file used: `data/reports/phase_c_morphology_v0_2_results.json`
- Morphology holdout: **not accessed**
- LM test: **not accessed**
- LM BPC: **not accessed or used**
- Phase C: **not rerun**
- Phase F: **not run**

## Overall diagnosis

- Dominant failure-mode labels: **C, E**
- Higher-F1 alternatives exist, but no evaluated nonzero λ selected one.
- The frozen efficiency path tokenizes StatBound text via text.split(), while the baseline wrapper encodes full lines; this explains tiny validation-TPC differences but is not a morphology-F1 path failure.
- Non-dominant checks: candidate-set failure = **not supported as dominant**; boundary-statistics failure = **not supported as dominant**; objective mismatch = **not supported** because no benchmark item changed; no-useful-alternative = **not supported**.

## Changed benchmark items and boundary outcomes

| λ | changed items | percentage | added boundaries | removed boundaries | potential shifts | improved F1 | worsened F1 | unchanged F1 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 0 | 0.00% | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.5 | 0 | 0.00% | 0 | 0 | 0 | 0 | 0 | 0 |
| 1.0 | 0 | 0.00% | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.0 | 0 | 0.00% | 0 | 0 | 0 | 0 | 0 | 0 |

A changed item means the selected StatBound piece sequence differs from ordinary Unigram8k. Added and removed boundaries are exact set differences. Potential shifts pair one removed location with one added location; they are reported separately and are not substituted for the raw set differences.

### λ=0.25 changed-item list

No benchmark item changed relative to Unigram8k.
All 162 selected candidates were Unigram n-best rank 1: `{'1': 162}`.

### λ=0.5 changed-item list

No benchmark item changed relative to Unigram8k.
All 162 selected candidates were Unigram n-best rank 1: `{'1': 162}`.

### λ=1.0 changed-item list

No benchmark item changed relative to Unigram8k.
All 162 selected candidates were Unigram n-best rank 1: `{'1': 162}`.

### λ=2.0 changed-item list

No benchmark item changed relative to Unigram8k.
All 162 selected candidates were Unigram n-best rank 1: `{'1': 162}`.

## n-best candidate availability

The n-best set is the frozen SentencePiece Unigram default plus the returned `nbest_encode_as_pieces(word, 16)` candidates, deduplicated by sequence. Percentages use all 162 items.

| λ | higher-F1 candidate exists | gold segmentation exists | StatBound selects higher-F1 candidate | StatBound selects gold |
|---:|---:|---:|---:|---:|
| 0.25 | 115 (70.99%) | 22 (13.58%) | 0 (0.00%) | 13 (8.02%) |
| 0.5 | 115 (70.99%) | 22 (13.58%) | 0 (0.00%) | 13 (8.02%) |
| 1.0 | 115 (70.99%) | 22 (13.58%) | 0 (0.00%) | 13 (8.02%) |
| 2.0 | 115 (70.99%) | 22 (13.58%) | 0 (0.00%) | 13 (8.02%) |

The per-item yes/no determination for all 162 items is stored under `item_candidate_availability` in the JSON artifact.

## Boundary-score distributions

These are the selected-candidate compatibility scores used by the frozen reranker, not gold labels.

| λ | zero | nonzero | mean | median | min | max |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 40 | 122 | -0.1204 | -0.0688 | -0.6966 | 0.2354 |
| 0.5 | 40 | 122 | -0.1204 | -0.0688 | -0.6966 | 0.2354 |
| 1.0 | 40 | 122 | -0.1204 | -0.0688 | -0.6966 | 0.2354 |
| 2.0 | 40 | 122 | -0.1204 | -0.0688 | -0.6966 | 0.2354 |

## Weighting analysis

The direct selection comparison is λ × (selected boundary score − top1 boundary score) versus the top1-to-selected Unigram score gap. For completeness, λ × selected boundary score is also reported.

| λ | λ×selected score mean/median/min/max | λ×score delta mean/median/min/max | top1→selected gap mean/median/min/max | selected combined score beats top1 |
|---:|---|---|---|---:|
| 0.25 | -0.0301/-0.0172/-0.1742/0.0589 | 0.0000/0.0000/0.0000/0.0000 | 0.0000/0.0000/0.0000/0.0000 | 0 |
| 0.5 | -0.0602/-0.0344/-0.3483/0.1177 | 0.0000/0.0000/0.0000/0.0000 | 0.0000/0.0000/0.0000/0.0000 | 0 |
| 1.0 | -0.1204/-0.0688/-0.6966/0.2354 | 0.0000/0.0000/0.0000/0.0000 | 0.0000/0.0000/0.0000/0.0000 | 0 |
| 2.0 | -0.2408/-0.1377/-1.3932/0.4709 | 0.0000/0.0000/0.0000/0.0000 | 0.0000/0.0000/0.0000/0.0000 | 0 |

Across every returned non-top1 candidate (not only the candidate selected by StatBound):

| λ | alternatives | λ×boundary-score delta mean/median/min/max | Unigram gap mean/median/min/max | signal−gap mean/median/min/max | signal > gap |
|---:|---:|---|---|---|---:|
| 0.25 | 2376 | 0.0311/0.0000/-0.1177/0.2896 | 13.1764/12.8688/0.0582/42.7013 | -13.1453/-12.8574/-42.7013/-0.0582 | 0 |
| 0.5 | 2376 | 0.0623/0.0000/-0.2354/0.5792 | 13.1764/12.8688/0.0582/42.7013 | -13.1142/-12.8107/-42.7013/-0.0582 | 0 |
| 1.0 | 2376 | 0.1245/0.0000/-0.4709/1.1584 | 13.1764/12.8688/0.0582/42.7013 | -13.0519/-12.7568/-42.7013/-0.0582 | 0 |
| 2.0 | 2376 | 0.2491/0.0000/-0.9418/2.3168 | 13.1764/12.8688/0.0582/42.7013 | -12.9273/-12.6617/-42.7013/-0.0582 | 0 |

Across all non-top1 candidates, the top1-to-alternative Unigram score-gap distribution is mean/median/min/max = **13.1764/12.8688/0.0582/42.7013** over 2376 candidate alternatives.
Items with any candidate-boundary-score variation: **115/162**; items with any nonzero candidate boundary score: **122/162**.

## Source of TPC differences

| λ | benchmark-word TPC | benchmark words changed vs Unigram | benchmark token-count delta | Phase C validation-text TPC |
|---:|---:|---:|---:|---:|
| 0.25 | 0.2455 | 0 (0.00%) | 0 | 0.2281 |
| 0.5 | 0.2455 | 0 (0.00%) | 0 | 0.2281 |
| 1.0 | 0.2455 | 0 (0.00%) | 0 | 0.2282 |
| 2.0 | 0.2455 | 0 (0.00%) | 0 | 0.2283 |

Conclusion: **TPC differences come from the broader validation-text path, not from changed benchmark-word segmentations.**
The tiny validation-TPC difference between ordinary Unigram and StatBound λ=0/0.25 is consistent with the frozen implementation’s separate text paths: baseline SentencePiece encodes full lines, whereas `StatBoundUnigramTokenizer.encode_text` applies `text.split()` before encoding. This does not change the benchmark-word morphology segmentation result.

## Implementation/dead-path audit

- **lambda_0_morphology_control:** True
- **candidate_set_is_frozen_unigram_nbest:** True
- **lambda_enters_combined_score:** True
- **boundary_compatibility_called_for_candidates:** True
- **candidate_set_size_min_median_max:** [5, 16.0, 16]
- **items_with_any_lambda_reranker_change:** 0
- **validation_whitespace_path_difference:** True
- **tokenizer_algorithm_modified:** False

Relevant frozen code paths were inspected without modification:
- n-best candidate construction: `src/tokenizers/statbound/unigram_adapter.py:55`
- λ-weighted combined score: `src/tokenizers/statbound/reranker.py:100`
- boundary compatibility: `src/tokenizers/statbound/reranker.py:44`
- StatBound word encoding: `src/tokenizers/statbound/tokenizer.py:79`

## Conclusion

The diagnosis is based on candidate availability, score magnitudes, selected boundary scores, and exact per-item comparisons. It does not change λ selection or interpret the development F1 as confirmatory evidence.
