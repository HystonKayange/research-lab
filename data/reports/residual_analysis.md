# Residual corpus analysis

**Generated:** 2026-08-04T03:55:23.929617Z
**Tool:** analyze_residual_corpus v1.0.0
**Config version:** 1.0.0
**Primary subtraction mode:** `whitespace_normalized`

> **No raw files were modified.** This analysis only reads `data/raw/` and writes under `data/metadata/`, `data/reports/`, and optionally `data/interim/`.

> **Residual candidates are not approved training data.** They are uncleaned, unlicensed (unverified), and generated only for review.

## 1. Executive summary

`existing_corpus` has **50752** lines. Under **whitespace_normalized** subtraction against Bible and Wikipedia, **0** lines (**0.0%** of total; **0.0%** of non-blank) are classified as `unique_candidate`.

Attributed to Bible and/or Wikipedia: **50546** lines. Blank: **206**.

Category counts (primary mode):

| category | count |
|----------|------:|
| `duplicate_of_bible` | 30864 |
| `duplicate_of_wikipedia` | 19682 |
| `duplicate_of_both` | 0 |
| `unique_candidate` | 0 |
| `blank` | 206 |
| `unresolved` | 0 |

Residual quality (unique candidates): 0 characters; ~0 word tokens; Chichewa-signal 0; EN/DE/mixed 0/0/0.

**Analytical recommendation (not a training decision):** `discard residual` — No unique candidate lines remain after subtraction; residual is empty.

## 2. Decomposition methodology

1. Load Bible, Wikipedia, and existing_corpus as UTF-8 (strict).
2. Build in-memory key sets for Bible and Wikipedia (non-blank lines only).
3. For each existing_corpus line (preserving original 1-based line numbers):
   - `blank` if empty/whitespace-only
   - `duplicate_of_both` if key ∈ Bible ∩ Wikipedia
   - `duplicate_of_bible` if key ∈ Bible only
   - `duplicate_of_wikipedia` if key ∈ Wikipedia only
   - `unique_candidate` otherwise
   - `unresolved` reserved (not used by current rules)
4. Comparison modes (in-memory only; no normalized corpus written):
   - `exact` — full line string equality
   - `whitespace_normalized` — trim + collapse internal whitespace
   - `casefold_whitespace_normalized` — diagnostic case-fold + whitespace
5. Primary residual decision uses `whitespace_normalized` (case-fold for residual decisions: False).
6. Residual quality uses the same transparent language-signal and boilerplate heuristics as the source audit (not authoritative LID).

## 3. Raw checksum verification

| source | pre-audit SHA-256 | post-audit SHA-256 | match |
|--------|-------------------|--------------------|:-----:|
| bible | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | yes |
| wikipedia | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | yes |
| existing_corpus | `32e65edccb4c341d45e55de3d35edc1dd8768cd6e47cfafeb22d21216c2c8932` | `32e65edccb4c341d45e55de3d35edc1dd8768cd6e47cfafeb22d21216c2c8932` | yes |

**raw_files_unchanged:** `True`

## 4. Exact subtraction results

- Mode: `exact`
- Bible keys: 30876
- Wikipedia keys: 18078
- Bible ∩ Wikipedia keys: 0
- Unique candidates: **0** (0.0% of total)
- Attributed (bible/wiki/both): 50546

| category | count |
|----------|------:|
| `duplicate_of_bible` | 30864 |
| `duplicate_of_wikipedia` | 19682 |
| `duplicate_of_both` | 0 |
| `unique_candidate` | 0 |
| `blank` | 206 |
| `unresolved` | 0 |

## 5. Whitespace-normalized subtraction results

- Mode: `whitespace_normalized`
- Bible keys: 30876
- Wikipedia keys: 17935
- Bible ∩ Wikipedia keys: 0
- Unique candidates: **0** (0.0% of total)
- Attributed (bible/wiki/both): 50546

| category | count |
|----------|------:|
| `duplicate_of_bible` | 30864 |
| `duplicate_of_wikipedia` | 19682 |
| `duplicate_of_both` | 0 |
| `unique_candidate` | 0 |
| `blank` | 206 |
| `unresolved` | 0 |

## 6. Case-fold diagnostic results

> Diagnostic only. Not used as the default residual decision unless `use_casefold_for_residual` is true.

- Mode: `casefold_whitespace_normalized`
- Bible keys: 30864
- Wikipedia keys: 17921
- Bible ∩ Wikipedia keys: 0
- Unique candidates: **0** (0.0% of total)
- Attributed (bible/wiki/both): 50546

| category | count |
|----------|------:|
| `duplicate_of_bible` | 30864 |
| `duplicate_of_wikipedia` | 19682 |
| `duplicate_of_both` | 0 |
| `unique_candidate` | 0 |
| `blank` | 206 |
| `unresolved` | 0 |

## 7. Residual size and percentage

Primary residual (`whitespace_normalized`): **0** lines; **0** characters; **~0** estimated word tokens.

Percentage of existing_corpus remaining as unique candidates: **0.0%** (of non-blank: **0.0%**).

Line length: min=None, median=None, mean=None, max=None; percentiles={'p50': None, 'p90': None, 'p95': None, 'p99': None}
Very short (<20): 0; very long (>500): 0
URL lines: 0; digit-only: 0; unusual-unicode lines: 0
Chichewa-relevant char counts: {'ŵ': 0, 'Ŵ': 0}

## 8. Residual language-signal distribution

> These are **heuristic signals**, not authoritative language labels.

| category | count | % |
|----------|------:|--:|
| `chichewa_signal` | 0 | 0.0 |
| `english_signal` | 0 | 0.0 |
| `german_signal` | 0 | 0.0 |
| `mixed_signal` | 0 | 0.0 |
| `insufficient_signal` | 0 | 0.0 |

## 9. Boilerplate and contamination findings

Lines matching any configured boilerplate pattern: **0**

| pattern | matching lines | occurrences |
|---------|---------------:|------------:|

## 10. Within-residual duplication

- Lines appearing more than once (exact): 0 (0.0%)
- Unique exact residual lines: 0
- Unique ws-normalized residual lines: 0

## 11. Representative review samples

Full sample set: `data/reports/residual_samples.jsonl` (0 records).

## 12. Evidence-based recommendation

**Option:** `discard residual`

**Rationale:** No unique candidate lines remain after subtraction; residual is empty.

**Supporting metrics:** `{"unique_candidate_lines": 0, "unique_percentage_of_total": 0.0, "chichewa_signal_rate": 0.0, "foreign_signal_rate": 0.0, "boilerplate_rate": 0.0, "url_lines": 0, "very_short_lines": 0}`

**Training eligibility:** not decided — residual is not approved training data

This recommendation is analytical only. Licensing, provenance, and native-speaker review remain required before any training use.

Allowed options considered:
- `discard residual` ← selected
- `preserve for manual review` 
- `clean as a separate source` 

## 13. Limitations

- Exact/normalized line equality misses paraphrase and near-duplicates.
- Language-signal categories are heuristics, not language identification.
- Term lists are provisional and require native-speaker review.
- No licensing or training-eligibility decision is made.
- Paragraph- or document-level attribution is not modeled.
- Case-fold mode is diagnostic unless use_casefold_for_residual is true.
- Residual candidate files under data/interim/ are not training corpora.

## 14. Raw modification statement

**No raw files were modified.** Pre- and post-analysis SHA-256 checksums match for Bible, Wikipedia, and existing_corpus.

## 15. Training-data statement

**Residual candidates are not approved training data.** Any optional file under `data/interim/` is uncleaned, unlicensed (license not verified), and generated only for human review. Do not train tokenizers or models on it.

Candidate review file (if written): `data/interim/existing_corpus/residual_candidates.txt`

