# Cleaning rule error analysis (v1 on frozen review sample)

**Generated:** 2026-08-04T08:16:18Z
**Sample:** `data/reports/cleaning_review_sample.jsonl` (367 records)
**Removed reviewed:** 287

Human labels are frozen. False removal = valid_chichewa or useful_mixed_chichewa.

## Summary table

| rule | n | correct | false | precision | false-removal rate |
|------|--:|--------:|------:|----------:|-------------------:|
| `drop_english_signal` | 40 | 35 | 5 | 0.875 | 0.125 |
| `drop_min_length` | 40 | 20 | 20 | 0.5 | 0.5 |
| `drop_mixed_signal` | 40 | 1 | 39 | 0.025 | 0.975 |
| `drop_max_length` | 30 | 17 | 13 | 0.566667 | 0.433333 |
| `dedupe_exact` | 25 | 6 | 19 | 0.24 | 0.76 |
| `drop_category` | 25 | 25 | 0 | 1.0 | 0.0 |
| `drop_url` | 25 | 13 | 12 | 0.52 | 0.48 |
| `drop_digit_only` | 20 | 20 | 0 | 1.0 | 0.0 |
| `drop_wikimedia` | 20 | 9 | 11 | 0.45 | 0.55 |
| `drop_blank` | 10 | 10 | 0 | 1.0 | 0.0 |
| `drop_mu_nkhani` | 6 | 1 | 5 | 0.166667 | 0.833333 |
| `drop_in_german_meta` | 3 | 3 | 0 | 1.0 | 0.0 |
| `drop_german_signal` | 2 | 2 | 0 | 1.0 | 0.0 |
| `drop_wikipedia_muzinenero` | 1 | 1 | 0 | 1.0 | 0.0 |

## Per-rule detail

### `drop_english_signal`

- Reviewed removals: **40**
- Correct / false: **35** / **5**
- Precision / FRR: **0.875** / **0.125**
- Labels: `{'foreign_language': 35, 'useful_mixed_chichewa': 5}`

False removals (examples):
- L13065 [useful_mixed_chichewa]: Pa 1 Okutobala 2021, a Doumbouya adalumbira ngati purezidenti wanthawi yayitali.Guinea swears in coup leader Mamady Doumbouya as interim president
- L13217 [useful_mixed_chichewa]: Munthawi yoyamba ya Abe, Suga adakhala Minister of Internal Affairs and Communications kuyambira 2006 mpaka 2007.
- L14514 [useful_mixed_chichewa]: Mu 1990, Soviet of the Crimea Oblast anaganiza zobwezeretsa Crimea ASSR.

Correct removals (examples):
- L151 [foreign_language]: ChibembaChinyanjaChitongaChingereziVesi WoyambaStand and sing for Zambia, proud and free,
- L155 [foreign_language]: All one, Strong and Free.Vesi lachiwiriAfrica is our own motherland,
- L653 [foreign_language]: Hills and valleys, soil so rich and rare

### `drop_min_length`

- Reviewed removals: **40**
- Correct / false: **20** / **20**
- Precision / FRR: **0.5** / **0.5**
- Labels: `{'valid_chichewa': 20, 'boilerplate_or_noise': 20}`

False removals (examples):
- L72 [valid_chichewa]: Mzuzu
- L254 [valid_chichewa]: Nyimbo ya Solomo
- L260 [valid_chichewa]: Hoseya

Correct removals (examples):
- L1021 [boilerplate_or_noise]: GA Gabon
- L1039 [boilerplate_or_noise]: GY Guyana
- L1153 [boilerplate_or_noise]: SV Salvador

### `drop_mixed_signal`

- Reviewed removals: **40**
- Correct / false: **1** / **39**
- Precision / FRR: **0.025** / **0.975**
- Labels: `{'useful_mixed_chichewa': 39, 'boilerplate_or_noise': 1}`

False removals (examples):
- L218 [useful_mixed_chichewa]: Blantyre ndi mzinda wofunika kwa dziko la Malawi chifukwa ndi mzinda omwe kumapezeka malo ofunika ngati Malawi Polytechnic,yomwe ndi sukulu ya za ukachenjede ku
- L1355 [useful_mixed_chichewa]: He was the third son of John Johnson, a lawyer of Ryde, and Mary Percival, his second wife, ..." - Baibulo, Buku Lopatulika ndilo Mau a Mulungu, anatanthauzirid
- L2062 [useful_mixed_chichewa]: Koma malowa anatchulidwa dzina lina ndi John II of Portugal ngati "Cape of Good Hope" (Cabo da Boa Esperança) chifukwa cha chiyembekezo chimene chinalipo chopez

Correct removals (examples):
- L8314 [boilerplate_or_noise]: The osiyanasiyana wochitachita wa Nikon D3200 ( Expeed 3 dzina lake Expeed 2 mtundu, 14 Tinthu yafupika kuti Akamva 12 ) kuposa ngakhale zonse chimango DSLRs ng

### `drop_max_length`

- Reviewed removals: **30**
- Correct / false: **17** / **13**
- Precision / FRR: **0.566667** / **0.433333**
- Labels: `{'valid_chichewa': 5, 'boilerplate_or_noise': 17, 'useful_mixed_chichewa': 8}`

False removals (examples):
- L192 [valid_chichewa]: Anthu ambiri ochoka ku mayikao a ku ulaya,South Africa ndi anthu akunja,ogwira ntchito kunja amakhala ku Lilongwe, ndiponso kuli ma NGOs ngati (Care Internation
- L326 [valid_chichewa]: Ndi povuta kunena tsiku leni leni lomwe Yesu anabadwa chifukwa zolembalemba zina zokhudza nkhaniyi zinasowa kapena kuonongeka ndiponso zaka 1900 zinadutsa chile
- L3946 [valid_chichewa]: Mapulogalamu ena akhalapo kwa zaka zoposa 2,000 ndipo adasintha kwambiri kuyambira nthawi imeneyo monga chinenero (cholembedwa m'zinenero zamitundu yonse kapena

Correct removals (examples):
- L3888 [boilerplate_or_noise]: Portrait Name Term of office Monarch Took office Left office Time in office 1 60px Sir Herbert Stanley 1924 1927 George V – 60px Richard Allmond Jeffrey Goode 1
- L3892 [boilerplate_or_noise]: Portrait Name Took office Left office Political party 80px Kenneth Kaunda 22 January 1964 24 October 1964 UNIP 80px Reuben Kamanga 24 October 1964 October 1967 
- L5911 [boilerplate_or_noise]: MoscowSaint PetersburgSochiLuzhniki StadiumOtkritie ArenaKrestovsky StadiumFisht Olympic StadiumCapacity: 78,011Capacity: 44,190Capacity: 64,468Capacity: 44,287

### `dedupe_exact`

- Reviewed removals: **25**
- Correct / false: **6** / **19**
- Precision / FRR: **0.24** / **0.76**
- Labels: `{'duplicate': 2, 'valid_chichewa': 19, 'boilerplate_or_noise': 4}`

False removals (examples):
- L2988 [valid_chichewa]: Delhi ndi boma lina la dziko la India.
- L7009 [valid_chichewa]: Zogwirizana zakunja
- L7715 [valid_chichewa]: Inabweretsedwa pa September 2, 2006 .

Correct removals (examples):
- L2581 [duplicate]: Kuchuluka: 3,372 ta’ata/km²
- L9572 [boilerplate_or_noise]: World Health Organization.
- L9704 [boilerplate_or_noise]: Weekly epidemiological record.

### `drop_category`

- Reviewed removals: **25**
- Correct / false: **25** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'boilerplate_or_noise': 25}`

Correct removals (examples):
- L388 [boilerplate_or_noise]: Category:Zambia
- L932 [boilerplate_or_noise]: Category:
- L1849 [boilerplate_or_noise]: Category: Media ku Calabria

### `drop_url`

- Reviewed removals: **25**
- Correct / false: **13** / **12**
- Precision / FRR: **0.52** / **0.48**
- Labels: `{'useful_mixed_chichewa': 12, 'boilerplate_or_noise': 12, 'foreign_language': 1}`

False removals (examples):
- L209 [useful_mixed_chichewa]: Pa Zambiri za nyengo ya ku Malawi,chitani click apa www.bbc.com/weather .
- L2127 [useful_mixed_chichewa]: George Washington ndi mtsogoleri wa dziko la United States kuyambira 1789 mpaka 1797.https://www.mountvernon.org/library/digitalhistory/digital-encyclopedia/art
- L3158 [useful_mixed_chichewa]: Pa May 28, 1995, boma la Taiwan unachitikira maliro chachikulu kwa iye kuti azikumbukira chachikulu Taiwanese woimba.https://repositories.lib.utexas.edu/handle/

Correct removals (examples):
- L1316 [boilerplate_or_noise]: http://el.wikipedia.org/wiki/Πύλη:Κύρια
- L1795 [boilerplate_or_noise]: Archive.org: https://web.archive.org/web/20091002215506/http://ls78.sweb.cz/lydnevi.htm%26gt;BERGER, Tilman (2004).
- L3729 [boilerplate_or_noise]: www.edirne.bel.tr

### `drop_digit_only`

- Reviewed removals: **20**
- Correct / false: **20** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'boilerplate_or_noise': 20}`

Correct removals (examples):
- L331 [boilerplate_or_noise]: 9
- L1881 [boilerplate_or_noise]: 3
- L3848 [boilerplate_or_noise]: 1978

### `drop_wikimedia`

- Reviewed removals: **20**
- Correct / false: **9** / **11**
- Precision / FRR: **0.45** / **0.55**
- Labels: `{'valid_chichewa': 11, 'boilerplate_or_noise': 9}`

False removals (examples):
- L20 [valid_chichewa]: Ntchito zina za Wikimedia
- L5117 [valid_chichewa]: Zigawo za Wikipedia zakhala zikuchitika ku Wikimedia chapitukulu, maphunziro ovomerezedwa monga Sonoma State University, Arizona State University, Middlebury Co
- L6551 [valid_chichewa]: Makampani ena athandiza Wikimedia mwa kupereka ma kompyuta, komanso pogwiritsa ntchito ma seva.

Correct removals (examples):
- L6541 [boilerplate_or_noise]: thumb Wikimedia Foundation logo
- L6542 [boilerplate_or_noise]: Wikimedia Foundation ndi maziko osapindulitsa.
- L6547 [boilerplate_or_noise]: Amaphatikizapo Wikimedia Foundation wiki, MediaWiki wiki, Test Wikipedia, Wikimedia Incubator, Bugzilla, ndi Wikimania wiki.

### `drop_blank`

- Reviewed removals: **10**
- Correct / false: **10** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'boilerplate_or_noise': 10}`

Correct removals (examples):
- L16 [boilerplate_or_noise]: 
- L3779 [boilerplate_or_noise]: 
- L5567 [boilerplate_or_noise]: 

### `drop_mu_nkhani`

- Reviewed removals: **6**
- Correct / false: **1** / **5**
- Precision / FRR: **0.166667** / **0.833333**
- Labels: `{'boilerplate_or_noise': 1, 'useful_mixed_chichewa': 4, 'valid_chichewa': 1}`

False removals (examples):
- L1908 [useful_mixed_chichewa]: Mu nkhani ya United States - ndipo malinga ndi US Census Bureau matanthauzo - kudera ndi: New England, Mid-Atlantic, East North pakati States, West North pakati
- L7597 [useful_mixed_chichewa]: Chigumula chimayambira koyamba kupyola pakati pa Halo: Combat Evolved , mu nkhani ya "343 Guilty Spark".
- L7885 [useful_mixed_chichewa]: Mu nkhani ya USA Today , Ortiz amanenanso kuti malo otsiriza ochokera ku Ugly Betty ndi mutu wakuti " Mmene Betty Anakhumudwitsiranso ", pamene Hilda adakhala p

Correct removals (examples):
- L2 [boilerplate_or_noise]: Mu nkhani

### `drop_in_german_meta`

- Reviewed removals: **3**
- Correct / false: **3** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'foreign_language': 3}`

Correct removals (examples):
- L13924 [foreign_language]: (in German) In: Rathauskorrespondenz, 27 May 2009Edita Gruberova ausgezeichnet (image) In: Rathauskorrespondenz, 27 May 2009
- L13928 [foreign_language]: Juni 2014 (in German) Musiktheaterpreis, retrieved 4 April 2015
- L13929 [foreign_language]: 2016: Ehrenplakette of the in Garmisch-PartenkirchenEröffnungsprogramm der Richard-Strauss-Festivals 2016 (in German) Richard-Strauss-Festival, retrieved 6 Apri

### `drop_german_signal`

- Reviewed removals: **2**
- Correct / false: **2** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'foreign_language': 2}`

Correct removals (examples):
- L1806 [foreign_language]: "Towards a unified slavic language", Fourth Language Creation Conference, Groningen.MEYER, Anna-Maria (2012): "Slavische Plansprachen auf dem Weg ins 21.
- L18984 [foreign_language]: Tsygankov, Daniel Beruf, Verbannung, Schicksal: Iwan Iljin und Deutschland // Archiv fuer Rechts- und Sozialphilosophie.

### `drop_wikipedia_muzinenero`

- Reviewed removals: **1**
- Correct / false: **1** / **0**
- Precision / FRR: **1.0** / **0.0**
- Labels: `{'boilerplate_or_noise': 1}`

Correct removals (examples):
- L14 [boilerplate_or_noise]: Wikipedia Muzinenero Zina

## Implications for v2

| Rule | Finding | v2 action |
|------|---------|-----------|
| drop_mixed_signal | 97.5% FRR | Disable delete-by-default; retain/tag |
| drop_min_length | 50% FRR | Conditional short-line only |
| drop_max_length | 43% FRR | No length-only delete |
| drop_url | 48% FRR | Strip URL; delete only if remainder empty/meta |
| drop_mu_nkhani | 83% FRR | Exact/nav-only match |
| drop_wikimedia | 55% FRR | Chrome/short/logo only; keep prose |
| drop_english_signal | 12.5% FRR | High-confidence foreign only |
| dedupe_exact | 76% FRR (vs human keep) | Defer full dedupe; precision-first |
| drop_category / digit / blank / german | High precision | Keep |

