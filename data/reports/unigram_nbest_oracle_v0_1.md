# Unigram n-best candidate-set oracle v0.1

Analysis only. Gold scores a frozen Unigram n-best=16 candidate set.
This is not a tokenizer, not V2, and not a hyperparameter search.

## Scope and locks

- Active development items: **162**
- Active benchmark SHA-256: `73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67`
- SHA verified: **True**
- n-best size: **16**
- Morphology holdout accessed: **False**
- LM test accessed: **False**
- LM BPC accessed: **False**
- Validation/train text opened: **False**
- λ/α selected: **False**

## Decision (pre-declared rule)

**`do_not_calibrate_wrong_signal`**

oracle room exists (ΔF1 0.2362) but only 41/115 (35.7%) of better-F1 items have Δcompat > 0.

This decision chooses a *family*, not α. Gold was not used as a training signal.

## Headline metrics

| system | macro P | macro R | macro F1 | exact | micro P | micro R | micro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unigram top-1 | 0.8431 | 0.4502 | 0.5551 | 0.0802 | 0.7548 | 0.4029 | 0.5253 |
| F1 oracle | 0.8315 | 0.8107 | 0.7913 | 0.1358 | 0.8047 | 0.7669 | 0.7853 |
| Compat oracle | 0.5457 | 0.5959 | 0.5169 | 0.0247 | 0.4933 | 0.5256 | 0.5089 |

- Official Unigram development F1 (Phase C): **0.5551**
- Recomputed Unigram F1: **0.5551**
- Match to Phase C Unigram F1: **True**

## Oracle gain over Unigram

- Macro ΔF1: **0.2362**  (SC4 needs +0.03)
- Macro ΔP: -0.0116
- Macro ΔR: 0.3605
- Δ exact rate: 0.0556  (22 vs 13 items)
- Micro ΔF1: 0.2600

## Availability

- Strictly higher-F1 candidate exists: **115/162 (70.99%)**
- Exact gold in n-best: **22/162 (13.58%)**
- Gold in n-best but Unigram is not gold: **9/162 (5.56%)**
- Unigram already a best-F1 candidate: **35/162 (21.60%)**
- F1 oracle ≠ Unigram top-1: **125/162 (77.16%)**
- Unigram already exact gold: **13/162 (8.02%)**

## Item-level F1 improvement magnitudes

Computed only where both Unigram and oracle official item F1 are defined.

- n defined ΔF1 items: **150**
- mean / median / max ΔF1: **0.2389** / 0.2843 / 0.6667
- P10 / P90: 0.0000 / 0.4571
- items with ΔF1 ≥ 0.10: **114/150 (76.00%)**
- items with ΔF1 ≥ 0.25: **82/150 (54.67%)**

## Oracle choice rank distribution

| Unigram rank of F1-oracle choice | n | % |
|---:|---:|---:|
| 1 | 37 | 22.84% |
| 2 | 38 | 23.46% |
| 3 | 24 | 14.81% |
| 4 | 11 | 6.79% |
| 5 | 12 | 7.41% |
| 6 | 8 | 4.94% |
| 7 | 5 | 3.09% |
| 8 | 1 | 0.62% |
| 9 | 6 | 3.70% |
| 10 | 3 | 1.85% |
| 11 | 2 | 1.23% |
| 12 | 3 | 1.85% |
| 13 | 3 | 1.85% |
| 14 | 3 | 1.85% |
| 15 | 1 | 0.62% |
| 16 | 5 | 3.09% |

- Median oracle rank among changed items: **4.0**

## Ceiling if only shallow n-best ranks may be used

| max Unigram rank | oracle macro F1 | ΔF1 vs Unigram | exact |
|---:|---:|---:|---:|
| 2 | 0.6631 | 0.1080 | 0.0988 |
| 4 | 0.7371 | 0.1820 | 0.1111 |
| 8 | 0.7705 | 0.2154 | 0.1235 |
| 16 | 0.7913 | 0.2362 | 0.1358 |

## Compatibility alignment

This is the measurement V1 could not make, because it never left top-1.

- Among items with a strictly better-F1 neighbour:
  - Δcompat > 0: **41/115 (35.65%)**
  - Δcompat = 0: **73/115 (63.48%)**
  - Δcompat < 0: **1/115 (0.87%)**
- Max-compat candidate equals max-F1 candidate: **19/162 (11.73%)**
- Max-compat has higher official F1 than Unigram: **43/162 (26.54%)**
- Max-compat has worse official F1 than Unigram: **57/162 (35.19%)**
- Compat-oracle macro F1: **0.5169** (Δ -0.0382)
- Compat-oracle exact: **0.0247**

Among the better-F1 items with Δcompat = 0:
- all disputed boundary positions have V1 strength 0: **73/73 (100.00%)**
- disputed positions scored / total disputed: **0/112**
- entire word has no positive V1 strengths: **27/73 (36.99%)**

### Within-n-best correlation of compat vs official F1

- Items with a defined Spearman: **112**
- Mean / median item Spearman: **-0.0346** / -0.1391
- Pooled Pearson / Spearman over all defined (compat, F1) pairs: **-0.0194** / **-0.0150** (n=2512)

## Stratification (F1-oracle ΔF1 vs Unigram, defined items only)

### source

| source | n | Unigram F1 | oracle F1 | ΔF1 | better-F1 exists | better and Δcompat>0 |
|---|---:|---:|---:|---:|---:|---:|
| bible | 120 | 0.5437 | 0.7922 | 0.2485 | 90 | 37 |
| wikipedia | 42 | 0.5863 | 0.7887 | 0.2023 | 25 | 4 |

### gold piece count

| gold pieces | n | Unigram F1 | oracle F1 | ΔF1 | better-F1 exists |
|---:|---:|---:|---:|---:|---:|
| 1 | 2 | — | — | — | 0 |
| 2 | 25 | 0.6426 | 0.7427 | 0.1001 | 3 |
| 3 | 26 | 0.7192 | 0.8205 | 0.1013 | 14 |
| 4 | 50 | 0.5297 | 0.7851 | 0.2554 | 42 |
| 5 | 38 | 0.4620 | 0.8011 | 0.3390 | 36 |
| 6 | 16 | 0.5147 | 0.8215 | 0.3068 | 15 |
| 7 | 5 | 0.4476 | 0.7733 | 0.3257 | 5 |

## Largest oracle F1 gains (development examples)

| item | word | Unigram | oracle | ΔF1 | Unigram rank | Δcompat |
|---|---|---|---|---:|---:|---:|
| `morph_dev_0021` | Matimu | `M+atimu` | `Ma+ti+mu` | 0.6667 | 2 | 0.6917 |
| `morph_dev_0060` | Nena | `Ne+na` | `N+en+a` | 0.6667 | 3 | -0.4709 |
| `morph_dev_0116` | wochenjera | `w+ochenjera` | `wo+chenje+ra` | 0.6667 | 2 | 0.2222 |
| `morph_dev_0035` | sadzalowamo | `sadzalowa+mo` | `s+a+dza+lowa+mo` | 0.5556 | 13 | 0.2000 |
| `morph_dev_0036` | silinakule | `silina+ku+le` | `si+li+na+ku+l+e` | 0.5556 | 16 | 0.0000 |
| `morph_dev_0122` | Tikukulemberani | `Ti+kukulemberani` | `Ti+ku+ku+lembera+ni` | 0.5556 | 5 | 0.1881 |
| `morph_dev_0112` | anakuchitirani | `ana+kuchitirani` | `a+na+ku+chitira+ni` | 0.5143 | 14 | 0.1109 |
| `morph_dev_0054` | adapita | `ada+pita` | `a+da+pit+a` | 0.5000 | 10 | 0.0000 |
| `morph_dev_0126` | zosafunika | `zosa+funika` | `zo+sa+funik+a` | 0.5000 | 7 | 0.0000 |
| `morph_dev_0006` | azigonekedwa | `azi+gone+ke+dwa` | `a+zi+gone+k+edwa` | 0.4643 | 4 | 0.0000 |
| `morph_dev_0001` | Analigawa | `Anali+gawa` | `A+na+li+gawa` | 0.4571 | 5 | 0.0000 |
| `morph_dev_0029` | silingathe | `sili+ngathe` | `si+li+nga+the` | 0.4571 | 5 | 0.1974 |

## Better-F1 items where compat does **not** agree (Δcompat ≤ 0)

| item | word | Unigram | better-F1 candidate | ΔF1 | Δcompat |
|---|---|---|---|---:|---:|
| `morph_dev_0060` | Nena | `Ne+na` | `N+en+a` | 0.6667 | -0.4709 |
| `morph_dev_0036` | silinakule | `silina+ku+le` | `si+li+na+ku+l+e` | 0.5556 | 0.0000 |
| `morph_dev_0054` | adapita | `ada+pita` | `a+da+pit+a` | 0.5000 | 0.0000 |
| `morph_dev_0126` | zosafunika | `zosa+funika` | `zo+sa+funik+a` | 0.5000 | 0.0000 |
| `morph_dev_0006` | azigonekedwa | `azi+gone+ke+dwa` | `a+zi+gone+k+edwa` | 0.4643 | 0.0000 |
| `morph_dev_0001` | Analigawa | `Anali+gawa` | `A+na+li+gawa` | 0.4571 | 0.0000 |
| `morph_dev_0037` | sanakonde | `sana+konde` | `s+a+na+konde` | 0.4571 | 0.0000 |
| `morph_dev_0039` | mudzamumvera | `mudza+mumvera` | `mu+dza+mu+mvera` | 0.4571 | 0.0000 |
| `morph_dev_0045` | mudzakhalako | `mudzakhala+ko` | `mu+dza+khala+ko` | 0.4571 | 0.0000 |
| `morph_dev_0099` | adzatitulutse | `adzati+tulutse` | `a+dza+ti+tulutse` | 0.4571 | 0.0000 |
| `morph_dev_0115` | nakamanganso | `naka+manganso` | `na+ka+manga+nso` | 0.4571 | 0.0000 |
| `morph_dev_0119` | anawapachika | `anawa+pachika` | `a+na+wa+pachika` | 0.4571 | 0.0000 |

## Integrity

- Gold reconstruction failures: **0**
- Candidate reconstruction failures: **0**
- Duplicate item IDs: **0**
- Candidate-set size min/median/max: 5 / 16.0 / 16
- Git HEAD: `fa978afb31558093045adef1c152ca1f670f2afd`
- Generated at: 2026-08-18T01:54:50.706520Z

## How this may and may not be used

Permitted: decide whether RelBound-Unigram V2, a different auxiliary score, or abandoning this generator is the next family.

Prohibited: using oracle choices, ranks, or ΔF1 to set α/λ, retrain Unigram, update boundary statistics, or filter vocabulary.

V1 remains a completed negative experiment. This file does not change λ*.

