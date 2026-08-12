# Cleaning policy validation — cleaning_v2

**Generated:** 2026-08-04T08:19:09.211504Z
**Config:** `configs/data/cleaning_v2.json`
**Validation records:** 367 (frozen labels)

## Metrics

| metric | value | target | met? |
|--------|------:|--------|:----:|
| removal_precision | 0.964602 | ≥ 0.90 | yes |
| false_removal_rate | 0.035398 | ≤ 0.10 | yes |
| useful_text_retention | 0.979275 | ≥ 0.90 | yes |
| noise_removal_recall | 0.626437 | — | — |
| kept_noise_rate (human kept-decision subset) | 0.1375 | — | — |
| foreign_leakage (human kept-decision) | 0.05 | — | — |

## Confusion matrix (human keep vs policy remove)

|  | policy remove | policy keep |
|--|--------------:|------------:|
| human remove (noise) | 109 (TP) | 65 (FN) |
| human keep (useful) | 4 (FP) | 189 (TN) |

## v1 vs v2 comparison

| metric | v1 | v2 |
|--------|---:|---:|
| removal_precision | 0.567944 | 0.964602 |
| false_removal_rate | 0.432056 | 0.035398 |
| useful retention / useful-text rate | 0.8625 | 0.979275 |

## False removals by rule (v2)

- `drop_high_confidence_foreign`: 3
- `drop_long_table_dump`: 1

## Example false positives (useful text removed)

- L19800 rule=`drop_high_confidence_foreign` [useful_mixed_chichewa]: Adawonekera m'mafilimu a The Little Engine That Could (2011), Scary or Die (2012), Namwino 3D (2013), Shuga (2013), The Monkey's Paw (2013), Walk.
- L10357 rule=`drop_long_table_dump` [useful_mixed_chichewa]: +Districts of MalawiRegionNamePopulation Total Area (km2)CapitalIndexCentralDedza830,5123,754Dedza1Dowa772,5693,077Dowa2Kasungu842,9538,017Kasungu3Lilongwe2,626
- L11757 rule=`drop_high_confidence_foreign` [useful_mixed_chichewa]: Wosankhidwa kukhala PurezidentiWothamanga mnzakePhwando 1.Edgar LunguNkandu LuoPatriotic Front2.Enock TongaBright Chomba3rd Liberation Movement3.Sean TemboHenry
- L1355 rule=`drop_high_confidence_foreign` [useful_mixed_chichewa]: He was the third son of John Johnson, a lawyer of Ryde, and Mary Percival, his second wife, ..." - Baibulo, Buku Lopatulika ndilo Mau a Mulungu, anatanthauzirid

## Example false negatives (noise kept)

- L2581 [duplicate]: Kuchuluka: 3,372 ta’ata/km²
- L9572 [boilerplate_or_noise]: World Health Organization.
- L9704 [boilerplate_or_noise]: Weekly epidemiological record.
- L9741 [boilerplate_or_noise]: Retrieved 22 April 2014.
- L10714 [boilerplate_or_noise]: † Adamwalira muofesi
- L16064 [duplicate]: Tsatanetsatane wamasewera
- L155 [foreign_language]: All one, Strong and Free.Vesi lachiwiriAfrica is our own motherland,
- L653 [foreign_language]: Hills and valleys, soil so rich and rare

## Promotion decision

Targets met on frozen set — promotion to `data/processed/` may be considered after license review.

Human labels were not modified.

