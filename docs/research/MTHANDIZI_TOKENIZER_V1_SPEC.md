# MthandiziTokenizer Prototype V1 — Executable Specification

**ID:** `statbound_unigram_v1`  
**Status:** `closed_negative` (algorithm remains the frozen V1 definition; do not edit after results)  
**Decision log:** `D-0010` (spec), `D-0013`–`D-0015` (evaluation and close)  
**Config:** `configs/tokenizers/statbound_unigram_v1.json`  
**Novelty claim:** provisional (composition; not a new primitive)  
**Scientific outcome:** negative on SC4 and SC1. Do not change this specification to chase those results.

Two independent implementations following this document and the frozen config must produce **identical** encodings on the same train corpus, base model, and hyperparameters (within floating-point tolerances documented below).

---

## 1. Scope and non-goals

### In scope (V1)
- Corpus-only statistical boundary discovery (TRAIN only)
- Unigram n-best re-ranking with a single bias strength \(\lambda\)
- Deterministic encode/decode with exact reconstruction of surface text
- Implementation unit/sanity tests

### Explicitly out of scope (this phase)
- Morphology Boundary F1 / active-195 scientific eval
- LM BPC/BPB training or evaluation
- Morphology holdout access
- LM test access
- Morphology-constrained BPE
- Supervised morph labels for learning

---

## 2. Inputs

| Input | Path / value |
|-------|----------------|
| Train corpus | `data/splits/chichewa_corpus_v0.1/train/combined.txt` |
| Base Unigram model | `data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model` |
| Normalization | identity (same as Unigram-8000 baseline) |
| Config | `configs/tokenizers/statbound_unigram_v1.json` |

**Forbidden inputs for boundary learning / training code paths:**

- any path containing `/validation/`, `/test/`, `/locked/`
- morphology benchmark annotations / holdout
- annotator files, self-review, AI annotator bundles

---

## 3. A — Unigram foundation

1. Load the frozen SentencePiece **Unigram** model (vocab_size = 8000).
2. Do **not** retrain SentencePiece for V1 boundary re-ranking (base lexical model is fixed).
3. Encoding of a **word** \(w\) (whitespace-delimited token, surface form as in text after identity normalization) uses SentencePiece’s word encoding with the model’s configured dummy prefix behavior (baseline: `add_dummy_prefix=true`).
4. **Unigram score** of a piece sequence \(S = (p_1,\ldots,p_k)\):

\[
\mathrm{unigram\_score}(S \mid w) = \sum_{j=1}^{k} \mathrm{score}(p_j)
\]

where \(\mathrm{score}(p_j)\) is SentencePiece `get_score(piece_to_id(p_j))` (piece log-probability under the trained Unigram model).

Higher (less negative) is better.

5. **Default Unigram segmentation** \(\mathrm{SP}(w)\) is `encode_as_pieces(w)` from the same model.

---

## 4. B — Corpus-only statistical boundary discovery

### 4.1 Token extraction from TRAIN

1. Read train file as UTF-8.
2. Split into whitespace-separated tokens (Python `str.split()`).
3. For boundary statistics, keep tokens \(w\) such that:
   - \(\mathrm{len}(w) \ge 2\)
   - \(w\) contains at least one Unicode letter (`str.isalpha` on some character)
4. Build:
   - \(f(w)\): type frequency (count of token occurrences)
   - type lexicon \(\mathcal{T} = \{w : f(w) \ge 1\}\)

### 4.2 Affix/context limits

Let `max_affix_context_length` \(= L_{\max} = 6\) (frozen).  
For word \(w\) with length \(n\), candidate internal cut positions:

\[
i \in \{1,2,\ldots,n-1\} \quad\text{with}\quad i \le L_{\max} \ \text{or}\ n-i \le L_{\max}
\]

(i.e., only cuts where the shorter side is at most \(L_{\max}\), **or** equivalently: consider all \(i\), but only score cuts with \(\min(i, n-i) \le L_{\max}\)).

**V1 definition (exact):** score a cut at \(i\) only if \(\min(i, n-i) \le L_{\max}\).

Left piece \(a = w[:i]\), right piece \(b = w[i:]\).

### 4.3 Corpus statistics

Over the type lexicon \(\mathcal{T}\):

\[
\begin{align*}
\mathrm{pref\_types}(a) &= |\{ t \in \mathcal{T} : t \text{ starts with } a \}| \\
\mathrm{suf\_types}(b) &= |\{ t \in \mathcal{T} : t \text{ ends with } b \}| \\
\mathrm{branch\_pref}(a) &= |\{ c : \exists t \in \mathcal{T},\ t = a + c + \ldots,\ |t| > |a| \}| \\
\mathrm{branch\_suf}(b) &= |\{ c : \exists t \in \mathcal{T},\ t = \ldots + c + b,\ |t| > |b| \}|
\end{align*}
\]

where \(c\) is a single Unicode character.

### 4.4 Support and productivity gates

Frozen thresholds:

- `min_type_support` \(S_{\min} = 5\): require \(\mathrm{pref\_types}(a) \ge S_{\min}\) **and** \(\mathrm{suf\_types}(b) \ge S_{\min}\)
- `min_productivity` \(P_{\min} = 3\): require \(\mathrm{branch\_pref}(a) \ge P_{\min}\) **or** \(\mathrm{branch\_suf}(b) \ge P_{\min}\)

If gates fail, raw score \(r(w,i) = 0\).

### 4.5 Length-one affix downweight

Let `min_affix_len_for_full_weight` \(= 2\), `length_one_affix_weight` \(\omega_1 = 0.15\).

\[
\omega(a,b) =
\begin{cases}
\omega_1 & \text{if } |a|=1 \text{ or } |b|=1 \\
1 & \text{otherwise}
\end{cases}
\]

This prevents mechanical preference for every one-character cut.

### 4.6 Raw cut score

\[
\begin{align*}
r(w,i) &= \omega(a,b) \cdot \Big(
  \log(1 + \mathrm{pref\_types}(a))
  + \log(1 + \mathrm{suf\_types}(b))
  + \log(1 + \mathrm{branch\_pref}(a))
  + \log(1 + \mathrm{branch\_suf}(b))
\Big)
\end{align*}
\]

with natural logarithm. If gates fail, \(r(w,i)=0\).

### 4.7 Per-word normalization to \([0,1]\)

Let \(R(w) = \max_{i} r(w,i)\). Boundary strength:

\[
s(w,i) =
\begin{cases}
0 & \text{if } R(w) = 0 \\
r(w,i) / R(w) & \text{otherwise}
\end{cases}
\]

Thus \(s(w,i) \in [0,1]\).

### 4.8 Artifact

Write JSON:

```json
{
  "formula_id": "statbound_v1_branch_productivity_log",
  "config_hash": "...",
  "train_path": "...",
  "n_types": ...,
  "n_tokens": ...,
  "words": {
    "<word>": {
      "freq": <int>,
      "strengths": {"1": 0.0, "2": 0.73, ...}
    }
  }
}
```

Only internal positions with \(s>0\) need be stored; missing \(i\) means \(s=0\).

**Vocabulary:** boundary stats are **not** vocabulary pieces.

---

## 5. C — Unigram segmentation re-ranking

### 5.1 Candidates

For word \(w\):

1. Query SentencePiece n-best piece sequences:

\[
\mathcal{C}(w) = \mathrm{NBestEncodeAsPieces}(w,\ N),\quad N=16
\]

2. If \(\mathrm{SP}(w) \notin \mathcal{C}(w)\), insert \(\mathrm{SP}(w)\) (must hold for \(\lambda=0\) equivalence).

3. Drop any candidate whose concatenation of pieces (after removing the SentencePiece whitespace marker `▁` for surface check) does not reconstruct \(w\).  
   **Exact surface check V1:**
   - Let \(\mathrm{surface}(S) = \mathrm{concat}(p.\mathrm{replace}(``▁", ``") \text{ for } p \in S)\).
   - Keep \(S\) iff \(\mathrm{surface}(S) = w\).

### 5.2 Boundary positions of a segmentation

Map pieces to character offsets in \(w\):

- Process pieces left to right.
- For each piece, strip a leading `▁` if present (does not consume a character of \(w\)).
- Remaining characters must match the next characters of \(w\).
- After each piece except the last, record boundary offset \(i =\) number of characters of \(w\) consumed so far.
- \(\mathrm{Bound}(S) \subseteq \{1,\ldots,n-1\}\).

If mapping fails, reject candidate.

### 5.3 Boundary compatibility

\[
\mathrm{compat}(S,w) =
\frac{1}{n-1}
\left(
  \sum_{i \in \mathrm{Bound}(S)} s(w,i)
  - \sum_{i \in \{1,\ldots,n-1\}\setminus \mathrm{Bound}(S)} s(w,i)
\right)
\quad (n=\mathrm{len}(w)\ge 2)
\]

For \(n < 2\), \(\mathrm{compat}=0\).

Properties:
- Rewards cuts at high \(s\)
- Penalizes missing cuts where \(s\) is high (crossing strong evidence)
- Does not reward arbitrary fragmentation when \(s\approx 0\) (compat \(\approx 0\))

### 5.4 Combined score

\[
\mathrm{score}(S \mid w) = \mathrm{unigram\_score}(S \mid w) + \lambda \cdot \mathrm{compat}(S,w)
\]

### 5.5 Selection and tie-breaking

Select \(S^\star = \arg\max_{S \in \mathcal{C}(w)} \mathrm{score}(S\mid w)\) with ties broken by, in order:

1. Higher `unigram_score`
2. Higher `compat`
3. Fewer pieces
4. Lexicographically smaller `"\x1f".join(pieces)` (ASCII unit separator)

### 5.6 Full-line encoding

1. Split line on whitespace **preserving** the sequence of tokens (use `line.split()` — collapses whitespace).  
   **V1 whitespace policy for scientific encode of pre-tokenized lines:** join encoded tokens with SentencePiece’s normal behavior for full strings.

**Exact V1 text encode (recommended, matches baseline train pipelines):**

- For a full string `text`, call base SP `encode_as_pieces(text)` to obtain the **default** segmentation lattice context, **but** re-rank **per whitespace word** independently:
  1. Tokenize `text` with `text.split()` into words \(w_1,\ldots,w_m\).
  2. For each \(w_t\), compute \(S_t^\star\) as above (word-level encode, with dummy prefix as SP does for a single-word encode).
  3. Emit pieces as the concatenation \(S_1^\star + S_2^\star + \cdots + S_m^\star\).

**Decode / reconstruction of a line:**  
`decode_pieces` using SentencePiece `decode_pieces` on the full piece list must recover a string that, after `split()` and re-join with single spaces, matches `" ".join(text.split())` (whitespace-normalized reconstruction).

**Exact reconstruction requirement (V1 tests):** for each whitespace token \(w\), \(\mathrm{surface}(S^\star(w)) = w\).

---

## 6. D — \(\lambda = 0\) control

When \(\lambda = 0\):

\[
\mathrm{score}(S\mid w) = \mathrm{unigram\_score}(S\mid w)
\]

**Requirement:** for all tested words, selected pieces equal `SentencePiece.encode_as_pieces(w)`.

**Proof obligation in tests:** automated suite on a fixed list of train-sampled and synthetic words.

If SentencePiece n-best scoring ever disagrees with `encode_as_pieces`, document and fail hard (do not silently redefine baseline).

---

## 7. E — Residual / vocabulary accounting

| Category | Count (V1) |
|----------|------------|
| Lexical / subword / char pieces from base Unigram model | 8000 |
| Extra pieces added by StatBound | **0** |
| Boundary stats entries | side table only (not vocab) |
| **Total effective vocabulary** | **8000** (same model file) |

Residual/OOV handling is exactly that of the base SentencePiece Unigram model (UNK / character pieces already inside the 8000).  
V1 **must not** enlarge the model vocabulary.

---

## 8. F — Training vs inference

| Phase | Boundary stats | \(\lambda\) | Model |
|-------|----------------|-------------|-------|
| Learn stats | Fit on TRAIN only | n/a | write JSON |
| Encode train/val/test/morph | **Frozen** stats file | frozen config | same SP model |

Boundary statistics must not be updated from validation, test, or morphology files.

---

## 9. Hyperparameter search space (frozen)

| Parameter | Frozen values / space |
|-----------|------------------------|
| \(L_{\max}\) | 6 |
| \(S_{\min}\) | 5 |
| \(P_{\min}\) | 3 |
| \(N\) n-best | 16 |
| \(\lambda\) **search space** | `{0.0, 0.25, 0.5, 1.0, 2.0}` |
| Default \(\lambda\) for packaging | 0.5 (not chosen from Mthandizi eval results) |
| \(\omega_1\) | 0.15 |

**Mandatory control:** \(\lambda=0.0\).  
**Forbidden:** expanding this set after seeing Mthandizi scientific results.

---

## 10. Floating-point tolerance

- Strengths stored with 10 decimal places in JSON.
- Score comparisons use exact float arithmetic of Python 3; ties use explicit tie-break keys (not float epsilon).
- Cross-implementation: absolute difference \(< 10^{-9}\) on compat scores for equal inputs is acceptable; piece sequences must match exactly.

---

## 11. Leakage guard

Any path used for learning boundary stats must pass `assert_train_only_path(path)`:

- must contain `/train/`
- must not match forbidden substrings in config

Morphology annotation paths raise `LeakageError` at runtime.

---

## 12. Implementation map

```
src/tokenizers/statbound/
  __init__.py
  leakage.py
  boundary_stats.py
  unigram_adapter.py
  reranker.py
  tokenizer.py
scripts/tokenizers/
  statbound_unigram_cli.py
tests/
  test_statbound_unigram_v1.py
```

---

## 13. Acceptance (implementation phase only)

- [x] Spec frozen  
- [ ] Unit tests pass  
- [ ] \(\lambda=0\) equivalence holds  
- [ ] Exact per-word reconstruction holds  
- [ ] Effective vocab = 8000  
- [ ] Morphology labels used for learning = 0  
- [ ] Holdout accessed = false  
- [ ] LM not trained  

Scientific SC1–SC4 evaluation is **not** part of this phase.
