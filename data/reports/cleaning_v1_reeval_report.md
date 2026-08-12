# Cleaning policy validation — cleaning_v1

**Generated:** 2026-08-04T08:19:09.836275Z
**Config:** `configs/data/cleaning.json`
**Validation records:** 367 (frozen labels)

## Metrics

| metric | value | target | met? |
|--------|------:|--------|:----:|
| removal_precision | 0.567944 | ≥ 0.90 | no |
| false_removal_rate | 0.432056 | ≤ 0.10 | no |
| useful_text_retention | 0.357513 | ≥ 0.90 | no |
| noise_removal_recall | 0.936782 | — | — |
| kept_noise_rate (human kept-decision subset) | 0.1375 | — | — |
| foreign_leakage (human kept-decision) | 0.05 | — | — |

## Confusion matrix (human keep vs policy remove)

|  | policy remove | policy keep |
|--|--------------:|------------:|
| human remove (noise) | 163 (TP) | 11 (FN) |
| human keep (useful) | 124 (FP) | 69 (TN) |

## v1 vs v2 comparison

| metric | v1 | v2 |
|--------|---:|---:|
| removal_precision | 0.567944 | 0.567944 |
| false_removal_rate | 0.432056 | 0.432056 |
| useful retention / useful-text rate | 0.8625 | 0.357513 |

## False removals by rule (v2)

- `drop_mixed_signal`: 39
- `drop_min_length`: 20
- `dedupe_exact`: 19
- `drop_max_length`: 13
- `drop_url`: 12
- `drop_wikimedia`: 11
- `drop_english_signal`: 5
- `drop_mu_nkhani`: 5

## Example false positives (useful text removed)

- L2988 rule=`dedupe_exact` [valid_chichewa]: Delhi ndi boma lina la dziko la India.
- L7009 rule=`dedupe_exact` [valid_chichewa]: Zogwirizana zakunja
- L7715 rule=`dedupe_exact` [valid_chichewa]: Inabweretsedwa pa September 2, 2006 .
- L9421 rule=`dedupe_exact` [valid_chichewa]: Kenako mu 1986 panapangidwa mtundu wina wa katemera womwe ndi wabwino poyerekezera ndi woyamba uja.
- L9457 rule=`dedupe_exact` [valid_chichewa]: M'madera amene matendawa si ofala kwenikweni, matendawa amafala kwambiri chifukwa chogwiritsira ntchito mankhwala ozunguza bongo ndiponso kudzera m'kugonana.
- L9466 rule=`dedupe_exact` [valid_chichewa]: Matendawa ali m'gulu la matenda a hepataitisi omwe amayambitsidwa ndi mavailasi awa: A, B, C, D, ndi E.
- L9549 rule=`dedupe_exact` [valid_chichewa]: Nthawi zambiri zizindikiro za matendawa zimaonekera kwa milungu 8 ndipo zina mwa zizindikirozo ndi: nseru, kusanza, kutsegula m'mimba, khungu kuchita chikasu, f
- L9563 rule=`dedupe_exact` [valid_chichewa]: Zizindikiro za hepataitisi A n'zofanana ndi zizindikiro za matenda ena ambiri choncho pamafunika kuyeza magazi kuti madokotala atsimikizire ngati munthu ali ndi

## Example false negatives (noise kept)

- L5234 [boilerplate_or_noise]: Mbalameyi nthawi zambiri imakhala yokhazikika pakati pawo (ngakhale kuti amuna 8% ndi amodzi), ali ndi maubwenzi apamwamba.
- L6979 [boilerplate_or_noise]: Adventures mu Paradaiso (1961) monga Esther Holmes
- L9308 [foreign_language]: Weekly epidemiological record.
- L9356 [foreign_language]: "Community-acquired bacterial meningitis in adults".
- L10601 [boilerplate_or_noise]: 201331 Disembala 198721 Novembala 2017ZANU-PF3Phelekezela Mphoko(wobadwa 1940)201721 Novembala 201724 Novembala 2017Odziyimira pawokha4Emmerson Mnangagwa(wobadw
- L11026 [boilerplate_or_noise]: Bhutan ( Thimphu ) (AS)
- L12221 [foreign_language]: Parks and Wildlife Tasmania – Tasmanian Devil – vocalisation, movie, FAQ
- L14414 [boilerplate_or_noise]: BreakdownOphedwaNthawiUmboniCivilians2,000+ ophedwa24 February – 2 March 2022Ukrainian government331 ophedwa24 February – 3 March 2022United NationsUAF, NGU, an

## Promotion decision

**Targets not fully met.** Do **not** promote to `data/processed/` based on this evaluation alone.

Human labels were not modified.

