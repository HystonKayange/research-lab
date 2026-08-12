# Cleaning before/after report

**Generated:** 2026-08-04T08:19:08.836730Z
**Tool:** clean_sources v2.0.0
**Config version:** 2.0.0

> **Raw files were not modified.** All outputs are under `data/interim/cleaning_v2`.

> Interim cleaned text is **not** final processed training data and is **not** an approval for training. Licensing remains unresolved.

## Sources cleaned

- **bible**: removed 0 lines; kept 31099; transform events 0
- **wikipedia**: removed 2606 lines; kept 17973; transform events 3201

## bible

- Input: `data/raw/bible/bible_clean.txt`
- Input SHA-256: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- Cleaned SHA-256: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- Notes: Light-touch; unchanged policy from v1.

### Rule hit counts (removals / transforms)

| rule | count |
|------|------:|
| _(none)_ | 0 |

### Before → after quality

| metric | before | after | delta |
|--------|-------:|------:|------:|
| total_lines | 31099 | 31099 | 0 |
| non_empty_lines | 31099 | 31099 | 0 |
| blank_lines | 0 | 0 | 0 |
| character_count_estimate | 4172214 | 4172214 | 0 |
| estimated_word_token_count | 575455 | 575455 | 0 |
| unique_exact_nonempty | 30876 | 30876 | 0 |
| duplicate_line_percentage | 1.1222 | 1.1222 | 0.0 |
| very_short_lines | 21 | 21 | 0 |
| very_long_lines | 0 | 0 | 0 |
| url_containing_lines | 0 | 0 | 0 |
| digit_only_lines | 0 | 0 | 0 |
| min_line_length | 13 | 13 | 0 |
| median_line_length | 124 | 124 | 0 |
| max_line_length | 437 | 437 | 0 |

#### Language-signal distribution (heuristic)

| category | before | after | before % | after % |
|----------|-------:|------:|---------:|--------:|
| `chichewa_signal` | 25904 | 25904 | 83.2953 | 83.2953 |
| `english_signal` | 0 | 0 | 0.0 | 0.0 |
| `german_signal` | 0 | 0 | 0.0 | 0.0 |
| `mixed_signal` | 0 | 0 | 0.0 | 0.0 |
| `insufficient_signal` | 5195 | 5195 | 16.7047 | 16.7047 |

#### Boilerplate matching lines

| pattern | before | after |
|---------|-------:|------:|
| `category_prefix` | 0 | 0 |
| `in_german_meta` | 0 | 0 |
| `mu_nkhani` | 0 | 0 |
| `url_http` | 0 | 0 |
| `url_www` | 0 | 0 |
| `wikimedia` | 0 | 0 |
| `wikipedia_muzinenero` | 0 | 0 |
| `wikipedia_word` | 0 | 0 |

### Sample removals (first matches by rule)

_No lines removed._

## wikipedia

- Input: `data/raw/wikipedia/wiki_clean.txt`
- Input SHA-256: `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7`
- Cleaned SHA-256: `69aac9abb9bc79e713b3d5d769f149aaaddda9fea9225b6ef554cb2ed7a99e0b`
- Notes: v2 precision-first: protect valid/mixed Chichewa; strong evidence for delete.

### Rule hit counts (removals / transforms)

| rule | count |
|------|------:|
| `transform:strip_edges` | 3127 |
| `drop_category` | 1547 |
| `drop_high_confidence_foreign` | 238 |
| `drop_blank` | 208 |
| `drop_short_conditional` | 205 |
| `drop_wikimedia_chrome` | 168 |
| `drop_digit_only` | 111 |
| `drop_url_only` | 105 |
| `transform:strip_urls` | 74 |
| `drop_blank_after_transform` | 10 |
| `drop_long_table_dump` | 9 |
| `drop_in_german_meta` | 3 |
| `drop_mu_nkhani_nav` | 1 |
| `drop_wikipedia_muzinenero` | 1 |

### Before → after quality

| metric | before | after | delta |
|--------|-------:|------:|------:|
| total_lines | 20579 | 17973 | -2606 |
| non_empty_lines | 20371 | 17973 | -2398 |
| blank_lines | 208 | 0 | -208 |
| character_count_estimate | 1928042 | 1817397 | -110645 |
| estimated_word_token_count | 273158 | 257284 | -15874 |
| unique_exact_nonempty | 18078 | 16698 | -1380 |
| duplicate_line_percentage | 14.3046 | 9.4141 | -4.890500000000001 |
| very_short_lines | 3818 | 2884 | -934 |
| very_long_lines | 77 | 54 | -23 |
| url_containing_lines | 74 | 0 | -74 |
| digit_only_lines | 111 | 0 | -111 |
| min_line_length | 1 | 2 | 1 |
| median_line_length | 75 | 86 | 11 |
| max_line_length | 3055 | 2546 | -509 |

#### Language-signal distribution (heuristic)

| category | before | after | before % | after % |
|----------|-------:|------:|---------:|--------:|
| `chichewa_signal` | 9611 | 9546 | 47.1798 | 53.113 |
| `english_signal` | 446 | 207 | 2.1894 | 1.1517 |
| `german_signal` | 2 | 0 | 0.0098 | 0.0 |
| `mixed_signal` | 276 | 266 | 1.3549 | 1.48 |
| `insufficient_signal` | 10036 | 7954 | 49.2661 | 44.2553 |

#### Boilerplate matching lines

| pattern | before | after |
|---------|-------:|------:|
| `category_prefix` | 1547 | 0 |
| `in_german_meta` | 3 | 0 |
| `mu_nkhani` | 6 | 5 |
| `url_http` | 69 | 0 |
| `url_www` | 34 | 0 |
| `wikimedia` | 40 | 30 |
| `wikipedia_muzinenero` | 1 | 0 |
| `wikipedia_word` | 72 | 39 |

### Sample removals (first matches by rule)

- **`drop_blank`**
  - L5556: ``
  - L5558: ``
  - L5969: ``
- **`drop_blank_after_transform`**
  - L1316: `http://el.wikipedia.org/wiki/Πύλη:Κύρια`
  - L3485: `http://opstinakotorvaros.com/`
  - L3488: `http://www.distancesfrom.com/distance-from-Siprage-to-Banja-Luka-Bosna-i-Hercegovina/DistanceHistory/5243320.aspx`
- **`drop_category`**
  - L382: `Category:Nyasa zinenero`
  - L481: `Category:ziPani za ndale za ku Malaŵi`
  - L8534: `Category:Anthu amoyo`
- **`drop_digit_only`**
  - L3849: `1983`
  - L8334: `2005`
  - L8940: `3`
- **`drop_high_confidence_foreign`**
  - L1806: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
  - L5380: `The aphids will then feed on the inner parts of the plant as well as the young stems and shoots.`
  - L9791: `"Global, regional, and national age-sex specific all-cause and cause-specific mortality for 240 causes of death, 1990...`
- **`drop_in_german_meta`**
  - L13924: `(in German) In: Rathauskorrespondenz, 27 May 2009Edita Gruberova ausgezeichnet (image) In: Rathauskorrespondenz, 27 M...`
  - L13928: `Juni 2014 (in German) Musiktheaterpreis, retrieved 4 April 2015`
  - L13929: `2016: Ehrenplakette of the in Garmisch-PartenkirchenEröffnungsprogramm der Richard-Strauss-Festivals 2016 (in German)...`
- **`drop_long_table_dump`**
  - L3892: `Portrait Name Took office Left office Political party 80px Kenneth Kaunda 22 January 1964 24 October 1964 UNIP 80px R...`
  - L5894: `ChiwerengeroGuluGawoPldWDLGFGAGDMfundo1843336411235+771052839265811137+74833835223108645+41694833185105942+1759583018...`
  - L10357: `+Districts of MalawiRegionNamePopulation Total Area (km2)CapitalIndexCentralDedza830,5123,754Dedza1Dowa772,5693,077Do...`
- **`drop_mu_nkhani_nav`**
  - L2: `Mu nkhani`
- **`drop_short_conditional`**
  - L2208: `thumb 250px Paris`
  - L2229: `thumb Cairo`
  - L2452: `Link`
- **`drop_url_only`**
  - L4012: `()`
  - L4033: `() •`
  - L4051: `() •`
- **`drop_wikimedia_chrome`**
  - L3902: `thumb 319x319px Jaynagar Majilpur Municipality`
  - L13934: `thumb 346x346px Jorge Carlos de Almeida Fonseca mu 2018`
  - L16023: `thumb 397x397px`
- **`drop_wikipedia_muzinenero`**
  - L14: `Wikipedia Muzinenero Zina`

## Raw checksum verification

| source | pre | post | match |
|--------|-----|------|:-----:|
| bible | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | yes |
| wikipedia | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | yes |

**raw_files_unchanged:** `True`

## Disclaimers

- v2 is interim only; not approved training data.
- Licensing still unresolved.
- Human validation labels are frozen and must not be modified.
- Do not promote to data/processed/ without meeting target criteria.

