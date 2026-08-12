# Source audit report

**Generated:** 2026-08-04T03:35:32.782297Z
**Tool:** audit_sources v1.0.0
**Config version:** 1.0.0

> **No source content was modified.** This audit only reads files under `data/raw/` and writes reports under `data/reports/` and `data/metadata/`.

## 1. Executive summary

This report measures structural quality, orthography, provisional language-signal heuristics, boilerplate patterns, within-source duplication, and cross-source exact overlap for three local Chichewa corpus sources.

**Measured highlights (see body for detail):**

- **bible**: 31099 non-empty lines; duplicate-line rate 1.1222%; heuristic EN/DE/mixed signals 0/0/0; ŵ count=0.
- **existing_corpus**: 50546 non-empty lines; duplicate-line rate 3.935%; heuristic EN/DE/mixed signals 440/2/276; ŵ count=310.
- **wikipedia**: 20371 non-empty lines; duplicate-line rate 14.3046%; heuristic EN/DE/mixed signals 446/2/276; ŵ count=382.

**Cross-source (whitespace-normalized nonempty lines):**

- `bible` vs `existing_corpus`: shared=30864, Jaccard=0.632329, cov(A←B)=0.999611, cov(B←A)=0.632485, note=`bible_substantially_covered_by_existing_corpus`
- `bible` vs `wikipedia`: shared=0, Jaccard=0.0, cov(A←B)=0.0, cov(B←A)=0.0, note=`neither_substantially_contained`
- `existing_corpus` vs `wikipedia`: shared=17934, Jaccard=0.367508, cov(A←B)=0.367515, cov(B←A)=0.999944, note=`wikipedia_substantially_covered_by_existing_corpus`

Licensing and training eligibility remain **unresolved** for all sources. See `data/reports/training_eligibility_review.md`.

## 2. Methodology

- Read each registered source as UTF-8; compute SHA-256.
- Structural stats use newline-split lines; blank = empty/whitespace-only.
- Language signals: whole-word, case-insensitive matches against provisional Chichewa / English / German term lists from config. A language signal requires ≥ 2 hits.
- Boilerplate: configured regular expressions (navigation, Category, URLs, HTML/wiki remnants, etc.).
- Overlap: in-memory comparison keys only — exact; whitespace-collapsed; optional case-folded. Units: nonempty lines, blank-line paragraphs, token shingles (window=5).
- Sampling: deterministic `random.Random` with seed 42.
- No NFC/NFD/NFKC/NFKD rewrites; normalization only observed.

## 3. Limitations

- Heuristic language signals are **not** language identification.
- Term lists are small, provisional, and need native-speaker review.
- Exact/shingle overlap misses paraphrase and near-duplicate content.
- Filenames like `*_clean.txt` do not prove prior cleaning quality.
- No external LID, web APIs, or ML models were used.
- License/provenance cannot be inferred from text statistics.

## 4. Per-source structural statistics

### bible

- Path: `data/raw/bible/bible_clean.txt`
- Size (bytes): 4218603
- SHA-256: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- Characters: 4172215
- Total lines: 31099
- Non-empty lines: 31099
- Blank lines: 0
- Unique exact lines: 30876
- Lines appearing >1 time: 349 (1.1222%)
- Line length min/mean/median/max: 13 / 133.1591 / 124 / 437
- Percentiles: {'p50': 124.0, 'p90': 212.0, 'p95': 241.0, 'p99': 296.0}
- Very short (<20): 21; very long (>500): 0
- Digit-only lines: 0
- URL-containing lines: 0
- Control-char lines: 0
- Replacement-char (U+FFFD) lines: 0
- Paragraphs: 1; shingles: 451225 (unique 429052)

### existing_corpus

- Path: `data/raw/existing_corpus/chichewa_corpus.txt`
- Size (bytes): 6103844
- SHA-256: `32e65edccb4c341d45e55de3d35edc1dd8768cd6e47cfafeb22d21216c2c8932`
- Characters: 6047673
- Total lines: 50752
- Non-empty lines: 50546
- Blank lines: 206
- Unique exact lines: 48941
- Lines appearing >1 time: 1989 (3.935%)
- Line length min/mean/median/max: 1 / 118.6387 / 111.0 / 3055
- Percentiles: {'p50': 111.0, 'p90': 208.0, 'p95': 241.75, 'p99': 315.0}
- Very short (<20): 3648; very long (>500): 77
- Digit-only lines: 111
- URL-containing lines: 74
- Control-char lines: 0
- Replacement-char (U+FFFD) lines: 0
- Paragraphs: 90; shingles: 648788 (unique 621933)

### wikipedia

- Path: `data/raw/wikipedia/wiki_clean.txt`
- Size (bytes): 1938045
- SHA-256: `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7`
- Characters: 1928043
- Total lines: 20579
- Non-empty lines: 20371
- Blank lines: 208
- Unique exact lines: 18078
- Lines appearing >1 time: 2914 (14.3046%)
- Line length min/mean/median/max: 1 / 93.626 / 75 / 3055
- Percentiles: {'p50': 75.0, 'p90': 198.0, 'p95': 240.0, 'p99': 355.2999999999993}
- Very short (<20): 3818; very long (>500): 77
- Digit-only lines: 111
- URL-containing lines: 74
- Control-char lines: 0
- Replacement-char (U+FFFD) lines: 0
- Paragraphs: 92; shingles: 201679 (unique 192965)

## 5. Language-signal findings

> Categories are **heuristic signals**, not definitive language labels. Collisions (e.g. short function words) can produce false positives.

### bible

Non-empty lines scored: 31099

| category | count | % |
|----------|------:|--:|
| chichewa_signal | 25904 | 83.2953 |
| english_signal | 0 | 0.0 |
| german_signal | 0 | 0.0 |
| mixed_signal | 0 | 0.0 |
| insufficient_signal | 5195 | 16.7047 |

No english/german/mixed-signal examples retained under sampling limits.

### existing_corpus

Non-empty lines scored: 50546

| category | count | % |
|----------|------:|--:|
| chichewa_signal | 35276 | 69.7899 |
| english_signal | 440 | 0.8705 |
| german_signal | 2 | 0.004 |
| mixed_signal | 276 | 0.546 |
| insufficient_signal | 14552 | 28.7896 |

Suspicious examples (heuristic; truncated):

- L48577 [german_signal] hits={'chichewa': 0, 'english': 0, 'german': 2}: `Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.`
- L50505 [german_signal] hits={'chichewa': 0, 'english': 0, 'german': 2}: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
- L17329 [english_signal] hits={'chichewa': 0, 'english': 59, 'german': 0}: `Country Head of stateMembers of the upper house Members of the lower house 5 3, 4 and 5 5 5 4 5 6 5 5 (President of F...`
- L34269 [english_signal] hits={'chichewa': 0, 'english': 33, 'german': 0}: `+Wikimania conferencesLogoConferenceDatePlaceAttendanceArchive of presentationsalt Logo of the Wikimania 2005 confere...`
- L16031 [english_signal] hits={'chichewa': 0, 'english': 26, 'german': 0}: `Dissatisfied 56 42 43 Angry 72 27 30 Satisfied 18 81 19 Enthusiastic 11 89 6 America's best days are In the future 40...`

### wikipedia

Non-empty lines scored: 20371

| category | count | % |
|----------|------:|--:|
| chichewa_signal | 9611 | 47.1798 |
| english_signal | 446 | 2.1894 |
| german_signal | 2 | 0.0098 |
| mixed_signal | 276 | 1.3549 |
| insufficient_signal | 10036 | 49.2661 |

Suspicious examples (heuristic; truncated):

- L1806 [german_signal] hits={'chichewa': 0, 'english': 0, 'german': 2}: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
- L18984 [german_signal] hits={'chichewa': 0, 'english': 0, 'german': 2}: `Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.`
- L10673 [english_signal] hits={'chichewa': 0, 'english': 59, 'german': 0}: `Country Head of stateMembers of the upper house Members of the lower house 5 3, 4 and 5 5 5 4 5 6 5 5 (President of F...`
- L8331 [english_signal] hits={'chichewa': 0, 'english': 33, 'german': 0}: `+Wikimania conferencesLogoConferenceDatePlaceAttendanceArchive of presentationsalt Logo of the Wikimania 2005 confere...`
- L19228 [english_signal] hits={'chichewa': 0, 'english': 26, 'german': 0}: `Dissatisfied 56 42 43 Angry 72 27 30 Satisfied 18 81 19 Enthusiastic 11 89 6 America's best days are In the future 40...`

## 6. Character and Unicode findings

### bible

- ASCII / non-ASCII: 4143128 / 29087
- alpha/num/ws/punct/other: 3483058/4742/575402/109011/2
- Chichewa-relevant chars: {'ŵ': 0, 'Ŵ': 0}
- Normalization observations (first 5000 non-empty lines): differ NFC=0, NFD=0, NFKC=0
- Top unusual codepoints: ʼ (U+02BC, n=11784), “ (U+201C, n=7964), ” (U+201D, n=6176), ‘ (U+2018, n=1742), ’ (U+2019, n=1417), — (U+2014, n=2)

### existing_corpus

- ASCII / non-ASCII: 6011213 / 36460
- alpha/num/ws/punct/other: 4981764/63891/838222/163288/508
- Chichewa-relevant chars: {'ŵ': 310, 'Ŵ': 1}
- Normalization observations (first 5000 non-empty lines): differ NFC=0, NFD=69, NFKC=36
- Top unusual codepoints: ʼ (U+02BC, n=11738), “ (U+201C, n=8000), ” (U+201D, n=6223), ’ (U+2019, n=1923), ‘ (U+2018, n=1771), – (U+2013, n=714), ŵ (U+0175, n=310), а (U+0430, n=138)

### wikipedia

- ASCII / non-ASCII: 1920497 / 7546
- alpha/num/ws/punct/other: 1542392/59745/269683/55717/506
- Chichewa-relevant chars: {'ŵ': 382, 'Ŵ': 1}
- Normalization observations (first 5000 non-empty lines): differ NFC=0, NFD=341, NFKC=202
- Top unusual codepoints: – (U+2013, n=717), ’ (U+2019, n=521), ŵ (U+0175, n=382), а (U+0430, n=138), о (U+043E, n=121), и (U+0438, n=111), е (U+0435, n=93), н (U+043D, n=91)

## 7. Boilerplate findings

Matching lines by pattern and source:

| pattern | bible | existing_corpus | wikipedia |
|---------|------:|------:|------:|
| `category_prefix` | 0 | 1174 | 1547 |
| `html_tag` | 0 | 0 | 0 |
| `image_meta` | 0 | 1 | 1 |
| `in_german_meta` | 0 | 3 | 3 |
| `mu_nkhani` | 0 | 6 | 6 |
| `url_http` | 0 | 69 | 69 |
| `url_www` | 0 | 34 | 34 |
| `wiki_link_brackets` | 0 | 0 | 0 |
| `wiki_template` | 0 | 0 | 0 |
| `wikimedia` | 0 | 40 | 40 |
| `wikipedia_muzinenero` | 0 | 1 | 1 |
| `wikipedia_word` | 0 | 72 | 72 |

### Examples — existing_corpus

- `category_prefix` (Wikipedia-style Category lines): 1174 lines, 1178 hits
  - L6209: `Category:Chaka chobadwira chikusowa (anthu amoyo)`
  - L16612: `Category:University of California, Los Angeles faculty`
- `wikipedia_word` (Mentions of Wikipedia): 72 lines, 77 hits
  - L8768: `Kusintha-ndi-thon (zinalembedwa ngati editathon kapena edit-a-thon mu chingerezi) ndi chochitika chokonzekera kumene ...`
  - L22307: `Mafayilo ochokera ku Wikimedia Commons atha kugwiritsidwa ntchito m'ma projekiti onse a Wikimedia m'zilankhulo zonse,...`
- `url_http` (HTTP(S) URLs): 69 lines, 86 hits
  - L2968: `George Washington ndi mtsogoleri wa dziko la United States kuyambira 1789 mpaka 1797.https://www.mountvernon.org/libr...`
  - L40313: `GK1 Wolfgang KleffRB5 Rainer BonhofCB3 Ulrich SurauCB4 Berti VogtsLB2 Dietmar DannerCM10 Günter Netzer (c)CM6 Christi...`
- `wikimedia` (Wikimedia project mentions): 40 lines, 46 hits
  - L12334: `Chotsatiracho chinalichonso Wikimania yoyamba yomwe inakambidwa ndi Lima Tretikov, yemwe ndi Mtsogoleri wamkulu wa Wi...`
  - L21380: `Zigawo za Wikipedia zakhala zikuchitika ku Wikimedia chapitukulu, maphunziro ovomerezedwa monga Sonoma State Universi...`
- `url_www` (www. hostnames): 34 lines, 41 hits
  - L4152: `Robert Mugabe Gabriel ( Shona: muɡaɓe 21 February 1924 - 6 September 2019) anali Zimbabwe chosintha ndi wandale amene...`
  - L11800: `Ku Ukraine, mayinawa amadziwika kuti Temporary occupation of the Autonomous Republic of Crimea ndi Sevastopol ndi Rus...`
- `mu_nkhani` (Chichewa Wikipedia article-contents nav): 6 lines, 6 hits
  - L1646: `Mu nkhani ya United States - ndipo malinga ndi US Census Bureau matanthauzo - kudera ndi: New England, Mid-Atlantic, ...`
  - L7887: `Mu nkhani ya USA Today , Ortiz amanenanso kuti malo otsiriza ochokera ku Ugly Betty ndi mutu wakuti " Mmene Betty Ana...`

### Examples — wikipedia

- `category_prefix` (Wikipedia-style Category lines): 1547 lines, 1551 hits
  - L220: `Category:Malaŵi`
  - L2384: `Category:China`
- `wikipedia_word` (Mentions of Wikipedia): 72 lines, 77 hits
  - L1315: `Wikipedia`
  - L3929: `– multilingual portal (contains links to all language editions) (wikipedia.com still redirects here)`
- `url_http` (HTTP(S) URLs): 69 lines, 86 hits
  - L3487: `http://www.satellitecitymaps.com/europe-map/bosnia-and-herzegovina-map/federation-of-bosnia-and-herzegovina-map/%C5%A...`
  - L8789: `Iye ndi munthu woyamba kulandira digiti ya doctorate mu chinenero cha Twi , chimodzi mwa mitundu ya chinenero cha Aka...`
- `wikimedia` (Wikimedia project mentions): 40 lines, 46 hits
  - L5121: `Msonkhano wautali kwambiri unachitikira ku Museo Soumaya ku Mexico City kuyambira June 9 mpaka 12, 2016, kumene anthu...`
  - L8436: `Gulu la bungwe la Wikimedia México, AC, lachigawo cha Mexican lomwe likuimira zofuna ndi zolinga za Wikimedia Foundat...`
- `url_www` (www. hostnames): 34 lines, 41 hits
  - L209: `Pa Zambiri za nyengo ya ku Malawi,chitani click apa www.bbc.com/weather .`
  - L3487: `http://www.satellitecitymaps.com/europe-map/bosnia-and-herzegovina-map/federation-of-bosnia-and-herzegovina-map/%C5%A...`
- `mu_nkhani` (Chichewa Wikipedia article-contents nav): 6 lines, 6 hits
  - L2: `Mu nkhani`
  - L7597: `Chigumula chimayambira koyamba kupyola pakati pa Halo: Combat Evolved , mu nkhani ya "343 Guilty Spark".`

## 8. Within-source duplication

### bible

- Distinct lines with exact repeats: 126
- Distinct lines with ws-normalized repeats: 126
- Distinct repeated paragraphs: 0
- Top repeated exact lines:
  - ×43: `Yehova anawuza Mose kuti,`
  - ×10: `Yehova anandiyankhula nati:`
  - ×9: `Yehova anandiyankhula kuti:`
  - ×8: `mbale imodzi yagolide yolemera magalamu 110, yodzaza ndi lubani;`
  - ×7: `Yehova anayankhula nane kuti,`

### existing_corpus

- Distinct lines with exact repeats: 384
- Distinct lines with ws-normalized repeats: 392
- Distinct repeated paragraphs: 1
- Top repeated exact lines:
  - ×146: `Zolemba`
  - ×114: `Zolemba`
  - ×82: `Category:Anthu amoyo`
  - ×76: `Zolemba`
  - ×53: `thumb`

### wikipedia

- Distinct lines with exact repeats: 621
- Distinct lines with ws-normalized repeats: 627
- Distinct repeated paragraphs: 1
- Top repeated exact lines:
  - ×163: `Zolemba`
  - ×116: `Zolemba`
  - ×95: `Category:Malaŵi`
  - ×90: `Category:Anthu amoyo`
  - ×76: `Zolemba`

## 9. Cross-source overlap matrix

Values below use **whitespace-normalized nonempty lines** (Jaccard / coverage of row by column).

| A \ B | bible | existing_corpus | wikipedia |
|-------|---|---|---|
| bible | — | J=0.6323; cov=0.9996 | J=0.0000; cov=0.0000 |
| existing_corpus | J=0.6323; cov=0.6325 | — | J=0.3675; cov=0.3675 |
| wikipedia | J=0.0000; cov=0.0000 | J=0.3675; cov=0.9999 | — |

## 10. Source-pair overlap details

### bible vs existing_corpus

#### Unit: `nonempty_lines`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 30876 | 48941 | 30864 | 0.999611 | 0.630637 | 0.630482 | bible_substantially_covered_by_existing_corpus |
| whitespace_normalized | 30876 | 48798 | 30864 | 0.999611 | 0.632485 | 0.632329 | bible_substantially_covered_by_existing_corpus |
| casefold_whitespace_normalized | 30864 | 48785 | 30864 | 1.0 | 0.632653 | 0.632653 | bible_substantially_covered_by_existing_corpus |

Shared examples (truncated):
- `Abale a ku Lusitra ndi Ikoniya anamuchitira iye umboni wabwino.`
- `Davide anatumiza mawu kwa Tamara ku nyumba yaufumu kuti, “Pita ku nyumba ya mlongo wako Amnoni ndipo ukamukonzere cha...`
- `Kenaka Ine ndidzathyola uta wa mʼdzanja lako lamanzere ndipo ndidzagwetsa mivi ya mʼdzanja lako lamanja.`

#### Unit: `paragraphs`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 1 | 88 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| whitespace_normalized | 1 | 88 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| casefold_whitespace_normalized | 1 | 88 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |

#### Unit: `token_shingles`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 429052 | 621933 | 429031 | 0.999951 | 0.689835 | 0.689811 | bible_substantially_covered_by_existing_corpus |
| whitespace_normalized | 429052 | 621933 | 429031 | 0.999951 | 0.689835 | 0.689811 | bible_substantially_covered_by_existing_corpus |
| casefold_whitespace_normalized | 427780 | 620480 | 427780 | 1.0 | 0.689434 | 0.689434 | bible_substantially_covered_by_existing_corpus |

Shared examples (truncated):
- `Abisalomu anapita ku nyumba yake`
- `Yehova kuti Sindidzakupha iwe ndi`
- `anga Davide Tsopano Yehova akubwezera`

### bible vs wikipedia

#### Unit: `nonempty_lines`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 30876 | 18078 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| whitespace_normalized | 30876 | 17935 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| casefold_whitespace_normalized | 30864 | 17921 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |

#### Unit: `paragraphs`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 1 | 90 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| whitespace_normalized | 1 | 90 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |
| casefold_whitespace_normalized | 1 | 90 | 0 | 0.0 | 0.0 | 0.0 | neither_substantially_contained |

#### Unit: `token_shingles`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 429052 | 192965 | 63 | 0.000147 | 0.000326 | 0.000101 | neither_substantially_contained |
| whitespace_normalized | 429052 | 192965 | 63 | 0.000147 | 0.000326 | 0.000101 | neither_substantially_contained |
| casefold_whitespace_normalized | 427780 | 192773 | 73 | 0.000171 | 0.000379 | 0.000118 | neither_substantially_contained |

Shared examples (truncated):
- `chifukwa cha chikondi chanu ndi`
- `mayiko ena pakati pa anthu`
- `ndi akuluakulu ena a ku`

### existing_corpus vs wikipedia

#### Unit: `nonempty_lines`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 48941 | 18078 | 18077 | 0.369363 | 0.999945 | 0.369356 | wikipedia_substantially_covered_by_existing_corpus |
| whitespace_normalized | 48798 | 17935 | 17934 | 0.367515 | 0.999944 | 0.367508 | wikipedia_substantially_covered_by_existing_corpus |
| casefold_whitespace_normalized | 48785 | 17921 | 17921 | 0.367347 | 1.0 | 0.367347 | wikipedia_substantially_covered_by_existing_corpus |

Shared examples (truncated):
- `Boma la Britain linakhazikhitsa Nyasaland Protectorate mu chaka cha 1907.`
- `Liverpool Football Club ndi kalabu yamasewera ophunzitsidwa bwino yomwe ili ku Liverpool, England.`
- `M'chigawo cha m'mphepete mwa nyanja ku Algeria, nyengo yachisanu imakhala yopanda mvula ndipo nyengo yotentha imakhal...`

#### Unit: `paragraphs`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 88 | 90 | 19 | 0.215909 | 0.211111 | 0.119497 | neither_substantially_contained |
| whitespace_normalized | 88 | 90 | 19 | 0.215909 | 0.211111 | 0.119497 | neither_substantially_contained |
| casefold_whitespace_normalized | 88 | 90 | 19 | 0.215909 | 0.211111 | 0.119497 | neither_substantially_contained |

Shared examples (truncated):
- `Birds of The Gambia by Barlow, Wacher and Disley,`
- `Maboma a South Africa Durban - wamdziko 595 061 (2011) Cape Town - wamdziko 3 740 026 (2011) Johannesburg - wamdziko ...`
- `Man of the Match: Antoine Griezmann (France) Assistant referees: Hernán Maidana (Argentina) Juan Pablo Belatti (Argen...`

#### Unit: `token_shingles`

| mode | |A| | |B| | shared | cov A←B | cov B←A | Jaccard | direction |
|------|----:|----:|-------:|--------:|--------:|--------:|-----------|
| exact | 621933 | 192965 | 192965 | 0.310267 | 1.0 | 0.310267 | wikipedia_substantially_covered_by_existing_corpus |
| whitespace_normalized | 621933 | 192965 | 192965 | 0.310267 | 1.0 | 0.310267 | wikipedia_substantially_covered_by_existing_corpus |
| casefold_whitespace_normalized | 620480 | 192773 | 192773 | 0.310684 | 1.0 | 0.310684 | wikipedia_substantially_covered_by_existing_corpus |

Shared examples (truncated):
- `FA Cups ndi maudindo 2`
- `alembe ndi kulemba nyimbo za`
- `anasamukira ku Chilanga mission station`

## 11. Representative suspicious examples

Full deterministic sample records: `data/reports/source_audit_samples.jsonl`.

### bible

- (no high-priority suspicious samples under current heuristics)

### existing_corpus

- [german_signal] L48577: `Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.`
- [german_signal] L50505: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
- [english_signal] L17329: `Country Head of stateMembers of the upper house Members of the lower house 5 3, 4 and 5 5 5 4 5 6 5 5 (President of F...`
- [english_signal] L34269: `+Wikimania conferencesLogoConferenceDatePlaceAttendanceArchive of presentationsalt Logo of the Wikimania 2005 confere...`
- [english_signal] L16031: `Dissatisfied 56 42 43 Angry 72 27 30 Satisfied 18 81 19 Enthusiastic 11 89 6 America's best days are In the future 40...`
- [english_signal] L44717: `"Therefore you also have by such admonition joined in close union the churches that were planted by Peter and Paul, t...`
- [english_signal] L31051: `+ Demographic subgroupTrumpHarris % oftotal voteIdeology Liberals 7 91 23 Moderates 40 57 42 Conservatives 90 9 34Par...`
- [english_signal] L19628: `251–261: "One of the great achievements of the past decade in the field of FGM is the shift in emphasis from the conc...`

### wikipedia

- [german_signal] L1806: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
- [german_signal] L18984: `Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.`
- [english_signal] L10673: `Country Head of stateMembers of the upper house Members of the lower house 5 3, 4 and 5 5 5 4 5 6 5 5 (President of F...`
- [english_signal] L8331: `+Wikimania conferencesLogoConferenceDatePlaceAttendanceArchive of presentationsalt Logo of the Wikimania 2005 confere...`
- [english_signal] L19228: `Dissatisfied 56 42 43 Angry 72 27 30 Satisfied 18 81 19 Enthusiastic 11 89 6 America's best days are In the future 40...`
- [english_signal] L4538: `"Therefore you also have by such admonition joined in close union the churches that were planted by Peter and Paul, t...`
- [english_signal] L19227: `+ Demographic subgroupTrumpHarris % oftotal voteIdeology Liberals 7 91 23 Moderates 40 57 42 Conservatives 90 9 34Par...`
- [english_signal] L3528: `251–261: "One of the great achievements of the past decade in the field of FGM is the shift in emphasis from the conc...`

## 12. Recommended human decisions

The following are **decision prompts**, not automated outcomes. Licensing cannot be decided by this tool.

| Source | Evidence summary | Suggested options for human review |
|--------|------------------|------------------------------------|
| bible | dup=1.1222%; foreign_heuristic_lines=0; url_lines=0 | train (if licensed) / holdout / exclude — evidence suggests relatively homogeneous religious text |
| existing_corpus | dup=3.935%; foreign_heuristic_lines=718; url_lines=74 | exclude or heavy filter / holdout — evidence suggests mixed content and likely overlap with other sources |
| wikipedia | dup=14.3046%; foreign_heuristic_lines=724; url_lines=74 | train after cleaning (if licensed) / holdout — evidence suggests boilerplate + possible non-Chichewa lines |

## 13. Proposed cleaning priorities

Priorities for a **future** cleaning design (not implemented here):

1. Complete license/provenance review before any training use.
2. Language-filter and boilerplate removal for `wikipedia` and especially `existing_corpus`.
3. Cross-source deduplication with explicit priority order once eligibility is known.
4. Light structural normalization only (documented); keep raw immutable.
5. Re-audit after cleaning before splits.

## 14. Modification statement

**No source content was modified.** Raw SHA-256 checksums recorded in this audit should match pre-audit inventory values.

### Warnings and limitations (machine copy)

- Language-signal categories are heuristics, not language identification.
- Term lists are provisional and require native-speaker review.
- Exact overlap does not capture near-duplicates or paraphrases.
- No licensing or training-eligibility decision is made by this tool.
- Raw corpus files must remain byte-identical after the audit.
- Chichewa, English, and German term lists are small, provisional, and must be reviewed by a native speaker / domain expert before being treated as reliable filters.

