# Prior-art search plan — Mthandizi tokenizer research v0.1

**Rule:** Do **not** fabricate literature references.  
**Rule:** Do **not** call the proposed method “novel” until this review is completed with **verified** sources.  
**Rule:** Empty table rows are intentional until filled from real papers.

---

## 1. Purpose

Map related work on morphology-aware and low-resource tokenization so that:

1. any later method description is positioned accurately;
2. remaining open space is stated carefully;
3. citations are real and checkable.

---

## 2. Search queries (to execute in scholarly indexes)

Run in Google Scholar, Semantic Scholar, ACL Anthology, arXiv, and library catalogs:

| ID | Query |
|----|--------|
| Q1 | morphology-aware tokenization |
| Q2 | morphology-aware subword segmentation |
| Q3 | Bantu language tokenization |
| Q4 | Chichewa OR Nyanja tokenization OR morphology NLP |
| Q5 | low-resource language tokenization |
| Q6 | linguistically informed subword segmentation |
| Q7 | morphology-constrained BPE |
| Q8 | morphology-aware Unigram LM tokenization |
| Q9 | hybrid character-subword models tokenization |
| Q10 | African language tokenization NLP |
| Q11 | agglutinative language tokenization BPE |
| Q12 | vocabulary allocation whole-word memorization subword |
| Q13 | unsupervised morphological segmentation Morfessor |
| Q14 | finite-state morphology tokenization neural LM |
| Q15 | SentencePiece Unigram BPE comparison morphology |

Record for each hit: title, authors, year, venue, URL/DOI, access date.

---

## 3. Inclusion / exclusion

**Include** if the work addresses at least one of:

- subword / morphological segmentation for LM or MT;
- linguistically constrained BPE/Unigram;
- low-resource or agglutinative tokenization;
- evaluation of fertility vs morphological adequacy.

**Exclude** if:

- cannot verify full text or reliable abstract;
- pure linguistic description with no computational method;
- unverifiable blog-only claims without archival version.

---

## 4. Verified reference table (empty until filled)

| paper | year | language | method | baseline | evaluation | main result | similarity to proposed method | remaining novelty space | verified source |
|-------|------|----------|--------|----------|------------|-------------|-------------------------------|-------------------------|-----------------|
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

Copy rows as needed. **verified source** must be DOI, ACL Anthology ID, or arXiv ID checked by a human.

---

## 5. Synthesis checklist (after search)

- [ ] List methods closest to each Phase C design family  
- [ ] Note which languages/families were evaluated  
- [ ] Note whether LM BPC/BPB under matched budgets was used  
- [ ] Note whether human morphological annotation was used  
- [ ] State what is **not** covered by prior work for Chichewa under this lab’s protocol  
- [ ] Update decision log if positioning changes  
- [ ] Only then consider carefully worded contribution statements  

---

## 6. Explicit non-claims (until review completes)

- Not claiming state of the art  
- Not claiming first morphology-aware tokenizer  
- Not claiming Bantu-general applicability  
- Not claiming linguistic correctness of any automatic segmenter  

---

## 7. Related internal artifacts

- Blueprint: `docs/research/MTHANDIZI_TOKENIZER_RESEARCH_BLUEPRINT_v0_1.md`  
- Decision log: `docs/research/MTHANDIZI_TOKENIZER_DECISION_LOG.md`  
- Config: `configs/research/mthandizi_tokenizer_research_v0_1.json`  

---

## 8. Verified-reference ingestion workflow

**Do not fabricate citations. Do not run external searches unless explicitly authorized.**

When a human has verified a paper from a real source, append one JSON object to:

`data/research/prior_art/verified_references_v0_1.jsonl`

(create the directory when first used).

### 8.1 Required fields per record

```json
{
  "reference_id": "ref_0001",
  "doi_or_authoritative_url": "",
  "title": "",
  "authors": [],
  "year": null,
  "venue": "",
  "languages": [],
  "method": "",
  "baselines": [],
  "datasets": [],
  "evaluation_metrics": [],
  "principal_findings": "",
  "similarity_to_design_families": {
    "C1_preseg_unigram_fallback": "",
    "C2_boundary_biased_unigram": "",
    "C3_morphology_constrained_bpe": "",
    "C4_hybrid_affix_stem_allocation": "",
    "C5_stat_affix_char_fallback": "",
    "C6_whole_word_regularization": "",
    "C7_family_consistency": "",
    "C8_stochastic_segmentation": "",
    "C9_char_byte_fallback": ""
  },
  "remaining_uncertainty": "",
  "verification_date": "",
  "verified_by": "",
  "notes": ""
}
```

### 8.2 Process

1. Obtain full citation from DOI, ACL Anthology, or arXiv (human).  
2. Fill the template; leave unknown fields empty/`null`, never invent.  
3. Set `verification_date` (UTC) and `verified_by`.  
4. Map similarity to each Phase C design family in one careful sentence or `n/a`.  
5. Optionally mirror a row into the markdown table in §4.  
6. Log material positioning changes in the decision log.  

### 8.3 Empty store marker

Until the first verified reference exists, the ingestion file may be absent.  
Absence means **zero verified references**, not “no related work in the world.”

### 8.4 CSV companion template

`data/research/prior_art/verified_references_template.csv` provides spreadsheet columns matching the JSON fields for offline note-taking before JSONL commit.
