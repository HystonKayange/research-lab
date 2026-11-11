# Strict internal-boundary evaluator v0.1

Status: implementation specification for a separately versioned evaluator.
Issued: 2026-11-11, before applying this evaluator to archived predictions.
Evaluator ID: `strict-internal-boundary-v0.1`.

This specification responds to known historical scoring limitations. It is not a
preregistration of the original experiments or an independent confirmatory test.
It does not amend the original scorer, benchmark v0.2, annotation policy, λ
selection, success criteria, or published V1 outcomes. Applying the new evaluator
to stored paths produces a post-hoc measurement audit under a different metric
version. It does not train, encode, or select a new candidate.

## 1. Input contract and validation

Each record supplies an explicit, nonempty surface string, gold pieces, and
prediction pieces. Pieces are lists/tuples of strings already expressed in the
surface alphabet. A string is not implicitly split into pieces. No type coercion,
case folding, apostrophe substitution, whitespace stripping, or Unicode
normalization is performed. Offsets count Unicode code points, matching Python
string indexing, not UTF-8 bytes or grapheme clusters.

Gold must have at least one piece, no empty piece, and concatenate exactly to the
surface. Predictions must reconstruct the same surface. Empty prediction pieces
are removed and counted as normalization artifacts; other pieces are unchanged.
This operation does not remove a literal `▁` character. Raw SentencePiece token
metadata requires an explicit external adapter and is not guessed here.

Invalid types, invalid gold, or failed reconstruction raise an error. Invalid
records are not silently omitted, repaired, or assigned whole-word predictions.
Neither an empty prediction list nor a list of empty strings reconstructs a
nonempty surface.

## 2. Boundaries and exact match

A boundary is the cumulative character length after a non-final, nonempty piece.
Every boundary must satisfy `0 < offset < len(surface)`. The public offset
validator rejects endpoint, out-of-range, Boolean, non-integer, and duplicate
offsets. No endpoint is scored as a morphological boundary.

Gold and prediction boundaries are sets. TP is their intersection, FP is predicted
minus gold, and FN is gold minus predicted. Canonical exact segmentation compares
gold pieces with the prediction after removing empty pieces. The input/raw
piece-list exact flag is also retained so exact-match changes remain auditable.
With valid reconstructing nonempty pieces, exact piece-list and boundary-set
agreement are equivalent.

## 3. Zero-denominator convention

For at least one validated item:

| Gold boundaries | Predicted boundaries | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| Both sets empty | Both sets empty | 1 | 1 | 1 |
| Nonempty | Empty | 0 | 0 | 0 |
| Empty | Nonempty | 0 | 0 | 0 |
| Nonempty | Nonempty | TP / predicted | TP / gold | 2TP / (2TP + FP + FN) |

In the final row, zero overlap gives F1=0. The same convention applies to pooled
counts. Jaccard is intersection/union, or 1 if both boundary sets are empty.
Correct whole-word analyses are therefore recognized, and failures to predict
boundaries do not disappear from the macro denominator.

## 4. Aggregation and denominators

Report both pooled **micro** P/R/F1 and arithmetic **macro** P/R/F1 over exactly
the same validated item set. Every metric's item denominator is explicit. Exact
match is reported separately as numerator, denominator, and rate.

Also report separate summaries for gold items with at least one internal boundary
and gold whole-word items, alongside counts of removed empty pieces and affected
items. Strata are reporting diagnostics, not item filters or selection criteria.

An empty evaluation collection has n=0 and null aggregate scores, not perfect
scores. A nonempty all-whole-word collection follows the table above. Invalid
records fail validation rather than reducing the denominator.

No new success threshold or λ-selection objective is introduced. New-version
scores must carry the evaluator ID and must not be substituted into V1's gates.

## 5. Archived-prediction audit

Allowed corpus-related inputs are the frozen active 162-item development gold,
stored Phase-C aggregates/selection record, the failure diagnostic, and the stored
Unigram oracle report. Implementation and specification hashes are provenance
inputs. No tokenizer models, corpus text, morphology holdout, LM test, LM BPC,
training, n-best generation, or new oracle selection are required.

Audit only paths actually persisted for each item. The stored Unigram top-1,
legacy-F1-selected path, and legacy-compatibility-selected path may be evaluated
as fixed paths. The latter two must not be called new-version oracle ceilings:
they are not reselected under this specification.

If only an aggregate exists for a system (for example BPE), report new-version
measurements as unavailable; do not infer them from aggregate values or encode
the words again. An archived certificate of identical StatBound/Unigram paths may
be reported as an equality fact, clearly distinguished from independent rescoring.

Show original recorded metrics, an internal-boundary diagnostic retaining the
legacy missing-value convention, and the new fixed-denominator metrics. This
separates normalization effects from denominator-policy effects. Keep a per-item
change log and hash every input before and after the audit. Original results,
source annotations, frozen policy files, and historical self-review measurements
must remain byte-for-byte unchanged.
