# Level B Chichewa morphology benchmark re-audit v0.1

This is a recommendation-only audit of the active 195-item development file. No benchmark annotation, canonical file, self-review file, or source annotation was modified.

## Governing standard

Level B — conservative medium granularity. Productive grammatical morphology and well-supported extensions are split; opaque lexical/derived stems are preserved. Syllable shape is never evidence for a morpheme boundary.

Final vowels are handled constructionally: they are split when a verbal paradigm and the sentence context independently recover the boundary, not by a blanket always/never rule. In particular, nena versus nene supports nen+a versus nen+e, so the relevant ndisananene analysis is ndi+sana+nen+e.

## Summary

| Measure | Count |
|---|---:|
| Active items audited | 195 |
| KEEP | 18 |
| REVISE | 133 |
| UNCERTAIN | 11 |
| EXCLUDE | 33 |

Historical measurements are preserved unchanged: exact agreement = 0.52; boundary F1 = 0.841. They remain measurements of the original annotation protocol and are not reinterpreted here.

## Systematic patterns flagged

Counts below are audited items flagged for the issue; categories can overlap.

| Issue | Count | Interpretation |
|---|---:|---|
| syllabic oversegmentation | 9 | Old boundaries divide syllables or lexical strings without grammatical evidence. |
| final-vowel issue | 125 | Old annotations commonly keep a recoverable verbal final vowel inside a stem, or split it without constructional support. |
| incorrect grammatical parse | 13 | A prefix/TAM/OM/passive analysis is assigned to the wrong substring or construction. |
| missing productive morphology | 33 | A supported passive, causative, applicative, stative, noun-class, or related boundary is absent. |
| noun-class issue | 15 | A recoverable noun-class or agreement boundary is missing or misidentified. |
| TAM issue | 12 | A TAM element is merged, split incorrectly, or assigned the wrong function. |
| post-final/clitic issue | 25 | A post-final clitic such as -nso, -ni, -be, -ko, or -po is not separated or is overinterpreted. |
| lexicalization/root uncertainty | 35 | Root versus derived stem cannot be safely resolved without stronger lexical/paradigmatic evidence. |
| locative issue | 7 | Locative contraction or prefix-versus-phrase status needs special handling. |
| language/quality issue | 38 | Name, foreign token, mixed-language item, loan status, or noisy source quality affects inclusion. |
| insufficient context | 1 | The isolated or truncated context does not license a confident constructional analysis. |

### Additional audit checks

These counts make the requested recurring patterns explicit. They are counts of audited items and may overlap. “Original whole-form” means the prior segmentation contained no `+`; it does not mean the token was linguistically unanalyzable.

| Pattern | Count | Operational definition |
|---|---:|---|
| syllabic_oversegmentation | 9 | Old boundaries that divide lexical material without independent morpheme evidence. |
| final_vowel_inconsistency | 125 | Items where a final-vowel boundary is supported, missing, or overinterpreted under the constructional rule. |
| subject_tam_object_prefix_inconsistency | 19 | Union of items flagged for an incorrect pre-stem parse or TAM issue. |
| noun_class_prefix_inconsistency | 15 | Items with a missing, merged, or uncertain noun-class/agreement boundary. |
| passive_applicative_causative_or_related_extension_inconsistency | 33 | Items where supported productive internal morphology is missing or requires review. |
| post_final_clitic_inconsistency | 25 | Items involving -nso, -ni, -be, -ko, -po, -di, or comparable post-final material. |
| sana_handling_cases | 5 | Five targeted items involving negative sa+na or the unified negative-anterior sana analysis. |
| nka_as_single_tam_cases | 2 | The two items where n+ka was rejected in favor of one nka TAM element. |
| lexicalized_stem_or_root_uncertainty | 35 | Items where root versus safest derived/lexical stem remains unresolved. |
| original_whole_form_items | 36 | Prior segmentation had no plus boundary. |
| original_whole_form_revised_to_internal_morphology | 2 | Prior whole-form label revised because productive internal morphology is recoverable. |
| original_whole_form_retained_or_provisional | 2 | Prior whole-form label kept or marked uncertain after audit. |
| original_whole_form_excluded_for_language_or_quality | 32 | Prior whole-form label excluded because the token is foreign, a name, numeric, or noisy. |

Notable systematic pattern: the old annotations often correctly located the broad grammatical complex but kept the entire lexical verb stem, including a recoverable final vowel, as one segment. Other recurring issues are fused negative-plus-subject sequences (especially s+a), treating sana as sa+na, treating nka as n+ka, and inconsistent recognition of noun-class prefixes and passive/applicative extensions.

## A. Proposed revisions

### morph_dev_0001 — Analigawa

Context:

> Ndipo anthu anachoka ndi kukayendera dziko lonse. Iwo analemba bwinobwino mʼbuku za dzikolo, mzinda ndi mzinda. Analigawa magawo asanu ndi awiri, ndipo anabwerera kwa Yoswa ku misasa ya ku Silo.

Original: `Anali+gawa`

Proposed: `A+na+li+gaw+a`

Analysis:

- A → 3SG/class-agreement subject marker
- na → past TAM
- li → class-5 object marker
- gaw → lexical root “divide”
- a → verbal final vowel

Reason for change: The current Anali+gawa merges independently grammatical material and leaves the verbal final vowel inside the lexical remainder.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: granularity; final-vowel issue; missing productive morphology.

### morph_dev_0002 — imafunsidwa

Context:

> Mu moyo wa tsiku ndi tsiku, koloko imafunsidwa kwa nthawi zosakwana tsiku koma kalendala imakambidwa kwa nthawi yaitali kuposa tsiku.

Original: `i+ma+funsidwa`

Proposed: `i+ma+funs+idw+a`

Analysis:

- i → subject/agreement marker
- ma → habitual/ongoing TAM
- funs → lexical root “ask/consult”
- idw → passive extension
- a → verbal final vowel

Reason for change: The passive of funsa is transparently recoverable as funs-idw-a; the current label leaves the productive passive and final vowel inside the stem.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0003 — nditenga

Context:

> Ngati munthuyo anena kuti, “Apseretu mafuta poyamba, ndipo kenaka mutenge mmene mufunira,” mtumikiyo amayankha kuti, “Ayi ndipatse tsopano lino. Ngati sutero, ine nditenga molanda.”

Original: `ndi+tenga`

Proposed: `ndi+teng+a`

Analysis:

- ndi → 1SG subject marker
- teng → lexical root “take”
- a → verbal final vowel

Reason for change: The context supplies a finite first-person verb; teng-a is a recoverable lexical-plus-final-vowel structure.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0004 — Ugone

Context:

> Gona konkuno usiku uno mpaka mmawa. Tsono ngati iyeyu adzakulowa chokolo, chabwino alowe. Koma ngati safuna kutero, ine ndikulumbira pamaso pa Yehova Wamoyo kuti ndidzakulowa chokolo. Ugone kuno mpaka

Original: `U+gone`

Proposed: `U+gon+e`

Analysis:

- u → 2SG subject marker
- gon → lexical root “sleep”
- e → imperative/subjunctive final vowel

Reason for change: The imperative/dependent form ugone supports a final e boundary; gon is the safest root.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0005 — ndikuwunikanso

Context:

> Uthengawu udawonedwa kuchokera ku Sweden ndi Prague ndipo pomwe akuphatikiza mtundu wathunthu ndikuwunikanso kuchokera pa nsanja ya 85 kupita ku "Proxima Centauri ipita pafupi ndi mwezi wapadziko lapa

Original: `ndi+ku+wunika+nso`

Proposed: `ndi+ku+wunik+a+nso`

Analysis:

- ndi → 1SG subject marker
- ku → progressive/present TAM
- wunik → lexical stem “inspect/review”
- a → verbal final vowel
- nso → post-final additive/repetitive clitic “also/again”

Reason for change: The pre-stem grammar and final nso are already well supported; the finite paradigm independently recovers wunik-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0006 — azigonekedwa

Context:

> Kuchotsa mimba m'njira yosatetezeka kumachititsa kuti amayi pafupifupi 47,000 azimwalira ndiponso kuti amayi 5 miliyoni azigonekedwa m'chipatala chaka chilichonse.

Original: `a+zi+gonekedwa`

Proposed: `a+zi+gonek+edw+a`

Analysis:

- a → class-2 subject marker
- zi → aspectual/modal pre-stem element
- gonek → safest lexical/derived stem “put to bed/hospitalize”
- edw → passive extension
- a → verbal final vowel

Reason for change: The context is passive hospitalization. Passive -edw- is productive, while the exact value of zi- is less secure; retain gonek- as the safe stem.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; TAM issue.

### morph_dev_0007 — Tikukudalitsani

Context:

> Wodala amene akubwera mʼdzina la Yehova. Tikukudalitsani kuchokera ku nyumba ya Yehova.

Original: `Ti+ku+ku+dalitsani`

Proposed: `Ti+ku+ku+dalits+a+ni`

Analysis:

- Ti → 1PL subject marker
- ku → progressive/present TAM
- ku → 2SG object marker
- dalits → lexical/derived stem “bless”
- a → verbal final vowel
- ni → plural/formal post-final marker

Reason for change: The two ku elements have different grammatical roles, and the polite/plural -ni follows the independently recoverable final a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0008 — imanenedwa

Context:

> Imfa Yoyamba Imfa imanenedwa kukhala yoposa 100   km mpaka 160   kilomita imodzi, malinga ndi gwero .

Original: `i+ma+nenedwa`

Proposed: `i+ma+nen+edw+a`

Analysis:

- i → subject/agreement marker
- ma → habitual/ongoing TAM
- nen → lexical root “say”
- edw → passive extension
- a → verbal final vowel

Reason for change: The passive of nena is transparently segmented as nen-edw-a in this habitual construction.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0009 — inasandukanso

Context:

> Kenaka Yehova anati kwa iye, “Igwire mtchira.” Ndipo Mose anayigwira mchira njokayo ndipo inasandukanso ndodo mʼdzanja lake.

Original: `ina+sanduka+nso`

Proposed: `i+na+sanduk+a+nso`

Analysis:

- i → subject/agreement marker
- na → past TAM
- sanduk → safest lexical/stative stem “change/turn into”
- a → verbal final vowel
- nso → post-final additive/repetitive clitic “again”

Reason for change: The grammar and post-final nso are clear; sanduk- is retained as a conservative stem rather than decomposed into syllables or an unsupported extension.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue; lexicalization/root uncertainty.

### morph_dev_0010 — chikulimbana

Context:

> Tsono chigulu chankhondo cha mitundu ina yonse chimene chikulimbana ndi mzinda wa Arieli nʼkumathira nkhondo mzindawo, malinga ake ndi kuwuzinga, chigulu chonsecho chidzazimirira ngati maloto, gati zi

Original: `chi+ku+limbana`

Proposed: `chi+ku+limban+a`

Analysis:

- chi → class-7 subject/agreement marker
- ku → progressive/present TAM
- limban → safest lexical/derived stem “fight”
- a → verbal final vowel

Reason for change: The finite verb supports a final a boundary, but limban- is kept intact because a reciprocal analysis of -an- is not independently established here.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0011 — inalimbana

Context:

> Anandimanga ndi zingwe za ku manda; misampha ya imfa inalimbana nane.

Original: `i+na+limbana`

Proposed: `i+na+limban+a`

Analysis:

- i → subject/agreement marker
- na → past TAM
- limban → safest lexical/derived stem “fight”
- a → verbal final vowel

Reason for change: The past prefix sequence is clear and the final a is recoverable; the internal history of limbana is conservatively left in the stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0012 — mudzandipezadi

Context:

> mudzandipezadi,” akutero Yehova, “ndipo ndidzakubwezerani zabwino zanu. Ndidzakusonkhanitsani kuchokera ku mayiko onse ndi kumalo konse kumene munali,” akutero Yehova, “ndipo ndidzakubweretsani kumalo

Original: `mu+dza+ndi+peza+di`

Proposed: `mu+dza+ndi+pez+a+di`

Analysis:

- mu → 2PL subject marker
- dza → future TAM
- ndi → 1SG object marker
- pez → lexical root “find”
- a → verbal final vowel
- di → post-final emphatic particle

Reason for change: The subject, future, object, and emphatic post-final are independently grammatical; pez-a is the recoverable verbal stem-plus-final-vowel sequence.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0016 — akanamasulidwa

Context:

> Agripa anati kwa Festo, “Munthu uyu akanamasulidwa akanakhala kuti sanapemphe zokaonekera kwa Kaisara.”

Original: `a+kana+masulidwa`

Proposed: `a+kana+masul+idw+a`

Analysis:

- a → subject/agreement marker
- kana → conditional/irrealis TAM
- masul → lexical stem “release”
- idw → passive extension
- a → verbal final vowel

Reason for change: The conditional passive construction makes masul-idw-a recoverable; the existing label hides both productive passive morphology and the final vowel.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0017 — kagwire

Context:

> “Kodi muganiza bwanji? Panali munthu wina anali ndi ana aamuna awiri. Anapita kwa woyamba nati, ‘Mwanawe pita kagwire ntchito lero mʼmunda wamphesa.’

Original: `ka+gwire`

Proposed: `ka+gwir+e`

Analysis:

- ka → consecutive/go-and pre-stem element
- gwir → lexical root “work/perform”
- e → imperative/subjunctive final vowel

Reason for change: The consecutive command kagwire supports ka plus a dependent final e; gwir- is the safest lexical root.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0018 — matsiriziro

Context:

> Ndinamva, koma sindinamvetsetse. Choncho ndinafunsa kuti, “Mbuye wanga, nanga matsiriziro a zonsezi adzakhala chiyani?”

Original: `ma+tsirizi+ro`

Proposed: `ma+tsiriziro`

Analysis:

- ma → class-6 plural noun prefix
- tsiriziro → safest deverbal nominal stem “ending/conclusion”

Reason for change: The current tsirizi+ro split is not independently supported. The lexical-family evidence supports a single nominal stem tsiriziro at Level B.

Evidence: Mchombo 2004, ch. 7, pp. 112–130 (nominal derivation); Msaka & Biberauer 2024, pp. 229–262 (Chichewa deverbal nominalization); lexical-family evidence; sentence context.

Confidence: **MEDIUM**

Disagreement type: syllabic oversegmentation; lexicalization/root uncertainty.

### morph_dev_0020 — anakakamizika

Context:

> Mu 1974 maphunziro a usilikali anakakamizika kwa omaliza sukulu ya fomu 5, omaliza maphunziro a yunivesite ndi akuluakulu aboma.

Original: `a+na+ka+kamizika`

Proposed: `a+na+kakamiz+ik+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- kakamiz → safest lexical stem “force/compel”
- ik → stative/inchoative extension
- a → verbal final vowel

Reason for change: The apparent ka after na is not independently a separate TAM in this form. Kakamizika has a plausible stative/inchoative -ik- relation to kakamiza, but the reduplicative/lexical base is kept intact.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: incorrect grammatical parse; missing productive morphology; final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0022 — masuleni

Context:

> Masautso a mu mtima mwanga achulukirachulukira; masuleni ku zowawa zanga.

Original: `ma+suleni`

Proposed: `masul+e+ni`

Analysis:

- masul → lexical root/stem “release”
- e → imperative/subjunctive final vowel
- ni → plural/formal post-final marker

Reason for change: Masuleni is an imperative plural, not ma- plus a noun-like remainder. The final e and post-final -ni are independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue; final-vowel issue; post-final/clitic issue; incorrect grammatical parse.

### morph_dev_0024 — anakazichotsa

Context:

> Ndipo ziwiya zagolide ndi zasiliva za ku Nyumba ya Mulungu zimene Nebukadinezara anazitenga mʼNyumba ya Mulungu ku Yerusalemu ndi kukaziyika mʼnyumba ya milungu ya ku Babuloni, anakazichotsa ku nyumba

Original: `a+na+ka+zi+chotsa`

Proposed: `a+na+ka+zi+chots+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- ka → consecutive/directional pre-stem element
- zi → class-8 object marker
- chots → lexical root “remove”
- a → verbal final vowel

Reason for change: The pre-stem sequence and class-8 object marker are clear; chots-a is the recoverable lexical-plus-final-vowel portion.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; missing productive morphology.

### morph_dev_0027 — cholimbana

Context:

> Yehova Mulungu wa Israeli akunenapo pa za nyumba za mu mzinda muno ndiponso pa za nyumba za mafumu a Yuda. Zidzagwetsedwa, ndipo palibe chifukwa cholimbana ndi mitumbira ya nkhondo ya Ababuloni.

Original: `cho+limbana`

Proposed: `cho+limban+a`

Analysis:

- cho → class-7 nominal/agreement element
- limban → safest lexical/derived stem “fight”
- a → verbal final vowel in the embedded verbal form

Reason for change: The class-7 element is clear in the construction chifukwa cholimbana; the finite/infinitival paradigm supports final a, but -an- is retained in the safe stem.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0028 — sanawalenge

Context:

> Kodi Yehova sanawalenge iwo ngati munthu mmodzi? Ndi ake mʼthupi ndi mu mzimu. Nʼchifukwa chiyani ali mmodzi? Chifukwa Iye amafuna ana opembedza Mulungu. Motero samala moyo wako wauzimu, ndipo usakhal

Original: `sa+na+wa+lenge`

Proposed: `s+a+na+wa+leng+e`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- na → past/anterior TAM
- wa → class-2 object marker
- leng → lexical root “create”
- e → negative final vowel

Reason for change: The negative past template is s-a-na-OM-ROOT-e. The boundaries sa and lenge therefore conceal independently grammatical s+a and root+final-e structure.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; TAM issue.

### morph_dev_0029 — silingathe

Context:

> Ngati banja lili lochepa moti silingathe kudya nyama yonse ya nkhosa, ligawane ndi banja lomwe layandikana nalo nyumba. Mabanja adziwiretu chiwerengero cha anthu amene alipo pokonzekera zimenezi. Muwe

Original: `si+li+nga+the`

Proposed: `si+li+nga+th+e`

Analysis:

- si → negative marker
- li → subject/copular agreement element
- nga → potential/ability modal element
- th → lexical root “be able”
- e → negative/dependent final vowel

Reason for change: The inability construction supports a negative plus li-nga sequence; the final e is recoverable and the root is safely th-, not the syllable the.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; TAM issue.

### morph_dev_0030 — sadzawathandizanso

Context:

> Popeza iwowo sakhudzidwa ndi ntchito za Yehova, ndi zimene manja ake anazichita, Iye adzawakhadzula ndipo sadzawathandizanso.

Original: `sa+dza+wa+thandiza+nso`

Proposed: `s+a+dza+wa+thandiz+a+nso`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- dza → future TAM
- wa → class-2 object marker
- thandiz → lexical/causative-related stem “help”
- a → verbal final vowel
- nso → post-final additive/repetitive clitic

Reason for change: The negative allomorph is s+a, and the context supports a productive pre-stem plus object sequence. The final a precedes post-final nso.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; post-final/clitic issue.

### morph_dev_0032 — sindikhalanso

Context:

> Nʼchifukwa chake Aisraeli sangathe kulimbana ndi adani awo. Iwo anathawa pamaso pa adani awo chifukwa ndiwo oyenera kuwonongedwa. Ine sindikhalanso ndi inu pokhapokha mutawononga chilichonse choyenera

Original: `si+ndi+khala+nso`

Proposed: `si+ndi+khal+a+nso`

Analysis:

- si → negative marker
- ndi → 1SG subject/present marker
- khal → lexical root “stay/live”
- a → verbal final vowel
- nso → post-final additive/repetitive clitic

Reason for change: The negative first-person construction is clear; khala should be treated as khal-a with post-final nso outside the verb.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0033 — sizidzamvekanso

Context:

> Ziwawa sizidzamvekanso mʼdziko lako, bwinja kapena chiwonongeko sizidzapezeka mʼdziko lako, ndidzakhala malinga ako okuteteza ndipo udzanditamanda.

Original: `si+zi+dza+mveka+nso`

Proposed: `si+zi+dza+mvek+a+nso`

Analysis:

- si → negative marker
- zi → class-8 subject marker
- dza → future TAM
- mvek → lexical root “be heard”
- a → verbal final vowel
- nso → post-final “again/still” clitic

Reason for change: The negative/future subject sequence is grammatical and the finite paradigm recovers mvek-a before nso.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0034 — sidzapulumuka

Context:

> Zedekiya mfumu ya Yuda sidzapulumuka mʼmanja mwa Ababuloni, koma idzaperekedwa kwa mfumu ya ku Babuloni. Adzayankhula naye ndi kuonana naye maso ndi maso.

Original: `si+dza+pulumuka`

Proposed: `si+dza+pulumuk+a`

Analysis:

- si → negative marker
- dza → future TAM
- pulumuk → lexical/stative stem “escape”
- a → verbal final vowel

Reason for change: The current prefix analysis is sound, but the finite verb supports an independent final a boundary.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0035 — sadzalowamo

Context:

> Ndidzakuchotserani anthu amene anandigalukira ndi kundiwukira. Ngakhale ndidzawatulutsa mʼdziko limene akukhalamo, koma sadzalowamo mʼdziko la Israeli. Pamenepo mudzadziwa kuti Ine ndine Yehova.

Original: `sa+dza+lowa+mo`

Proposed: `s+a+dza+low+a+mo`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- dza → future TAM
- low → lexical root “enter”
- a → verbal final vowel
- mo → post-final locative element

Reason for change: The negative future template is s-a-dza-ROOT-a; mo is external locative material, not part of the lexical stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; post-final/clitic issue.

### morph_dev_0036 — silinakule

Context:

> Simei anali ndi ana aamuna 16 ndi ana aakazi 6, koma abale ake sanabereke ana ambiri; kotero banja lawo silinakule ngati anthu ena a ku Yuda.

Original: `si+li+na+kule`

Proposed: `si+li+na+kul+e`

Analysis:

- si → negative marker
- li → subject/agreement element
- na → past/anterior TAM
- kul → lexical root “grow”
- e → negative final vowel

Reason for change: The negative past/dependent form supports kul-e; the existing kule hides the independently recoverable negative final vowel.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0037 — sanakonde

Context:

> Abale athuwo anamugonjetsa ndi magazi a Mwana Wankhosa ndiponso mawu a umboni wawo. Iwo anadzipereka kwathunthu, moti sanakonde miyoyo yawo.

Original: `sa+na+konde`

Proposed: `s+a+na+kond+e`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- na → past TAM
- kond → lexical root “want/like”
- e → negative final vowel

Reason for change: Sanakonde follows the negative past template s-a-na-ROOT-e; kond-e is not a syllabic split of the root.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue.

### morph_dev_0038 — sikukupezekanso

Context:

> Motero kuweruza kolungama kwalekeka ndipo choonadi chili kutali ndi ife; kukhulupirika sikukupezekanso mʼmabwalo a milandu, ndipo kuona mtima sikukupezekanso mʼmenemo.

Original: `si+ku+ku+pezeka+nso`

Proposed: `si+ku+ku+pez+ek+a+nso`

Analysis:

- si → negative marker
- ku → impersonal/class-15 subject element
- ku → progressive/present TAM
- pez → lexical root “find”
- ek → stative/passive-like extension “be found”
- a → verbal final vowel
- nso → post-final “again/still” clitic

Reason for change: The double ku is grammatical pre-stem material in the impersonal/progressive construction, while pezek-a gives a supported derived stem and final vowel. The exact status of -ek- is less secure than its function.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; post-final/clitic issue; lexicalization/root uncertainty.

### morph_dev_0039 — mudzamumvera

Context:

> Mwanena motsimikiza lero lino kuti Yehova ndiye Mulungu wanu ndi kuti mudzayenda mʼnjira zake, kusunga malangizo, malamulo ndi zonse akukulamulani ndi kutinso mudzamumvera.

Original: `mu+dza+mu+mvera`

Proposed: `mu+dza+mu+mver+a`

Analysis:

- mu → 2PL subject marker
- dza → future TAM
- mu → class-1 object marker
- mver → lexical stem “hear/obey”
- a → verbal final vowel

Reason for change: The subject, future, and object markers are clear; mver-a is recoverable from the finite paradigm.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0040 — ndinawalamulira

Context:

> Ine sindidzachotsanso phazi la Aisraeli kuchoka mʼdziko limene ndawapatsa makolo ako, ngatitu iwowa adzasamalira kuchita chilichonse chimene ndinawalamulira za malamulo onse, malangizo ndi miyambo ime

Original: `ndi+na+wa+lamulira`

Proposed: `ndi+na+wa+lamulir+a`

Analysis:

- ndi → 1SG subject marker
- na → past TAM
- wa → class-2 object marker
- lamulir → safest lexical/derived stem “command”
- a → verbal final vowel

Reason for change: The old pre-stem parse is supported; lamulir- is retained as a safe stem rather than forcing an unsupported internal extension, and final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0041 — adzamubweretsa

Context:

> Pa nthawi yake Mulungu adzamubweretsa kwa ife. Mulungu ndi wodalitsika ndipo Iye yekha ndiye Wolamulira, Mfumu ya mafumu, Mbuye wa ambuye.

Original: `a+dza+mu+bweretsa`

Proposed: `a+dza+mu+bwer+ets+a`

Analysis:

- a → subject/agreement marker
- dza → future TAM
- mu → class-1 object marker
- bwer → lexical root “come”
- ets → causative extension “bring/cause to come”
- a → verbal final vowel

Reason for change: Bweretsa has the productive causative relation “bring/cause to come”; the future subject/object sequence is clear.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0042 — wolonjezedwa

Context:

> Iye anafunsa kuti, “Koma nanga inu mumati Ine ndine yani?” Petro anayankha kuti, “Mpulumutsi wolonjezedwa uja wa Mulungu.”

Original: `wo+lonje+zedwa`

Proposed: `wo+lonjez+edw+a`

Analysis:

- wo → class-1 relative/qualificative agreement
- lonjez → lexical/causative-related stem “promise”
- edw → passive extension
- a → verbal final vowel

Reason for change: The current lonje+zedwa split is not a morpheme boundary. The passive of lonjeza is lonjez-edw-a.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: syllabic oversegmentation; missing productive morphology; final-vowel issue.

### morph_dev_0044 — kuchipereka

Context:

> Chikho cha Farao chinali mʼmanja mwanga, ndipo ndinatenga mphesa, kupsinyira mu chikho cha Farao ndi kuchipereka mʼmanja mwake.”

Original: `ku+chi+pereka`

Proposed: `ku+chi+perek+a`

Analysis:

- ku → class-15 infinitive prefix
- chi → class-7 object marker
- perek → lexical stem “give/offer”
- a → verbal final vowel

Reason for change: The infinitive and object marker are clear; perek-a is the safest lexical-plus-final-vowel analysis.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0045 — mudzakhalako

Context:

> “ ‘Amenewa akhale malamulo ndi malangizo kwa inu nthawi zonse ndi ku mibado ya mʼtsogolo, kulikonse kumene mudzakhalako.

Original: `mu+dza+khala+ko`

Proposed: `mu+dza+khal+a+ko`

Analysis:

- mu → 2PL subject marker
- dza → future TAM
- khal → lexical root “stay/be”
- a → verbal final vowel
- ko → post-final locative/deictic element

Reason for change: The future verb ends in recoverable khal-a; ko is outside the verbal stem as locative/deictic material.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0046 — mumayitanira

Context:

> Ngati momwe mumayitanira pa tsiku la phwando, chimodzimodzinso mwandiyitanira zoopsa mbali zonse. Pa tsiku limene Yehova wakwiya palibe amene angathawe ndi kukhala ndi moyo; mdani wanga wawononga onse

Original: `mu+ma+yitanira`

Proposed: `mu+ma+yitanir+a`

Analysis:

- mu → 2PL subject marker
- ma → habitual/ongoing TAM
- yitanir → safest lexical/derived stem “call/invite”
- a → verbal final vowel

Reason for change: The habitual construction is clear. A possible applicative history of yitanir- is not needed for Level B; the final a is independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0047 — kunanenedwa

Context:

> “Munamva kuti kunanenedwa kwa anthu kale kuti, ‘Usaphe ndipo kuti aliyense amene apha munthu adzaweruzidwa.’

Original: `ku+na+nenedwa`

Proposed: `ku+na+nen+edw+a`

Analysis:

- ku → class-15 infinitive/impersonal subject element
- na → past/anterior TAM
- nen → lexical root “say”
- edw → passive extension
- a → verbal final vowel

Reason for change: The impersonal passive “it was said” supports ku-na-nen-edw-a; the passive and final vowel are not syllabic material.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0048 — mudzaziyese

Context:

> “ ‘Mukadzalowa mʼdzikomo ndi kudzala mtengo wa mtundu uliwonse wa zipatso, zipatso zakezo mudzaziyese ngati zodetsedwa. Ndiye kuti kwa zaka zitatu zidzakhale zoletsedwa kwa inu. Musadzazidye nthawi im

Original: `mu+dza+zi+yese`

Proposed: `mu+dza+zi+yes+e`

Analysis:

- mu → 2PL subject marker
- dza → future TAM
- zi → class-8 object marker
- yes → lexical root “test”
- e → subjunctive/dependent final vowel

Reason for change: The object marker and dependent final e are recoverable in the complement construction.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0049 — munkachitira

Context:

> Dzambatukani, dzambatukani! Valani zilimbe, Inu Yehova; dzambatukani, monga munkachitira masiku amakedzana, monga nthawi ya mibado yakale. Si ndinu kodi amene munaduladula Rahabe, amene munabaya chinj

Original: `mu+n+ka+chitira`

Proposed: `mu+nka+chit+ir+a`

Analysis:

- mu → 2PL subject marker
- nka → habitual/remote-past TAM element
- chit → lexical root “do”
- ir → applicative extension
- a → verbal final vowel

Reason for change: Nka- is treated as one established TAM element here, not n+ka. Chitir-a has a supported applicative relation, while the final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: incorrect grammatical parse; missing productive morphology; final-vowel issue.

### morph_dev_0050 — Kundipembedza

Context:

> Ambuye akuti, “Anthu awa amandipembedza Ine ndi pakamwa pawo, ndi kundilemekeza Ine ndi milomo yawo, koma mitima yawo ili kutali ndi Ine. Kundipembedza kwawo ndi kwa chiphamaso. Amandipembedza motsata

Original: `Ku+ndi+pembedza`

Proposed: `Ku+ndi+pembedz+a`

Analysis:

- ku → class-15 infinitive prefix
- ndi → 1SG object marker
- pembedz → lexical/causative-related stem “worship”
- a → verbal final vowel

Reason for change: The infinitive and object marker are clear; pembedz-a is the recoverable lexical-plus-final-vowel portion.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0051 — kuwadyetsa

Context:

> Ophunzira ake anayankha nati, “Kodi ndi kuti kuthengo kuno kumene munthu angapeze buledi okwanira kuwadyetsa?”

Original: `ku+wa+dyetsa`

Proposed: `ku+wa+dyets+a`

Analysis:

- ku → class-15 infinitive prefix
- wa → class-2 object marker
- dyets → causative stem “feed”
- a → verbal final vowel

Reason for change: Dyetsa has the clear causative relation “make/effect eating” → “feed”; the finite/infinitival final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0052 — idzachita

Context:

> Ndodo ya munthu amene ndamusankha idzachita maluwa potero ndidzaletsa madandawulo osatha a Aisraeli otsutsana nawe.”

Original: `i+dza+chita`

Proposed: `i+dza+chit+a`

Analysis:

- i → subject/agreement marker
- dza → future TAM
- chit → lexical root “do/make”
- a → verbal final vowel

Reason for change: The future template is clear and chita is recoverable as chit-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0053 — anamutenga

Context:

> Enoki anayenda ndi Mulungu; ndipo iye sanaonekenso chifukwa Mulungu anamutenga.

Original: `a+na+mu+tenga`

Proposed: `a+na+mu+teng+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- mu → class-1 object marker
- teng → lexical root “take”
- a → verbal final vowel

Reason for change: The object marker is independently grammatical and the final a is recoverable from tenga.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0054 — adapita

Context:

> Kenaka adapita ku sukulu ya sekondale ya Dedza kumene adapambana bwino kwambiri mayeso a Cambridge mchaka cha 1956.

Original: `a+da+pita`

Proposed: `a+da+pit+a`

Analysis:

- a → subject/agreement marker
- da → past/perfect TAM
- pit → lexical root “go”
- a → verbal final vowel

Reason for change: The current pre-stem analysis is retained; the finite paradigm supports a separate final a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0055 — anatengapo

Context:

> Tsono wantchito uja anatengapo ngamira khumi mwa ngamira za mbuye wake pamodzi ndi zinthu zabwino za mitundumitundu. Ndipo ananyamuka kupita ku mzinda wa Nahori, mʼdziko la Mesopotamiya.

Original: `a+na+tenga+po`

Proposed: `a+na+teng+a+po`

Analysis:

- a → subject/agreement marker
- na → past TAM
- teng → lexical root “take”
- a → verbal final vowel
- po → post-final locative/partitive element

Reason for change: Po follows the verbal final vowel; it is not part of the lexical stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0056 — chofuna

Context:

> Kodi mukufuna kuti Aigupto azinena kuti, ‘Munali ndi cholinga choyipa chofuna kuwaphera ku mapiri kuno ndi kuwawonongeratu pa dziko lapansi pamene munkawatulutsa ku Igupto kuja?’ Ayi, chonde mkwiyo wa

Original: `cho+funa`

Proposed: `cho+fun+a`

Analysis:

- cho → class-7 nominal/agreement element
- fun → lexical root “want/desire”
- a → final vowel of the embedded verbal form

Reason for change: The class-7 element in chofuna is clear. The embedded fun-a form supports a final-vowel boundary, though the whole construction is nominalized.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; noun-class issue.

### morph_dev_0057 — pita

Context:

> Tsiku lina Yehova anamuwuza Abramu kuti, “Tuluka mʼdziko lako. Siya abale ako ndi banja la abambo ako ndipo pita ku dziko limene ndidzakusonyeza.

Original: `pi+ta`

Proposed: `pit+a`

Analysis:

- pit → lexical root “go”
- a → imperative final vowel

Reason for change: Pi+ta has no independent morpheme evidence. The imperative pita is pit-a, not a split between two syllables.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: syllabic oversegmentation; final-vowel issue.

### morph_dev_0058 — inkayenda

Context:

> Pamene mfumu inkayenda pa khoma la mzindawo, mayi wina anafuwulira mfumuyo kuti, “Thandizeni mbuye wanga mfumu!”

Original: `i+n+ka+yenda`

Proposed: `i+nka+yend+a`

Analysis:

- i → subject/agreement marker
- nka → habitual/remote-past TAM element
- yend → lexical root “walk/go”
- a → verbal final vowel

Reason for change: Nka- is treated as one established TAM element here; n+ka would be an unsupported subdivision. The final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: incorrect grammatical parse; final-vowel issue; TAM issue.

### morph_dev_0059 — anabwerako

Context:

> Patapita masiku makumi anayi, anthu aja anabwerako kokazonda dziko lija.

Original: `a+na+bwera+ko`

Proposed: `a+na+bwer+a+ko`

Analysis:

- a → subject/agreement marker
- na → past TAM
- bwer → lexical root “come/return”
- a → verbal final vowel
- ko → post-final locative/deictic element

Reason for change: The finite final a precedes the external locative/deictic ko.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0060 — Nena

Context:

> “Nena kwa Alevi: ‘Pamene mupereka gawo labwino lopambana zonse, gawo limenelo lidzawerengedwa kwa inu ngati lochokera popunthira tirigu kapenanso kopsinyira mphesa.

Original: `Ne+na`

Proposed: `Nen+a`

Analysis:

- Nen → lexical root “say/tell”
- a → imperative final vowel

Reason for change: Ne+na is a syllabic split. The imperative nena is analyzed as nen-a, supported by the nena/nene paradigm.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: syllabic oversegmentation; final-vowel issue.

### morph_dev_0061 — tinachita

Context:

> ‘Zimene mudzayenera kunena kwa Yosefe ndi izi: Ndikukupempha kuti uwakhululukire abale ako cholakwa chawo ndi machimo awo, popeza anakuchitira zoyipa.’ Ndiye tsopano chonde tikhululukireni zolakwa zim

Original: `ti+na+chita`

Proposed: `ti+na+chit+a`

Analysis:

- ti → 1PL subject marker
- na → past TAM
- chit → lexical root “do”
- a → verbal final vowel

Reason for change: The past finite form supports chit-a; the older ti+na split is retained.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0062 — amaphunzira

Context:

> Moyo wanga umalakalaka Inu usiku wonse; nthawi yammawa ndimafunafuna Inu. Pamene muweruza dziko lapansi anthu amaphunzira kuchita chilungamo.

Original: `a+ma+phunzira`

Proposed: `a+ma+phunzir+a`

Analysis:

- a → subject/agreement marker
- ma → habitual/ongoing TAM
- phunzir → safest lexical/derived stem “learn/study”
- a → verbal final vowel

Reason for change: The habitual morphology is clear. Any deeper history of phunzir- is lexicalized enough that Level B keeps it as the safest stem.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0063 — mumakhala

Context:

> Ndipo iwowo adzawuza anthu okhala mʼdziko lino zimenezi. Anthuwa amva kale kuti Inu Yehova mumakhala pakati pa anthu amenewa ndi kuti Inuyo Yehova mwawaonekera maso ndi maso. Mtambo wanu umakhala pamw

Original: `mu+ma+khala`

Proposed: `mu+ma+khal+a`

Analysis:

- mu → 2PL subject marker
- ma → habitual/ongoing TAM
- khal → lexical root “stay/live”
- a → verbal final vowel

Reason for change: Mumakhala has a productive subject/TAM sequence and a recoverable final a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0065 — unalikuŵalira

Context:

> Mwa Iyeyo munali moyo, Edipo moyowo unalikuŵalira anthu.

Original: `u+na+li+ku+ŵalira`

Proposed: `u+na+li+ku+ŵalir+a`

Analysis:

- u → subject/agreement marker
- na → past TAM
- li → copular/progressive element
- ku → progressive/locative pre-stem element
- ŵalir → safest lexical/derived stem
- a → verbal final vowel

Reason for change: The pre-stem sequence is retained conservatively; the finite paradigm supports final a, while the internal analysis of ŵalir- is not forced.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0067 — adziŵa

Context:

> Patapita miyezi itatu, Danica ndi Kalli adziŵa kuti Charlie ndi weniweni ndipo nkhani yake idasokonezedwa ndi Lawrence, mphunzitsi wake wakale wa koleji.

Original: `a+dziŵa`

Proposed: `a+dziŵ+a`

Analysis:

- a → class-2 subject marker
- dziŵ → lexical root “know”
- a → verbal final vowel

Reason for change: Adziŵa is a finite verb; the root dziŵ- and final a are independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0069 — sanaloŵe

Context:

> Panthaŵi imodzimodziyo, sanaloŵe nawo m’nkhondo za Nkhondo ya Russo-Japan.

Original: `sa+na+loŵe`

Proposed: `s+a+na+loŵ+e`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- na → past/anterior TAM
- loŵ → lexical root “enter”
- e → negative/dependent final vowel

Reason for change: The negative past/dependent template is s-a-na-ROOT-e. Loŵe is not lo+ŵe or another syllabic split.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; TAM issue.

### morph_dev_0070 — ameneŵa

Context:

> Masiku ano chikhalidwe ndi mitundu dongosolo kusonyeza mtundu wa ankachita pakati European atsamunda, anthu ameneŵa, African akapolo ndi ana awo.

Original: `a+meneŵa`

Proposed: `a+mene+ŵa`

Analysis:

- a → class-2 agreement prefix
- mene → relative/demonstrative stem
- ŵa → proximal demonstrative/deictic element

Reason for change: The outer a- agreement and final -ŵa demonstrative element are supported by the demonstrative paradigm; splitting the remainder into syllables would not be justified.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: noun-class issue; granularity.

### morph_dev_0073 — chikuloŵera

Context:

> Pamene Mbuye Wamkulu alowa mu tulo ta Cristana , Cortana amamuuza kuti amuphonya, koma amamulimbikitsa pommuuza kuti, "Ndipatseni ine pamene mukufunikira ine." Ngati masewerawa atha kumapeto kwa zovut

Original: `chi+ku+loŵera`

Proposed: `chi+ku+loŵer+a`

Analysis:

- chi → class-7 subject/agreement marker
- ku → progressive/present TAM
- loŵer → safest lexical/derived stem “enter/return”
- a → verbal final vowel

Reason for change: The pre-stem morphology is clear; final a is recoverable, while the possible applicative history of loŵer- is not forced.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0074 — chigaŵanike

Context:

> Nzika ndi akuluakulu ena anafuna kuti chigawocho chigaŵanike, pamene wolamulira wamkulu sanali kutero.

Original: `chi+gaŵanike`

Proposed: `chi+gaŵan+ik+e`

Analysis:

- chi → class-7 subject/agreement marker
- gaŵan → safest lexical/derived stem “divide/share”
- ik → stative/inchoative extension “become divided”
- e → subjunctive/dependent final vowel

Reason for change: The subjunctive context and the gaŵanika “be divided” contrast support -ik- and final e; -an- remains inside the conservative stem.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0076 — yaikulu

Context:

> Pa 24 Oktoba 1964, Zambia inadziimira yekha ku United Kingdom ndi nduna yaikulu Kenneth Kaunda anakhala pulezidenti woyamba.

Original: `ya+i+kulu`

Proposed: `ya+ikulu`

Analysis:

- ya → associative concord
- ikulu → safest lexical adjectival stem “large/chief”

Reason for change: Ya+i+kulu treats the initial vowel of the adjectival stem as an unsupported independent piece. The safer analysis is ya+ikulu.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: syllabic oversegmentation; lexicalization/root uncertainty.

### morph_dev_0083 — anasankha

Context:

> Iye anasankha amuna odziwa bwino ntchito zawo ndipo anawayika kuti akhale atsogoleri, oyangʼanira anthu motere: atsogoleri a anthu 1,000, ena a anthu 500, ena a anthu makumi asanu ndi ena a anthu khum

Original: `a+na+sankha`

Proposed: `a+na+sankh+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- sankh → lexical root “choose”
- a → verbal final vowel

Reason for change: The past finite form supports sankh-a; no smaller internal split is needed.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0084 — ndikutsitsimutseni

Context:

> Ndikuganiza kuti nʼkoyenera ndikanali mu msasa uno, kuti ndikutsitsimutseni ndi kukukumbutsani,

Original: `ndi+ku+tsitsimutseni`

Proposed: `ndi+ku+tsitsimuts+e+ni`

Analysis:

- ndi → 1SG subject marker
- ku → 2PL object/agreement element
- tsitsimuts → lexical/reduplicated causative-related stem “refresh”
- e → subjunctive/dependent final vowel
- ni → plural/formal post-final marker

Reason for change: The current word-final material is better analyzed as final e plus plural/formal -ni; tsitsimuts- is kept intact rather than decomposed into syllables.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; post-final/clitic issue; lexicalization/root uncertainty.

### morph_dev_0085 — sichikugwira

Context:

> Kotero malamulo anu atha mphamvu, ndipo chilungamo sichikugwira ntchito. Anthu oyipa aposa olungama, kotero apotoza chilungamo.

Original: `si+chi+ku+gwira`

Proposed: `si+chi+ku+gwir+a`

Analysis:

- si → negative marker
- chi → class-7 subject/agreement marker
- ku → progressive/present TAM
- gwir → lexical root “hold/work”
- a → verbal final vowel

Reason for change: The negative progressive template is clear and the final a is independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0087 — Mudzateteza

Context:

> “Mudzateteza osalungama mpaka liti, ndi kukondera anthu oyipa?

Original: `Mu+dza+teteza`

Proposed: `Mu+dza+tetez+a`

Analysis:

- mu → 2PL subject marker
- dza → future TAM
- tetez → lexical stem “protect/defend”
- a → verbal final vowel

Reason for change: The future verb is mu-dza-tetez-a; Mu+dza+teteza omits a recoverable final vowel.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0088 — ananeneza

Context:

> Mwa lamulo la mfumu, anthu onse amene ananeneza Danieli aja anagwidwa ndi kukaponyedwa mʼdzenje la mikango, pamodzi ndi akazi awo ndi ana awo. Ndipo asanafike pansi pa dzenjelo, mikango inawawakha ndi

Original: `a+na+neneza`

Proposed: `a+na+nenez+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- nenez → safest lexical/derived stem “accuse/report”
- a → verbal final vowel

Reason for change: The past prefix sequence is clear and the final a is recoverable; nenez- is kept intact rather than forcing a deeper lexical split.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0089 — potengera

Context:

> Ngati banja lili lochepa moti silingathe kudya nyama yonse ya nkhosa, ligawane ndi banja lomwe layandikana nalo nyumba. Mabanja adziwiretu chiwerengero cha anthu amene alipo pokonzekera zimenezi. Muwe

Original: `po+tengera`

Proposed: `po+tenger+a`

Analysis:

- po → locative/relative pre-stem element
- tenger → safest lexical/derived stem “take/consider”
- a → verbal final vowel

Reason for change: The po construction is established, but potengera is partly lexicalized. Split only the clear external element and final a.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0090 — amalonjeza

Context:

> Mulungu si munthu kuti aname, kapena mwana wa munthu kuti asinthe maganizo ake. Kodi amayankhula koma osachita? Kodi amalonjeza koma osakwaniritsa?

Original: `a+ma+lonjeza`

Proposed: `a+ma+lonjez+a`

Analysis:

- a → subject/agreement marker
- ma → habitual/ongoing TAM
- lonjez → lexical/derived stem “promise”
- a → verbal final vowel

Reason for change: The habitual paradigm supports lonjez-a; no unsupported split of lonjez- is introduced.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0091 — akutchinjirize

Context:

> Pakuti adzalamulira angelo ake za iwe, kuti akutchinjirize mosamala pa njira zako zonse;

Original: `a+ku+tchinjirize`

Proposed: `a+ku+tchinjiriz+e`

Analysis:

- a → subject/agreement marker
- ku → subjunctive/relative pre-stem element
- tchinjiriz → safest lexical/derived stem “protect”
- e → subjunctive/dependent final vowel

Reason for change: The complement/relative context licenses final e; the internal history of tchinjiriz- is not needed for Level B.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0092 — umapewa

Context:

> Msewu wa munthu wowongoka mtima umapewa zoyipa; wopenyetsetsa kumene akupita amasunga moyo wake.

Original: `u+ma+pewa`

Proposed: `u+ma+pew+a`

Analysis:

- u → 2SG/class-3 subject marker
- ma → habitual/ongoing TAM
- pew → lexical root “avoid”
- a → verbal final vowel

Reason for change: The habitual finite form supports pew-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0093 — adzakuyikira

Context:

> Kodi udzanena chiyani pamene [Yehova] adzakuyikira anthu amene unkanena kuti ndi abale ako akukugonjetsa ndi kukulamulira? Kodi sudzamva zowawa ngati za mayi pa nthawi yake yochira?

Original: `a+dza+ku+yikira`

Proposed: `a+dza+ku+yik+ir+a`

Analysis:

- a → subject/agreement marker
- dza → future TAM
- ku → 2SG object marker
- yik → lexical root “put/place”
- ir → applicative extension
- a → verbal final vowel

Reason for change: Yikira has the productive applied relation “put for/onto”; the future and object-marker sequence is clear.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0094 — anyonga

Context:

> Iye amanyoza anthu otchuka ndipo anthu anyonga amawatha mphamvu.

Original: `a+nyonga`

Proposed: `a+nyong+a`

Analysis:

- a → subject/agreement marker
- nyong → lexical root “despise/mock”
- a → verbal final vowel

Reason for change: The finite verb supports nyong-a; a+nyonga leaves the final-vowel boundary implicit.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0098 — zalembedwera

Context:

> “Tidzabweranso nawo ku Nyumba ya Mulungu, kwa ansembe amene amatumikira ku Nyumba ya Mulungu ana athu aamuna oyamba kubadwa ndi ana angʼombe oyamba kubadwa monga zalembedwera mu Malamulo. Tidzaperekan

Original: `za+lembe+dwera`

Proposed: `za+lemb+edw+er+a`

Analysis:

- za → class-8 associative/agreement concord
- lemb → lexical root “write”
- edw → passive extension
- er → applicative extension
- a → verbal final vowel

Reason for change: The context supports “as written for/in” and the passive-plus-applicative sequence lemb-edw-er-a is recoverable. The old lembe+dwera split is not a morpheme analysis.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0099 — adzatitulutse

Context:

> Koma Paulo anati kwa asilikaliwo: “Iwo anatikwapula pa gulu la anthu asanatiweruze, ngakhale kuti ndife nzika za Chiroma natiponya mʼndende. Kodi tsopano akufuna kutitulutsa mwamseri? Ayi! Asiyeni abw

Original: `a+dza+ti+tulutse`

Proposed: `a+dza+ti+tuluts+e`

Analysis:

- a → subject/agreement marker
- dza → future TAM
- ti → 1PL object marker
- tuluts → causative stem “release/bring out”
- e → subjunctive/dependent final vowel

Reason for change: The object marker and the causative stem are clear; the complement context licenses final e.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0100 — sindilola

Context:

> Koma Farao anati, “Yehova ndani kuti ine ndimumvere ndi kulola Aisraeli kuti apite? Ine Yehova sindikumudziwa ndipo sindilola kuti Aisraeli apite.”

Original: `si+ndi+lola`

Proposed: `si+ndi+lol+a`

Analysis:

- si → negative marker
- ndi → 1SG subject/present marker
- lol → lexical root “allow”
- a → verbal final vowel

Reason for change: The negative first-person form supports lol-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0101 — yamilandu

Context:

> Swann anatulutsidwa m'ndende ya Alachua County Jail tsiku lomwelo ndipo adamuuza kuti akalumikizane ndi misonkhano yamilandu.

Original: `ya+milandu`

Proposed: `ya+mi+landu`

Analysis:

- ya → associative concord
- mi → class-4 noun prefix
- landu → lexical noun stem “case/lawsuit”

Reason for change: The class-4 prefix mi- is overt inside milandu; ya+milandu misses a productive noun-class boundary.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0102 — amavulala

Context:

> Anthu omwe anayesera kudzipha koma sanafe nthawi zambiri amavulala ngakhalenso kulumala kumene.

Original: `a+ma+vula+la`

Proposed: `a+ma+vulal+a`

Analysis:

- a → subject/agreement marker
- ma → habitual/ongoing TAM
- vulal → safest lexical/stative stem “be injured”
- a → verbal final vowel

Reason for change: Vula+la is not supported by an independent morpheme paradigm. Retain vulal- as the safest stem and recover the final a.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: syllabic oversegmentation; final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0103 — nʼzolekana

Context:

> “Monga momwe mlengalenga muli kutali ndi dziko lapansi, momwemonso zochita zanga nʼzolekana kutali ndi zochita zanu, ndipo maganizo anga ndi osiyana kutali ndi maganizo anu.

Original: `nʼ+zolekana`

Proposed: `nʼ+zo+lekan+a`

Analysis:

- nʼ → copular element
- zo → class-10 agreement element
- lekan → lexical/derived stem “differ/separate”
- a → final vowel of the qualificative/verb form

Reason for change: The class-10 agreement element zo- is independently grammatical and the final a is recoverable; lekan- is kept as the safe stem.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; noun-class issue.

### morph_dev_0105 — yachinkhoswe

Context:

> Kugwirizana kwa Charles ndi Camilla Parker Bowles kudalengezedwa pa 10 February 2005; adamupatsa mphete yachinkhoswe yomwe inali ya agogo ake.

Original: `ya+chinkhoswe`

Proposed: `ya+chi+nkhoswe`

Analysis:

- ya → associative concord
- chi → class-7 noun prefix
- nkhoswe → lexical noun stem “engagement/fiancé-related matter”

Reason for change: The class-7 prefix chi- is overt inside chinkhoswe and should not be hidden in the lexical remainder.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0108 — amatsamwitsidwa

Context:

> Mbewu zimene zinagwa pakati pa minga zikuyimira anthu amene amamva mawu, koma akamayenda mʼnjira zawo amatsamwitsidwa ndi zodandaulitsa za moyo uno, chuma ndi zosangalatsa, ndipo iwo samakhwima.

Original: `a+ma+tsamwitsidwa`

Proposed: `a+ma+tsamwits+idw+a`

Analysis:

- a → class-2 subject marker
- ma → habitual/ongoing TAM
- tsamwits → lexical/causative-related stem “cause to stumble/distress”
- idw → passive extension
- a → verbal final vowel

Reason for change: The phrase “be distressed/choked by” gives independent passive evidence for -idw-. Retain tsamwits- as the safe stem instead of attempting a deeper syllabic/root split.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0109 — anakupanga

Context:

> Yehova amene anakupanga iwe, anakuwumba iwe mʼmimba ya amayi ako, ndi amene adzakuthandiza iwe. Iye akuti, Usachite mantha, iwe Yakobo, mtumiki wanga, Yesuruni, amene ndinakusankha.

Original: `a+na+ku+panga`

Proposed: `a+na+ku+pang+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- ku → 2SG object marker
- pang → lexical root “make”
- a → verbal final vowel

Reason for change: The subject, past, and object marker are clear; pang-a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0112 — anakuchitirani

Context:

> Kodi alipo mulungu amene anayeserapo kudzitengera mtundu wa anthu kuwachotsa mu mtundu unzake mwa mayesero, zizindikiro zozizwitsa, nkhondo, komanso mwa mphamvu zake zopanda malire, kapena mwa zochita

Original: `a+na+ku+chitirani`

Proposed: `a+na+ku+chit+ir+a+ni`

Analysis:

- a → subject/agreement marker
- na → past TAM
- ku → object/agreement marker
- chit → lexical root “do”
- ir → applicative extension
- a → verbal final vowel
- ni → plural/formal post-final marker

Reason for change: The applied meaning “do for/to you” supports -ir-, and the final a plus -ni sequence is independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; post-final/clitic issue.

### morph_dev_0114 — titumize

Context:

> Tsono nonse munabwera kwa ine ndi kuti, “Tiyeni titumize anthu ayambe apita kuti akazonde dzikolo ndi kutibweretsera mawu pa za njira yomwe tidzere ndi za mizinda imene tikafikireko.”

Original: `ti+tumize`

Proposed: `ti+tumiz+e`

Analysis:

- ti → 1PL subject marker
- tumiz → lexical/causative stem “send”
- e → subjunctive/volitional final vowel

Reason for change: The “let us send” context licenses final e; tumiz- is retained as the safe stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0115 — nakamanganso

Context:

> Abenjamini anachitadi zimenezi. Mwa akazi amene ankavina aja anagwirapo ena, malingana ndi chiwerengero chawo, nawatenga kuti akhale akazi awo. Kenaka ananyamuka kubwerera ku dziko la kwawo, nakamanga

Original: `na+ka+manga+nso`

Proposed: `na+ka+mang+a+nso`

Analysis:

- na → sequential/conjunctive pre-stem element
- ka → consecutive/directional TAM element
- mang → lexical root “build”
- a → verbal final vowel
- nso → post-final additive/repetitive clitic

Reason for change: The pre-stem sequence is grammatical and the final a precedes post-final nso.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0118 — Ndidzamupangira

Context:

> Ndipo Yehova Mulungu anati, “Sibwino kuti munthu akhale yekha. Ndidzamupangira mnzake womuthandiza.”

Original: `Ndi+dza+mu+pangira`

Proposed: `Ndi+dza+mu+pang+ir+a`

Analysis:

- ndi → 1SG subject marker
- dza → future TAM
- mu → class-1 object marker
- pang → lexical root “make”
- ir → applicative extension
- a → verbal final vowel

Reason for change: The requested/helper meaning supports the applicative pang-ir-a relation, and the future subject/object sequence is clear.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0119 — anawapachika

Context:

> anapita kukatenga mafupa a Sauli ndi mwana wake Yonatani kwa anthu a ku Yabesi Giliyadi (iwo anawatenga mwamseri kuchoka pabwalo la ku Beti-Sani, kumene Afilisti anawapachika atapha Sauli ku Gilibowa)

Original: `a+na+wa+pachika`

Proposed: `a+na+wa+pachik+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- wa → class-2 object marker
- pachik → lexical/causative-related stem “hang”
- a → verbal final vowel

Reason for change: The object marker is clear; pachik- is retained as a safe stem and final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0120 — msonkhano

Context:

> Pa tsiku loyamba muzichita msonkhano wopatulika, ndipo winanso uzikhala pa tsiku lachisanu ndi chiwiri. Musamagwire ntchito masiku onsewa, koma ntchito yokonza chakudya yokha kuti aliyense adye. Izi n

Original: `msonkhano`

Proposed: `m+sonkhano`

Analysis:

- m → class-3 noun prefix
- sonkhano → lexical noun stem “assembly/meeting”

Reason for change: Msonkhano is a class-3 noun with an overt m- prefix; treating it as wholly unanalyzed misses a productive noun-class boundary.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0122 — Tikukulemberani

Context:

> Tikukulemberani zimenezi kuti chimwemwe chathu chikhale chathunthu.

Original: `Ti+ku+ku+lemberani`

Proposed: `Ti+ku+ku+lember+a+ni`

Analysis:

- Ti → 1PL subject marker
- ku → progressive/present TAM
- ku → 2PL object marker
- lember → applicative/derived stem “write for/to”
- a → verbal final vowel
- ni → plural/formal post-final marker

Reason for change: The two ku elements have distinct grammatical roles; lember-a and the post-final -ni are recoverable from the applicative construction.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue; post-final/clitic issue.

### morph_dev_0123 — ndisananene

Context:

> Akuluakulu sanadziwe kumene ndinapita kapena zimene ndimachita, chifukwa pa nthawiyi nʼkuti ndisananene kalikonse kwa Ayuda kapena ansembe, anthu olemekezeka kapena akuluakulu, kapena wina aliyense am

Original: `ndi+sa+na+nene`

Proposed: `ndi+sana+nen+e`

Analysis:

- ndi → 1SG subject marker
- sana → negative anterior/pre-stem TAM “not yet/before”
- nen → lexical root “say”
- e → dependent/subjunctive final vowel

Reason for change: The negative TAM sana is treated as one pre-stem element. The nena↔nene paradigm independently recovers nen+e, so ndi+sa+na+nene and ndi+sa+na+ne+ne are rejected.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; TAM issue; syllabic oversegmentation; final-vowel issue.

### morph_dev_0124 — ndidzawayeretsa

Context:

> Chigawo chachitatuchi ndidzachiyika pa moto; ndidzawayeretsa monga momwe amayeretsera siliva ndi kuwayesa monga momwe amayesera golide. Adzayitana pa dzina langa ndipo Ine ndidzawayankha; Ine ndidzane

Original: `ndi+dza+wa+yeretsa`

Proposed: `ndi+dza+wa+yer+ets+a`

Analysis:

- ndi → 1SG subject marker
- dza → future TAM
- wa → class-2 object marker
- yer → lexical root “clean”
- ets → causative extension “cleanse”
- a → verbal final vowel

Reason for change: Yeretsa is a productive causative/ factitive relation from yera; the object marker and future sequence are clear.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0125 — sizinachitikepo

Context:

> Munali chikondwerero chachikulu mu Yerusalemu, pakuti kuyambira masiku a Solomoni mwana wa Davide mfumu ya Israeli sizinachitikepo zotere mu Yerusalemu.

Original: `si+zi+na+chitike+po`

Proposed: `si+zi+na+chit+ik+e+po`

Analysis:

- si → negative marker
- zi → class-8 subject marker
- na → past/anterior TAM
- chit → lexical root “happen/do”
- ik → stative/inchoative extension
- e → negative/dependent final vowel
- po → post-final temporal/locative element

Reason for change: The negative past form and post-final po are clear; chit-ik-e is supported by the “happen/come about” derived stem.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue; post-final/clitic issue.

### morph_dev_0126 — zosafunika

Context:

> Ngakhale kuti madokotala ena amakonda kucheka kapena kung'amba njira yoberekera pofuna kuikulitsa, nthawi zambiri zimenezi zimakhala zosafunika.

Original: `zo+sa+funika`

Proposed: `zo+sa+funik+a`

Analysis:

- zo → class-10 agreement prefix
- sa → negative/privative prefix
- funik → lexical/derived stem “be needed”
- a → final vowel of the qualificative form

Reason for change: The class-10 agreement and privative sa- are independently grammatical; funik-a is safer than a syllabic split.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; noun-class issue.

### morph_dev_0128 — Khululukirani

Context:

> Ndipo khululukirani anthu anu amene akuchimwirani. Khululukirani zolakwa zonse akuchitirani ndipo mufewetse mitima ya amene anawagonjetsawo kuti awachitire chifundo;

Original: `Khululuki+ra+ni`

Proposed: `Khululuk+ir+a+ni`

Analysis:

- Khululuk → lexical root/stem “forgive”
- ir → applicative extension
- a → imperative final vowel
- ni → plural/formal post-final marker

Reason for change: Khululukirani is an imperative plural: khululuk-ir-a-ni. The old khululuki+ra+ni split follows orthographic chunks rather than the productive applicative and final-vowel pattern.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue; post-final/clitic issue; syllabic oversegmentation.

### morph_dev_0129 — namupeza

Context:

> Ndipo anabwerera kwa iye namupeza atayima pafupi ndi nsembe yake pamodzi ndi akuluakulu onse a Mowabu.

Original: `na+mu+peza`

Proposed: `na+mu+pez+a`

Analysis:

- na → sequential/conjunctive pre-stem element
- mu → class-1 object marker
- pez → lexical root “find”
- a → verbal final vowel

Reason for change: The object marker is clear and the final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0130 — atchulidwa

Context:

> Anthu amene atchulidwa mayina aja anatenga akapolowo, ndipo kuchokera pa zolanda ku nkhondo, anawaveka onse amene anali maliseche. Anawapatsa zovala ndi nsapato, chakudya ndi chakumwa ndi mankhwala. O

Original: `a+tchuli+dwa`

Proposed: `a+tchul+idw+a`

Analysis:

- a → subject/agreement marker
- tchul → lexical root “name/mention”
- idw → passive extension
- a → verbal final vowel

Reason for change: Atchulidwa is the transparent passive tchul-idw-a; tchuli+dwa is not a supported morpheme analysis.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue; syllabic oversegmentation.

### morph_dev_0131 — linatsimikiziranso

Context:

> Mu 2016, bungwe la United Nations General Assembly linatsimikiziranso kusavomereza kuphatikizikako ndikudzudzula "kukhala kwa kanthawi kochepa kwa gawo la Ukraine - Autonomous Republic of Crimea ndi m

Original: `lina+tsimikizira+nso`

Proposed: `li+na+tsimikizir+a+nso`

Analysis:

- li → class-5 subject/agreement marker
- na → past TAM
- tsimikizir → safest lexical/derived stem “confirm”
- a → verbal final vowel
- nso → post-final repetitive/additive clitic

Reason for change: The class-5 subject li- and past na- are independently recoverable; final a precedes nso. The lexicalized tsimikizir- stem is retained.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue; incorrect grammatical parse.

### morph_dev_0132 — kudzathira

Context:

> Salimenezeri mfumu ya ku Asiriya anabwera kudzathira nkhondo Hoseya amene anali pansi pa ulamuliro wake ndipo ankapereka msonkho kwa iyeyo.

Original: `ku+dza+thira`

Proposed: `ku+dza+thir+a`

Analysis:

- ku → class-15 infinitive prefix
- dza → directional/consecutive “come to” element
- thir → lexical stem “pour/launch”
- a → verbal final vowel

Reason for change: The ku+dza construction is supported in the infinitival directional context; thir-a is recoverable, while the idiomatic history of thira nkhondo is retained.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; TAM issue.

### morph_dev_0134 — kwamgwirizano

Context:

> Chifukwa chakukhazikika kwamgwirizano kapena mgwirizano pakati pa boma la Rhodesia ndi zipani zochepa zaku Africa, zomwe sizinatengeredwe chifukwa chake sizinachite nawo nkhondo, zisankho zidachitika 

Original: `kwa+mgwirizano`

Proposed: `kwa+m+gwirizano`

Analysis:

- kwa → associative/locative concord
- m → class-3 noun prefix
- gwirizano → lexical noun stem “agreement/union”

Reason for change: The class-3 m- prefix is overt inside mgwirizano and should not be absorbed into the lexical remainder.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0137 — uchitira

Context:

> Inu munagawa nyanja anthu anu akupenya, kotero kuti anadutsa powuma, koma munamiza mʼmadzi akuya anthu amene ankawalondola monga mmene uchitira mwala mʼmadzi ozama.

Original: `u+chitira`

Proposed: `u+chit+ir+a`

Analysis:

- u → subject/agreement marker
- chit → lexical root “do”
- ir → applicative extension
- a → verbal final vowel

Reason for change: The context supports the applied relation uchitira “as you do”; -ir- and final a are recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0138 — zikadzatha

Context:

> Yehova akuti, “Zaka 70 za ku Babuloni zikadzatha, ndidzabwera kudzakuchitirani zabwino zonse zimene ndinakulonjezani zija, ndipo ndidzakubwezerani ku malo ano.

Original: `zi+ka+dza+tha`

Proposed: `zi+ka+dza+th+a`

Analysis:

- zi → class-8 subject marker
- ka → conditional/temporal TAM
- dza → future/remote-future TAM
- th → lexical root “end/finish”
- a → final vowel

Reason for change: The conditional/future sequence is grammatical; th-a is the lexical-plus-final-vowel portion.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; TAM issue.

### morph_dev_0140 — zidzakusokonezani

Context:

> Zimene muzidzaziona zidzakusokonezani mitu.

Original: `zi+dza+ku+sokoneza+ni`

Proposed: `zi+dza+ku+sokonez+a+ni`

Analysis:

- zi → class-8 subject marker
- dza → future TAM
- ku → 2SG object marker
- sokonez → lexical/causative-related stem “confuse”
- a → verbal final vowel
- ni → plural/formal post-final marker

Reason for change: The future and object marker are clear; the final a precedes the post-final formal/plural marker -ni.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0141 — sakakhulupirira

Context:

> Koma ngati sakakhulupirira zizindikiro ziwiri izi kapena kukumvera, ukatunge madzi a mu mtsinje wa Nailo ndi kuwathira pa mtunda powuma ndipo madziwo adzasanduka magazi.”

Original: `sa+ka+khulupirira`

Proposed: `s+a+ka+khulupirir+a`

Analysis:

- s → negative allomorph
- a → subject/agreement marker
- ka → conditional TAM
- khulupirir → lexical/derived stem “believe/trust”
- a → verbal final vowel

Reason for change: The negative conditional template is s-a-ka-ROOT-a; khulupirir- is retained as the safe lexical stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; TAM issue.

### morph_dev_0142 — anandibweretsera

Context:

> “Kodi zimenezi mukuziyesa zachabe, inu nonse mukudutsa? Yangʼanani ndipo muone. Kodi pali mavuto ofanana ndi amene andigwerawa, amene Ambuye anandibweretsera pa tsiku la ukali wake?

Original: `a+na+ndi+bweretsera`

Proposed: `a+na+ndi+bwer+ets+er+a`

Analysis:

- a → subject/agreement marker
- na → past TAM
- ndi → 1SG object marker
- bwer → lexical root “come”
- ets → causative extension “bring”
- er → applicative extension “bring for/to”
- a → verbal final vowel

Reason for change: The lexical family bwer-a → bwer-ets-a → bwer-ets-er-a supports both productive extensions in the context “brought upon me.”

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0143 — zidatumizidwa

Context:

> Zithunzi zosagwirizana ndi zomwe zidachitikazi zidatumizidwa ndi The Guardian pa YouTube, yomwe idalandira mawonedwe opitilira 50 miliyoni mkati mwa maola 24, kukhala imodzi mwamavidiyo omwe amawonedw

Original: `zi+da+tumizidwa`

Proposed: `zi+da+tumiz+idw+a`

Analysis:

- zi → class-8 subject marker
- da → past/perfect TAM
- tumiz → lexical/causative stem “send”
- idw → passive extension
- a → verbal final vowel

Reason for change: The passive “were sent” supports tumiz-idw-a; the old tumizidwa block hides the passive and final vowel.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0144 — wachisomo

Context:

> “Ndipo pa nyumba ya Davide ndi pa anthu okhala mu Yerusalemu ndidzakhuthulirapo mzimu wachisomo ndi wopemphera. Iwo adzandiyangʼana Ine, amene anamubaya, ndipo adzamulirira kwambiri monga momwe munthu

Original: `wa+chisomo`

Proposed: `wa+chi+somo`

Analysis:

- wa → associative concord
- chi → class-7 noun prefix
- somo → lexical noun stem “grace/kindness”

Reason for change: The class-7 prefix chi- is overt in chisomo and is independently recoverable after the associative wa-.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0148 — ndidzadziwa

Context:

> Ine ndipempha mtsikana wina kuti, ‘Chonde tula mtsuko wako kuti ndimweko madzi.’ Tsono iye akayankha kuti ‘Imwani,’ ndipo ndidzapatsanso ngamira zanu madziwo, ameneyo akhale mkazi amene mwasankhira mt

Original: `ndi+dza+dziwa`

Proposed: `ndi+dza+dziw+a`

Analysis:

- ndi → 1SG subject marker
- dza → future TAM
- dziw → lexical root “know”
- a → verbal final vowel

Reason for change: The first-person future form supports dziw-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0150 — Anaphunzira

Context:

> Anaphunzira zamalamulo ku University of Fort Hare komanso University of Witwatersrand asanagwire ntchito ngati loya ku Johannesburg.

Original: `A+na+phunzira`

Proposed: `A+na+phunzir+a`

Analysis:

- A → subject/agreement marker
- na → past TAM
- phunzir → safest lexical/derived stem “study/learn”
- a → verbal final vowel

Reason for change: The past form is clear. Phunzir- is retained as the safest stem rather than imposing an uncertain internal -ir- analysis; final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0151 — tilimbane

Context:

> Tipatseni chithandizo kuti tilimbane ndi mdani wathu, pakuti thandizo lochokera kwa munthu ndi lopanda phindu.

Original: `ti+limbane`

Proposed: `ti+limban+e`

Analysis:

- ti → 1PL subject marker
- limban → safest lexical stem “fight”
- e → subjunctive/volitional final vowel

Reason for change: The purpose/volitional context licenses final e; limb-an is retained as a safe stem rather than assumed reciprocal.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0152 — ukatenge

Context:

> Ndipo ukatenge botololi ndi kuthira mafuta pa mutu wake ndipo ukanene kuti, ‘Yehova akuti, Ine ndikudzoza iwe kukhala mfumu ya Israeli.’ Kenaka ukatsekule chitseko ndi kuthawa ndipo usakachedwe!”

Original: `u+ka+tenge`

Proposed: `u+ka+teng+e`

Analysis:

- u → 2SG subject marker
- ka → consecutive/go-and marker
- teng → lexical root “take”
- e → subjunctive/dependent final vowel

Reason for change: The command sequence supports teng+e; the current tenge stem hides the final-vowel boundary.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0156 — yopserezayo

Context:

> “ ‘Koma ngati chopereka cha nsembe yopserezayo ndi nkhosa kapena mbuzi kuchokera pa ziweto zake, munthuyo apereke yayimuna yopanda chilema.

Original: `yo+psereza+yo`

Proposed: `yo+pserez+a+yo`

Analysis:

- yo → class-9 relative/qualificative agreement
- pserez → safest lexical stem “burn”
- a → verbal final vowel
- yo → demonstrative/deictic element

Reason for change: The relative/qualificative construction supports the outer yo elements; final a should not remain inside psereza.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; noun-class issue.

### morph_dev_0157 — ndidzakhazika

Context:

> Mu mtima mwako unkanena kuti, “Ndidzakwera mpaka kumwamba; ndidzakhazika mpando wanga waufumu pamwamba pa nyenyezi za Mulungu; ndidzakhala pa mpando waufumu pa phiri losonkhanirako, pamwamba penipeni 

Original: `ndi+dza+khazika`

Proposed: `ndi+dza+khazik+a`

Analysis:

- ndi → 1SG subject marker
- dza → future TAM
- khazik → lexical stem “establish/set”
- a → verbal final vowel

Reason for change: The current future parse is sound; final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0158 — mukawuze

Context:

> Mngeloyo anati, “Pitani, ku mabwalo a Nyumba ya Mulungu ndipo mukawuze anthu uthenga onse wamoyo watsopanowu.”

Original: `mu+ka+wuze`

Proposed: `mu+ka+wuz+e`

Analysis:

- mu → 2PL subject marker
- ka → consecutive/go-and marker
- wuz → lexical root “tell”
- e → subjunctive/dependent final vowel

Reason for change: The command sequence licenses wuz+e.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0160 — kubwezera

Context:

> Paja ife pobwera kuchokera ku Kanaani tinatenga ndalama kubwezera zimene tinazipeza mʼmatumba mwathu. Ndiye pali chifukwa chanji kuti tikabe siliva kapena golide mʼnyumba mwa mbuye wanu?

Original: `ku+bwezera`

Proposed: `ku+bwezer+a`

Analysis:

- ku → class-15 infinitive prefix
- bwezer → safest lexical/derived stem “return/repay”
- a → verbal final vowel

Reason for change: The lexical family may involve an applied -er, but the safe Level-B stem is bwezer- and final a is recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0163 — zidzadyera

Context:

> Mʼmbulu ndi mwana wankhosa wamkazi zidzadyera pamodzi. Mkango udzadya udzu monga ngʼombe, koma fumbi ndiye chidzakhale chakudya cha njoka. Pa phiri langa lopatulika sipadzakhala chinthu chopweteka kap

Original: `zi+dza+dyera`

Proposed: `zi+dza+dyer+a`

Analysis:

- zi → class-10 subject marker
- dza → future TAM
- dyer → safest lexical/derived stem “eat/graze”
- a → verbal final vowel

Reason for change: The current outer parse is plausible; final a is recoverable while any applied history of dyer- remains uncertain.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0166 — Mdima

Context:

> Mdima ndi mthunzi wa imfa zikhale pa tsiku limeneli; mtambo uphimbe tsikuli; mdima wandiweyani udetse kuwala kwake.

Original: `Mdima`

Proposed: `M+dima`

Analysis:

- M → class-3 noun prefix
- dima → lexical noun stem “darkness”

Reason for change: Mdima is a class-3 noun with an overt m- prefix; sentence-initial capitalization does not erase the noun-class boundary.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0168 — wokunthidwa

Context:

> “Iwe mzinda wozunzika, wokunthidwa ndi namondwe ndiponso wopanda wokutonthoza, Ine ndidzakongoletsa miyala yako. Maziko ako ndidzamanga ndi miyala ya safiro.

Original: `wo+kunthidwa`

Proposed: `wo+kunth+idw+a`

Analysis:

- wo → class-1 relative/qualificative agreement
- kunth → lexical root “pound/strike”
- idw → passive extension
- a → verbal final vowel

Reason for change: The context is an adjectival passive “battered by a storm”; passive -idw- and final a are recoverable.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0169 — ikuphatikizira

Context:

> Ntchito ya WHO ikuphatikizira kulimbikitsa chisamaliro chaumoyo wa anthu onse, kuwunika zoopsa zaumoyo wa anthu, kuwongolera mayankho pakagwa zadzidzidzi, komanso kulimbikitsa thanzi.

Original: `i+ku+phatikizira`

Proposed: `i+ku+phatikizir+a`

Analysis:

- i → subject agreement
- ku → present/progressive TAM
- phatikizir → safest lexical/derived stem “include”
- a → verbal final vowel

Reason for change: The current outer parse is sound; final a is recoverable, while any internal applied history is not forced.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0171 — ndikanakupatsa

Context:

> Ndinakupatsanso banja la mbuye wako ndiponso akazi a mbuye wako mʼmanja mwako. Ine ndinakupatsanso banja la Israeli ndi Yuda. Ndipo ngati zinthu zonse izi zinali zochepa, Ine ndikanakupatsa zambiri.

Original: `ndi+ka+na+ku+patsa`

Proposed: `ndi+ka+na+ku+pats+a`

Analysis:

- ndi → 1SG subject marker
- ka → conditional TAM
- na → anterior/past TAM
- ku → 2SG object marker
- pats → lexical stem “give”
- a → verbal final vowel

Reason for change: The conditional/anterior sequence and object marker are clear; final a is missing.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0172 — ukwapule

Context:

> Chilango chakonzedwa kale kuti chigwere anthu oyipa, ndipo mkwapulo wakonzedwa kale kuti ukwapule misana ya anthu opusa.

Original: `u+kwapule`

Proposed: `u+kwapul+e`

Analysis:

- u → subject/agreement marker
- kwapul → lexical root/stem “whip”
- e → subjunctive/dependent final vowel

Reason for change: The context licenses a dependent final e; the root is kwapul-, not an additional single-character fragment.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0173 — Kwezani

Context:

> Ndipo anati, “Kwezani mbendera ya Yehova. Yehova adzachitabe nkhondo ndi mibado yonse ya Aamaleki.”

Original: `Kweza+ni`

Proposed: `Kwez+a+ni`

Analysis:

- Kwez → lexical stem “raise”
- a → imperative final vowel
- ni → plural/formal imperative/post-final marker

Reason for change: The imperative plural/formal marker is post-final; the final a should be kept as its own licensed verbal slot.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0174 — lidasungidwa

Context:

> Aphungu adalipira msonkho m'buku lachitonthozo lomwe lidasungidwa ku House of Commons Library, komanso ku Westminster Hall ndi Portcullis House.

Original: `li+da+sungidwa`

Proposed: `li+da+sung+idw+a`

Analysis:

- li → class-5 subject/relative agreement
- da → past/perfect TAM
- sung → lexical root “keep/store”
- idw → passive extension
- a → verbal final vowel

Reason for change: The relative clause describes a book that was kept/stored. The passive sung-idw-a is recoverable, while li-da supplies the class-5 subject and past/perfect morphology.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0186 — sichidzikuza

Context:

> Chikondi nʼcholeza mtima, chikondi nʼchokoma mtima, chilibe nsanje, sichidzikuza, sichidzitamandira.

Original: `si+chi+dzi+kuza`

Proposed: `si+chi+dzi+kuz+a`

Analysis:

- si → negative marker
- chi → class-7 subject/agreement marker
- dzi → reflexive object marker
- kuz → lexical root “boast/exalt”
- a → verbal final vowel

Reason for change: The reflexive dzi- is grammatical pre-stem material and the finite negative form supports kuz-a.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0187 — mwayankhulawa

Context:

> Hezekiya anayankha kuti, “Mawu a Yehova amene mwayankhulawa ndi abwino. Pakuti iye ankaganiza kuti, ‘Kodi pa nthawi yanga sipadzakhala mtendere ndi bata?’ ”

Original: `mwa+yankhula+wa`

Proposed: `mwa+yankhul+a+wa`

Analysis:

- mwa → 2PL subject/perfect marker
- yankhul → lexical root “speak”
- a → verbal final vowel
- wa → relative/anaphoric post-final element

Reason for change: The relative construction supports a verbal final a before the following relative/anaphoric -wa; yankhul- is retained as the safe stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; post-final/clitic issue.

### morph_dev_0188 — kuwabalalitsira

Context:

> “Iwo adzadziwa kuti Ine ndine Yehova, ndikadzawamwaza pakati pa anthu a mitundu ina ndi kuwabalalitsira ku mayiko ena.

Original: `ku+wa+balalitsira`

Proposed: `ku+wa+balalits+ir+a`

Analysis:

- ku → class-15 infinitive prefix
- wa → class-2 object marker
- balalits → causative stem “scatter”
- ir → applicative extension
- a → verbal final vowel

Reason for change: Balalitsira has a supported causative-plus-applicative relation, and the infinitive/object sequence is clear.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0189 — itamaliza

Context:

> Tottenham yapambana 4-3 pamapenalty kick itamaliza 2-2 pamagulu onse.

Original: `i+ta+maliza`

Proposed: `i+ta+maliz+a`

Analysis:

- i → subject agreement
- ta → temporal/dependent pre-stem element “after/when”
- maliz → lexical stem “finish”
- a → verbal final vowel

Reason for change: The temporal ta construction is clear and final a is independently recoverable.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; TAM issue.

### morph_dev_0190 — zimawonjezeka

Context:

> 47 Pamene midadada yatsopano imakumbidwa nthawi zonse, zovuta zosintha chipika zimawonjezeka pamene nthawi ikupita ndipo chiwerengero cha midadada yotsatira (yotchedwanso zitsimikiziro za chipikacho) 

Original: `zi+ma+wonjezeka`

Proposed: `zi+ma+wonjez+ek+a`

Analysis:

- zi → class-10 subject marker
- ma → habitual/ongoing TAM
- wonjez → lexical/causative-related stem “increase”
- ek → stative/inchoative extension “become more”
- a → verbal final vowel

Reason for change: Wonjeza versus wonjezeka gives a good compositional stative/inchoative contrast, but deeper root structure remains conservative.

Evidence: Mchombo 2004, ch. 5 §§5.5–5.7, pp. 70–89 (productive extensions); Mchombo 2005/2007, pp. 204–218 (extension functions and argument structure); clear lexical/valency paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: missing productive morphology; final-vowel issue; lexicalization/root uncertainty.

### morph_dev_0191 — yampoto

Context:

> Monga momwe mphepo yampoto imabweretsera mvula, chonchonso mjedu umadzetsa mkwiyo.

Original: `ya+mpoto`

Proposed: `ya+m+poto`

Analysis:

- ya → associative concord
- m → class-3 noun prefix
- poto → lexical noun stem “north”

Reason for change: Mpoto is a class-3 noun; the current ya+mpoto boundary misses the overt m- class prefix.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue.

### morph_dev_0192 — wasungunulidwa

Context:

> Siliva wako wasanduka wachabechabe, vinyo wako wabwino wasungunulidwa ndi madzi.

Original: `wa+sungunulidwa`

Proposed: `wa+sungunul+idw+a`

Analysis:

- wa → subject/agreement element
- sungunul → lexical stem “dilute/melt”
- idw → passive extension
- a → verbal final vowel

Reason for change: The context explicitly gives a passive “was diluted”; -idw- and final a are clear.

Evidence: Mchombo 2004, ch. 6 §§6.1–6.2, pp. 90–95 (passive); Mchombo 2007, pp. 505–508 (passive -idw-/-edw-); clear passive argument-structure reading; sentence context.

Confidence: **HIGH**

Disagreement type: missing productive morphology; final-vowel issue.

### morph_dev_0193 — linkatchedwa

Context:

> Tsiku la Chikumbutso cha Dziko (Khmer: ទិវាជាតិនៃការចងចាំ, romanized: Tivea Cheate nei kar Changcham), lomwe kale linkatchedwa National Day of Hatred, lomwe limachitika pachaka pa Meyi 20, ku Cambodia

Original: `li+nka+tchedwa`

Proposed: `li+nka+tchedw+a`

Analysis:

- li → class-5 subject/relative agreement
- nka → used-to/past habitual TAM element
- tchedw → passive stem “be called”
- a → verbal final vowel

Reason for change: The old pre-stem parse is plausible; final a is recoverable and tchedw- is retained as a safe passive stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue; TAM issue.

### morph_dev_0194 — natisamala

Context:

> Pafupi ndi malowa panali munda wa Popliyo, mkulu wa boma la pa chilumbacho. Iye anatilandira natisamala bwino masiku atatu.

Original: `na+ti+samala`

Proposed: `na+ti+samal+a`

Analysis:

- na → sequential/conjunctive element
- ti → 1PL object marker
- samal → lexical root “care for/look after”
- a → verbal final vowel

Reason for change: The current host and object marker are clear; final a is missing.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0195 — sanayipeze

Context:

> Rakele anati kwa abambo ake, “Pepanitu musandikwiyire mbuye wanga chifukwa choti sinditha kuyimirira pamaso panu chifukwa ndili kumwezi.” Choncho Labani anafunafuna koma sanayipeze milungu ija.

Original: `sa+na+yi+peze`

Proposed: `s+a+na+yi+pez+e`

Analysis:

- s → reduced negative allomorph
- a → subject marker
- na → past TAM
- yi → class-9 object marker
- pez → lexical root “find”
- e → negative/dependent final vowel

Reason for change: The negative plus subject sequence is recoverable and peze contains the licensed negative final e.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: incorrect grammatical parse; final-vowel issue; TAM issue.

### morph_dev_0197 — Anawapitikitsabe

Context:

> Koma ena anatembenuka nathawira ku chipululu ku thanthwe la Rimoni. Mwa iwowa Aisraeli anapha Abenjamini 5,000 mʼmisewu yayikulu. Anawapitikitsabe Abenjaminiwo mpaka kufika ku Gidomu ndi kuphanso ena 

Original: `A+na+wa+pitikitsa+be`

Proposed: `A+na+wa+pitikits+a+be`

Analysis:

- A → class-2 subject marker
- na → past TAM
- wa → class-2 object marker
- pitikits → safest lexical/derived stem “pursue”
- a → verbal final vowel
- be → post-final “still/continuing” clitic

Reason for change: The current -be clitic is correctly external, but final a is recoverable; pitikits- remains a conservative stem.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**

Disagreement type: final-vowel issue; post-final/clitic issue; lexicalization/root uncertainty.

### morph_dev_0199 — amuyike

Context:

> Ngati chikanga cha pa khungulo chikuoneka choyera, ndipo kuya kwake sikukuonekera kuti kwapitirira khungu ndi ubweya wake pamalopo sunasanduke woyera, wansembe amuyike wodwalayo padera kwa masiku asan

Original: `a+mu+yike`

Proposed: `a+mu+yik+e`

Analysis:

- a → subject marker
- mu → class-1 object marker
- yik → lexical root “put/place”
- e → subjunctive/dependent final vowel

Reason for change: The command/subjunctive context licenses yik+e; no extra syllabic split is justified.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: final-vowel issue.

### morph_dev_0200 — laulendowu

Context:

> Iye anali ndi dzina laulendowu.

Original: `la+ulendo+wu`

Proposed: `la+u+lendo+wu`

Analysis:

- la → class-5 associative concord
- u → class-14 noun prefix
- lendo → lexical noun stem “journey/travel”
- wu → class-14 demonstrative/deictic element

Reason for change: The current analysis misses the overt class-14 prefix u- inside ulendo.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (noun classes and agreement); Corbett & Mtenje 1987, pp. 1–38 (Chichewa agreement system); clear class/agreement paradigm; sentence context.

Confidence: **HIGH**

Disagreement type: noun-class issue; granularity.

## B. Uncertain items

These records should not be converted into forced gold analyses without native-speaker or trained-linguist adjudication.

### morph_dev_0043 — pakatipa

Context:

> Pafupifupi anthu 10 mpaka 15 pa 100 aliwonse amene asonyeza zizindikiro za matendawa, zizindikirozo zimayambiranso pakatipa miyezi 6 kuchokera pamene tizilombo ta matendawa tinalowa m'thupi.

Original: `pa+katipa`

Provisional: `pa+katipa`

Analysis:

- pa → possible locative/prepositional element
- katipa → safest lexical remainder; internal structure unresolved

Unresolved issue: The context does not establish whether pa- is a productive locative prefix or part of a lexicalized adverb. Do not split katipa by syllable shape.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **LOW**; disagreement type: locative issue; lexicalization/root uncertainty; language/quality issue.

### morph_dev_0064 — m’Chicheŵa

Context:

> Hastings Kamuzu Banda." Dzina lakuti Ngwazi limatanthauza “mkulu wa mafumu” (litali kwenikweni, “mkango waukulu,” kapena, ena anganene, “wogonjetsa”) m’Chicheŵa.

Original: `m’+Chicheŵa`

Provisional: `m’+Chicheŵa`

Analysis:

- m’ → contracted mu-/locative preposition
- Chicheŵa → lexical language-name stem

Unresolved issue: The contraction is orthographically clear, but the degree to which m’ is morphologically independent in this phrase should be confirmed by a native speaker; do not split the language name.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **LOW**; disagreement type: locative issue; language/quality issue.

### morph_dev_0071 — M’nthaŵi

Context:

> M’nthaŵi imene anali kumeneko, anagwirizana ndi katswiri wina wa chinenero cha Afro-America Mark Hanna Watkins, akumapereka chidziŵitso cha chinenero chake cha Chichewa.

Original: `M’+nthaŵi`

Provisional: `M’+nthaŵi`

Analysis:

- M’ → contracted mu-/locative element
- nthaŵi → lexical noun stem “time”

Unresolved issue: The contraction M’ is orthographically visible, but whether it should receive a standalone benchmark boundary depends on the treatment of locative prepositions/clitics in the annotation manual.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **LOW**; disagreement type: locative issue; language/quality issue.

### morph_dev_0078 — kumadzulo

Context:

> Zidzukulu zako zidzachuluka ngati fumbi la pa dziko lapansi ndipo zidzabalalikira kumadzulo ndi kummawa, kumpoto ndi kummwera. Anthu onse adzalandira madalitso kudzera mwa iwe ndi zidzukulu zako.

Original: `ku+madzulo`

Provisional: `ku+madzulo`

Analysis:

- ku → locative/directional preposition or prefix
- madzulo → lexical temporal/directional noun stem “west/evening”

Unresolved issue: Ku- is plausible in the directional construction, but ku-madzulo may be lexicalized as a fixed directional expression; retain the split provisionally pending native-speaker judgment.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **LOW**; disagreement type: locative issue; lexicalization/root uncertainty.

### morph_dev_0106 — m'gululi

Context:

> Chifukwa cha kalendala yachitukuko cha mpikisano wa CAF mu 2018-19, magulu okwana 20 omwe ali m'gululi adzagawidwa m'magulu awiri a magulu khumi, limodzi la magulu ochokera kumpoto ndi limodzi la magu

Original: `m'+gulu+li`

Provisional: `m'+gulu+li`

Analysis:

- mʼ → contracted mu-/locative preposition
- gulu → lexical noun stem “group”
- li → locative/proximal demonstrative element

Unresolved issue: The construction is plausibly mu-gulu-li “in this group,” but the contracted locative and final demonstrative require a consistent native-speaker decision.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **MEDIUM**; disagreement type: locative issue.

### morph_dev_0136 — aloe

Context:

> “Monga zigwa zotambalala, monga minda mʼmbali mwa mtsinje, monga aloe wodzalidwa ndi Yehova, monga mikungudza mʼmbali mwa madzi.

Original: `aloe`

Provisional: `aloe`

Analysis:

- aloe → loan/plant-name lexical item; internal morphology not established

Unresolved issue: The context is Chichewa but aloe is a loan or citation plant name with no secure productive Chichewa morphology in the item. A native speaker should decide whether to keep it as a whole loan or exclude it.

Evidence: Paas 2016, Oxford Chichewa Dictionary (lexical evidence); Maxson, Common Chichewa Verbs with Their Common Variants (secondary lexical-family evidence); Mchombo 2004, ch. 5/6 (extension diagnostics where relevant); sentence context.

Confidence: **LOW**; disagreement type: language/quality issue; lexicalization/root uncertainty.

### morph_dev_0155 — watiwona

Context:

> 'watiwona'

Original: `wa+ti+wona`

Provisional: `wa+ti+won+a`

Analysis:

- wa → class-2 subject marker
- ti → 1PL object marker
- won → lexical root “see”
- a → verbal final vowel

Unresolved issue: The morphology is plausible, but the context contains only the isolated token; the clause-level TAM/interpretation cannot be confirmed.

Evidence: Mchombo 2004, ch. 5 §§5.2–5.6, pp. 63–75 (verb template, clitics, SM/TAM/OM/FV); Mchombo 2007, pp. 500–504 (pre-stem morphology and final-vowel constructions); clear finite or dependent verbal paradigm; sentence context.

Confidence: **MEDIUM**; disagreement type: insufficient context; final-vowel issue.

### morph_dev_0181 — chitambasulire

Context:

> Nʼchifukwa chake mkwiyo wa Yehova wayakira anthu ake; watambasula dzanja lake pa anthuwo ndipo akuwakantha Mapiri akugwedezeka, ndipo mitembo ya anthu yangoti mbwee mʼmisewu ngati zinyalala. Komabe ng

Original: `chi+tambasulire`

Provisional: `chi+tambasulire`

Analysis:

- chi → possible class-7/derivational or agreement element
- tambasulire → safest lexical remainder; internal -ir- and final -e are unresolved

Unresolved issue: The source context is noisy and does not establish whether this is a class-7 nominal/qualificative form or a productive applied verbal form. Do not force ta+mba+su or tambasul+ir+e.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **LOW**; disagreement type: lexicalization/root uncertainty; final-vowel issue; noun-class issue; language/quality issue.

### morph_dev_0183 — m’nyumbazo

Context:

> M’zaka za m’ma 1800 madzi akukwera pang’onopang’ono m’nyumbazo, ndi kufika kwa gasi pansanjika zonse.

Original: `m’+nyumba+zo`

Provisional: `m’+nyumba+zo`

Analysis:

- m’ → contracted mu-/m(u)- locative element
- nyumba → class-9/10 lexical noun stem
- zo → class-10 demonstrative/deictic element

Unresolved issue: The noun and demonstrative are clear, but the contracted locative is subject to the locative morphologization dispute.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **MEDIUM**; disagreement type: locative issue.

### morph_dev_0185 — movutika

Context:

> Uwapulumutse amene akutengedwa kuti akaphedwe; uwalanditse amene akuyenda movutika kupita kokaphedwa.

Original: `mo+vutika`

Provisional: `mo+vutika`

Analysis:

- mo → possible locative/adverbial element
- vutika → safest lexical/stative stem “suffer/move with difficulty”

Unresolved issue: Mo- may be a locative/adverbial element, but the lexicalized status of mo-vutika and -ik- is not recoverable from this context alone.

Evidence: Mchombo 2004, ch. 2, pp. 14–31 (locative classes); Bresnan & Mchombo 1995, pp. 239–254 (locatives and lexical integrity); locative/phrase construction in context.

Confidence: **LOW**; disagreement type: locative issue; lexicalization/root uncertainty.

### morph_dev_0196 — ndidzamwenso

Context:

> Ndikuwuzani kuti sindidzamwanso kuchokera ku chipatso cha mtengo wa mpesa kuyambira lero mpaka tsiku ilo pamene ndidzamwenso mwatsopano ndi inu mu ufumu wa Atate anga.”

Original: `ndi+dza+mwe+nso`

Provisional: `ndi+dza+mwe+nso`

Analysis:

- ndi → 1SG subject marker
- dza → future/remote-future TAM
- mwe → surface lexical-stem remainder of “drink”
- nso → post-final “again” clitic

Unresolved issue: The boundary before -nso is strong, but mwe versus mwa is a dialectal/orthographic issue and should not be promoted to a confident final-vowel analysis.

Evidence: Downing & Mtenje 2017, ch. 5, pp. 90–108 (syllable structure and morphophonology); Mchombo 2004, ch. 5 (morpheme order and final-vowel slot); clear lexical paradigm; sentence context.

Confidence: **LOW**; disagreement type: final-vowel issue; post-final/clitic issue; lexicalization/root uncertainty.

## C. Kept items

These current segmentations are compatible with Level B as written. “KEEP” does not mean the original annotation is authoritative; it means no supported change is recommended at this audit stage.

| Item | Surface | Kept segmentation | Confidence |
|---|---|---|---|
| morph_dev_0015 | matchalitchi | `ma+tchalitchi` | HIGH |
| morph_dev_0021 | Matimu | `Ma+timu` | HIGH |
| morph_dev_0023 | Davideyo | `Davide+yo` | HIGH |
| morph_dev_0025 | kuphwanyaphwanya | `ku+phwanya+phwanya` | HIGH |
| morph_dev_0066 | Chiŵerengero | `Chi+ŵerengero` | HIGH |
| morph_dev_0072 | ziŵeto | `zi+ŵeto` | HIGH |
| morph_dev_0075 | lachiŵiri | `la+chi+ŵiri` | HIGH |
| morph_dev_0081 | komanso | `koma+nso` | HIGH |
| morph_dev_0082 | akapolo | `a+kapolo` | HIGH |
| morph_dev_0111 | Chiyambi | `Chi+yambi` | HIGH |
| morph_dev_0116 | wochenjera | `wo+chenjera` | HIGH |
| morph_dev_0121 | winanso | `wina+nso` | HIGH |
| morph_dev_0135 | zoonadi | `zoona+di` | HIGH |
| morph_dev_0159 | ndikumenyeni | `ndi+ku+menye+ni` | HIGH |
| morph_dev_0161 | fupi | `fupi` | HIGH |
| morph_dev_0162 | zosochera | `zo+sochera` | MEDIUM |
| morph_dev_0167 | zimodzimodzizo | `zi+modzi+modzi+zo` | HIGH |
| morph_dev_0178 | makhadi | `ma+khadi` | HIGH |

## D. Excluded items

| Item | Surface | Reason |
|---|---|---|
| morph_dev_0013 | manoma | The token is a team nickname or proper label in an English sports context, not a reliably analyzable Chichewa word. |
| morph_dev_0014 | SantillanaManager | The token is a Spanish personal name followed by an English role label in a lineup dump. |
| morph_dev_0019 | Darussalam | The token is the Malay/Arabic place name Darussalam, not a Chichewa morphological word. |
| morph_dev_0026 | Yekoliya | The token is a biblical personal name, not a reliably analyzable Chichewa word. |
| morph_dev_0031 | Sarisekimu | The token is a biblical/personal name in a proper-name list, not a reliably analyzable Chichewa word. |
| morph_dev_0068 | Khweŵa | The token is identified by the surrounding word list as Tumbuka/Ngoni rather than target-language Chichewa. |
| morph_dev_0077 | Remaliya | The token is a biblical personal name, not a reliably analyzable Chichewa word. |
| morph_dev_0079 | Karl | The token is a personal name in a foreign sports lineup. |
| morph_dev_0080 | Michel | The token is a French personal name in a biographical context. |
| morph_dev_0086 | oral | The token is the English word “oral” in a medical phrase, not a Chichewa lexical item. |
| morph_dev_0096 | Adaliya | The token is a biblical personal name, not a reliably analyzable Chichewa word. |
| morph_dev_0104 | Sergetsev | The token is a Russian personal name in a foreign-language quotation context. |
| morph_dev_0107 | Ngonis | The token is a historical/ethnonymic proper name in a source context, not a reliably analyzable Chichewa word. |
| morph_dev_0110 | observations | The token is the English plural noun “observations” in a technical citation context. |
| morph_dev_0113 | 1871 | The token is a year numeral, not a Chichewa morphological word. |
| morph_dev_0127 | Never | The token is the English word “Never” in a song title, not a Chichewa lexical item. |
| morph_dev_0139 | Ted | The token is the English personal name Ted in a film-production context. |
| morph_dev_0145 | Kde | The token is a Czech-language fragment/name, not a reliably analyzable Chichewa word. |
| morph_dev_0146 | Bogopil | The token is a foreign place name, not a reliably analyzable Chichewa word. |
| morph_dev_0147 | heliometer | The token is the English scientific term “heliometer,” not a Chichewa lexical item. |
| morph_dev_0149 | 325 | The token is a year numeral, not a Chichewa morphological word. |
| morph_dev_0153 | 14,500 | The token is a numeral/measurement, not a Chichewa morphological word. |
| morph_dev_0154 | Gruberová | The token is a Slovak personal name. |
| morph_dev_0164 | Tome | The token is a foreign place-name fragment from Sao Tome. |
| morph_dev_0165 | lawimake | The context appears to contain a corrupted or foreign “law firm” expression; lawimake is not securely Chichewa or morphologically analyzable. |
| morph_dev_0170 | Yoyakini | The token is a biblical personal name. |
| morph_dev_0175 | Koninkrijk | The token is the Dutch word Koninkrijk in a foreign-language place-name expression, not a Chichewa lexical item. |
| morph_dev_0177 | over | The token is the English preposition/adverb “over” in an English citation context. |
| morph_dev_0179 | Kees | The token is a personal name in a foreign sports lineup. |
| morph_dev_0180 | Orinoco | The token is the foreign river name Orinoco. |
| morph_dev_0182 | Also | The token is the English word “Also” in an English citation context, not a Chichewa lexical item. |
| morph_dev_0184 | Iliza | The token is a personal name, not a reliably analyzable Chichewa word. |
| morph_dev_0198 | PVC | The token is the PVC acronym/technical material label, not an analyzable Chichewa word. |

## Evidence and limitations

Evidence was prioritized as Chichewa-specific scholarly grammar, clear paradigms, lexical-family evidence, sentence context, and only then the prior annotation note. Prior human annotations were treated as historical observations, not as authoritative linguistic evidence.

- Mchombo 2004: [official excerpt](https://assets.cambridge.org/052157/3785/excerpt/0521573785_excerpt.pdf), especially chs. 2, 5–7.
- Mchombo 2005/2007: [Argument Structure and Morphology in Chichewa](https://web.stanford.edu/group/cslipublications/cslipublicationsTLS/TLS9-2005/TLS9_Mchombo_Sam.pdf) and [Chichewa (Bantu)](https://www.blackwellpublishing.com/content/BPL_Images/Content_store/WWW_Content/9780631226949/27Chap25.pdf).
- Bresnan & Mchombo 1995: [The Lexical Integrity Principle](https://web.stanford.edu/~bresnan/Bresnan-Mchombo1995_Article_TheLexicalIntegrityPrincipleEv.pdf).
- Hyman & Mchombo 1992: [Morphotactic Constraints in the Chichewa Verb Stem](https://journals.linguisticsociety.org/proceedings/index.php/BLS/article/download/1579/1354/1549).
- Downing & Mtenje 2017: [The Phonology of Chichewa](https://global.oup.com/academic/product/the-phonology-of-chichewa-9780198724742).
- Msaka & Biberauer 2024: [Noun class prefixes are not generally nominalisers](https://www.mmll.cam.ac.uk/files/v16_msaka_biberauer.pdf).

The audit does not alter the active file. Human reviewers should adjudicate especially the locative contractions, lexicalized -ik/-ek and -ir/-er forms, nominalization endings, and noisy/loan items. The JSON and CSV contain the complete item-level record and preserve the original notes and segmentations.

## Final console summary

    active items audited: 195/195
    KEEP: 18
    REVISE: 133
    UNCERTAIN: 11
    EXCLUDE: 33
    automatic annotation changes applied: false
    BPE outputs accessed: false
    Unigram outputs accessed: false
    StatBound outputs accessed: false
    morphology holdout accessed: false
    LM test accessed: false
    scientific tokenizer evaluation run: false

Generated from the active 195 source file without modifying it.
