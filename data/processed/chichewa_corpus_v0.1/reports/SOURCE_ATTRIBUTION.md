# Source attribution — Chichewa Corpus project

**Status:** Required notices for redistributed or adapted text  
**Reviewer:** Hyston Kayange  
**Reviewed at:** 2026-08-05T01:30:00Z  

This document provides **source-specific** attribution. Do not collapse both sources into a single generic credit line.

This is project documentation to support compliance; **it is not legal advice**. Downstream users remain responsible for meeting CC BY-SA 4.0 and source-specific conditions.

---

## 1. Chichewa Wikipedia

**Source ID:** `wikipedia`  
**Project:** Chichewa Wikipedia (`nywiki`) — https://ny.wikipedia.org/  
**Text license:** [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/) (`CC-BY-SA-4.0`)  
**Copyright:** Individual Chichewa Wikipedia contributors retain copyright in their contributions. The Wikimedia Foundation hosts the project and does **not** own all article copyrights.

### Attribution notice

> Text in this corpus that originates from Chichewa Wikipedia was derived from the Chichewa Wikipedia project (https://ny.wikipedia.org/, database `nywiki`). Wikipedia text is available under the Creative Commons Attribution-ShareAlike 4.0 International License (https://creativecommons.org/licenses/by-sa/4.0/). Contributors retain their respective copyrights; see article history pages on Chichewa Wikipedia for contributor lists. This corpus applies offline extraction and Cleaning Policy v2 transforms (line removals and light text transforms). These modifications are not endorsed by the Wikimedia Foundation or the Wikipedia communities. Do not imply endorsement by Wikimedia or Wikipedia.

### Acquisition note

* Stated download artifact: `nywiki-latest-pages-articles.xml.bz2`
* Moving URL used: https://dumps.wikimedia.org/nywiki/latest/nywiki-latest-pages-articles.xml.bz2
* Stated local download date (human-reported): 2026-04-03
* **Limitation:** The original `.bz2` archive is not retained in this repository. An immutable dated dump URL and dump SHA-256 could not be proven from repository artifacts.

### Redistribution conditions (text)

* Attribution as above (or equivalent compliant form)
* License notice and link to CC BY-SA 4.0
* Clear indication of modifications (extraction + cleaning)
* Share-alike for redistributed adaptations of the text
* Commercial reuse is permitted **under the license terms**

### Model weights

Whether trained model weights constitute adapted material under CC BY-SA is an **unresolved legal interpretation**. No claim is made here that weights are or are not share-alike-encumbered.

Full structured record: `data/metadata/source_provenance/wikipedia.json`

---

## 2. Biblica Chichewa Bible

**Source ID:** `bible`  
**Official translation title (provenance only):** Biblica® Tsekulani Mawu a Mulungu mu Chichewa Chalero  
**Abbreviation:** TCCl  
**Language:** Chichewa (Malawi), identifier `nya`  
**Copyright holder:** Biblica, Inc.  
**Copyright notice:** Copyright © 2002, 2016 by Biblica, Inc.  
**Text license:** [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/) (`CC-BY-SA-4.0`)  
**Official source page:** https://ebible.org/details.php?id=nya  
**Download (VPL zip):** https://ebible.org/Scriptures/nya_vpl.zip  
**Source page date:** 2025-05-20  

### Attribution notice (modified / derived text)

> The original Chichewa Bible work by Biblica, Inc. (*Biblica® Tsekulani Mawu a Mulungu mu Chichewa Chalero* / *Open God's Word in Contemporary Chichewa*) is available free from Biblica/open.bible and eBible.org (https://ebible.org/details.php?id=nya). Copyright © 2002, 2016 by Biblica, Inc. Licensed under Creative Commons Attribution-ShareAlike 4.0 International (https://creativecommons.org/licenses/by-sa/4.0/). This corpus contains **extracted and processed** text; formatting, extraction, and cleaning changes were made. These modifications are **not necessarily endorsed** by Biblica, Inc. Because this is a modified/derived research artifact, the **Biblica®** trademark is **not** used as the brand name of *Chichewa Corpus v0.1*. Official derivative attribution wording from the licensor: “The original work by Biblica, Inc. is available for free at www.biblica.com and open.bible.”

### Trademark conditions (must preserve)

From the official eBible/Biblica licensing text (verified against the source page):

* Unmodified redistribution may retain the Biblica® trademark.
* If the text is **modified or adapted**, the Biblica® trademark **must be removed** unless written permission is obtained.
* Modifications must be clearly indicated.
* The original work must be attributed to Biblica, Inc.
* Derivatives must remain available under CC BY-SA 4.0.
* Required copyright and source notices must be preserved.
* No endorsement by Biblica is implied by packaging in this corpus.

### Redistribution conditions (text)

* Attribution and copyright notice as above
* License notice and link to CC BY-SA 4.0
* Modification notice
* Share-alike for redistributed adaptations
* Biblica trademark rules for derivatives (this corpus is treated as modified)
* Commercial reuse is permitted **under the license terms** and trademark conditions

### Model weights

Same unresolved interpretation as for Wikipedia: CC BY-SA treatment of distributed cleaned text does **not** automatically determine the status of trained model weights.

Full structured record: `data/metadata/source_provenance/bible.json`

---

## 3. Existing composite corpus (excluded)

**Source ID:** `existing_corpus`  

Not included in the processed corpus. Residual analysis found **no unique residual lines** after Bible and Wikipedia subtraction (complete line-level containment aside from blanks). This is a **technical** exclusion. Licensing of the underlying Bible and Wikipedia content is handled on those sources, not by re-including the composite file.

Raw artifact retained at `data/raw/existing_corpus/chichewa_corpus.txt` for provenance only.

---

## Combined redistribution summary

| Source | License | Attribution | Share-alike (text adaptations) | In processed corpus |
|--------|---------|:-----------:|:------------------------------:|:-------------------:|
| wikipedia | CC BY-SA 4.0 | required | required | yes |
| bible | CC BY-SA 4.0 | required | required | yes |
| existing_corpus | n/a (composite) | n/a | n/a | **no** |

Processed corpus brand: **Chichewa Corpus v0.1** (not “Biblica® …” and not “Wikipedia”).
