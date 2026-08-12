# Cleaning before/after report

**Generated:** 2026-08-04T04:05:42.596146Z
**Tool:** clean_sources v1.0.0
**Config version:** 1.0.0

> **Raw files were not modified.** All outputs are under `data/interim/cleaning`.

> Interim cleaned text is **not** final processed training data and is **not** an approval for training. Licensing remains unresolved.

## Sources cleaned

- **bible**: removed 0 lines; kept 31099; transform events 0
- **wikipedia**: removed 6181 lines; kept 14398; transform events 1425

## bible

- Input: `data/raw/bible/bible_clean.txt`
- Input SHA-256: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- Cleaned SHA-256: `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89`
- Notes: Light-touch cleaning. Bible is relatively homogeneous; avoid aggressive language filters.

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
- Cleaned SHA-256: `aa5550fd242069a13ce146756d1aa883d1b3ae8a82e90506d92fa6a6040db332`
- Notes: Stronger filters for navigation, categories, URLs, foreign-signal lines, and within-source exact duplicates.

### Rule hit counts (removals / transforms)

| rule | count |
|------|------:|
| `drop_min_length` | 3167 |
| `drop_category` | 1547 |
| `transform:strip_edges` | 1425 |
| `drop_english_signal` | 413 |
| `dedupe_exact` | 292 |
| `drop_mixed_signal` | 267 |
| `drop_blank` | 208 |
| `drop_digit_only` | 111 |
| `drop_url` | 74 |
| `drop_max_length` | 56 |
| `drop_wikimedia` | 34 |
| `drop_mu_nkhani` | 6 |
| `drop_in_german_meta` | 3 |
| `drop_german_signal` | 2 |
| `drop_wikipedia_muzinenero` | 1 |

### Before → after quality

| metric | before | after | delta |
|--------|-------:|------:|------:|
| total_lines | 20579 | 14398 | -6181 |
| non_empty_lines | 20371 | 14398 | -5973 |
| blank_lines | 208 | 0 | -208 |
| character_count_estimate | 1928042 | 1648965 | -279077 |
| estimated_word_token_count | 273158 | 233168 | -39990 |
| unique_exact_nonempty | 18078 | 14388 | -3690 |
| duplicate_line_percentage | 14.3046 | 0.1389 | -14.165700000000001 |
| very_short_lines | 3818 | 98 | -3720 |
| very_long_lines | 77 | 0 | -77 |
| url_containing_lines | 74 | 0 | -74 |
| digit_only_lines | 111 | 0 | -111 |
| min_line_length | 1 | 18 | 17 |
| median_line_length | 75 | 102.0 | 27.0 |
| max_line_length | 3055 | 499 | -2556 |

#### Language-signal distribution (heuristic)

| category | before | after | before % | after % |
|----------|-------:|------:|---------:|--------:|
| `chichewa_signal` | 9611 | 9326 | 47.1798 | 64.7729 |
| `english_signal` | 446 | 0 | 2.1894 | 0.0 |
| `german_signal` | 2 | 0 | 0.0098 | 0.0 |
| `mixed_signal` | 276 | 0 | 1.3549 | 0.0 |
| `insufficient_signal` | 10036 | 5072 | 49.2661 | 35.2271 |

#### Boilerplate matching lines

| pattern | before | after |
|---------|-------:|------:|
| `category_prefix` | 1547 | 0 |
| `in_german_meta` | 3 | 0 |
| `mu_nkhani` | 6 | 0 |
| `url_http` | 69 | 0 |
| `url_www` | 34 | 0 |
| `wikimedia` | 40 | 0 |
| `wikipedia_muzinenero` | 1 | 0 |
| `wikipedia_word` | 72 | 29 |

### Sample removals (first matches by rule)

- **`dedupe_exact`**
  - L9351: `Zizindikiro zinanso zingakhale monga kusokonezeka maganizo kapena bongo kusiya kugwira ntchito moyenera, kusanza, ndi...`
  - L9395: `Miliri ina yocheperapo ya matendawa imabukanso m'madera osiyanasiyana padziko lapansili.`
  - L9403: `Weekly epidemiological record.`
- **`drop_blank`**
  - L5556: ``
  - L5558: ``
  - L5969: ``
- **`drop_category`**
  - L382: `Category:Nyasa zinenero`
  - L481: `Category:ziPani za ndale za ku Malaŵi`
  - L8534: `Category:Anthu amoyo`
- **`drop_digit_only`**
  - L3849: `1983`
  - L8334: `2005`
  - L8940: `3`
- **`drop_english_signal`**
  - L3532: `6/6:"Data sources: UNICEF global databases, 2014, based on Demographic and Health Surveys (DHS), Multiple Indicator C...`
  - L12942: `Guidelines for Sabbath Observance, document voted by the General Conference Session of 1990`
  - L16298: `Petersburg Faculty of Physics and Mathematics komanso pa Academy of Petersburg Arts.`
- **`drop_german_signal`**
  - L1806: `"Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavis...`
  - L18984: `Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.`
- **`drop_in_german_meta`**
  - L13924: `(in German) In: Rathauskorrespondenz, 27 May 2009Edita Gruberova ausgezeichnet (image) In: Rathauskorrespondenz, 27 M...`
  - L13928: `Juni 2014 (in German) Musiktheaterpreis, retrieved 4 April 2015`
  - L13929: `2016: Ehrenplakette of the in Garmisch-PartenkirchenEröffnungsprogramm der Richard-Strauss-Festivals 2016 (in German)...`
- **`drop_max_length`**
  - L3946: `Mapulogalamu ena akhalapo kwa zaka zoposa 2,000 ndipo adasintha kwambiri kuyambira nthawi imeneyo monga chinenero (ch...`
  - L7891: `Nick Lorena 2002 Mkazi wa Lehi Kelly Filimu yochepa 2003 Carolina Christen 2007 Tortilla Kumwamba Chicana 2008 Wing'o...`
  - L8566: `+ Televizioni Chaka Mutu Udindo Mfundo 2000-01 Jardins Proibidos Sara Kutayidwa Kwakukulu Chisipanishi sopo opera yof...`
- **`drop_min_length`**
  - L1001: `CZ Czechia`
  - L3064: `Switzerland (de.`
  - L4626: `Riemer Faber`
- **`drop_mixed_signal`**
  - L1769: `Matenda a Ebola anapezeka koyamba m’dziko la Sudan kenako m’dziko la Democratic Republic of the Congo.`
  - L9335: `Ndpo katemerayu ali pagulu la mankhwala ofunika kwambiri otchedwa World Health Organization's List of Essential Medic...`
  - L11453: `Maudindo omwe amapezeka mumafomu a Game & Watch amasiyanasiyana kuchokera ku Mickey Mouse mpaka Balloon Fight, kuphat...`
- **`drop_mu_nkhani`**
  - L2: `Mu nkhani`
  - L1908: `Mu nkhani ya United States - ndipo malinga ndi US Census Bureau matanthauzo - kudera ndi: New England, Mid-Atlantic, ...`
  - L7597: `Chigumula chimayambira koyamba kupyola pakati pa Halo: Combat Evolved , mu nkhani ya "343 Guilty Spark".`
- **`drop_url`**
  - L9894: `She has gained recognition and multiple awards from Born n Bred "Recognition award" in 2012, Mosi Lager Zambian Music...`
  - L11510: `mu 1847 kuchokera ku zitsanzo zomwe zidapezeka ku Liberia.https://onlinelibrary.wiley.com/doi/abs/10.1002/evan.20203 ...`
  - L11951: `Nyimbo za Bach zimaimbidwa, kuphunzira ndikusangalala padziko lonse lapansi.https://www.oxfordmusiconline.com/grovemu...`
- **`drop_wikimedia`**
  - L3926: `Ndilo buku lalikulu kwambiri komanso lodziwika bwino lomwe likuwonekera pa intaneti, ndipo ndi imodzi mwa malo otchuk...`
  - L5117: `Zigawo za Wikipedia zakhala zikuchitika ku Wikimedia chapitukulu, maphunziro ovomerezedwa monga Sonoma State Universi...`
  - L6547: `Amaphatikizapo Wikimedia Foundation wiki, MediaWiki wiki, Test Wikipedia, Wikimedia Incubator, Bugzilla, ndi Wikimani...`
- **`drop_wikipedia_muzinenero`**
  - L14: `Wikipedia Muzinenero Zina`

## Raw checksum verification

| source | pre | post | match |
|--------|-----|------|:-----:|
| bible | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | `55445a0e0a5359e243f1773de623af1716bf4d3cd835afd83c4407cbaf85fc89` | yes |
| wikipedia | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | `cf7c5ba6d8c0d4770eee3306bab9f4be1dfc9570930a9aa7f3613c0ffb4587b7` | yes |

**raw_files_unchanged:** `True`

## Disclaimers

- Interim cleaned outputs are not final processed training data.
- Licensing and allowed_for_training remain unresolved until human review.
- Language-signal filters are transparent heuristics, not authoritative language identification.
- Raw files under data/raw/ must remain byte-identical.

